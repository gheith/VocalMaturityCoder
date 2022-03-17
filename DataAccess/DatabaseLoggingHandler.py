"""
DbHandler

Represents a logging handler that logs entries to the Database, using the SQL Alchemy engine.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"

import logging
import traceback
from datetime import datetime
from sqlalchemy.orm.session import Session
from DataAccess.BaseDB import LogEntry


class DatabaseLoggingHandler(logging.Handler):

    DbSession: Session = None
    userID = 0
    sessionID = 0

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emits the current log record to the current handler.
        """
        trace = traceback.format_exc() if record.exc_info else None

        log = LogEntry(
            TimeStamp=datetime.now(),
            UserID=self.userID,
            SessionID=self.sessionID,
            Level=record.levelname,
            Module=record.module,
            Function=record.funcName,
            Message=record.msg,
            Exception=trace,
        )

        self.DbSession.add(log)
        self.DbSession.commit()
