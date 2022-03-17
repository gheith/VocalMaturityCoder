"""
AddRecordingsToDB

A script that checks the Recording metadata file, which must be located in the data folder, where ".csv", ".its" and
".wav" files are present. This is an admin script that performs the follow:

1- Add metadata to the Recording table.
2- Add segment information to the Segment Table.
3- Add related recording information, like day typicality and exclusion times.

Note that this script does NOT create a batch from one or more recording, and does NOT setup the sample pool. This is
done using a different script.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.2.0"
__status__ = "Production"


import re
import lzma
from lxml import etree
from os.path import join, exists
from datetime import datetime, timedelta, date
from typing import List, Tuple
from csv import DictReader

from VmcLoader import getConnectionInformation, ConnectionType, DataFolder

from DataAccess.BaseDB import *
from sqlalchemy.orm.session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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


def verifyFileNamesAndContent(baseName: str) -> bool:
    """
    Checks for the existence of recording related files: '.csv', '.its', '.wav'. Also, confirms that:
        - ITS file name is the same one tagged in the XML inside.
        - All entries in the CVS 5-min file have the same ITS file name as desired.
    """
    fileNames = [f'{baseName}{ext}' for ext in ('.csv', '.its', '.wav')]
    filePaths = [join(DataFolder, f'{fileName}') for fileName in fileNames]

    # Check for existence.
    if not all(exists(filePath) for filePath in filePaths):
        print(f'    Breaking Error: One or more file is missing from {fileNames}.')
        print(f'    NOTE: Files with exact names must reside in the data folder {DataFolder}.')
        return False

    # Check content of ITS file.
    itsFilePath = join(DataFolder, f"{baseName}.its")

    with open(itsFilePath, "r") as itsFile:
        itsString = itsFile.read()

    # Ignore the XML declaration if present.
    startIndex = itsString.find('<ITS fileName')
    itsString = itsString[startIndex:]

    # This line will produce an error if the first tag is NOT 'ITS'.
    itsXml = etree.fromstring(itsString)

    itsFileName = itsXml.attrib['fileName']
    if itsFileName != baseName:
        print(f'    Breaking Error: ITS "fileName={itsFileName}" does NOT match {baseName}.its.')
        print(f'    NOTE: The "fileName" attribute in the ITS file MUST match the base file name.')
        return False

    csvFilePath = join(DataFolder, f"{baseName}.csv")
    rows = loadSourceDataFile(csvFilePath)

    # Identify File Style.
    if "Timestamp" in rows[0]:
        headerName = "ProcessingFile"
    elif "Timezone" in rows[0]:
        headerName = "ITS_File_Name"
    else:
        print(f'    Breaking Error: Unidentified Segment File Style! Unable to check ITS file names in Segment CSV file.')
        return False

    itsFileNameInCVS = {row[headerName] for row in rows}
    if len(itsFileNameInCVS) != 1 or f'{itsFileNameInCVS.pop()}'.lower() != f"{baseName}.its":
        print(f'    Breaking Error: ITS file names in Segment CSV file are not acceptable.')
        return False

    return True


def addNewRecordingsToDB(dbSession: Session) -> None:
    """
    Checks the reference recordings file for new additions, and loads them into the DB. Entries may also be added to
    ExclusionDuration, DayTypicality, and InterpretiveTimeSegment tables in the database.
    """

    filePath = join(DataFolder, "Recording.csv")

    rows = loadSourceDataFile(filePath)

    # Get the list of current recordings to identify what is missing.
    dbRecordings = (dbSession.query(Recording.AssessmentID, RecordingType.Description)
                    .join(RecordingType, Recording.RecordingTypeID == RecordingType.RecordingTypeID)
                    .all()
    )

    # Obtain all the recordings mentioned in the file.
    fileRecordings = {(row["AssessmentID"], row["RecordingType"]) for row in rows if not row['Skip']}

    newRecordings = set(fileRecordings) - set(dbRecordings)

    if not newRecordings:
        print('No new recordings have been found.')
        print('NOTE: Recordings marked as "Skip" will not be loaded.')
        return

    print(f'The following {len(newRecordings)} recording(s) have been identified:\n')
    print(", ".join([f"({asst}, {recType})" for asst, recType in newRecordings]))

    # Load support tables.
    errorCodeMap = {record.Symbol: record.ErrorCodeID for record in dbSession.query(ErrorCode).all()}
    dataUseOptionMap = {record.ConsentOptionNumber: record.DataUseOptionID
                        for record in dbSession.query(DataUseOption).all()}
    recordingTypeMap = {record.Description: record.RecordingTypeID for record in dbSession.query(RecordingType).all()}
    participantMap = {record.ChildID: record.ParticipantID for record in dbSession.query(Participant).all()}
    userMap = {record.UserName: record.UserID for record in dbSession.query(User).all()}

    # This is a quick function to reduce typing.
    parseIf = lambda fn, name: fn(row[name]) if row[name] else None

    for row in rows:
        current = row["AssessmentID"], row["RecordingType"]

        if current not in newRecordings or row["Skip"]:
            continue

        print(f'Working on {current} ...')

        if row["RecordingType"] not in recordingTypeMap:
            print(f'    Breaking Error: Recording Type {row["RecordingType"]} is unknown.')
            print(f'    NOTE: If this is a new type, please update the "RecordingType" table in the DB.')
            continue

        if row["ChildID"] not in participantMap:
            print(f'    Breaking Error: Participant {row["ChildID"]} is unknown.')
            print('    NOTE: If this is a new participant, please add the participant first.')
            continue

        baseFileName = row["BaseFileName"]
        if not verifyFileNamesAndContent(baseFileName):
            continue

        recordingDate = row["RecordingDate"]

        match = re.match(r"(?P<DateTime>.+)\s\(.+\)", row["StartTime"])
        startTime = getDateTime(match["DateTime"])
        match = re.match(r"(?P<DateTime>.+)\s\(.+\)", row["EndTime"])
        endTime = getDateTime(match["DateTime"])

        if row["ChildWakeTime"]:
            childWakeTime = datetime.strptime(row["ChildWakeTime"], "%I:%M").time()
            entryDate = datetime.strptime(recordingDate, "%m/%d/%y").date()

            childWakeTimestamp = datetime.combine(entryDate, childWakeTime)
        else:
            childWakeTimestamp = None

        childWordCount = parseIf(int, "ChildWordCount")

        if row["HasPhrases"]:
            hasPhrases = row["HasPhrases"].lower() == "yes"
        else:
            hasPhrases = None

        notes = ""
        if row["RecordingNotes"]:
            notes += f"RecordingNotes:\n{row['RecordingNotes']}\n\n"
        if row["ScrubSheetNotes"]:
            notes += f"ScrubSheetNotes:\n{row['ScrubSheetNotes']}\n\n"
        notes = notes if notes else None

        entry = Recording(
            RecordingTypeID=recordingTypeMap[row["RecordingType"]],
            ParticipantID=participantMap[row["ChildID"]],
            AssessmentID=row["AssessmentID"],
            RecordingDate=recordingDate,
            AgeAtRecordingInMonths=row["AgeAtRecordingInMonths"],
            BaseFileName=baseFileName,
            StartTime=startTime,
            EndTime=endTime,
            ChildWakeTime=childWakeTimestamp,
            Duration=endTime - startTime,
            ErrorCodeID=errorCodeMap[row["ErrorCode"]] if row["ErrorCode"] else None,
            ConsentFormVersion=parseIf(int, "ConsentFormVersion"),
            ChildWordCount=childWordCount,
            HasPhrases=hasPhrases,
            DataUseOptionID=dataUseOptionMap[int(row["DataUseOption"])] if row["DataUseOption"] else None,
            AdultWordCount=parseIf(int, "AdultWordCount"),
            AdultWordCountPercentile=parseIf(float, "AdultWordCountPercentile"),
            AdultWordCountStandardScore=parseIf(float, "AdultWordCountStandardScore"),
            ConversationalTurnCount=parseIf(int, "ConversationalTurnCount"),
            ConversationalTurnPercentile=parseIf(float, "ConversationalTurnPercentile"),
            ConversationalTurnStandardScore=parseIf(float, "ConversationalTurnStandardScore"),
            ChildVocalizationCount=parseIf(int, "ChildVocalizationCount"),
            ChildVocalizationPercentile=parseIf(float, "ChildVocalizationPercentile"),
            ChildVocalizationStandardScore=parseIf(float, "ChildVocalizationStandardScore"),
            AutomatedVocalizationAssessmentPercentile=parseIf(float, "AutomatedVocalizationAssessmentPercentile"),
            AutomatedVocalizationAssessmentStandardScore=parseIf(float, "AutomatedVocalizationAssessmentStandardScore"),
            VocalProductivityPercentile=parseIf(float, "VocalProductivityPercentile"),
            VocalProductivityStandardScore=parseIf(float, "VocalProductivityStandardScore"),
            Meaningful=getDuration(row["Meaningful"]),
            Silence=getDuration(row["Silence"]),
            Electronic=getDuration(row["Electronic"]),
            Distant=getDuration(row["Distant"]),
            Noise=getDuration(row["Noise"]),
            Overlap=getDuration(row["Overlap"]),
            TimeZone=row["TimeZone"],
            Notes=notes,
            IsScrubbed=row["IsScrubbed"] == "1",
            IsValid=(False if row["IsValid"] == "0" else True),
        )

        dbSession.add(entry)

        addItsFileForRecording(dbSession, entry)

        addTimeExclusions(dbSession, entry, row)

        addRecordingSegments(dbSession, entry)

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

        print(f'Completed {current}\n')


def addItsFileForRecording(dbSession: Session, recording: Recording) -> None:
    """
    Inserts the ITS Data associated with the current recording.
    """
    itsFilePath = join(DataFolder, f"{recording.BaseFileName}.its")

    with open(itsFilePath, "r") as itsFile:
        itsString = itsFile.read()

    # Ignore the XML declaration if present.
    startIndex = itsString.find('<ITS fileName')
    itsString = itsString[startIndex:]

    itsBytes = itsString.encode("UTF-8")

    itsSmall = lzma.compress(itsBytes, preset=9 | lzma.PRESET_EXTREME)
    itsEntry = InterpretiveTimeSegment(Recording=recording, FileData=itsSmall)

    dbSession.add(itsEntry)


def addTimeExclusions(dbSession: Session, recording: Recording, row: dict) -> None:
    """
    Inserts the exclusion times associated with the current recording.
    """
    exclusionMap = {record.Description: record.ExclusionTypeID for record in dbSession.query(ExclusionType).all()}
    entryDate = datetime.strptime(recording.RecordingDate, "%m/%d/%y")

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


def addRecordingSegments(dbSession: Session, recording: Recording) -> None:
    """
    Inserts the CSV file information into the Segment Table.
    """
    csvFilePath = join(DataFolder, f"{recording.BaseFileName}.csv")
    rows = loadSourceDataFile(csvFilePath)

    recordingStartTime = recording.StartTime

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
        raise ValueError("Unidentified Segment File Style!")


if __name__ == "__main__":

    print(f"Starting @ {datetime.now()} ... \n")

    cType = ConnectionType.Production
    connectionStr, encKey = getConnectionInformation(cType)

    engine = create_engine(connectionStr, isolation_level="READ_COMMITTED")
    SessionMaker = sessionmaker(bind=engine, expire_on_commit=False)
    localSession = SessionMaker()

    addNewRecordingsToDB(localSession)

    localSession.commit()
    localSession.close()

    print()
    print(f"End @ {datetime.now()} ... \n")
