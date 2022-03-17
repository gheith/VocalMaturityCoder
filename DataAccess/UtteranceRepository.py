"""
Defines the DB Access methods to the Utterance, UtteranceCode, and UtteranceSamplePool table.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.2.0"
__status__ = "Production"


from random import shuffle
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict
from collections import Counter
from itertools import groupby, tee, zip_longest
from sqlalchemy import or_
from DataAccess.BaseDB import *
from DataAccess.BaseRepository import BaseRepository
from Models.UtteranceModel import UtteranceModel
from Models.UtteranceCodeModel import UtteranceCodeModel
from Models.UtteranceCodeConsensusModel import UtteranceCodeConsensusModel


class UtteranceRepository(BaseRepository):
    def __init__(self):
        """
        Initializes a new instance of the repository.
        """
        super().__init__()

    def addUtterancesToSamplePool(self, batchGroup: int, coderCount: int = 3) -> None:
        """
        Adds utterances to be coded by the desired number of coders.
        """
        utteranceIDs = (
            self.DbSession.query(Utterance.UtteranceID)
            .join(Segment, Utterance.SegmentID == Segment.SegmentID)
            .join(Recording, Segment.RecordingID == Recording.RecordingID)
            .join(CodingBatch, Recording.RecordingID == CodingBatch.RecordingID)
            .filter(CodingBatch.Group == batchGroup)
            .all()
        )

        poolUtterances = [uID[0] for uID in utteranceIDs] * coderCount
        shuffle(poolUtterances)

        samples = []
        for utteranceID in poolUtterances:
            sample = UtteranceSamplePool(UtteranceID=utteranceID, CodingBatchGroup=batchGroup, AddedOn=datetime.now(), ModifiedOn=datetime.now())

            samples.append(sample)

        self.DbSession.bulk_save_objects(samples)

        # self.commitChanges()

    def saveNewUtteranceCode(self, utteranceCode: UtteranceCodeModel) -> bool:
        """
        Saves the passed code, and updates it for future updates.
        """

        poolSample = (
            self.DbSession.query(UtteranceSamplePool)
            .filter(UtteranceSamplePool.UtteranceSamplePoolID == utteranceCode.UtteranceSamplePoolID)
            .one()
        )

        if poolSample is None or not poolSample.IsProcessing or poolSample.CoderID is not None:
            return False

        poolSample.CoderID = utteranceCode.CoderID
        poolSample.IsProcessing = False
        poolSample.ModifiedOn = datetime.now()

        nonCanonicalCount = utteranceCode.TotalSyllableCount - utteranceCode.CanonicalSyllableCount
        annotationID = (
            self.DbSession.query(UtteranceTypeAnnotation.UtteranceTypeAnnotationID)
            .filter(UtteranceTypeAnnotation.Description == utteranceCode.Annotation)
            .one()
        )

        coding = UtteranceCoding(
            UtteranceID=utteranceCode.UtteranceID,
            CoderID=utteranceCode.CoderID,
            UtteranceTypeAnnotationID=annotationID,
            TotalSyllableCount=utteranceCode.TotalSyllableCount,
            CanonicalSyllableCount=utteranceCode.CanonicalSyllableCount,
            WordSyllableCount=utteranceCode.WordSyllableCount,
            WordCount=utteranceCode.WordCount,
            NonCanonicalSyllableCount=nonCanonicalCount,
            Comments=utteranceCode.Comments if utteranceCode.Comments else None,
        )

        self.DbSession.add(coding)
        self.DbSession.commit()

        utteranceCode.UtteranceCodingID = coding.UtteranceCodingID

        return True

    def updateUtteranceCode(self, utteranceCode: UtteranceCodeModel) -> bool:
        """
        Saves the passed code, and updates it for future updates.
        """

        dbUtteranceCode = (
            self.DbSession.query(UtteranceCoding)
            .filter(UtteranceCoding.UtteranceCodingID == utteranceCode.UtteranceCodingID)
            .one()
        )

        if dbUtteranceCode is None:
            return False

        nonCanonicalCount = utteranceCode.TotalSyllableCount - utteranceCode.CanonicalSyllableCount

        annotationID = (
            self.DbSession.query(UtteranceTypeAnnotation.UtteranceTypeAnnotationID)
            .filter(UtteranceTypeAnnotation.Description == utteranceCode.Annotation)
            .one()
        )

        dbUtteranceCode.UtteranceCodingID = utteranceCode.UtteranceCodingID
        dbUtteranceCode.UtteranceID = utteranceCode.UtteranceID
        dbUtteranceCode.CoderID = utteranceCode.CoderID
        dbUtteranceCode.UtteranceTypeAnnotationID = annotationID
        dbUtteranceCode.TotalSyllableCount = utteranceCode.TotalSyllableCount
        dbUtteranceCode.CanonicalSyllableCount = utteranceCode.CanonicalSyllableCount
        dbUtteranceCode.WordSyllableCount = utteranceCode.WordSyllableCount
        dbUtteranceCode.WordCount = utteranceCode.WordCount
        dbUtteranceCode.NonCanonicalSyllableCount = nonCanonicalCount
        dbUtteranceCode.Comments = utteranceCode.Comments if utteranceCode.Comments else None

        self.DbSession.commit()

        return True

    def getSampleForUser(self, userID: int) -> Optional[UtteranceModel]:
        """
        Returns the next utterance to be coded, if any samples can be coded by the current user.
        """
        subquery = (
            self.DbSession.query(UtteranceSamplePool.UtteranceID)
            .join(UtteranceCoding, UtteranceSamplePool.UtteranceID == UtteranceCoding.UtteranceID,)
            .filter(UtteranceCoding.CoderID == userID)
            .distinct(UtteranceSamplePool.UtteranceID)
            .subquery()
        )

        sample = (
            self.DbSession.query(
                UtteranceSamplePool.UtteranceSamplePoolID,
                UtteranceSamplePool.UtteranceID,
                Utterance.DurationInSeconds,
                Utterance.AudioFileName,
                Utterance.AudioFileData,
            )
            .join(Utterance)
            .filter(
                UtteranceSamplePool.IsProcessing == False,
                UtteranceSamplePool.CoderID.is_(None),
                UtteranceSamplePool.UtteranceID.notin_(subquery),
            )
            .order_by(UtteranceSamplePool.UtteranceSamplePoolID)
            .with_for_update(of=UtteranceSamplePool)
            .first()
        )

        if not sample:
            return None

        poolSample = (
            self.DbSession.query(UtteranceSamplePool)
            .filter(UtteranceSamplePool.UtteranceSamplePoolID == sample.UtteranceSamplePoolID)
            .one()
        )

        # Reserve the row, then release.
        poolSample.IsProcessing = True
        poolSample.ModifiedOn = datetime.now()
        self.commitChanges()

        utterance = UtteranceModel(
            UtteranceSamplePoolID=sample.UtteranceSamplePoolID,
            UtteranceID=sample.UtteranceID,
            DurationInSeconds=sample.DurationInSeconds,
            AudioFileName=sample.AudioFileName,
            AudioFileData=sample.AudioFileData,
            AudioFilePath="",
        )

        return utterance

    def getUtteranceAudioByID(self, utteranceID: int) -> Optional[UtteranceModel]:
        """
        Returns the utterance object, for a given utterance ID.
        """
        sample = self.DbSession.query(Utterance).filter(Utterance.UtteranceID == utteranceID).one()

        if not sample:
            return None

        utterance = UtteranceModel(
            UtteranceSamplePoolID=-1,
            UtteranceID=sample.UtteranceID,
            DurationInSeconds=sample.DurationInSeconds,
            AudioFileName=sample.AudioFileName,
            AudioFileData=sample.AudioFileData,
            AudioFilePath="",
        )

        return utterance

    def getCodingRateOfUsers(self, startDate: datetime = None, endDate: datetime = None, maxSessionPause: timedelta = timedelta(minutes=10),
                             performAggregation = True):
        """
        Calculates and returns the coding rate of users, within the given dates.
        """
        subquery = (self.DbSession.query(User.FirstName, User.LastName, UtteranceCoding.CoderID, UtteranceCoding.UtteranceID, UtteranceCoding.AddedOn)
                    .join(User).filter(or_(UtteranceCoding.Comments.is_(None), UtteranceCoding.Comments != 'Legacy Code'))
                    .order_by(User.FirstName, User.LastName, UtteranceCoding.AddedOn))

        if startDate is not None:
            subquery = subquery.filter(UtteranceCoding.AddedOn >= startDate)

        if endDate is not None:
            subquery = subquery.filter(UtteranceCoding.AddedOn <= endDate)

        result = subquery.all()

        if not performAggregation:
            return result

        rateMap = {}

        # Group by and operate on coders.
        for (firstName, lastName), userCodes in groupby(result, lambda record: (record.FirstName, record.LastName)):
            codes1, codes2 = tee(userCodes)
            next(codes2, None)  # Drop the first entry in the second list.

            currentSession = []
            userSessions = []

            # Identify sessions within the user. A new session is expected if the difference between two entries is greater than 10 min.
            for firstEntry, secondEntry in zip_longest(codes1, codes2, fillvalue=None):
                currentSession.append(firstEntry)

                # If the next entry is for a new session
                if secondEntry is not None and secondEntry.AddedOn - firstEntry.AddedOn > maxSessionPause:
                    userSessions.append(currentSession)
                    currentSession = []

            # The last session must be added when done.
            userSessions.append(currentSession)

            # Calculate Session Stats: Session Duration, Session Code Count
            rateMap[(firstName, lastName)] = [(s[-1].AddedOn - s[0].AddedOn, len(s)) for s in userSessions]

        return rateMap

    def generateUtteranceReport(self) -> List[UtteranceCodeConsensusModel]:
        """
        Gets a list of all coded utterances for recordings that have been completed. This list includes also some
        metadata for of the recordings for which the utterances belong to.
        """
        # Recordings that are still being coded.
        inProcessRecordingsSubquery = self._getRecordingsInProcess()

        dbUtterances = (
            self.DbSession.query(Utterance.UtteranceID,
                                 Recording.AssessmentID,
                                 Recording.RecordingDate,
                                 Participant.ChildID,
                                 Sex.Description.label("ChildSex"),
                                 Participant.DateOfBirth.label("ChildDOB"),
                                 Recording.AgeAtRecordingInMonths,
                                 GeneticRisk.Description.label("ChildGroup"),
                                 Segment.SegmentID,
                                 SelectionCriterion.Symbol.label("SelectionCriterion"),
                                 Utterance.StartTimeInSeconds,
                                 Utterance.EndTimeInSeconds,
                                 Utterance.DurationInSeconds,
                                 Utterance.MinimumPitch,
                                 Utterance.MaximumPitch,
                                 Utterance.AveragePitch,
                                 Utterance.PitchRange
            )
            .join(UtteranceCoding, Utterance.UtteranceID == UtteranceCoding.UtteranceID)
            .join(Segment, Utterance.SegmentID == Segment.SegmentID)
            .join(Recording, Segment.RecordingID == Recording.RecordingID)
            .join(Participant, Recording.ParticipantID == Participant.ParticipantID)
            .join(Sex, Participant.SexID == Sex.SexID)
            .join(GeneticRisk, Participant.GeneticRiskID == GeneticRisk.GeneticRiskID)
            .join(SelectionCriterion, Segment.SelectionCriterionID == SelectionCriterion.SelectionCriterionID)
            .filter(Recording.IsValid == True, UtteranceCoding.IsAcceptable, Recording.RecordingID.notin_(inProcessRecordingsSubquery))
            .distinct()
            .order_by(Utterance.UtteranceID)
            .all()
        )

        dbUtteranceCodes = (
            self.DbSession.query(UtteranceCoding.AddedOn.label('CodingTime'),                           # Index 0
                                 UtteranceCoding.UtteranceID,                                           # Index 1
                                 User.FirstName.concat(" ").concat(User.LastName).label("Coder"),       # Index 2
                                 UtteranceCoding.TotalSyllableCount,                                    # Index 3
                                 UtteranceCoding.CanonicalSyllableCount,                                # Index 4
                                 UtteranceCoding.NonCanonicalSyllableCount,                             # Index 5
                                 UtteranceCoding.WordSyllableCount,                                     # Index 6
                                 UtteranceCoding.WordCount,                                             # Index 7
                                 UtteranceType.Description.label("UtteranceType"),                      # Index 8
                                 UtteranceTypeAnnotation.Description.label("UtteranceTypeAnnotation")   # Index 9
            )
            .join(Utterance, UtteranceCoding.UtteranceID == Utterance.UtteranceID)
            .join(Segment, Utterance.SegmentID == Segment.SegmentID)
            .join(Recording, Segment.RecordingID == Recording.RecordingID)
            .join(UtteranceTypeAnnotation,
                  UtteranceCoding.UtteranceTypeAnnotationID == UtteranceTypeAnnotation.UtteranceTypeAnnotationID
            )
            .join(UtteranceType, UtteranceTypeAnnotation.UtteranceTypeID == UtteranceType.UtteranceTypeID)
            .join(User, UtteranceCoding.CoderID == User.UserID)
            .filter(Recording.IsValid == True, UtteranceCoding.IsAcceptable, Recording.RecordingID.notin_(inProcessRecordingsSubquery))
            .distinct()
            .order_by(UtteranceCoding.UtteranceID, UtteranceCoding.AddedOn)
            .all()
        )

        # Safety checks: Identify that the number of returned rows is a multiple of 3, and that each consecutive
        # three rows are for the same utterance.
        if len(dbUtterances) * 3 != len(dbUtteranceCodes):
            raise ValueError("Sizes of returned types do NOT match.")

        utteranceIDs = Counter([row.UtteranceID for row in dbUtteranceCodes])
        idCounts = set(utteranceIDs.values())

        if len(idCounts) != 1 or 3 not in idCounts:
            raise ValueError("Utterance codes have inconsistent frequencies.")

        # Safety checks passed at this point.
        consensusReport = self._calculateUtteranceConsensus(dbUtteranceCodes, dbUtterances)

        return consensusReport

    def _calculateUtteranceConsensus(self, utteranceCodes, utterances) -> List[UtteranceCodeConsensusModel]:
        """
        Calculates and returns a list of utterance information that includes coding aggregate information.
        """
        # The rows are sorted by utterance IDs, so it can be split into chunks by index.
        utteranceIndices = range(0, len(utteranceCodes), 3)
        consensusReport = []

        # Calculate aggregate information.
        for utterance, codeIndex in zip(utterances, utteranceIndices):
            totalConsensus, totalPercent, totalAverage = self.getConsensus(utteranceCodes, codeIndex, 3)
            canonicalConsensus, canonicalPercent, canonicalAverage = self.getConsensus(utteranceCodes, codeIndex, 4)
            nCanonicalConsensus, nCanonicalPercent, nCanonicalAverage = self.getConsensus(utteranceCodes, codeIndex, 5)
            wordSylConsensus, wordSylPercent, wordSylAverage = self.getConsensus(utteranceCodes, codeIndex, 6)
            wordConsensus, wordPercent, wordAverage = self.getConsensus(utteranceCodes, codeIndex, 7)
            speechConsensus, speechPercent, _ = self.getConsensus(utteranceCodes, codeIndex, 8, False)
            maturityConsensus, maturityPercent, _ = self.getConsensus(utteranceCodes, codeIndex, 9, False)

            utteranceCodingInfo = UtteranceCodeConsensusModel(
                UtteranceID=utterance.UtteranceID,
                AssessmentID=utterance.AssessmentID,
                RecordingDate=utterance.RecordingDate,
                ChildID=utterance.ChildID,
                ChildSex=utterance.ChildSex,
                ChildDOB=utterance.ChildDOB,
                AgeAtRecording=round(utterance.AgeAtRecordingInMonths, 2),
                ChildGroup=utterance.ChildGroup,
                SegmentID=utterance.SegmentID,
                SelectionCriterion=utterance.SelectionCriterion,
                StartTime=utterance.StartTimeInSeconds,
                EndTime=utterance.EndTimeInSeconds,
                Duration=round(utterance.DurationInSeconds, 3),
                MinPitch=utterance.MinimumPitch,
                MaxPitch=utterance.MaximumPitch,
                AveragePitch=utterance.AveragePitch,
                PitchRange=utterance.PitchRange,

                TotalSyllableCountConsensus=totalConsensus,
                TotalSyllableCountAgreementPercent=totalPercent,
                TotalSyllableCountAverage=totalAverage,
                CanonicalSyllableCountConsensus=canonicalConsensus,
                CanonicalSyllableCountAgreementPercent=canonicalPercent,
                CanonicalSyllableCountAverage=canonicalAverage,
                NonCanonicalSyllableCountConsensus=nCanonicalConsensus,
                NonCanonicalSyllableCountAgreementPercent=nCanonicalPercent,
                NonCanonicalSyllableCountAverage=nCanonicalAverage,
                WordSyllableCountConsensus=wordSylConsensus,
                WordSyllableCountAgreementPercent=wordSylPercent,
                WordSyllableCountAverage=wordSylAverage,
                WordCountConsensus=wordConsensus,
                WordCountAgreementPercent=wordPercent,
                WordCountAverage=wordAverage,
                UtteranceTypeConsensus=speechConsensus,
                UtteranceTypeAgreementPercent=speechPercent,
                UtteranceAnnotationConsensus=maturityConsensus,
                UtteranceAnnotationAgreementPercent=maturityPercent
            )

            consensusReport.append(utteranceCodingInfo)

        return consensusReport

    def _getRecordingsInProcess(self):
        """
        returns a subquery of Recording IDs that are being processed in the Sample Pool.
        """
        inProcessRecordingsSubquery = (
            self.DbSession.query(Recording.RecordingID)
            .join(Segment, Recording.RecordingID == Segment.RecordingID)
            .join(Utterance, Segment.SegmentID == Utterance.SegmentID)
            .join(UtteranceSamplePool, Utterance.UtteranceID == UtteranceSamplePool.UtteranceID)
            .filter(or_(UtteranceSamplePool.CoderID.is_(None),
                    UtteranceSamplePool.IsProcessing))
            .distinct(Recording.RecordingID)
            .subquery()
        )

        return inProcessRecordingsSubquery

    @staticmethod
    def getConsensus(rows: List, startingRowIndex: int, columnIndex: int, withAverage: bool = True
                     ) -> Tuple[Optional[int], float, Optional[float]]:
        """
        Identifies if there is a majority value at the given column, for rows [rowIndex : rowIndex + 3]. Otherwise,
        return None.

        Note that this method is made for exactly 3 codes. If more codes are expected, it needs to be updated to use
        majority voting. This is expected to process a large set of records.

        :param rows: Utterance Codes returned from the DB Query.
        :param startingRowIndex: The starting row index to check.
        :param columnIndex: The index of the desired field to check.
        :param withAverage: A flag to indicate that speech-based average should be calculated for numeric values.
        :returns: A tuple of three values: consensus, average, agreementPercent
            consensus: If two or three values agree, we accept the value. Otherwise None.
            agreementPercent: All agree => 1.0, two agree => 0.67. Otherwise, 0.0
            average: Optional for numeric values. Average of *Speech* rows. If no Speech rows, None.
        """

        voting = Counter([rows[i][columnIndex] for i in range(startingRowIndex, startingRowIndex + 3)])

        # All codes agree.
        if len(voting) == 1:
            consensus, _ = voting.most_common(1)[0]
            agreementPercent = 1.

        # two of three agree.
        elif len(voting) == 2:
            consensus, _ = voting.most_common(1)[0]
            agreementPercent = 0.67

        # No agreement.
        else:
            consensus = None
            agreementPercent = 0.

        if withAverage:
            averageBase = [rows[i][columnIndex] for i in range(startingRowIndex, startingRowIndex + 3)
                           if rows[i].UtteranceType == "Speech"]
            average = sum(averageBase) / len(averageBase) if averageBase else None
        else:
            average = None

        return consensus, agreementPercent, average
