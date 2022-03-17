"""
BaseRepository

This file add common functionality to all generated repositories. It is expected to be inherited from and extended.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


from sqlalchemy.orm.session import Session


class BaseRepository:
    """
    Defines the base class for all repositories.
    """

    DbSession: Session = None

    @classmethod
    def endDbSession(cls):
        """
        Close the DB Session, as the last action in the lifetime of the program..
        """
        if cls.DbSession is not None:
            cls.DbSession.close()

    @classmethod
    def rollbackDbSession(cls):
        """
        Rollbacks the current transaction, if an error has occurred.
        """
        if cls.DbSession is not None:
            cls.DbSession.rollback()

    def commitChanges(self) -> None:
        """
        Performs a DB Session Commit via direct invocation. This prevents calling commit multiple times with no need.
        """

        self.DbSession.commit()
