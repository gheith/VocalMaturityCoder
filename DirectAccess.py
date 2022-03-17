"""
Direct Access

A script that contains functionality with direct access to the DB. This would help in perform admin operations without
going through the GUI, or waiting for features to be deployed.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"

import csv
import attr
from typing import List
from datetime import datetime
from os.path import join, dirname, abspath
from enum import Enum
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import logging
from logging.config import fileConfig
from logging.handlers import TimedRotatingFileHandler

from Crypto.Cipher import AES
from DataAccess.DatabaseLoggingHandler import DatabaseLoggingHandler
from DataAccess.UserRepository import UserRepository
from DataAccess.RecordingRepository import RecordingRepository
from DataAccess.UtteranceRepository import UtteranceRepository
from Models.UtteranceCodeConsensusModel import UtteranceCodeConsensusModel

from VmcLoader import getConnectionInformation, ConnectionType, DataFolder


class UserType(Enum):
    SystemAdministrator = 200
    Professor = 300
    LabStaff = 400
    GraduateStudent = 500
    UndergraduateStudent = 600


def getNextSample(dbSession: Session, userID: int) -> None:
    """
    Gets the next available sample to code.
    """
    UtteranceRepository.DbSession = dbSession

    repository = UtteranceRepository()

    try:
        user = repository.getSampleForUser(userID)
        print(f"Obtained row {user.UtteranceSamplePoolID}.")
    except Exception as ex:
        print(f"An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


def addNewUser(dbSession: Session, userName: str, password: str, firstName: str, middleName: str, lastName: str, email: str, userType: UserType):
    """
    Add the new user to the system.
    """
    # Check if any parameter, except middleName, is empty.
    if any(len(field) == 0 for field in [userName, password, firstName, lastName, email]):
        print("One or more required values passed are empty. User has not been added.")
        return

    UserRepository.DbSession = dbSession
    repository = UserRepository()

    try:
        repository.addNewUser(userName=userName,
                              password=password,
                              firstName=firstName,
                              middleName=middleName,
                              lastName=lastName,
                              email=email,
                              userType=userType.value
        )

        repository.commitChanges()

        print(f'User "{firstName} {lastName}" added successfully.')

    except Exception as ex:
        print(f"An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


def updatePassword(dbSession: Session, userName: str, password: str) -> None:
    """
    Updates the password for the given user.
    """
    UserRepository.DbSession = dbSession

    repository = UserRepository()

    try:
        user = repository.getByUserName(userName)
        user.NewPassword = password
        user.IsActive = True

        repository.updateUser(user)

        repository.commitChanges()

    except Exception as ex:
        print(f"An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


def checkUserWithPassword(dbSession: Session, userName: str, password: str) -> None:
    """
    Updates the password for the given user.
    """
    UserRepository.DbSession = dbSession

    repository = UserRepository()

    try:
        isValid = repository.checkForUser(userName, password)
        print(f"Is the password correct? The answer is: {isValid}")
    except Exception as ex:
        print(f"An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


def createNewRecordingBatch(dbSession: Session, key: bytes, recordingsFolderPath: str, assessmentIDs: List[str]) -> None:
    """
    For the assessment ID passed, that is already in the DB, create a new Batch assignment, then create utterance
    samples to be coded via populating the SamplePool table.
    """
    RecordingRepository.DbSession = dbSession
    UtteranceRepository.DbSession = dbSession

    rRepository = RecordingRepository()
    uRepository = UtteranceRepository()

    try:

        group = rRepository.addNewCodingBatch(assessmentIDs)

        if group is None:
            return

        for assessmentID in assessmentIDs:
            isSuccessful = rRepository.selectSegmentsFor(assessmentID)
            print(f"Segments for '{assessmentID}' Selected Successfully: {isSuccessful}")

            if not isSuccessful:
                raise ValueError("Could NOT perform segment selection.")

            isSuccessful = rRepository.selectUtterancesFor(recordingsFolderPath, key, assessmentID)
            print(f"Utterances for '{assessmentID}' Extracted from Audio Successfully: {isSuccessful}\n")

        uRepository.addUtterancesToSamplePool(group)

        print(f"Committing Utterance Samples for Group {group}\n")
        dbSession.commit()

    except Exception as ex:
        print(f"An Exception occurred: {ex.args}\n\nRolling Back.")
        dbSession.rollback()
    finally:
        rRepository.endDbSession()


def generateCodingReport(dbSession: Session) -> List[UtteranceCodeConsensusModel]:
    """
    Generates an information report of utterances of all completed recordings. The report includes utterance metadata,
    and their coding information.
    """
    UtteranceRepository.DbSession = dbSession

    repository = UtteranceRepository()

    try:
        consensusReport = repository.generateUtteranceReport()
        return consensusReport
    except Exception as ex:
        print(f"Unable to generate consensus report. An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


def saveUtteranceCodingReport(filePath: str, consensusReport: List[UtteranceCodeConsensusModel]) -> None:
    """
    Saves the list of utterances, along with their aggregate data, to a csv file.
    """
    # Modify the field names for better readability.
    header = ["UtteranceID",
              "AssessmentID",
              "RecordingDate",
              "ChildID",
              "ChildSex",
              "ChildDOB",
              "AgeAtRecording (Months)",
              "ParticipantGroup (Risk)",
              "SegmentID",
              "SelectionCriterion",
              "StartTime (Seconds)",
              "EndTime (Seconds)",
              "Duration (Seconds)",
              "MinPitch (Hz)",
              "MaxPitch (Hz)",
              "AveragePitch (Hz)",
              "PitchRange (Hz)",

              "TotalSyllables (Consensus)",
              "TotalSyllables (%Agree)",
              "TotalSyllables (Average)",

              "CanonicalSyllables (Consensus)",
              "CanonicalSyllables (%Agree)",
              "CanonicalSyllables (Average)",

              "NonCanonicalSyllables (Consensus)",
              "NonCanonicalSyllables (%Agree)",
              "NonCanonicalSyllables (Average)",

              "WordSyllables (Consensus)",
              "WordSyllables (%Agree)",
              "WordSyllables (Average)",

              "Words (Consensus)",
              "Words (%Agree)",
              "Words (Average)",

              "Speech (Consensus)",
              "Speech (%Agree)",

              "Maturity (Consensus)",
              "Maturity (%Agree)",
    ]

    with open(filePath, 'w', newline='') as reportFile:
        writer = csv.writer(reportFile)
        writer.writerow(header)

        for utterance in consensusReport:
            row = [v if v is not None else "None" for v in attr.astuple(utterance)]
            writer.writerow(row)


def getUtteranceAudioByID(dbSession: Session, key: bytes, targetFolder: str, utteranceID: int) -> None:
    """
    Gets an utterance audio, and saves it in the desired location.
    """
    UtteranceRepository.DbSession = dbSession

    repository = UtteranceRepository()

    try:
        utterance = repository.getUtteranceAudioByID(utteranceID)

        if not utterance:
            print(f"No utterance found for ID: {utteranceID}")
            return

        # Save audio file.
        audioPath = join(targetFolder, f"{utteranceID:05d}_{utterance.AudioFileName}")

        with open(audioPath, "wb") as audioFile:
            encryptedData = utterance.AudioFileData
            nonce = encryptedData[:16]
            encryptedAudio = encryptedData[16:]
            cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
            audioBytes = cipher.decrypt(encryptedAudio)
            audioFile.write(audioBytes)

    except Exception as ex:
        print(f"An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


def getCodingRateOfUsers(dbSession: Session, startDateString: str, endDateString: str) -> None:
    """
    Calculates and returns the coding rate of users, within the given dates.
    """
    UtteranceRepository.DbSession = dbSession

    repository = UtteranceRepository()

    try:
        startingDate = datetime.strptime(startDateString, '%Y-%m-%d') if startDateString else None
        endingDate = datetime.strptime(endDateString, '%Y-%m-%d') if endDateString else None

        title = f'Coding Rate Report Create On {datetime.now():%m/%d/%Y  %I:%M:%S %p}'
        header1 = ' Coder Name         |   Codes  | Sessions |    Coding Rate (Codes/Hour)    '
        header2 = '                                          |  Minimum |  Maximum | Average  '
        sDate = startDateString if startDateString else '2020-01-01'
        eDate = endDateString if endDateString else f'{datetime.now():%Y-%m-%d}'
        dateRange = f'    Start Date = {sDate:>11}, End Date = {eDate:>11}'
        separator = '-' * 80
        reportLines = [separator, title, dateRange, separator, header1, header2, separator]

        rateMap = repository.getCodingRateOfUsers(startingDate, endingDate)
        for (firstName, lastName), userRate in rateMap.items():
            userName = f'{firstName} {lastName}'
            codeCount = sum([cCount for _, cCount in userRate])
            rates = [cCount / (duration.total_seconds() / 3600) for duration, cCount in userRate if cCount > 1]
            avgRate = sum(rates) / len(rates)

            line = f'{userName:<20}|{codeCount: 10d}|{len(userRate): 10d}|{min(rates): 9.2f} |{max(rates): 9.2f} |{avgRate: 9.2f} '

            reportLines.append(line)

        # Print Result.
        reportLines.append(separator)
        print("\n".join(reportLines))
    except Exception as ex:
        print(f"An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


def getCodingTimestampsOfUsers(dbSession: Session, startDateString: str, endDateString: str, filePath) -> None:
    """
    Returns the non-legacy codes and their timestamps.
    """
    UtteranceRepository.DbSession = dbSession

    repository = UtteranceRepository()

    try:
        startingDate = datetime.strptime(startDateString, '%Y-%m-%d') if startDateString else None
        endingDate = datetime.strptime(endDateString, '%Y-%m-%d') if endDateString else None

        codingReport = repository.getCodingRateOfUsers(startingDate, endingDate, performAggregation=False)
        header = ["FirstName", "LastName", "UserID", "UtteranceID", "AddedOn"]
        with open(filePath, 'w', newline='') as reportFile:
            writer = csv.writer(reportFile)
            writer.writerow(header)

            for entry in codingReport:
                writer.writerow(entry)

    except Exception as ex:
        print(f"An Exception occurred: {ex.args}")
    finally:
        repository.endDbSession()


if __name__ == "__main__":

    print(f"Starting @ {datetime.now()} ... \n")

    cType = ConnectionType.Production
    connectionStr, encKey = getConnectionInformation(cType)

    engine = create_engine(connectionStr, isolation_level="READ_COMMITTED")
    SessionMaker = sessionmaker(bind=engine, expire_on_commit=False)
    DatabaseLoggingHandler.DbSession = SessionMaker()

    configFilePath = join(dirname(abspath(__file__)), 'log.config')
    fileConfig(configFilePath)
    logger = logging.getLogger()

    # This code will help identify the machine & the log file location.
    if type(logger.handlers[0]) is TimedRotatingFileHandler:
        logFilePath = logger.handlers[0].baseFilename
        message = f'Logging to: "{logFilePath}"\n'
        print(message)
        logger.info(message, extra={"UserID": 0, "SessionID": 0})

    # Set these to start a task.
    localSession = SessionMaker()

    # ################################################################################################################
    # Below are the set of tasks that can be performs using this file. Uncomment ONLY one task.
    # ################################################################################################################

    # # Task: Add a new user to the database.
    # # ###########################################

    # userName = ""       # This is the career account of the user, e.g. "agheith"
    # password = ""       # This should be a four digit to be simple to remember, e.g. "9546".
    # firstName = ""
    # middleName = ""     # If no middle name is available, leave empty.
    # lastName = ""
    # email = ""          # The full purdue email, e.g. "agheith@purdue.edu"
    #
    # # This can be anyone of the options: UndergraduateStudent, GraduateStudent, LabStaff, Professor, SystemAdministrator
    # userType = UserType.UndergraduateStudent
    #
    # addNewUser(localSession, userName, password, firstName, middleName, lastName, email, userType)

    # # Task: Update Password for an existing user.
    # # ###########################################

    # # User name and password are both strings, i.e. enclosed in single or double quotes.
    # userName = ""       # This is the career account of the user, e.g. "agheith"
    # password = ""       # This should be a four digit to be simple to remember, e.g. "9546".
    #
    # updatePassword(localSession, userName, password)

    # # Task: Get an Utterance audio
    # # ###########################################

    # # Create a file that contains Utterance IDs to extract. The text file must have one ID per line,
    # # with no additional commas or any empty lines.
    # utteranceListFilePath = r""
    #
    # # Create an empty folder to save all utterance audio files in.
    # targetLocation = r""
    #
    # with open(utteranceListFilePath, "r") as uFile:
    #     targetIDs = [int(u) for u in uFile.read().splitlines()]
    #
    # for uID in targetIDs:
    #     getUtteranceAudioByID(localSession, encKey, targetLocation, uID)

    # Task: Create a new batch.
    # ###########################################

    # IDs = ['5651_5', '5811_1']
    # createNewRecordingBatch(localSession, encKey, DataFolder, IDs)

    # # Task: Generate Utterance Consensus Report.
    # # ###########################################
    #
    # reportFilePath = r""
    # report = generateCodingReport(localSession)
    # if not report:
    #     raise ValueError("Report is not present.")
    # saveUtteranceCodingReport(reportFilePath, report)

    # # Task: Get Coding Timestamps.
    # # ###########################################
    #
    # reportFilePath = r""
    #
    # # These date should be formatted as YYYY-MM-DD, e.g. 2020-01-01, or be left empty, as ''.
    # startDate = '2020-08-01'
    # endDate = ''
    #
    # getCodingTimestampsOfUsers(localSession, startDate, endDate, reportFilePath)

    # # Task: Generate Coding Rate Report.
    # # ###########################################
    #
    # # These date should be formatted as YYYY-MM-DD, e.g. 2020-01-01, or be left empty, as ''.
    # startDate = '2020-08-01'
    # endDate = ''
    #
    # getCodingRateOfUsers(localSession, startDate, endDate)

    print()
    print(f"End @ {datetime.now()} ... \n")
