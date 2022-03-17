"""
Defines the DB Access methods to the User table.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


import base64
from typing import List
from hashlib import scrypt
from secrets import token_bytes
from datetime import datetime
from DataAccess.BaseDB import User
from DataAccess.BaseRepository import BaseRepository
from Models.UserModel import UserModel


class UserRepository(BaseRepository):
    def __init__(self):
        """
        Initializes a new instance of the repository.
        """
        super().__init__()

    @staticmethod
    def convertPasswordToHash(password: str) -> str:
        """
        Given the password entered by the user, applies the hashing algorithm to store the password hash in the DB.
        """

        # NOTE: Password Content in the DB:
        #   algorithm, iterationCount, blockSize, parallelizationFactor, salt, dbPassword
        #   static values:
        #       algorithm = scrypt
        #       iterationCount = 16384
        #       blockSize = 8
        #       parallelizationFactor = 1
        #   dynamic values:
        #       salt = token_urlsafe(12)

        algorithm = "scrypt"
        iterationCount = 16384
        blockSize = 8
        pFactor = 1
        salt = token_bytes(12)
        salt64Bytes = base64.b64encode(salt)
        passwordBytes = password.encode("UTF-8")

        passwordHash = scrypt(passwordBytes, salt=salt64Bytes, n=iterationCount, r=blockSize, p=pFactor)
        passwordHash64String = str(base64.b64encode(passwordHash), "UTF-8")
        salt64String = str(salt64Bytes, "UTF-8")

        elements = [
            algorithm,
            str(iterationCount),
            str(blockSize),
            str(pFactor),
            salt64String,
            passwordHash64String,
        ]

        dbPassword = "$".join(elements)

        return dbPassword

    def getAll(self) -> List[UserModel]:
        """
        Returns all available Users. This is an admin functionality for auditing.
        """

        dbUsers = self.DbSession.query(User).all()

        users = []
        for dbUser in dbUsers:
            user = UserModel(
                UserID=dbUser.UserID,
                UserName=dbUser.UserName,
                DbPassword=dbUser.Password,
                NewPassword="",
                FirstName=dbUser.FirstName,
                MiddleName=dbUser.MiddleName,
                LastName=dbUser.LastName,
                Email=dbUser.Email,
                UserType=dbUser.UserType.Description,
                UserTypeID=dbUser.UserTypeID,
                IsActive=dbUser.IsActive,
                IsAdmin=dbUser.IsAdmin,
                IsLocked=dbUser.IsLocked,
            )

            users.append(user)

        return users

    def addNewUser(self, userName: str, password: str, firstName: str, middleName: str, lastName: str, email: str, userType: int) -> bool:
        """
        Adds a new user to the system. This is an admin functionality for auditing.
        """

        dbUsers = self.DbSession.query(User).order_by(User.UserID).all()

        # Check if the user exists.
        if any(dbUser.UserName == userName for dbUser in dbUsers):
            return False

        lastID = dbUsers[-1].UserID
        newPassword = self.convertPasswordToHash(password)

        dbUser = User(
            UserID=lastID + 100,
            UserName=userName,
            Password=newPassword,
            FirstName=firstName,
            MiddleName=middleName if middleName != "" else None,
            LastName=lastName,
            Email=email,
            UserTypeID=userType,
            IsActive=True,
            IsAdmin=False,
            IsLocked=False,
            ModifiedOn=datetime.now()
        )

        self.DbSession.add(dbUser)

        return True

    def getByUserName(self, userName: str) -> UserModel:
        """
        Returns the user that matches the user name provided. This method assume existence of the given user.
        """

        dbUser = self.DbSession.query(User).filter(User.UserName == userName).one()

        user = UserModel(
            UserID=dbUser.UserID,
            UserName=dbUser.UserName,
            DbPassword=dbUser.Password,
            NewPassword="",
            FirstName=dbUser.FirstName,
            MiddleName=dbUser.MiddleName,
            LastName=dbUser.LastName,
            Email=dbUser.Email,
            UserType=dbUser.UserType.Description,
            UserTypeID=dbUser.UserTypeID,
            IsActive=dbUser.IsActive,
            IsAdmin=dbUser.IsAdmin,
            IsLocked=dbUser.IsLocked,
        )

        return user

    def updateUser(self, user: UserModel) -> None:
        """
        Updates the passed user information in the DB. Note that "commit()" must be called externally.
        """
        dbUser = self.DbSession.query(User).filter(User.UserID == user.UserID).one()

        if user.NewPassword:
            newPassword = self.convertPasswordToHash(user.NewPassword)
            dbUser.Password = newPassword
            user.DBPassword = newPassword
            user.NewPassword = ""

        dbUser.UserID = user.UserID
        dbUser.UserName = user.UserName
        dbUser.FirstName = user.FirstName
        dbUser.MiddleName = user.MiddleName
        dbUser.LastName = user.LastName
        dbUser.Email = user.Email
        dbUser.UserTypeID = user.UserTypeID
        dbUser.IsActive = user.IsActive
        dbUser.IsAdmin = user.IsAdmin
        dbUser.IsLocked = user.IsLocked
        dbUser.ModifiedOn = datetime.now()

    def checkForUser(self, userName: str, password: str) -> bool:
        """
        Checks whether the current user name and password matches an entry in the DB.
        """
        user = self.DbSession.query(User).filter(User.UserName == userName).one()

        if user.Password is None:
            return False

        _, iterationCount, blockSize, pFactor, salt, dbPasswordHash = user.Password.split("$")

        passwordBytes = password.encode("UTF-8")
        saltBytes = salt.encode("UTF-8")

        passwordHash = scrypt(passwordBytes, salt=saltBytes, n=int(iterationCount), r=int(blockSize), p=int(pFactor),)
        passwordHash64 = str(base64.b64encode(passwordHash), "UTF-8")

        return passwordHash64 == dbPasswordHash and not user.IsLocked
