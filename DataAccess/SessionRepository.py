"""
Defines the DB Access methods to the DB table 'Session'.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


from typing import List
from datetime import datetime
from DataAccess.BaseDB import Session
from DataAccess.BaseRepository import BaseRepository


class SessionRepository(BaseRepository):
    def __init__(self):
        """
        Initializes a new instance of the repository.
        """
        super().__init__()

    def getAll(self) -> List[Session]:
        """
        Returns all available sessions. This is an admin functionality for auditing.
        """

        return self.DbSession.query(Session).all()

    def getByUser(self, userID: int) -> List[Session]:
        """
        Returns a list of all sessions for a given user.
        """
        return self.DbSession.query(Session).filter(Session.UserID == userID).all()

    def getNewCodingSessionID(self, userID: int) -> int:
        """
        Creates a new coding session entry in the DB, and returns the ID of that session to be used henceforth during
        the application lifetime.
        """
        session = Session(UserID=userID, StartedOn=datetime.now(), LastAccessedOn=datetime.now())

        self.DbSession.add(session)
        self.DbSession.commit()

        newSessionID = session.SessionID
        return newSessionID

    def updateSessionInformation(self, sessionID: int) -> None:
        """
        Updates the Session with the last accessed date time.
        """
        session = self.DbSession.query(Session).filter(Session.SessionID == sessionID).one()
        session.LastAccessedOn = datetime.now()

        self.DbSession.commit()
