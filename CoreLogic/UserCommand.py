"""
User Command

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
import logging
from attr.validators import instance_of

from Models.UserModel import UserModel
from CoreLogic.BaseCommand import BaseCommand, BaseRequest, BaseResponse
from DataAccess.UserRepository import UserRepository
from DataAccess.SessionRepository import SessionRepository


class UserRequest(BaseRequest):
    @attr.s
    class RequestForGetUserWithCheck:
        UserName = attr.ib(validator=instance_of(str))
        Password = attr.ib(validator=instance_of(str))

    @attr.s
    class RequestForUpdateUser:
        User = attr.ib(validator=instance_of(UserModel))
        SessionID = attr.ib(validator=instance_of(int))


class UserResponse(BaseResponse):
    @attr.s
    class ResponseForGetUserWithCheck:
        User = attr.ib(validator=instance_of(UserModel))
        SessionID = attr.ib(validator=instance_of(int))


class UserCommand(BaseCommand):
    def __init__(self):
        """
        Initializes the command to be used against the repo.
        """
        super().__init__()

        self.repository = UserRepository()
        self.sessionRepository = SessionRepository()
        self.response = UserResponse()

    def executeForGetUserWithCheck(self, request: UserRequest.RequestForGetUserWithCheck) -> UserResponse:
        """
        Uses the given request to connect to the DB and returns the response.
        """
        try:
            message = f'Attempting to get information for user "{request.UserName}".'
            self.logger.debug(message, extra={"UserID": 0, "SessionID": 0})

            isValid = self.repository.checkForUser(request.UserName, request.Password)

            if not isValid:
                self.response.isSuccessful = False
                self.response.message = "Provided credentials are NOT correct."

                message = f"User {request.UserName} does not exist."
                self.logger.debug(message, extra={"UserID": 0, "SessionID": 0})
                return self.response

            user = self.repository.getByUserName(request.UserName)

            sessionID = self.sessionRepository.getNewCodingSessionID(user.UserID)

            self.response.isSuccessful = True

            message = f"User {user.UserName} retrieved successfully."
            self.logger.info(message, extra={"UserID": user.UserID, "SessionID": sessionID})

            self.response.result = self.response.ResponseForGetUserWithCheck(User=user, SessionID=sessionID)

        except Exception as ex:

            self.response.isSuccessful = False
            self.response.message = "Unable to perform operation 'GetUserWithCheck'. An exception has occurred."
            self.response.exception = ex

            message = f'An exception occurred when retrieving information for user "{request.UserName}".'
            self.logger.error(message, exc_info=True, extra={"UserID": 0, "SessionID": 0})

        return self.response

    def executeForUpdateUser(self, request: UserRequest.RequestForUpdateUser) -> UserResponse:
        """
        Uses the given request to connect to the DB and returns the response.
        """
        attributeMap = {"UserID": request.User.UserID, "SessionID": request.SessionID}
        try:
            message = (
                f"Attempting to update information for user "
                f"(ID: {request.User.UserID}, UserName: {request.User.UserName})."
            )
            self.logger.debug(message, extra=attributeMap)

            self.repository.updateUser(request.User)

            self.response.isSuccessful = True

            message = (
                f"Updating information was successful for user (ID: {request.User.UserID}, "
                f"UserName: {request.User.UserName})."
            )
            self.logger.debug(message, extra=attributeMap)

        except Exception as ex:

            self.response.isSuccessful = False
            self.response.message = "Unable to perform operation 'GetUserWithCheck'. An exception has occurred."
            self.response.exception = ex
            message = (
                f"An exception occurred when updating information for user "
                f"(ID: {request.User.UserID}, UserName: {request.User.UserName})."
            )
            self.logger.error(message, exc_info=True, extra=attributeMap)

        return self.response
