"""
VMC Loader File

This file is the entry point of the application. It is intended to be used to perform a check for newer versions
of the application, if they exist, to auto-update the application to the latest.

This form contains icons obtained from:
<a href='https://dryicons.com/'> Icon by Dryicons </a>
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.3.0"
__status__ = "Production"


import sys
import time
import logging
from logging.handlers import TimedRotatingFileHandler
from logging.config import fileConfig
from os.path import join, dirname, abspath
from enum import Enum
from typing import Tuple

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QSplashScreen

from Presentation.LoginForm import LoginForm
from Presentation.CodingGUI import CodingGUI
from DataAccess.DatabaseLoggingHandler import DatabaseLoggingHandler
from MasterStyleSheet import masterStyleSheet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from qdarkstyle import load_stylesheet_pyqt5
from CloudUpdater import performApplicationUpdate

# TODO: Populate this varible with the location of the audio files.
DataFolder = r""


class ConnectionType(Enum):
    Development = 0
    Production = 1


def getConnectionInformation(connectionType: ConnectionType) -> Tuple[str, bytes]:
    """
    Loads the DB connection string elements to establish a connection to the DB.
    """

    # TODO: Populate the property map with the PostgreSQL connection info.
    if connectionType == ConnectionType.Production:
        propertyMap = {
            "Dialect": "postgresql",
            "UserName": "",
            "Password": "",
            "Server": "",
            "Port": "5432",
            "DatabaseName": "",
            "AudioEncryptionKey": "",
        }

    # TODO: Pick an encryption password to secure the audio files in the cloud DB.
    else:
        propertyMap = {
            "Dialect": "postgresql",
            "UserName": "postgres",
            "Password": "",
            "Server": "localhost",
            "Port": "5432",
            "DatabaseName": "VocalMaturityDB",
            "AudioEncryptionKey": "<Put the encryption Password here.>",
        }

    # Connection parameters.
    dialect = propertyMap["Dialect"]
    userName = propertyMap["UserName"]
    password = propertyMap["Password"]
    server = propertyMap["Server"]
    port = propertyMap["Port"]
    dbName = propertyMap["DatabaseName"]

    connection = f"{dialect}://{userName}:{password}@{server}:{port}/{dbName}"

    # Audio Encryption Key.
    encryptionKey = propertyMap["AudioEncryptionKey"].encode("UTF-8")

    return connection, encryptionKey


def showSplash(app: QApplication, mainForm: QWidget):
    """
    Shows a splash screen until the main application starts.

    :param mainForm: The widget that will take over from the splash screen.
    :param app: The QtApplication instance that runs this app.
    """

    # Create and display the splash screen.
    splashScreen = QPixmap(":/images/SplashSmall.png")
    splash = QSplashScreen(splashScreen, Qt.WindowStaysOnTopHint)
    splash.setMask(splashScreen.mask())
    splash.show()
    app.processEvents()
    time.sleep(0.75)
    splash.finish(mainForm)
    app.processEvents()


def setApplicationProperties(app: QApplication):
    """
    Sets basic texts in the application to allow for better branding.
    """
    app.setApplicationName("Vocal Maturity Coding Application")
    app.setDesktopFileName("VMC")
    app.setApplicationDisplayName("Vocal Maturity Coding Application")
    app.setOrganizationName("NDD Lab")
    app.setApplicationVersion(__version__)

    app.setStyleSheet(masterStyleSheet)


def startCodingApplication(appLogger, SessionMaker, qtApp, encryptionKey) -> int:
    """
    Starts the execution of the coding application. First, this method captures the user login, then we pass these
    to the Coding GUI.
    """

    userID = 0
    sessionID = 0
    exitCode = 0

    try:
        appLogger.info("VMC Application Starting.", extra={"UserID": 0, "SessionID": 0})
        ui = LoginForm(dbSession=SessionMaker())

        showSplash(qtApp, ui)

        ui.show()

        qtApp.exec_()

        if not ui.isLoginSuccessful:
            appLogger.error("Login was NOT successful.", extra={"UserID": 0, "SessionID": 0})
            return -1

        userID = ui.user.UserID
        sessionID = ui.sessionID

        DatabaseLoggingHandler.userID = userID
        DatabaseLoggingHandler.sessionID = sessionID

        appLogger.debug("Login Successful.", extra={"UserID": userID, "SessionID": sessionID})

        ui = CodingGUI(ui.user, ui.sessionID, encryptionKey)
        ui.show()
        qtApp.exec_()

    except:
        exMessage = "A critical error has occurred. The application will now close."
        print(exMessage)
        appLogger.critical(exMessage, exc_info=True, extra={"UserID": userID, "SessionID": sessionID})
        exitCode = -2

    finally:
        appLogger.info("VMC Application Ending.", extra={"UserID": userID, "SessionID": sessionID})

    return exitCode


if __name__ == "__main__":

    cType = ConnectionType.Production
    connectionStr, encKey = getConnectionInformation(cType)

    engine = create_engine(connectionStr, isolation_level="READ_COMMITTED")
    dbSessionMaker = sessionmaker(bind=engine, expire_on_commit=False)
    DatabaseLoggingHandler.DbSession = dbSessionMaker()

    configFilePath = join(dirname(abspath(__file__)), 'log.config')
    fileConfig(configFilePath)
    logger = logging.getLogger()

    # This code will help identify the machine & the log file location.
    if logger.handlers and type(logger.handlers[0]) is TimedRotatingFileHandler:
        logFilePath = logger.handlers[0].baseFilename
        message = f'Logging to: "{logFilePath}"'
        print(message)
        logger.info(message, extra={"UserID": 0, "SessionID": 0})

    # Suppress AWS Logging.
    logging.getLogger('boto3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)
    logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    # Check for a new application version.
    hasUpdated = performApplicationUpdate()

    if hasUpdated:
        message = f'Application has been updated, and will close. Please restart the application.'
        print(message)
        logger.info(message, extra={"UserID": 0, "SessionID": 0})
        sys.exit()

    # Now, we start the GUI application.
    guiApp = QApplication(sys.argv)
    setApplicationProperties(guiApp)

    # Dummy Statement to load DarkStyle resources.
    load_stylesheet_pyqt5()

    code = startCodingApplication(logger, dbSessionMaker, guiApp, encKey)

    sys.exit(code)
