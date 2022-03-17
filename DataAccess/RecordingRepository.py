"""
Defines the DB Access methods to the Recording, Segment and Utterance tables.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


from typing import List, Optional
import lzma
import numpy as np
import parselmouth
from lxml import etree
from os.path import join
from datetime import datetime
from itertools import chain
from random import sample
from tempfile import TemporaryDirectory

from Crypto.Cipher import AES
from pydub import AudioSegment

from DataAccess.BaseDB import *
from DataAccess.BaseRepository import BaseRepository
from sqlalchemy import not_, and_


class RecordingRepository(BaseRepository):
    def __init__(self):
        """
        Initializes a new instance of the repository.
        """
        super().__init__()

    def addNewCodingBatch(self, assessmentIDs: List[str]) -> Optional[int]:
        """
        Adds the passes IDs into the CodingBatch table, and returns the new group number if successful.
        """
        recordings = (
            self.DbSession.query(Recording)
            .filter(
                Recording.RecordingTypeID == self.getHomeRecordingTypeID(), Recording.AssessmentID.in_(assessmentIDs),
            )
            .all()
        )

        if len(recordings) != len(assessmentIDs):
            raise ValueError("One or more Assessment IDs are not present in the DB.")

        # Check if any of the assessment IDs added are in the Batch table.
        batches = (
            self.DbSession.query(CodingBatch)
            .join(Recording, CodingBatch.RecordingID == Recording.RecordingID)
            .filter(
                Recording.RecordingTypeID == self.getHomeRecordingTypeID(), Recording.AssessmentID.in_(assessmentIDs),
            )
            .all()
        )

        if len(batches) > 0:
            return None

        recordingIDs = (
            self.DbSession.query(Recording.RecordingID)
            .filter(
                Recording.RecordingTypeID == self.getHomeRecordingTypeID(), Recording.AssessmentID.in_(assessmentIDs),
            )
            .all()
        )

        newGroup = self.DbSession.query(CodingBatch.Group).order_by(CodingBatch.Group.desc()).first()[0] + 100

        for recordingID in recordingIDs:
            batch = CodingBatch(RecordingID=recordingID, Group=newGroup)
            self.DbSession.add(batch)

        return newGroup

    def getHomeRecordingTypeID(self):
        """
        Returns the Home Recording Type ID. This is a frequently needed value.
        """
        homeRecording = (
            self.DbSession.query(RecordingType.RecordingTypeID).filter(RecordingType.Description == "Home").scalar()
        )

        return homeRecording

    def selectUtterancesFor(self, recordingsFolderPath: str, key: bytes, assessmentID: str) -> bool:
        """
        For the assessment ID passed, with selected segments, this method adds the utterances of those segments for
        coding.
        """
        segmentData = (
            self.DbSession.query(Segment, Recording)
            .join(Recording, Segment.RecordingID == Recording.RecordingID)
            .filter(
                Segment.IsSelected,
                Recording.RecordingTypeID == self.getHomeRecordingTypeID(),
                Recording.AssessmentID == assessmentID,
            )
            .all()
        )

        # Guard against missing selections.
        if len(segmentData) == 0:
            return False

        utterances = (
            self.DbSession.query(Utterance)
            .join(Segment, Utterance.SegmentID == Segment.SegmentID)
            .join(Recording, Segment.RecordingID == Recording.RecordingID)
            .filter(Recording.RecordingTypeID == self.getHomeRecordingTypeID(), Recording.AssessmentID == assessmentID,)
            .all()
        )

        # Skip if already added.
        if len(utterances) > 0:
            return True

        self.addNewUtterancesFor(segmentData, recordingsFolderPath, key)

        return True

    def addNewUtterancesFor(self, segmentData, recordingsFolderPath, key) -> None:
        """
        Adds the utterances from the given recording that are within the given segments.
        """
        _, recording = segmentData[0]
        recordingBaseFileName = recording.BaseFileName
        recordingFilePath = join(recordingsFolderPath, f"{recordingBaseFileName}.wav")

        utterances = self.getUtterancesInSegments(segmentData)

        # NOTE: the audio library uses time-based indexing, where each sample is 1ms.
        recordingAudio = AudioSegment.from_wav(recordingFilePath)
        targetFolder = TemporaryDirectory(prefix="VMC_")

        dbUtterances = []
        for segmentID, startTime, endTime in utterances:

            utteranceFileName = f"{recordingBaseFileName}_{startTime}_{endTime}.mp3"
            targetAudioPath = join(targetFolder.name, utteranceFileName)

            # Slice based on the time, inclusively.
            utteranceAudio = recordingAudio[startTime * 1000 : endTime * 1000]
            utteranceAudio.export(targetAudioPath).close()

            with open(targetAudioPath, "rb") as audioFile:
                audioBytes = audioFile.read()

            sound = parselmouth.Sound(targetAudioPath)
            pitchInfo = sound.to_pitch().selected_array["frequency"]
            pitchInfo = pitchInfo[pitchInfo != 0]
            if pitchInfo.size == 0:
                pitchInfo = np.array([0.0])

            cipher = AES.new(key, AES.MODE_EAX)
            nonce = cipher.nonce
            encryptedAudioBytes = cipher.encrypt(audioBytes)

            utterance = Utterance(
                SegmentID=segmentID,
                StartTimeInSeconds=startTime,
                EndTimeInSeconds=endTime,
                DurationInSeconds=round(endTime - startTime, 4),
                AudioFileName=utteranceFileName,
                AudioFileData=nonce + encryptedAudioBytes,
                MinimumPitch=np.amin(pitchInfo),
                MaximumPitch=np.amax(pitchInfo),
                AveragePitch=np.average(pitchInfo),
                PitchRange=(np.amax(pitchInfo) - np.amin(pitchInfo)),
            )
            dbUtterances.append(utterance)

        self.DbSession.add_all(dbUtterances)

        # Delete temporary audio files.
        targetFolder.cleanup()

    def getUtterancesInSegments(self, segments):
        """
        Identifies and returns the utterances that are part of the given segments.
        """
        # Get the ITS file.
        _, recording = segments[0]
        recordingID = recording.RecordingID
        itsCompressedData = (
            self.DbSession.query(InterpretiveTimeSegment.FileData)
            .filter(InterpretiveTimeSegment.RecordingID == recordingID)
            .scalar()
        )

        itsData = lzma.decompress(itsCompressedData).decode("UTF-8")
        itsXml = etree.fromstring(itsData)

        # The times in the file are stored using ISO 8601 duration is seconds: "PT<float>S", e.g. "PT21.83S".
        parseISO = lambda isoTime: float(isoTime[2:-1])

        # Get all available utterances for this recording.
        recordingUtterances = [
            (parseISO(s.attrib["startTime"]), parseISO(s.attrib["endTime"]))
            for s in itsXml.iter("Segment")
            if s.attrib["spkr"] == "CHN"
        ]

        # Filter for those whose start time is within a selected segment.
        utterances = []
        for segment, _ in segments:
            utterances += [
                (segment.SegmentID, uStart, uEnd)
                for uStart, uEnd in recordingUtterances
                if segment.StartTimeInSeconds <= uStart < segment.EndTimeInSeconds
            ]

        return utterances

    def selectSegmentsFor(self, assessmentID: str, highVolubilityCount: int = 10, randomCount: int = 20) -> bool:
        """
        For the assessment ID passed, that is already in the DB, extract some segments based on high volubility, or
        random selection, and return the list of selected segment IDs.
        """
        # Check if we have any exclusions.
        exclusions = (
            self.DbSession.query(ExclusionDuration)
            .join(Recording)
            .filter(Recording.RecordingTypeID == self.getHomeRecordingTypeID(), Recording.AssessmentID == assessmentID,)
            .all()
        )

        query = (
            self.DbSession.query(Segment)
            .join(Recording, Segment.RecordingID == Recording.RecordingID)
            .filter(Recording.RecordingTypeID == self.getHomeRecordingTypeID(), Recording.AssessmentID == assessmentID,)
            .order_by(Segment.ChildVocalizationCount.desc())
        )

        # Filter out exclusions.
        if exclusions:
            query = query.join(ExclusionDuration, Recording.RecordingID == ExclusionDuration.RecordingID,).filter(
                not_(
                    and_(
                        Segment.StartTime >= ExclusionDuration.StartTime, Segment.EndTime <= ExclusionDuration.EndTime,
                    )
                )
            )

        segments = query.all()

        # Guard against double-selection.
        if any(s.IsSelected for s in segments):
            return True

        # Reject selection if we do not have enough.
        if len(segments) < highVolubilityCount + randomCount:
            return False

        hvSegments = [(s, "HV") for s in segments[:highVolubilityCount]]
        rsSegments = [(s, "RS") for s in sample(segments[highVolubilityCount:], randomCount)]

        criterionMap = {c.Symbol: c.SelectionCriterionID for c in self.DbSession.query(SelectionCriterion).all()}

        # Mark selections in the DB.
        for segment, criterion in chain(hvSegments, rsSegments):
            segment.IsSelected = True
            segment.SelectionCriterionID = criterionMap[criterion]
            segment.ModifiedOn = datetime.now()

        return True
