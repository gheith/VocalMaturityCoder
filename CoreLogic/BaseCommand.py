"""
Base Command

This contains the common properties to be used across Command, Request to and Response instances.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


import logging
from DataAccess.BaseRepository import BaseRepository


class BaseRequest:
    pass


class BaseResponse:
    def __init__(self):
        self.isSuccessful = False
        self.message = None
        self.exception = None
        self.result = None


class BaseCommand:

    DbSession = None

    def __init__(self):
        """
        Initializes the command to be used against the repo.
        """
        self.logger = logging.getLogger()

        # Set the static property first.
        BaseRepository.DbSession = self.DbSession

    @classmethod
    def endDbSession(cls) -> None:
        """
        Closes the current DB Session.
        """
        BaseRepository.endDbSession()

    @classmethod
    def rollbackDbSession(cls) -> None:
        """
        Rollbacks the current transaction, if an error has occurred.
        """
        BaseRepository.rollbackDbSession()
