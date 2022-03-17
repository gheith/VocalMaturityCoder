"""
Utterance Code Consensus Model

Represents all the information associated with the utterance, and its participant, along with the consensus of
the coding information from multiple coders.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"

import attr
from attr.validators import instance_of, optional
from datetime import date


@attr.s
class UtteranceCodeConsensusModel:

    UtteranceID = attr.ib(validator=instance_of(int))
    AssessmentID = attr.ib(validator=instance_of(str))
    RecordingDate = attr.ib(validator=instance_of(date))
    ChildID = attr.ib(validator=instance_of(str))
    ChildSex = attr.ib(validator=instance_of(str))
    ChildDOB = attr.ib(validator=instance_of(date))
    AgeAtRecording = attr.ib(validator=instance_of(float))
    ChildGroup = attr.ib(validator=instance_of(str))
    SegmentID = attr.ib(validator=instance_of(int))
    SelectionCriterion = attr.ib(validator=instance_of(str))
    StartTime = attr.ib(validator=instance_of(float))
    EndTime = attr.ib(validator=instance_of(float))
    Duration = attr.ib(validator=instance_of(float))
    MinPitch = attr.ib(validator=instance_of(float))
    MaxPitch = attr.ib(validator=instance_of(float))
    AveragePitch = attr.ib(validator=instance_of(float))
    PitchRange = attr.ib(validator=instance_of(float))

    TotalSyllableCountConsensus = attr.ib(validator=optional(instance_of(int)))
    TotalSyllableCountAgreementPercent = attr.ib(validator=instance_of(float))
    TotalSyllableCountAverage = attr.ib(validator=optional(instance_of(float)))

    CanonicalSyllableCountConsensus = attr.ib(validator=optional(instance_of(int)))
    CanonicalSyllableCountAgreementPercent = attr.ib(validator=instance_of(float))
    CanonicalSyllableCountAverage = attr.ib(validator=optional(instance_of(float)))

    NonCanonicalSyllableCountConsensus = attr.ib(validator=optional(instance_of(int)))
    NonCanonicalSyllableCountAgreementPercent = attr.ib(validator=instance_of(float))
    NonCanonicalSyllableCountAverage = attr.ib(validator=optional(instance_of(float)))

    WordSyllableCountConsensus = attr.ib(validator=optional(instance_of(int)))
    WordSyllableCountAgreementPercent = attr.ib(validator=instance_of(float))
    WordSyllableCountAverage = attr.ib(validator=optional(instance_of(float)))

    WordCountConsensus = attr.ib(validator=optional(instance_of(int)))
    WordCountAgreementPercent = attr.ib(validator=instance_of(float))
    WordCountAverage = attr.ib(validator=optional(instance_of(float)))

    UtteranceTypeConsensus = attr.ib(validator=optional(instance_of(str)))
    UtteranceTypeAgreementPercent = attr.ib(validator=instance_of(float))

    UtteranceAnnotationConsensus = attr.ib(validator=optional(instance_of(str)))
    UtteranceAnnotationAgreementPercent = attr.ib(validator=instance_of(float))

