"""
The consumer class that enhances the PyQt5 generated Python class with more logic.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


import logging
from PyQt5.QtCore import Qt, QPoint, QSequentialAnimationGroup, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QMouseEvent, QKeyEvent, QPixmap
from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect, QLineEdit

from Presentation.LoginFormBase import Ui_FormLogin
from CoreLogic.UserCommand import *
from sqlalchemy.orm.session import Session


class LoginForm(QWidget, Ui_FormLogin):
    def __init__(
        self, loginUser: str = "Coder", dbSession: Session = None, parent: QWidget = None,
    ):
        """
        Initializes an instance of the login form, and passes the user type as a string.

        :param loginUser: A string that is either "Coder" or "Admin"
        :param parent: The parent form of this form. This value is not used, but is included as a convention.
        """
        super(LoginForm, self).__init__(parent)
        self.setupUi(self)

        self.logger = logging.getLogger()

        self.isLoginSuccessful = False
        self.user = None
        self.sessionID = 0

        # Sets the DB Session for all commands.
        BaseCommand.DbSession = dbSession

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(False)

        # Modification and set up to the form.
        self.lblLogin = f"{loginUser} Login"

        self._setupSuccessAnimation()

        self.shakingAnimationGroup = None
        self.btnLogin.clicked.connect(self._loginToApplication)
        self.btnExit.clicked.connect(self.close)

        self.txtUserName.textChanged.connect(self._clearWarningOnEdit)
        self.txtPassword.textChanged.connect(self._clearWarningOnEdit)

        # Mouse-related variables.
        self.mousePosition = 0
        self.isMousePressed = False

        self.logDebug("Login UI Initiated.")

    def close(self) -> None:
        """
        Overrides the closing of the window to guarantee cleaning resources.
        """
        BaseCommand.endDbSession()
        self.logDebug("Login UI Closing.")
        super().close()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Overrides the event provided by the base Widget, to facilitate normal form moving operation. This is needed
        because of the use of Translucent Background.
        """
        # We shall override only the left-click.
        if not event.button() == Qt.LeftButton:
            return

        self.isMousePressed = True
        self.mousePosition = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Overrides the event provided by the base Widget, to facilitate normal form moving operation. This is needed
        because of the use of Translucent Background.
        """
        windowPosition = event.globalPos()

        # Guard against bad mouse event.
        if not self.isMousePressed or self.mousePosition == 0:
            return

        diff = windowPosition - self.mousePosition
        self.move(diff)

        # Update to the last location.
        self.mousePosition = windowPosition - self.pos()

        # Reset the animation group, to update window location.
        self.shakingAnimationGroup = None

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Overrides the event provided by the base Widget. No actual use for this function, but added to complete
        overriding all mouse functions.
        """
        self.mousePosition = event.globalPos() - self.pos()
        self.isMousePressed = False

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        Overrides the event provided by the base Widget. No actual use for this function, but added to complete
        overriding all mouse functions.
        """
        pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Overrides pressing the 'Enter'/'Esc' key to react as pressing 'Yes' and 'No'.
        """
        keyValue = event.key()
        if keyValue == Qt.Key_Enter:
            self._loginToApplication()

        if keyValue == Qt.Key_Escape:
            self.close()

        return

    def _validateCredentials(self, userName: str, password: str) -> None:
        """
        Connects to the DB to validate the credentials entered by the user.
        """
        self.logDebug(f'Attempting to validate credentials for "{userName}".')

        request = UserRequest().RequestForGetUserWithCheck(UserName=userName, Password=password)
        command = UserCommand()
        response = command.executeForGetUserWithCheck(request)

        if not response.isSuccessful:
            self.isLoginSuccessful = False

            self.logDebug(f'Credentials passed for "{userName}" failed validation.')
            return

        self.isLoginSuccessful = True
        self.user = response.result.User
        self.sessionID = response.result.SessionID

        self.logInfo(f'Credentials passed for "{userName}" are successful.')

    def _loginToApplication(self) -> None:
        """
        Performs the necessary steps to initiate login to the main application. If things are in order,
        it passes the torch to the main application. Else, it warns the users of errors.
        """
        self.logDebug(f"Acquiring credentials.")
        userName = self.txtUserName.text().strip().lower()
        password = self.txtPassword.text().strip()

        if userName == "":
            self._showRedOnEmpty(self.txtUserName)
            self._shakeFormOnError()
            return

        if password == "":
            self._showRedOnEmpty(self.txtPassword)
            self._shakeFormOnError()
            return

        self._validateCredentials(userName, password)

        if not self.isLoginSuccessful:
            self._shakeFormOnError()
            return

        self.successAnimationGroup.start()
        self.successAnimationGroup.finished.connect(self.close)

    def _shakeFormOnError(self) -> None:
        """
        Shake the form, with color indication, to indicate an error in login information.
        """
        if self.shakingAnimationGroup is None:
            self._setupShakingAnimation()

        self.shakingAnimationGroup.start()
        self.shakingAnimationGroup.finished.connect(lambda: self.setStyleSheet(""))

    def _showRedOnEmpty(self, textBox: QLineEdit) -> None:
        """
        Change the border of empty text boxes to red.
        """
        errorStyle = f"QLineEdit#{textBox.objectName()} {{border: 1px solid #ff0000;}}"
        textBox.setStyleSheet(errorStyle)

    def _clearWarningOnEdit(self) -> None:
        """
        Change the border of back to original style by resetting the error style.
        """
        textBox = self.sender()
        textBox.setStyleSheet("")

    def _setupShakingAnimation(self) -> None:
        """
        Sets up two sequential cosine animations for the form. This will be used on errors.
        """
        offset = 75
        duration = 50
        startLocation = self.pos()
        endLocation = QPoint(startLocation.x() + offset, startLocation.y())

        self.shakingAnimationGroup = QSequentialAnimationGroup()

        animation1 = QPropertyAnimation(self, b"pos")
        animation1.setDuration(duration)
        animation1.setStartValue(startLocation)
        animation1.setEndValue(endLocation)
        animation1.setEasingCurve(QEasingCurve.CosineCurve)

        animation2 = QPropertyAnimation(self, b"pos")
        animation2.setDuration(duration)
        animation2.setStartValue(endLocation)
        animation2.setEndValue(startLocation)
        animation2.setEasingCurve(QEasingCurve.CosineCurve)

        self.shakingAnimationGroup.addAnimation(animation1)
        self.shakingAnimationGroup.addAnimation(animation2)

        self.shakingAnimationGroup.start()

    def _setupSuccessAnimation(self) -> None:
        """
        Sets up an opacity animation on a green label to show a successful login.
        """

        # Assign the image.
        self.lblGreenCheck.setPixmap(QPixmap(":/icons/green-check.svg"))

        # This is how we introduce the opacity property for the label.
        self.effect = QGraphicsOpacityEffect()
        self.lblGreenCheck.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0.0)

        duration = 700
        pause = 200
        self.successAnimationGroup = QSequentialAnimationGroup()

        animation1 = QPropertyAnimation(self.effect, b"opacity")
        animation1.setDuration(duration)
        animation1.setStartValue(0.0)
        animation1.setEndValue(1.0)
        animation1.setEasingCurve(QEasingCurve.InQuint)

        self.successAnimationGroup.addAnimation(animation1)
        self.successAnimationGroup.addPause(pause)

    def logInfo(self, message: str) -> None:
        """
        A utility function that logs info with log level INFO.
        """
        attributeMap = {"UserID": 0 if self.user is None else self.user.UserID, "SessionID": self.sessionID}
        self.logger.info(message, extra=attributeMap)

    def logDebug(self, message: str) -> None:
        """
        A utility function that logs info with log level DEBUG.
        """
        attributeMap = {"UserID": 0 if self.user is None else self.user.UserID, "SessionID": self.sessionID}
        self.logger.debug(message, extra=attributeMap)
