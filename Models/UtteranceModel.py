"""
Utterance Model

Represents the information associated with an utterance pulled from the coding sample pool, so that it can be used for
for coding.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


import attr
from attr.validators import instance_of


@attr.s
class UtteranceModel:
    UtteranceSamplePoolID = attr.ib(validator=instance_of(int), default=-1)
    UtteranceID = attr.ib(validator=instance_of(int), default=-1)
    DurationInSeconds = attr.ib(validator=instance_of(float), default=0.0)
    AudioFileName = attr.ib(validator=instance_of(str), default="")
    AudioFilePath = attr.ib(validator=instance_of(str), default="")
    AudioFileData = attr.ib(validator=instance_of(bytes), default=b"")
