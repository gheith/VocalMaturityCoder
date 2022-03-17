"""
DataImporter

A script to do a single time import of legacy coding data. For this process, if the table is NOT empty, the process
will not perform any insertions, as we do need to do additional checks.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


import re
import os
import time
from os.path import join
from datetime import datetime, timedelta, date
from typing import List, Tuple
from csv import DictReader
from collections import Counter

from VmcLoader import getConnectionInformation, ConnectionType

from Crypto.Cipher import AES
from pydub import AudioSegment
from DataAccess.BaseDB import *
from sqlalchemy.orm.session import Session
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker


# The location of the initial setup files.
baseFolder = r""


def getDuration(spanStr: str) -> timedelta:
    """
    Parses a cell in the row that may contain an integer (for number of seconds,) or an interval.
    """

    span = spanStr
    if not span:
        return timedelta()

    m = re.match(r"(\d{1,2}):(\d{2}):(\d{2})", span)

    if m:
        return timedelta(hours=int(m[1]), minutes=int(m[2]), seconds=int(m[3]))

    return timedelta(seconds=int(span))


def getInteger(intStr: str) -> int:
    """
    Tries to parse an integer, and returns 0 if parsing did not work.
    """
    try:
        value = int(intStr)
        return value
    except ValueError:
        return 0


def getDateTime(dateTime: str) -> datetime:
    """
    Tries to parse a date time string in one of two formats.
    """
    format1 = "%m/%d/%y  %I:%M:%S %p"
    format2 = "%m/%d/%Y  %I:%M:%S %p"
    format3 = "%m/%d/%y  %H:%M"
    format4 = "%Y-%m-%d  %H:%M"

    try:
        value = datetime.strptime(dateTime, format1)
        return value
    except ValueError:
        pass

    try:
        value = datetime.strptime(dateTime, format2)
        return value
    except ValueError:
        pass

    try:
        value = datetime.strptime(dateTime, format3)
        return value
    except ValueError:
        pass

    try:
        value = datetime.strptime(dateTime, format4)
        return value
    except ValueError:
        pass


def getExclusions(exclusionDate: date, durationText: str) -> List[Tuple[datetime, datetime]]:
    """
    Parses the given string for one or more time intervals, represented by their start and end times.
    """

    dateFormat = "%I:%M %p"
    durations = durationText.split(",")

    intervals = []
    for duration in durations:

        start, end = duration.split("-")

        startTime = datetime.strptime(start.strip(), dateFormat)
        endTime = datetime.strptime(end.strip(), dateFormat)

        startDateTime = datetime.combine(exclusionDate, startTime.time())
        endDateTime = datetime.combine(exclusionDate, endTime.time())

        intervals.append((startDateTime, endDateTime))

    return intervals


def loadSourceDataFile(filePath: str) -> List[dict]:
    """
    Reads the CSV file from the path given, and returns a list of rows, as ordered dictionaries, as defined by the
    Python CSV module.

    :param filePath: Full path for the CSV file.
    :return: Rows as Ordered Dictionaries.
    """

    rows = []

    with open(filePath, "r") as csvFile:
        reader = DictReader(csvFile)

        for row in reader:
            resultMap = {}

            for k, v in row.items():

                if k is None:
                    continue

                resultMap[k.strip()] = v.strip() if v.strip() else None

            rows.append(resultMap)

    return rows


def insertBasicTables(dbSession: Session) -> None:
    """
    Loads the tables in the database that have very few columns, and do NOT change frequently.
    """

    # DataUseOption:
    # --------------
    current = dbSession.query(DataUseOption).all()

    if len(current) == 0:
        filePath = join(baseFolder, "DataUseOption.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns: ID, ConsentOptionNumber, Description
        for row in rows:
            entry = DataUseOption(
                DataUseOptionID=row["ID"],
                ConsentOptionNumber=row["ConsentOptionNumber"],
                Description=row["Description"],
            )
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'DataUseOption' is complete.")

    # ErrorCode:
    # --------------
    current = dbSession.query(ErrorCode).all()

    if len(current) == 0:
        filePath = join(baseFolder, "ErrorCode.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID, Symbol, Description
        for row in rows:
            entry = ErrorCode(ErrorCodeID=row["ID"], Symbol=row["Symbol"], Description=row["Description"],)
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'ErrorCode' is complete.")

    # ExclusionType
    # --------------
    current = dbSession.query(ExclusionType).all()

    if len(current) == 0:
        filePath = join(baseFolder, "ExclusionType.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID,Description
        for row in rows:
            entry = ExclusionType(ExclusionTypeID=row["ID"], Description=row["Description"])
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'ExclusionType' is complete.")

    # GeneticRisk
    # --------------
    current = dbSession.query(GeneticRisk).all()

    if len(current) == 0:
        filePath = join(baseFolder, "GeneticRisk.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID,Description
        for row in rows:
            entry = GeneticRisk(GeneticRiskID=row["ID"], Description=row["Description"])
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'GeneticRisk' is complete.")

    # RecordingType
    # --------------
    current = dbSession.query(RecordingType).all()

    if len(current) == 0:
        filePath = join(baseFolder, "RecordingType.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID,Description
        for row in rows:
            entry = RecordingType(RecordingTypeID=row["ID"], Description=row["Description"])
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'RecordingType' is complete.")

    # SelectionCriterion
    # --------------
    current = dbSession.query(SelectionCriterion).all()

    if len(current) == 0:
        filePath = join(baseFolder, "SelectionCriterion.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID, Description, Symbol
        for row in rows:
            entry = SelectionCriterion(
                SelectionCriterionID=row["ID"], Description=row["Description"], Symbol=row["Symbol"],
            )
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'SelectionCriterion' is complete.")

    # Sex
    # --------------
    current = dbSession.query(Sex).all()

    if len(current) == 0:
        filePath = join(baseFolder, "Sex.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID, Description
        for row in rows:
            entry = Sex(SexID=row["ID"], Description=row["Description"])
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'Sex' is complete.")

    # UserType
    # --------------
    current = dbSession.query(UserType).all()

    if len(current) == 0:
        filePath = join(baseFolder, "UserType.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID, Description
        for row in rows:
            entry = UserType(UserTypeID=row["ID"], Description=row["Description"])
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'UserType' is complete.")

    # UtteranceType
    # --------------
    current = dbSession.query(UtteranceType).all()

    if len(current) == 0:
        filePath = join(baseFolder, "UtteranceType.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID, Description
        for row in rows:
            entry = UtteranceType(UtteranceTypeID=row["ID"], Description=row["Description"])
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'UtteranceType' is complete.")

    # UtteranceTypeAnnotation
    # ------------------------
    current = dbSession.query(UtteranceTypeAnnotation).all()

    if len(current) == 0:
        filePath = join(baseFolder, "UtteranceTypeAnnotation.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID, UtteranceTypeID, Description
        for row in rows:
            entry = UtteranceTypeAnnotation(
                UtteranceTypeAnnotationID=row["ID"],
                UtteranceTypeID=row["UtteranceTypeID"],
                Description=row["Description"],
            )
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'UtteranceTypeAnnotation' is complete.")

    # User
    # ------------------------
    current = dbSession.query(User).all()

    if len(current) == 0:
        filePath = join(baseFolder, "User.csv")
        rows = loadSourceDataFile(filePath)

        # CSV Columns - ID, UserName, Password, FirstName, MiddleName, LastName, Email, UserTypeID, IsActive, IsAdmin
        for row in rows:
            entry = User(
                UserID=row["ID"],
                UserName=row["UserName"],
                Password=row["Password"],
                FirstName=row["FirstName"],
                MiddleName=(row["MiddleName"] if row["MiddleName"] else None),
                LastName=row["LastName"],
                Email=row["Email"],
                UserTypeID=row["UserTypeID"],
                IsActive=(row["IsActive"] == "1"),
                IsAdmin=(row["IsAdmin"] == "1"),
            )
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'User' is complete.")

    # Participant
    # ------------------------
    current = dbSession.query(Participant).all()

    if len(current) == 0:
        filePath = join(baseFolder, "Participant.csv")
        rows = loadSourceDataFile(filePath)

        sexMap = {record.Description: record.SexID for record in dbSession.query(Sex).all()}
        riskMap = {record.Description: record.GeneticRiskID for record in dbSession.query(GeneticRisk).all()}

        # CSV Columns - ChildID, Sex, DateOfBirth, GeneticRisk
        for row in rows:
            entry = Participant(
                DateOfBirth=row["DateOfBirth"],
                ChildID=row["ChildID"],
                SexID=sexMap[row["Sex"]],
                GeneticRiskID=riskMap[row["GeneticRisk"]],
            )
            dbSession.add(entry)

        dbSession.commit()
        print("Loading table 'Participant' is complete.")


def insertRecordingTables(dbSession: Session) -> None:
    """
    Loads the Recording, ExclusionDuration, DayTypicality, CodingBatch and InterpretiveTimeSegment
    tables in the database.
    """

    # Recording
    # ------------------------
    current = dbSession.query(Recording).all()

    if len(current) != 0:
        return

    filePath = join(baseFolder, "Recording.csv")
    rows = loadSourceDataFile(filePath)

    errorCodeMap = {record.Symbol: record.ErrorCodeID for record in dbSession.query(ErrorCode).all()}
    dataUseOptionMap = {
        record.ConsentOptionNumber: record.DataUseOptionID for record in dbSession.query(DataUseOption).all()
    }
    recordingTypeMap = {record.Description: record.RecordingTypeID for record in dbSession.query(RecordingType).all()}
    participantMap = {record.ChildID: record.ParticipantID for record in dbSession.query(Participant).all()}
    userMap = {record.UserName: record.UserID for record in dbSession.query(User).all()}

    for row in rows:

        # Note: This is a temporary flag in the data. It should be removed once the initial data set has all been
        # verified to be valid.
        if row["Skip"]:
            continue
        # print(f'Starting row {row["Index"]}')

        parseIf = lambda fn, name: fn(row[name]) if row[name] else None

        recordingTypeID = recordingTypeMap[row["RecordingType"]]
        participantID = participantMap[row["ChildID"]]
        assessmentID = row["AssessmentID"]
        recordingDate = row["RecordingDate"]
        ageAtRecordingInMonths = row["AgeAtRecordingInMonths"]
        baseFileName = row["BaseFileName"]

        match = re.match(r"(?P<DateTime>.+)\s\(.+\)", row["StartTime"])
        startTime = getDateTime(match["DateTime"])

        match = re.match(r"(?P<DateTime>.+)\s\(.+\)", row["EndTime"])
        endTime = getDateTime(match["DateTime"])

        if row["ChildWakeTime"]:

            childWakeTime = datetime.strptime(row["ChildWakeTime"], "%I:%M").time()
            entryDate = datetime.strptime(recordingDate, "%m/%d/%Y").date()

            childWakeTimestamp = datetime.combine(entryDate, childWakeTime)
        else:
            childWakeTimestamp = None

        errorCodeID = errorCodeMap[row["ErrorCode"]] if row["ErrorCode"] else None
        consentFormVersion = parseIf(int, "ConsentFormVersion")

        childWordCount = parseIf(int, "ChildWordCount")

        if row["HasPhrases"]:
            hasPhrases = row["HasPhrases"].lower() == "yes"
        else:
            hasPhrases = None

        dataUseOptionID = dataUseOptionMap[int(row["DataUseOption"])] if row["DataUseOption"] else None

        adultWordCount = parseIf(int, "AdultWordCount")
        adultWordCountPercentile = parseIf(float, "AdultWordCountPercentile")
        adultWordCountStandardScore = parseIf(float, "AdultWordCountStandardScore")
        conversationalTurnCount = parseIf(int, "ConversationalTurnCount")
        conversationalTurnPercentile = parseIf(float, "ConversationalTurnPercentile")
        conversationalTurnStandardScore = parseIf(float, "ConversationalTurnStandardScore")
        childVocalizationCount = parseIf(int, "ChildVocalizationCount")
        childVocalizationPercentile = parseIf(float, "ChildVocalizationPercentile")
        childVocalizationStandardScore = parseIf(float, "ChildVocalizationStandardScore")
        automatedVocalizationAssessmentPercentile = parseIf(float, "AutomatedVocalizationAssessmentPercentile")
        automatedVocalizationAssessmentStandardScore = parseIf(float, "AutomatedVocalizationAssessmentStandardScore")
        vocalProductivityPercentile = parseIf(float, "VocalProductivityPercentile")
        vocalProductivityStandardScore = parseIf(float, "VocalProductivityStandardScore")
        timeZone = row["TimeZone"]

        notes = ""
        if row["RecordingNotes"]:
            notes += f"RecordingNotes:\n{row['RecordingNotes']}\n\n"
        if row["ScrubSheetNotes"]:
            notes += f"ScrubSheetNotes:\n{row['ScrubSheetNotes']}\n\n"
        notes = notes if notes else None

        isScrubbed = row["IsScrubbed"] == "1"
        isValid = row["IsValid"] == "1"

        entry = Recording(
            RecordingTypeID=recordingTypeID,
            ParticipantID=participantID,
            AssessmentID=assessmentID,
            RecordingDate=recordingDate,
            AgeAtRecordingInMonths=ageAtRecordingInMonths,
            BaseFileName=baseFileName,
            StartTime=startTime,
            EndTime=endTime,
            ChildWakeTime=childWakeTimestamp,
            Duration=endTime - startTime,
            ErrorCodeID=errorCodeID,
            ConsentFormVersion=consentFormVersion,
            ChildWordCount=childWordCount,
            HasPhrases=hasPhrases,
            DataUseOptionID=dataUseOptionID,
            AdultWordCount=adultWordCount,
            AdultWordCountPercentile=adultWordCountPercentile,
            AdultWordCountStandardScore=adultWordCountStandardScore,
            ConversationalTurnCount=conversationalTurnCount,
            ConversationalTurnPercentile=conversationalTurnPercentile,
            ConversationalTurnStandardScore=conversationalTurnStandardScore,
            ChildVocalizationCount=childVocalizationCount,
            ChildVocalizationPercentile=childVocalizationPercentile,
            ChildVocalizationStandardScore=childVocalizationStandardScore,
            AutomatedVocalizationAssessmentPercentile=automatedVocalizationAssessmentPercentile,
            AutomatedVocalizationAssessmentStandardScore=automatedVocalizationAssessmentStandardScore,
            VocalProductivityPercentile=vocalProductivityPercentile,
            VocalProductivityStandardScore=vocalProductivityStandardScore,
            Meaningful=getDuration(row["Meaningful"]),
            Silence=getDuration(row["Silence"]),
            Electronic=getDuration(row["Electronic"]),
            Distant=getDuration(row["Distant"]),
            Noise=getDuration(row["Noise"]),
            Overlap=getDuration(row["Overlap"]),
            TimeZone=timeZone,
            Notes=notes,
            IsScrubbed=isScrubbed,
            IsValid=isValid,
        )

        dbSession.add(entry)

        insertItsFiles(dbSession, entry)

        insertExclusionTable(dbSession, entry, row)

        # Day Typicality
        # --------------
        typicalities = [
            (row["DayTypicalityPercentage1"], row["FirstEntry"]),
            (row["DayTypicalityPercentage2"], row["SecondEntry"]),
            (row["DayTypicalityPercentage3"], row["ThirdEntry"]),
        ]

        for percent, userName in typicalities:
            if not percent:
                continue

            typicality = DayTypicality(Recording=entry, AddedBy=userMap[userName], TypicalityPercentage=int(percent),)
            dbSession.add(typicality)

    dbSession.commit()

    print("Loading table 'Recording' is complete.")
    print("Loading table 'DayTypicality' is complete.")
    print("Loading table 'ExclusionDuration' is complete.")
    print("Loading table 'InterpretiveTimeSegment' is complete.")


def insertItsFiles(dbSession: Session, recording: Recording) -> None:
    """
    Inserts the ITS Data associated with the current recording.
    """

    # InterpretiveTimeSegment
    # -----------------------
    baseItsFolder = r"D:\Temp\VMC ITS Files"
    # # ITS String File
    # # --------------------------------------------------------------
    # itsFilePath = join(baseItsFolder, f"{baseFileName}.its")
    #
    # with open(itsFilePath, "r") as itsFile:
    #     itsBytes = itsFile.read().encode("UTF-8")
    #
    # itsSmall = lzma.compress(itsBytes, preset=9 | lzma.PRESET_EXTREME)
    # before = len(itsBytes)
    # after = len(itsSmall)
    # ratio = round(after / before * 100, 2)
    #
    # totalSize += after
    # now = datetime.strftime(datetime.now(), "%I:%M:%S %p")
    #
    # print(f'{now}:    ITS File "{baseFileName}.its" {before:,} => {after:,}. Ratio = {ratio}%')
    # Compressed ITS File.
    # --------------------------------------
    datFilePath = join(baseItsFolder, f"{recording.BaseFileName}.dat")

    with open(datFilePath, "br") as itsFile:
        itsSmall = itsFile.read()

    itsEntry = InterpretiveTimeSegment(Recording=recording, FileData=itsSmall)

    dbSession.add(itsEntry)


def insertExclusionTable(dbSession: Session, recording: Recording, row: dict) -> None:
    """
    Inserts the exclusion times associated with the current recording.
    """

    # Exclusions.
    # -----------
    exclusionMap = {record.Description: record.ExclusionTypeID for record in dbSession.query(ExclusionType).all()}
    entryDate = datetime.strptime(recording.RecordingDate, "%m/%d/%Y")

    if row["NapTimes"]:
        napTimes = getExclusions(entryDate, row["NapTimes"])
        for startTime, endTime in napTimes:
            exclusion = ExclusionDuration(
                Recording=recording,
                ExclusionTypeID=exclusionMap["Nap Time"],
                StartTime=startTime,
                EndTime=endTime,
                Duration=endTime - startTime,
            )

            dbSession.add(exclusion)

    if row["ScrubTimes"]:
        scrubTimes = getExclusions(entryDate, row["ScrubTimes"])

        for startTime, endTime in scrubTimes:

            exclusion = ExclusionDuration(
                Recording=recording,
                ExclusionTypeID=exclusionMap["Scrub Time"],
                StartTime=startTime,
                EndTime=endTime,
                Duration=endTime - startTime,
            )

            dbSession.add(exclusion)


def insertBatchTable(dbSession: Session) -> None:
    """
    Inserts the information about Recording grouping, referred to as a CodingBatch.
    """

    # CodingBatch
    # ------------------------
    current = dbSession.query(CodingBatch).all()

    if len(current) != 0:
        return

    filePath = join(baseFolder, "CodingBatch.csv")
    rows = loadSourceDataFile(filePath)

    recordingTypeMap = {record.Description: record.RecordingTypeID for record in dbSession.query(RecordingType).all()}

    recordingMap = {
        (record.AssessmentID, record.RecordingTypeID): record.RecordingID for record in dbSession.query(Recording).all()
    }

    allAsmtIDs = {record.AssessmentID for record in dbSession.query(Recording).all()}

    # CSV Columns - Group, AssessmentID, RecordingType
    for row in rows:
        rType = recordingTypeMap[row["RecordingType"]]
        asmtID = row["AssessmentID"]

        key = (asmtID, rType)
        if key not in recordingMap:
            print(f'Cannot Insert Group = {row["Group"]}, Assessment ID = {asmtID}, IsPresent = {asmtID in allAsmtIDs}')
            continue

        entry = CodingBatch(RecordingID=recordingMap[(asmtID, rType)], Group=int(row["Group"]))
        dbSession.add(entry)

    dbSession.commit()

    print("Loading table 'CodingBatch' is complete.")


def insertSegmentTable(dbSession: Session) -> None:
    """
    Inserts the CSV file information into the Segment Table.
    """

    baseCsvFolder = r"D:\Temp\VMC Segment Files"
    recordings = dbSession.query(Recording).all()
    current = dbSession.query(Segment).all()

    if len(current) != 0:
        return

    for recording in recordings:

        csvFilePath = join(baseCsvFolder, f"{recording.BaseFileName}.csv")
        rows = loadSourceDataFile(csvFilePath)

        recordingStartTime = recording.StartTime

        print(csvFilePath)

        # Identify File Style.
        if "Timestamp" in rows[0]:

            for rowIndex, row in enumerate(rows):

                timestamp = getDateTime(row["Timestamp"])
                duration = getDuration(row["Duration"])

                if rowIndex == 0:
                    startTime = timestamp + timedelta(minutes=5) - duration
                    endTime = timestamp + timedelta(minutes=5)
                elif rowIndex == len(rows) - 1:
                    startTime = timestamp
                    endTime = timestamp + duration
                else:
                    startTime = timestamp
                    endTime = timestamp + timedelta(minutes=5)
                    duration = timedelta(minutes=5)

                # print(f"Timestamp:  Start = {startTime}, End = {endTime}, Duration = {duration}")
                segment = Segment(
                    RecordingID=recording.RecordingID,
                    StartTime=startTime,
                    EndTime=endTime,
                    StartTimeInSeconds=(startTime - recordingStartTime).total_seconds(),
                    EndTimeInSeconds=(endTime - recordingStartTime).total_seconds(),
                    Duration=duration,
                    AdultWordCount=getInteger(row["AWC.Actual"]),
                    ConversationalTurnCount=getInteger(row["CTC.Actual"]),
                    ChildVocalizationCount=getInteger(row["CVC.Actual"]),
                    Meaningful=getDuration(row["Meaningful"]),
                    Silence=getDuration(row["Silence"]),
                    Electronic=getDuration(row["TV"]),
                    Distant=getDuration(row["Distant"]),
                    Noise=getDuration(row["Noise"]),
                )
                dbSession.add(segment)

        elif "Timezone" in rows[0]:

            for row in rows:

                match = re.match(r"(?P<DateTime>.+)\s\(.+\)", row["StartTime"])
                startTime = getDateTime(match["DateTime"])

                match = re.match(r"(?P<DateTime>.+)\s\(.+\)", row["EndTime"])
                endTime = getDateTime(match["DateTime"])

                # This is a guard against some numerical errors in the CSV files.
                if endTime.second == 59 and int(row["Duration_Secs"]) == 300:
                    endTime += timedelta(seconds=1)
                if startTime.second == 59 and int(row["Duration_Secs"]) == 300:
                    startTime += timedelta(seconds=1)

                duration = endTime - startTime

                if int(row["Duration_Secs"]) != duration.total_seconds():
                    print(f"Timezone:  Start = {startTime}, End = {endTime}, Duration = {duration}")

                segment = Segment(
                    RecordingID=recording.RecordingID,
                    StartTime=startTime,
                    EndTime=endTime,
                    StartTimeInSeconds=(startTime - recordingStartTime).total_seconds(),
                    EndTimeInSeconds=(endTime - recordingStartTime).total_seconds(),
                    Duration=duration,
                    AdultWordCount=getInteger(row["AWC_COUNT"]),
                    ConversationalTurnCount=getInteger(row["CT_COUNT"]),
                    ChildVocalizationCount=getInteger(row["CV_COUNT"]),
                    Meaningful=getDuration(row["Meaningful"]),
                    Silence=getDuration(row["Silence"]),
                    Electronic=getDuration(row["TV_Secs"]),
                    Distant=getDuration(row["Distant"]),
                    Noise=getDuration(row["Noise"]),
                    Overlap=getDuration(row["Overlap"]),
                )
                dbSession.add(segment)
        else:
            print("Unidentified Segment File Style!")

    dbSession.commit()

    print("Loading table 'Segment' is complete.")


def insertUtteranceTables(dbSession: Session) -> None:
    """
    Inserts the Utterance and utterance codes into the DB.
    """
    current = dbSession.query(Utterance).all()

    if len(current) != 0:
        return

    # Obtain the Assessment IDs in the Recording table, for Home Recordings.
    recordingMap = {
        record.AssessmentID: record.RecordingID
        for record in dbSession.query(Recording).all()
        if record.RecordingTypeID == 100
    }

    annotationMap = {
        "Canonical syllables": 100,
        "Non-canonical syllables": 200,
        "Words": 300,
        "Laughing": 400,
        "Crying": 500,
        "Don't mark": 600,
        "Unsure": 600,
    }

    userMap = {record.UserName: record.UserID for record in dbSession.query(User).all()}

    filePath = join(baseFolder, "Utterance.csv")
    rows = loadSourceDataFile(filePath)

    utteranceAssessmentIDs = {row["AssessmentID"] for row in rows}

    # Get the recording IDs that are present in both the CSV file, and the DB Table.
    commonAssessmentIDs = set(recordingMap.keys()) & utteranceAssessmentIDs

    for assessmentID in sorted(commonAssessmentIDs):

        recordingID = recordingMap[assessmentID]
        recordingSegments = dbSession.query(Segment).filter(Segment.RecordingID == recordingID).all()

        # CSV Segment File Name. "20190501_140431_022870"
        if assessmentID == "4081_1":
            print(
                "Skipping Assessment ID '4081_1' Due to to problems in the CSV file. "
                "File contains multiple recording dates."
            )
            continue

        # Get the rows for the current working assessment ID.
        assessmentRows = [row for row in rows if row["AssessmentID"] == assessmentID]
        print(f"Assessment ID {assessmentID} has {len(assessmentRows)} Rows.")

        # Perform a sanity check on segment and utterance selection types.
        for singleSegment in recordingSegments:
            segmentStart = singleSegment.StartTimeInSeconds
            segmentEnd = singleSegment.EndTimeInSeconds
            segmentUtterances = [
                row["SelectionCriterion"]
                for row in assessmentRows
                if segmentStart <= float(row["StartTime"]) < segmentEnd
            ]
            if not segmentUtterances:
                continue

            selectionCounter = Counter(segmentUtterances)
            if len(selectionCounter) != 1:
                print(
                    f"{assessmentID} segment ({singleSegment.StartTimeInSeconds}, {singleSegment.EndTimeInSeconds}) "
                    f"contains {selectionCounter.most_common()}."
                )

        for row in assessmentRows:

            if row["Bad Criterion"]:
                continue

            if row["AssessmentID"] != assessmentID:
                continue

            if row["SelectionCriterion"] == "HV":
                selectionCriterionID = 100
            elif row["SelectionCriterion"] == "RS":
                selectionCriterionID = 200
            else:
                continue

            startTimeInSecond = float(row["StartTime"])
            endTimeInSecond = float(row["EndTime"])

            minimumPitch = float(row["MinimumPitch"])
            maximumPitch = float(row["MaximumPitch"])
            averagePitch = float(row["AveragePitch"])

            # Obtain the segment that this utterance belongs to, which should ONLY be one segment.
            validSegments = [
                s for s in recordingSegments if s.StartTimeInSeconds <= startTimeInSecond < s.EndTimeInSeconds
            ]

            if len(validSegments) != 1:
                print(f"Look into row# {row['Index']}. Row matched {len(validSegments)} segments.")
                continue

            segment = validSegments[0]

            if not segment.IsSelected:
                segment.IsSelected = True
                segment.SelectionCriterionID = selectionCriterionID
            elif segment.SelectionCriterionID != selectionCriterionID:
                print(f"Mark row# {row['Index']} as bad.")
                continue

            utterance = Utterance(
                SegmentID=segment.SegmentID,
                StartTimeInSeconds=startTimeInSecond,
                EndTimeInSeconds=endTimeInSecond,
                DurationInSeconds=round(endTimeInSecond - startTimeInSecond, 4),
                AudioFileName="",
                AudioFileData=b"",
                MinimumPitch=minimumPitch,
                MaximumPitch=maximumPitch,
                AveragePitch=averagePitch,
                PitchRange=(maximumPitch - minimumPitch),
            )

            dbSession.add(utterance)

            # We will NOT use the codes if the row is marked as having bad codes.
            if row["Bad Coders"]:
                continue

            # Add the coding data.
            for i in ["1", "2", "3"]:

                totalSyllableCount = getInteger(row[f"TotalSyllableCount{i}"])
                canonicalSyllableCount = getInteger(row[f"CanonicalSyllableCount{i}"])
                wordSyllableCount = getInteger(row[f"WordSyllableCount{i}"])
                nonCanonicalSyllableCount = totalSyllableCount - canonicalSyllableCount - wordSyllableCount

                utteranceCoding = UtteranceCoding(
                    Utterance=utterance,
                    CoderID=userMap[row[f"Coder{i}"]],
                    UtteranceTypeAnnotationID=annotationMap[row[f"Annotation{i}"]],
                    TotalSyllableCount=totalSyllableCount,
                    CanonicalSyllableCount=canonicalSyllableCount,
                    WordSyllableCount=wordSyllableCount,
                    NonCanonicalSyllableCount=nonCanonicalSyllableCount,
                    WordCount=getInteger(row[f"WordCount{i}"]),
                    Comments="Legacy Code",
                )

                dbSession.add(utteranceCoding)

    dbSession.commit()
    print("Loading table 'Utterance' is complete.")
    print("Loading table 'UtteranceCoding' is complete.")


# def readUtteranceSound(
#     recordingBaseFileName: str, startTime: float, endTime: float
# ) -> Tuple[str, bytes]:
#     """
#     Reads the recording audio, and extracts the segment that pertains the current utterance.
#
#     :return: Wave File Name, and Wave File Data compressed.
#     """
#
#     utteranceFileName = f"{recordingBaseFileName}_{startTime}_{endTime}.mp3"
#
#     recordingFolder = r"C:\Temp\Audio"
#     recordingFilePath = join(recordingFolder, f"{recordingBaseFileName}.wav")
#
#     # NOTE: the audio library uses time-based indexing, where each sample is 1ms.
#     recordingAudio = AudioSegment.from_wav(recordingFilePath)
#
#     starting = time.perf_counter()
#
#     # Slice based on the time, inclusively.
#     utteranceAudio = recordingAudio[startTime * 1000 : endTime * 1000]
#
#     targetFolder = r"D:\Temp\Utterance Files"
#     targetAudioPath = join(targetFolder, utteranceFileName)
#
#     utteranceAudio.export(targetAudioPath).close()
#
#     with open(targetAudioPath, "rb") as audioFile:
#         audioBytes = audioFile.read()
#
#     ending = time.perf_counter()
#     duration = ending - starting
#     print(
#         f'File "{utteranceFileName}" of size {len(utteranceAudio)} completed in {duration:4.2f} secs.'
#     )
#
#     return utteranceFileName, audioBytes


def insertUtteranceSoundFiles(dbSession: Session, key: bytes) -> None:
    """
    Updates the utterances in the DB with their audio from the large recording files.
    """
    # TODO: Populate with specific folders.
    recordingFolder = r""
    targetFolder = r""

    current = dbSession.query(Utterance).all()

    if len(current) == 0:
        return

    recordings = dbSession.query(Recording).filter(Recording.RecordingTypeID == 100).all()

    for recording in recordings:
        utterances = (
            dbSession.query(Utterance)
            .join(Segment)
            .join(Recording)
            .filter(Recording.RecordingID == recording.RecordingID)
            .all()
        )

        if not utterances:
            continue

        starting = time.perf_counter()

        recordingFilePath = join(recordingFolder, f"{recording.BaseFileName}.wav")

        # NOTE: the audio library uses time-based indexing, where each sample is 1ms.
        recordingAudio = AudioSegment.from_wav(recordingFilePath)

        for utterance in utterances:
            startTime = utterance.StartTimeInSeconds
            endTime = utterance.EndTimeInSeconds
            utteranceFileName = f"{recording.BaseFileName}_{startTime}_{endTime}.mp3"

            # Slice based on the time, inclusively.
            utteranceAudio = recordingAudio[startTime * 1000 : endTime * 1000]

            targetAudioPath = join(targetFolder, utteranceFileName)

            if os.path.exists(targetAudioPath):
                os.remove(targetAudioPath)

            utteranceAudio.export(targetAudioPath).close()

            with open(targetAudioPath, "rb") as audioFile:
                audioBytes = audioFile.read()

            cipher = AES.new(key, AES.MODE_EAX)

            nonce = cipher.nonce
            encryptedAudioBytes = cipher.encrypt(audioBytes)

            utterance.AudioFileName = utteranceFileName
            utterance.AudioFileData = nonce + encryptedAudioBytes

        ending = time.perf_counter()
        duration = ending - starting

        print(
            f"Recording {recording.BaseFileName} has {len(utterances)} utterances. Completed in {duration:4.2f} secs."
        )
        dbSession.commit()


def getDatabaseSession(connectionString: str) -> Session:
    """
    Creates an instance of the DB Session that allows for full data access.
    """
    connection = connectionString
    engine = create_engine(connection, isolation_level="SERIALIZABLE")
    SessionType = sessionmaker(bind=engine, expire_on_commit=False)

    session = SessionType()

    return session


def insertRandomUtteranceSamplePool(dbSession: Session) -> None:
    """
    Inserts some random entries in the Sample Pool table for testing purposes.
    """
    entries = dbSession.query(Utterance).order_by(desc(Utterance.DurationInSeconds)).limit(20).all()

    for index, entry in enumerate(entries):

        if index < 5:
            coder1 = 1000
            coder2 = 1100
        else:
            coder1 = None
            coder2 = None

        if index == 10:
            break

        sample1 = UtteranceSamplePool(UtteranceID=entry.UtteranceID, CodingBatchGroup=1, CoderID=coder1)

        dbSession.add(sample1)
        if coder1 is not None:
            coding1 = UtteranceCoding(UtteranceID=entry.UtteranceID, CoderID=coder1, UtteranceTypeAnnotationID=500,)

            dbSession.add(coding1)

        sample2 = UtteranceSamplePool(UtteranceID=entry.UtteranceID, CodingBatchGroup=1, CoderID=coder2)

        dbSession.add(sample2)

        if coder2 is not None:
            coding2 = UtteranceCoding(UtteranceID=entry.UtteranceID, CoderID=coder2, UtteranceTypeAnnotationID=400,)

            dbSession.add(coding2)

        sample3 = UtteranceSamplePool(UtteranceID=entry.UtteranceID, CodingBatchGroup=1)

        dbSession.add(sample3)

    dbSession.commit()


if __name__ == "__main__":

    print(f"Starting @ {datetime.now()} ... \n")

    connectionType = ConnectionType.Production
    connectionString, key = getConnectionInformation(connectionType)
    localSession = getDatabaseSession(connectionString)

    insertBasicTables(localSession)
    insertRecordingTables(localSession)
    insertBatchTable(localSession)

    insertSegmentTable(localSession)
    insertUtteranceTables(localSession)

    insertUtteranceSoundFiles(localSession, key)

    # insertRandomUtteranceSamplePool(localSession)

    localSession.close()

    print()
    print(f"End @ {datetime.now()} ... \n")
