# coding: utf-8
from sqlalchemy import Boolean, CHAR, CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, SmallInteger, String, Table, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class LogEntry(Base):
    __tablename__ = "LogEntry"
    __table_args__ = {"schema": "Main"}

    LogEntryID = Column(Integer, primary_key=True)
    TimeStamp = Column(DateTime, nullable=False, server_default=text("now()"))
    UserID = Column(Integer)
    SessionID = Column(Integer)
    Level = Column(String(25), nullable=False)
    Module = Column(String(256))
    Function = Column(String(256))
    Message = Column(String)
    Exception = Column(String)


class DataUseOption(Base):
    __tablename__ = 'DataUseOption'
    __table_args__ = {'schema': 'Main'}

    DataUseOptionID = Column(Integer, primary_key=True)
    ConsentOptionNumber = Column(SmallInteger, nullable=False)
    Description = Column(String(100), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class ErrorCode(Base):
    __tablename__ = 'ErrorCode'
    __table_args__ = {'schema': 'Main'}

    ErrorCodeID = Column(Integer, primary_key=True)
    Symbol = Column(String(5), nullable=False)
    Description = Column(String(256), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class ExclusionType(Base):
    __tablename__ = 'ExclusionType'
    __table_args__ = {'schema': 'Main'}

    ExclusionTypeID = Column(Integer, primary_key=True)
    Description = Column(String(100), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class GeneticRisk(Base):
    __tablename__ = 'GeneticRisk'
    __table_args__ = {'schema': 'Main'}

    GeneticRiskID = Column(Integer, primary_key=True)
    Description = Column(String(100), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class RecordingType(Base):
    __tablename__ = 'RecordingType'
    __table_args__ = {'schema': 'Main'}

    RecordingTypeID = Column(Integer, primary_key=True)
    Description = Column(String(100), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class SelectionCriterion(Base):
    __tablename__ = 'SelectionCriterion'
    __table_args__ = {'schema': 'Main'}

    SelectionCriterionID = Column(Integer, primary_key=True)
    Description = Column(String(100), nullable=False)
    Symbol = Column(CHAR(2), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class Sex(Base):
    __tablename__ = 'Sex'
    __table_args__ = {'schema': 'Main'}

    SexID = Column(Integer, primary_key=True)
    Description = Column(String(100), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class UserType(Base):
    __tablename__ = 'UserType'
    __table_args__ = {'schema': 'Main'}

    UserTypeID = Column(Integer, primary_key=True)
    Description = Column(String(256), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class UtteranceType(Base):
    __tablename__ = 'UtteranceType'
    __table_args__ = {'schema': 'Main'}

    UtteranceTypeID = Column(Integer, primary_key=True)
    Description = Column(String(50), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))


class Participant(Base):
    __tablename__ = 'Participant'
    __table_args__ = {'schema': 'Main'}

    ParticipantID = Column(Integer, primary_key=True)
    DateOfBirth = Column(Date, nullable=False)
    ChildID = Column(String(20), nullable=False, unique=True)
    SexID = Column(ForeignKey('Main.Sex.SexID'), nullable=False)
    GeneticRiskID = Column(ForeignKey('Main.GeneticRisk.GeneticRiskID'), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    GeneticRisk = relationship('GeneticRisk')
    Sex = relationship('Sex')


class User(Base):
    __tablename__ = 'User'
    __table_args__ = {'schema': 'Main'}

    UserID = Column(Integer, primary_key=True)
    UserName = Column(String(128), unique=True)
    Password = Column(String(128))
    FirstName = Column(String(100), nullable=False)
    MiddleName = Column(String(100))
    LastName = Column(String(100), nullable=False)
    Email = Column(String(256), nullable=False, unique=True)
    UserTypeID = Column(ForeignKey('Main.UserType.UserTypeID'), nullable=False)
    IsActive = Column(Boolean, nullable=False, server_default=text("true"))
    IsAdmin = Column(Boolean, nullable=False, server_default=text("false"))
    IsLocked = Column(Boolean, nullable=False, server_default=text("false"))
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    UserType = relationship('UserType')


class UtteranceTypeAnnotation(Base):
    __tablename__ = 'UtteranceTypeAnnotation'
    __table_args__ = {'schema': 'Main'}

    UtteranceTypeAnnotationID = Column(Integer, primary_key=True)
    UtteranceTypeID = Column(ForeignKey('Main.UtteranceType.UtteranceTypeID'), nullable=False)
    Description = Column(String(50), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    UtteranceType = relationship('UtteranceType')


class Recording(Base):
    __tablename__ = 'Recording'
    __table_args__ = (
        CheckConstraint('("EndTime" > "StartTime") AND (("EndTime" - "StartTime") = "Duration")'),
        UniqueConstraint('AssessmentID', 'RecordingTypeID'),
        {'schema': 'Main'}
    )

    RecordingID = Column(Integer, primary_key=True)
    RecordingTypeID = Column(ForeignKey('Main.RecordingType.RecordingTypeID'), nullable=False)
    ParticipantID = Column(ForeignKey('Main.Participant.ParticipantID'), nullable=False)
    AssessmentID = Column(String(25), nullable=False)
    RecordingDate = Column(Date, nullable=False)
    AgeAtRecordingInMonths = Column(Float, nullable=False)
    BaseFileName = Column(String(100), nullable=False)
    StartTime = Column(DateTime, nullable=False)
    EndTime = Column(DateTime, nullable=False)
    ChildWakeTime = Column(DateTime, comment='A manually entered value. Only valid for Home recordings.')
    Duration = Column(INTERVAL, nullable=False)
    ErrorCodeID = Column(ForeignKey('Main.ErrorCode.ErrorCodeID'))
    ConsentFormVersion = Column(SmallInteger, comment='A manually entered value. Only valid for Home recordings.')
    ChildWordCount = Column(SmallInteger, comment='A manually entered value. Only valid for Home recordings.')
    HasPhrases = Column(Boolean, comment='A manually entered value. Only valid for Home recordings.')
    DataUseOptionID = Column(ForeignKey('Main.DataUseOption.DataUseOptionID'), comment='A manually entered value. Only valid for Home recordings.')
    AdultWordCount = Column(Integer)
    AdultWordCountPercentile = Column(Integer)
    AdultWordCountStandardScore = Column(Float)
    ConversationalTurnCount = Column(Integer)
    ConversationalTurnPercentile = Column(Integer)
    ConversationalTurnStandardScore = Column(Float)
    ChildVocalizationCount = Column(Integer)
    ChildVocalizationPercentile = Column(Integer)
    ChildVocalizationStandardScore = Column(Float)
    AutomatedVocalizationAssessmentPercentile = Column(Integer)
    AutomatedVocalizationAssessmentStandardScore = Column(Float)
    VocalProductivityPercentile = Column(Integer)
    VocalProductivityStandardScore = Column(Float)
    TimeZone = Column(String(50), nullable=False)
    Meaningful = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='Duration coming from all near and clear human sources.')
    Silence = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='Duration in which there is little to no ambient sound.')
    Electronic = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='Duration coming from television or other electronic sources. (SP: TV_Elec).')
    Distant = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='SP: Duration coming from all far-field human sources.')
    Noise = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='SP: Duration coming from all near noises (bumps, claps, etc.)')
    Overlap = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='SP: Duration coded as speech overlapping with something else.')
    Notes = Column(Text)
    IsScrubbed = Column(Boolean, nullable=False, server_default=text("false"))
    IsValid = Column(Boolean, nullable=False, server_default=text("true"))
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    DataUseOption = relationship('DataUseOption')
    ErrorCode = relationship('ErrorCode')
    Participant = relationship('Participant')
    RecordingType = relationship('RecordingType')


class Session(Base):
    __tablename__ = 'Session'
    __table_args__ = {'schema': 'Main'}

    SessionID = Column(Integer, primary_key=True)
    UserID = Column(ForeignKey('Main.User.UserID'), nullable=False)
    StartedOn = Column(DateTime, nullable=False, server_default=text("now()"), comment='The date and time the user has logged in to the system.')
    LastAccessedOn = Column(DateTime, nullable=False, server_default=text("now()"), comment='The date and time the user has entered the last utterance code. This is updated with every coding entered.')

    User = relationship('User')


class CodingBatch(Base):
    __tablename__ = 'CodingBatch'
    __table_args__ = {'schema': 'Main'}

    CodingBatchID = Column(Integer, primary_key=True)
    RecordingID = Column(ForeignKey('Main.Recording.RecordingID'), nullable=False)
    Group = Column(Integer, nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    Recording = relationship('Recording')


class DayTypicality(Base):
    __tablename__ = 'DayTypicality'
    __table_args__ = {'schema': 'Main'}

    DayTypicalityID = Column(Integer, primary_key=True)
    RecordingID = Column(ForeignKey('Main.Recording.RecordingID'), nullable=False)
    TypicalityPercentage = Column(Float, nullable=False)
    AddedBy = Column(ForeignKey('Main.User.UserID'), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    User = relationship('User')
    Recording = relationship('Recording')


class ExclusionDuration(Base):
    __tablename__ = 'ExclusionDuration'
    __table_args__ = (
        CheckConstraint('("EndTime" > "StartTime") AND (("EndTime" - "StartTime") = "Duration")'),
        UniqueConstraint('StartTime', 'EndTime'),
        {'schema': 'Main'}
    )

    ExclusionDurationID = Column(Integer, primary_key=True)
    RecordingID = Column(ForeignKey('Main.Recording.RecordingID'), nullable=False)
    StartTime = Column(DateTime, nullable=False)
    EndTime = Column(DateTime, nullable=False)
    Duration = Column(INTERVAL, nullable=False)
    ExclusionTypeID = Column(ForeignKey('Main.ExclusionType.ExclusionTypeID'), nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    ExclusionType = relationship('ExclusionType')
    Recording = relationship('Recording')


class InterpretiveTimeSegment(Base):
    __tablename__ = 'InterpretiveTimeSegment'
    __table_args__ = {'schema': 'Main'}

    InterpretiveTimeSegmentID = Column(Integer, primary_key=True)
    RecordingID = Column(ForeignKey('Main.Recording.RecordingID'), nullable=False)
    FileData = Column(LargeBinary, nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    Recording = relationship('Recording')


class Segment(Base):
    __tablename__ = 'Segment'
    __table_args__ = (
        CheckConstraint('"EndTimeInSeconds" > "StartTimeInSeconds"'),
        CheckConstraint('("EndTime" > "StartTime") AND (("EndTime" - "StartTime") = "Duration")'),
        UniqueConstraint('RecordingID', 'StartTime', 'EndTime'),
        {'schema': 'Main'}
    )

    SegmentID = Column(Integer, primary_key=True)
    RecordingID = Column(ForeignKey('Main.Recording.RecordingID'), nullable=False)
    IsSelected = Column(Boolean, nullable=False, server_default=text("false"))
    SelectionCriterionID = Column(ForeignKey('Main.SelectionCriterion.SelectionCriterionID'))
    StartTime = Column(DateTime, nullable=False)
    EndTime = Column(DateTime, nullable=False)
    StartTimeInSeconds = Column(Float, nullable=False, comment='The starting time of the segment, in seconds, with respect to the recording.')
    EndTimeInSeconds = Column(Float, nullable=False, comment='The starting time of the segment, in seconds, with respect to the recording.')
    Duration = Column(INTERVAL, nullable=False)
    AdultWordCount = Column(Integer, nullable=False, server_default=text("0"))
    ConversationalTurnCount = Column(Integer, nullable=False, server_default=text("0"))
    ChildVocalizationCount = Column(Integer, nullable=False, server_default=text("0"))
    Meaningful = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='Duration coming from all near and clear human sources.')
    Silence = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='Duration in which there is little to no ambient sound.')
    Electronic = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='Duration coming from television or other electronic sources. (SP: TV_Elec).')
    Distant = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='SP: Duration coming from all far-field human sources.')
    Noise = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='SP: Duration coming from all near noises (bumps, claps, etc.)')
    Overlap = Column(INTERVAL, nullable=False, server_default=text("'00:00:00'::interval"), comment='SP: Duration coded as speech overlapping with something else.')
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    Recording = relationship('Recording')
    SelectionCriterion = relationship('SelectionCriterion')


class Utterance(Base):
    __tablename__ = 'Utterance'
    __table_args__ = (
        CheckConstraint('"EndTimeInSeconds" > "StartTimeInSeconds"'),
        UniqueConstraint('SegmentID', 'StartTimeInSeconds', 'EndTimeInSeconds'),
        {'schema': 'Main'}
    )

    UtteranceID = Column(Integer, primary_key=True)
    SegmentID = Column(ForeignKey('Main.Segment.SegmentID'), nullable=False)
    StartTimeInSeconds = Column(Float, nullable=False, comment='The starting time of the utterance, with respect to the sound file, in seconds.')
    EndTimeInSeconds = Column(Float, nullable=False, comment='The ending time of the utterance, with respect to the sound file, in seconds.')
    DurationInSeconds = Column(Float, nullable=False, comment='The difference, in seconds, between the starting time and the ending time of the utterance.')
    AudioFileName = Column(String(256), nullable=False)
    AudioFileData = Column(LargeBinary, nullable=False)
    MinimumPitch = Column(Float, nullable=False)
    MaximumPitch = Column(Float, nullable=False)
    AveragePitch = Column(Float, nullable=False)
    PitchRange = Column(Float, nullable=False)
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    Segment = relationship('Segment')


class UtteranceCoding(Base):
    __tablename__ = 'UtteranceCoding'
    __table_args__ = (
        UniqueConstraint('UtteranceID', 'CoderID'),
        {'schema': 'Main'}
    )

    UtteranceCodingID = Column(Integer, primary_key=True)
    UtteranceID = Column(ForeignKey('Main.Utterance.UtteranceID'), nullable=False)
    CoderID = Column(ForeignKey('Main.User.UserID'), nullable=False)
    UtteranceTypeAnnotationID = Column(ForeignKey('Main.UtteranceTypeAnnotation.UtteranceTypeAnnotationID'), nullable=False)
    TotalSyllableCount = Column(SmallInteger, nullable=False, server_default=text("0"))
    CanonicalSyllableCount = Column(SmallInteger, nullable=False, server_default=text("0"))
    WordSyllableCount = Column(SmallInteger, nullable=False, server_default=text("0"))
    WordCount = Column(SmallInteger, nullable=False, server_default=text("0"))
    NonCanonicalSyllableCount = Column(SmallInteger, nullable=False, server_default=text("0"))
    Comments = Column(Text)
    IsAcceptable = Column(Boolean, nullable=False, server_default=text("true"))
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    User = relationship('User')
    Utterance = relationship('Utterance')
    UtteranceTypeAnnotation = relationship('UtteranceTypeAnnotation')


class UtteranceSamplePool(Base):
    __tablename__ = 'UtteranceSamplePool'
    __table_args__ = {'schema': 'Main'}

    UtteranceSamplePoolID = Column(Integer, primary_key=True)
    UtteranceID = Column(ForeignKey('Main.Utterance.UtteranceID'), nullable=False)
    CodingBatchGroup = Column(Integer, nullable=False)
    CoderID = Column(ForeignKey('Main.User.UserID'))
    IsProcessing = Column(Boolean, nullable=False, server_default=text("false"))
    AddedOn = Column(DateTime, nullable=False, server_default=text("now()"))
    ModifiedOn = Column(DateTime, nullable=False, server_default=text("now()"))

    User = relationship('User')
    Utterance = relationship('Utterance')
