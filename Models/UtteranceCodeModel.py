"""
Utterance Code Model

Represents all the coding information associated with the utterance, as entered by the current coder.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"

import attr
from attr.validators import instance_of


@attr.s
class UtteranceCodeModel:
    UtteranceSamplePoolID = attr.ib(validator=instance_of(int), default=-1)

    # This field will not be used except if the user changes their code, which can only happen in the same session.
    UtteranceCodingID = attr.ib(validator=instance_of(int), default=-1)
    UtteranceID = attr.ib(validator=instance_of(int), default=-1)
    CoderID = attr.ib(validator=instance_of(int), default=-1)
    Annotation = attr.ib(validator=instance_of(str), default="")
    TotalSyllableCount = attr.ib(validator=instance_of(int), default=0)
    CanonicalSyllableCount = attr.ib(validator=instance_of(int), default=0)
    WordSyllableCount = attr.ib(validator=instance_of(int), default=0)
    WordCount = attr.ib(validator=instance_of(int), default=0)
    Comments = attr.ib(validator=instance_of(str), default="")
