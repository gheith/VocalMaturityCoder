"""
Utterance Command

This contains the Command, Request to and Response from the Data Access. The general pattern for using this class goes
as follows:

    1- Create a Request with one of the inner classes, 'RequestFor...'.
    2- Invoke the method 'executeFor...' in the Command.
    3- In the method, build and return a Response, with one of the inner classes, 'ResponseFor...' populates.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


import attr
from attr.validators import instance_of

import logging
from Models.UtteranceModel import UtteranceModel
from Models.UtteranceCodeModel import UtteranceCodeModel

from CoreLogic.BaseCommand import BaseCommand, BaseRequest, BaseResponse
from DataAccess.SessionRepository import SessionRepository
from DataAccess.UtteranceRepository import UtteranceRepository


class UtteranceRequest(BaseRequest):
    @attr.s
    class RequestForGetNewUtterance:
        UserID = attr.ib(validator=instance_of(int))
        SessionID = attr.ib(validator=instance_of(int))

    @attr.s
    class RequestForSaveOrUpdateUtteranceCode:
        UserID = attr.ib(validator=instance_of(int))
        UtteranceID = attr.ib(validator=instance_of(int))
        UtteranceCode = attr.ib(validator=instance_of(UtteranceCodeModel))
        SessionID = attr.ib(validator=instance_of(int))


class UtteranceResponse(BaseResponse):
    @attr.s
    class ResponseForGetNewUtterance:
        Utterance = attr.ib(validator=instance_of(UtteranceModel))


class UtteranceCommand(BaseCommand):
    def __init__(self):
        """
        Initializes the command to be used against the repo.
        """
        super().__init__()

        self.utteranceRepository = UtteranceRepository()
        self.sessionRepository = SessionRepository()
        self.response = UtteranceResponse()

    def executeForGetNewUtterance(self, request: UtteranceRequest.RequestForGetNewUtterance) -> UtteranceResponse:
        """
        Uses the given request to connect to the DB and returns the response.
        """

        attributeMap = {"UserID": request.UserID, "SessionID": request.SessionID}

        try:
            self.logger.debug("Attempting to get new utterance.", extra=attributeMap)

            utterance = self.utteranceRepository.getSampleForUser(request.UserID)
            self.response.isSuccessful = True

            self.logger.debug("Database hit was successful.", extra=attributeMap)

            if utterance is not None:
                self.response.result = self.response.ResponseForGetNewUtterance(Utterance=utterance)
                self.logger.info(f"Utterance ID {utterance.UtteranceID} retrieved.", extra=attributeMap)
            else:
                self.logger.info(f"No utterances available for coding.", extra=attributeMap)
                self.response.message = "There does not seem to be an utterance available for you to code."

            self.sessionRepository.updateSessionInformation(request.SessionID)
        except Exception as ex:

            self.response.isSuccessful = False
            self.response.message = "Unable to perform operation 'GetNewUtterance'. An exception has occurred."
            self.response.exception = ex

            self.logger.error(f"An exception occurred during database hit.", exc_info=True, extra=attributeMap)
            self.rollbackDbSession()

        return self.response

    def executeForSaveOrUpdateUtteranceCode(
        self, request: UtteranceRequest.RequestForSaveOrUpdateUtteranceCode
    ) -> UtteranceResponse:
        """
        Uses the given request to connect to the DB and returns the response.
        """
        attributeMap = {"UserID": request.UserID, "SessionID": request.SessionID}

        try:
            message = f"Attempting to save utterance code for Utterance ID {request.UtteranceID}."
            self.logger.debug(message, extra=attributeMap)

            # New Code.
            if request.UtteranceCode.UtteranceCodingID == -1:
                operation = "saved"
                isPersisted = self.utteranceRepository.saveNewUtteranceCode(request.UtteranceCode)
            else:
                operation = "updated"
                isPersisted = self.utteranceRepository.updateUtteranceCode(request.UtteranceCode)

            self.response.isSuccessful = isPersisted

            if isPersisted:
                message = f"Successfully {operation} new code for Utterance ID {request.UtteranceID}."
                self.logger.info(message, extra=attributeMap)
            else:
                message = f"New code for Utterance ID {request.UtteranceID} cannot be {operation}."
                self.logger.error(message, extra=attributeMap)
            self.sessionRepository.updateSessionInformation(request.SessionID)

        except Exception as ex:

            self.response.isSuccessful = False
            self.response.message = "Unable to Save/Update Utterance Code. An exception has occurred."
            self.response.exception = ex
            message = f"An exception occurred while processing Utterance ID {request.UtteranceID}."
            self.logger.error(message, exc_info=True, extra=attributeMap)


        return self.response
