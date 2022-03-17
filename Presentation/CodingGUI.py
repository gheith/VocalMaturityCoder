"""
The consumer class that enhances the PyQt5 generated Python class with more logic.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"


import logging
from math import ceil
from datetime import timedelta
from tempfile import TemporaryDirectory
from os.path import join
from Crypto.Cipher import AES

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QMouseEvent, QPixmap, QIcon
from PyQt5.QtWidgets import QWidget, QMessageBox

from PyQt5.QtMultimedia import QMediaPlayer, QAudio, QMediaContent
from PyQt5.QtWidgets import QButtonGroup

from Presentation.CodingGuiBase import Ui_FormCoding
from Models.UserModel import UserModel
from CoreLogic.UtteranceCommand import *


class CodingGUI(QWidget, Ui_FormCoding):
    def __init__(self, user: UserModel, sessionID: int, key: bytes, parent: QWidget = None):
        """
        Initializes an instance of the Coding GUI, and sets some attributes.

        :param parent: The parent form of this form. This value is not used, but is included as a convention.
        """
        super(CodingGUI, self).__init__(parent)
        self.setupUi(self)

        self.logger = logging.getLogger()
        self.attributeMap = {"UserID": user.UserID, "SessionID": sessionID}

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Player Setup
        # ------------
        # Icons for the play button.
        self.playIcon = QIcon()
        self.playIcon.addPixmap(QPixmap(":/icons/Player/play.svg"), QIcon.Normal, QIcon.Off)
        self.pauseIcon = QIcon()
        self.pauseIcon.addPixmap(QPixmap(":/icons/Player/pause.svg"), QIcon.Normal, QIcon.Off)
        # Disable navigation at the start.
        self.btnNext.setEnabled(False)
        self.btnPrevious.setEnabled(False)

        # The media player.
        self.player = QMediaPlayer(self, QMediaPlayer.LowLatency)
        self.player.setAudioRole(QAudio.MusicRole)
        self.btnPlay.clicked.connect(self.playOrPauseAudio)
        self.btnNext.clicked.connect(self.getNextAudio)
        self.btnPrevious.clicked.connect(self.getPreviousAudio)
        self.player.positionChanged.connect(self.updatePositionSlider)
        self.player.stateChanged.connect(self.handlePlayerStateChange)

        # Creates groupings of the coding widgets to facilitate modifying their behavior according to the application
        # state.
        self.annotationButtonGroup = QButtonGroup(self.grpType)
        self.annotationButtonGroup.addButton(self.rdoLaughing)
        self.annotationButtonGroup.addButton(self.rdoCrying)
        self.annotationButtonGroup.addButton(self.rdoNonCanonical)
        self.annotationButtonGroup.addButton(self.rdoCanonical)
        self.annotationButtonGroup.addButton(self.rdoWord)
        self.annotationButtonGroup.addButton(self.rdoNonCodable)
        self.annotationButtonGroup.buttonClicked.connect(self.updateForAnnotation)
        self.nonCodableGroup = QButtonGroup(self.grpNonCodable)
        self.nonCodableGroup.addButton(self.rdoOtherSpeaker)
        self.nonCodableGroup.addButton(self.rdoOverlappingSound)
        self.nonCodableGroup.addButton(self.rdoVegetativeSound)
        self.nonCodableGroup.addButton(self.rdoNoise)

        self.playerGroup = [
            self.lblUtteranceFileName,
            self.lblSliderBegin,
            self.lblSliderEnd,
            self.sldPlayer,
            self.btnPlay,
        ]

        self.codingTextPairs = [
            (self.lblTotalSyllables, self.txtTotalSyllables),
            (self.lblCanonicalSyllables, self.txtCanonicalSyllables),
            (self.lblWordSyllables, self.txtWordSyllables),
            (self.lblWords, self.txtWords),
        ]

        self.playDuration = 0
        self.duration = 0
        self.key = key

        self.btnExit.clicked.connect(self.close)
        self.btnMinimize.clicked.connect(self.showMinimized)

        # Apply information passed from Login.
        titleText = f"Coder:     {user.LastName}, {user.FirstName}"
        self.lblCurrentUser.setText(titleText)
        self.sessionID = sessionID
        self.user = user

        self.codingHistory = []
        self.currentUtteranceIndex = 0
        self.currentUtterance = None
        self.currentUtteranceCode = None
        self.annotation = None

        # Temp folder used if no target folder selected.
        self.tempAudioFolder = TemporaryDirectory(prefix="VMC_")
        self.resetForNewUtterance()

        # Main buttons.
        self.btnDownload.clicked.connect(self.getNewUtterance)
        self.btnSave.clicked.connect(self.persistUtteranceCodeToDB)

        # Mouse-related variables.
        self.mousePosition = 0
        self.isMousePressed = False

        self.logger.debug("Coding UI Initiated.", extra=self.attributeMap)

    def close(self) -> None:
        """
        Overrides the closing of the window to guarantee cleaning resources.
        """
        # Close current DB Session.
        BaseCommand.endDbSession()

        # # Windows require special permissions to handle deleting temp files and folders.
        # if platform.system() != 'Windows':
        #     # Delete any audio files downloaded
        #     self.tempAudioFolder.cleanup()

        self.logger.debug("Coding UI Closing.", extra=self.attributeMap)
        super().close()

    def getNewUtterance(self) -> None:
        """
        Downloads a new utterance object from the DB.
        """
        self.logger.info("Getting a new utterance.", extra=self.attributeMap)

        request = UtteranceRequest().RequestForGetNewUtterance(UserID=self.user.UserID, SessionID=self.sessionID)
        command = UtteranceCommand()
        response = command.executeForGetNewUtterance(request)

        if response.isSuccessful and response.result is None:
            QMessageBox().information(
                self, "Information", "There are no more utterances that you can code.", QMessageBox.Ok,
            )
            self.logger.info("No utterances available.", extra=self.attributeMap)
            return

        if not response.isSuccessful:
            QMessageBox().critical(
                self,
                "DB Error",
                "Unable to retrieve a new utterance. Please close the application and contact the administrator.",
                QMessageBox.Ok,
            )
            self.logger.critical("Unable to retrieve utterances.", extra=self.attributeMap)
            return

        self.resetForNewUtterance()
        self.btnDownload.setEnabled(False)
        self.btnPrevious.setEnabled(False)
        self.btnNext.setEnabled(False)

        self.currentUtterance = response.result.Utterance
        message = (
            f"Utterance ID {self.currentUtterance.UtteranceID}, "
            f"FileName: {self.currentUtterance.AudioFileName} retrieved."
        )
        self.logger.info(message, extra=self.attributeMap)

        if self.codingHistory:
            self.currentUtteranceIndex = len(self.codingHistory)

        print(f"Utterance ID {self.currentUtterance.UtteranceID}")

        # Save audio file.
        audioPath = join(self.tempAudioFolder.name, self.currentUtterance.AudioFileName)

        with open(audioPath, "wb") as audioFile:
            encryptedData = self.currentUtterance.AudioFileData
            nonce = encryptedData[:16]
            encryptedAudio = encryptedData[16:]
            cipher = AES.new(self.key, AES.MODE_EAX, nonce=nonce)
            audioBytes = cipher.decrypt(encryptedAudio)
            audioFile.write(audioBytes)

        self.currentUtterance.AudioFilePath = audioPath
        self.setAudioInPlayer()

    def setAudioInPlayer(self):
        """
        Loads the current utterance into the player.
        """
        message = f"Loading Utterance ID {self.currentUtterance.UtteranceID} into audio player."
        self.logger.debug(message, extra=self.attributeMap)

        audioPath = self.currentUtterance.AudioFilePath
        self.player.setMedia(QMediaContent(QUrl().fromLocalFile(audioPath)))

        self.duration = ceil(self.currentUtterance.DurationInSeconds)
        self.updateDurationLabel(self.duration)

        # Reset the label showing where the audio is at.
        self.playDuration = 0

        # Enable entry widgets.
        for button in self.annotationButtonGroup.buttons():
            button.setEnabled(True)

        self.lblComments.setEnabled(True)
        self.txtComments.setEnabled(True)

        for widget in self.playerGroup:
            widget.setEnabled(True)

        fileLabel = f"{self.currentUtterance.AudioFileName}    ID# {self.currentUtterance.UtteranceID}"
        self.lblUtteranceFileName.setText(fileLabel)

    def playOrPauseAudio(self):
        """
        Handles the GUI behavior of playing/pausing audio when the button is clicked.
        """
        if self.player.state() == QMediaPlayer.PlayingState:
            self.logger.debug(f"Pausing Utterance ID {self.currentUtterance.UtteranceID}.", extra=self.attributeMap)
            self.player.pause()
        else:
            self.logger.debug(f"Playing Utterance ID {self.currentUtterance.UtteranceID}.", extra=self.attributeMap)
            self.player.play()

    def handlePlayerStateChange(self):
        """
        Changes the icon of the play button based on the state of the player, and resets the slider when done.
        """
        if self.player.state() == QMediaPlayer.PlayingState:
            self.btnPlay.setIcon(self.pauseIcon)
        else:
            self.btnPlay.setIcon(self.playIcon)

        if self.player.state() == QMediaPlayer.StoppedState:
            self.sldPlayer.setValue(0)
            self.playDuration = 0
            self.lblSliderBegin.setText("00:00")

    def getPreviousAudio(self):
        """
        Loads the previous audio from the play list.
        """
        if self.currentUtteranceIndex > 0:
            self.currentUtteranceIndex -= 1

        # print(f"getPreviousAudio: CurrentIndex = {self.currentUtteranceIndex}")

        self.currentUtterance, self.currentUtteranceCode = self.codingHistory[self.currentUtteranceIndex]

        self.setAudioInPlayer()
        self.applyCurrentUtteranceCode()

        message = f"Loading previous utterance, ID {self.currentUtterance.UtteranceID}."
        self.logger.debug(message, extra=self.attributeMap)

    def getNextAudio(self):
        """
        Loads the next to current audio from the play list.
        """
        if self.currentUtteranceIndex < len(self.codingHistory) - 1:
            self.currentUtteranceIndex += 1

        # print(f"getNextAudio: CurrentIndex = {self.currentUtteranceIndex}")

        self.currentUtterance, self.currentUtteranceCode = self.codingHistory[self.currentUtteranceIndex]

        self.setAudioInPlayer()
        self.applyCurrentUtteranceCode()

        message = f"Loading next utterance, ID {self.currentUtterance.UtteranceID}."
        self.logger.debug(message, extra=self.attributeMap)

    def updateDurationLabel(self, duration: int):
        """
        Updates the label of the duration.

        :duration: A the ceiling value of the number of seconds.
        """
        durationStr = str(timedelta(seconds=duration))[2:]
        self.lblSliderEnd.setText(f"{durationStr}")

        # The maximum is an integer.
        self.sldPlayer.setMaximum(duration)

    def updatePositionSlider(self, position):
        """
        Updates the slider of the player.
        """
        if self.player.state() != QMediaPlayer.PlayingState:
            return

        self.playDuration += 1
        self.sldPlayer.setValue(self.playDuration)

        durationStr = str(timedelta(seconds=self.playDuration))[2:]
        self.lblSliderBegin.setText(f"{durationStr}")

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

    def updateForAnnotation(self) -> None:
        """
        Updates the visual of the App for every selection of the main annotation. This includes enabling/disabling
        certain parts of the entry widgets. Also, update the annotation based on the user's choice.
        """
        group = self.sender()

        radio = group.checkedButton()
        self.annotation = radio.text()

        # Start by resetting all widgets of interest.
        for button in self.nonCodableGroup.buttons():
            button.setEnabled(False)

        for label, textBox in self.codingTextPairs:
            label.setEnabled(False)
            textBox.setEnabled(False)

        if radio is self.rdoNonCodable:
            self.annotation = None
            for button in self.nonCodableGroup.buttons():
                button.setEnabled(True)

        if radio is self.rdoNonCanonical or radio is self.rdoCanonical or radio is self.rdoWord:
            self.lblTotalSyllables.setEnabled(True)
            self.txtTotalSyllables.setEnabled(True)

        if radio is self.rdoCanonical or radio is self.rdoWord:
            self.lblCanonicalSyllables.setEnabled(True)
            self.txtCanonicalSyllables.setEnabled(True)

        if radio is self.rdoWord:
            self.lblWordSyllables.setEnabled(True)
            self.txtWordSyllables.setEnabled(True)
            self.lblWords.setEnabled(True)
            self.txtWords.setEnabled(True)

        self.btnSave.setEnabled(True)

    def resetForNewUtterance(self) -> None:
        """
        Clears the widgets to be ready for getting a new utterance coding.
        """
        self.logger.debug("Resetting UI for a new utterance.", extra=self.attributeMap)

        self.currentUtterance = None
        self.currentUtteranceCode = None

        self.annotationButtonGroup.setExclusive(False)
        self.nonCodableGroup.setExclusive(False)

        for button in self.annotationButtonGroup.buttons():
            button.setChecked(False)
            button.setEnabled(False)

        for button in self.nonCodableGroup.buttons():
            button.setEnabled(False)

        self.annotationButtonGroup.setExclusive(True)
        self.nonCodableGroup.setExclusive(True)

        for widget in self.playerGroup:
            widget.setEnabled(False)
        self.lblUtteranceFileName.setText("")

        for label, textBox in self.codingTextPairs:
            label.setEnabled(False)
            textBox.setEnabled(False)
            textBox.setText("0")

        self.lblComments.setEnabled(False)
        self.txtComments.setEnabled(False)
        self.txtComments.setPlainText("")

        self.btnSave.setEnabled(False)
        self.lblSliderBegin.setText("00:00")
        self.sldPlayer.setValue(0)

        self.btnDownload.setEnabled(True)
        if len(self.codingHistory) > 0:
            self.btnPrevious.setEnabled(True)
            self.btnNext.setEnabled(True)

    def persistUtteranceCodeToDB(self) -> None:
        """
        Captures the choices of the coder for the utterance and saves them to the DB.
        """
        getInt = lambda textBox: 0 if not textBox.isEnabled() or not textBox.text() else int(textBox.text())

        if self.annotation is None:
            annotation = self.nonCodableGroup.checkedButton().text()
        else:
            annotation = self.annotation

        comments = self.txtComments.toPlainText().strip()

        # Determine if this is a new code, or an update.
        if not self.currentUtteranceCode:
            utteranceCode = UtteranceCodeModel(
                UtteranceCodingID=-1,
                UtteranceSamplePoolID=self.currentUtterance.UtteranceSamplePoolID,
                UtteranceID=self.currentUtterance.UtteranceID,
                CoderID=self.user.UserID,
                Annotation=annotation,
                TotalSyllableCount=getInt(self.txtTotalSyllables),
                CanonicalSyllableCount=getInt(self.txtCanonicalSyllables),
                WordSyllableCount=getInt(self.txtWordSyllables),
                WordCount=getInt(self.txtWords),
                Comments=comments,
            )

            # Capture/update the current utterance code.
            self.currentUtteranceCode = utteranceCode

            # Update the history. This is only needed for new codes.
            pair = self.currentUtterance, self.currentUtteranceCode
            self.codingHistory.append(pair)
        else:
            self.currentUtteranceCode.Annotation = annotation
            self.currentUtteranceCode.TotalSyllableCount = getInt(self.txtTotalSyllables)
            self.currentUtteranceCode.CanonicalSyllableCount = getInt(self.txtCanonicalSyllables)
            self.currentUtteranceCode.WordSyllableCount = getInt(self.txtWordSyllables)
            self.currentUtteranceCode.WordCount = getInt(self.txtWords)
            self.currentUtteranceCode.Comments = comments

        message = (
            f"Attempting to save coding for utterance ID {self.currentUtterance.UtteranceID}. "
            f"Coding info = {self.currentUtteranceCode}"
        )
        self.logger.debug(message, extra=self.attributeMap)

        request = UtteranceRequest().RequestForSaveOrUpdateUtteranceCode(
            UserID=self.user.UserID,
            UtteranceID=self.currentUtterance.UtteranceID,
            UtteranceCode=self.currentUtteranceCode,
            SessionID=self.sessionID,
        )
        command = UtteranceCommand()
        response = command.executeForSaveOrUpdateUtteranceCode(request)

        if not response.isSuccessful:
            QMessageBox().critical(
                self,
                "Error Saving Code",
                f"There was an error attempting to save your utterance code.\nDB Error Message: '{response.message}'.\n"
                f"Please stop coding and contact the administrator.",
                QMessageBox.Ok,
            )

            message = f"Unable to save coding for utterance ID {self.currentUtterance.UtteranceID}."
            self.logger.error(message, extra=self.attributeMap)
            return

        message = f"Coding for utterance ID {self.currentUtterance.UtteranceID} saved successfully."
        self.logger.debug(message, extra=self.attributeMap)

        self.resetForNewUtterance()

    def applyCurrentUtteranceCode(self) -> None:
        """
        Applies the current utterance code to the GUI, to allow for potential modification.
        """
        utteranceCode = self.currentUtteranceCode

        message = f"Loading coding for utterance ID {self.currentUtterance.UtteranceID}."
        self.logger.debug(message, extra=self.attributeMap)

        # # First, reset the GUI. Then, checking the radio buttons should adjust it.
        # self.resetForNewUtterance()

        self.txtTotalSyllables.setText(str(utteranceCode.TotalSyllableCount))
        self.txtCanonicalSyllables.setText(str(utteranceCode.CanonicalSyllableCount))
        self.txtWordSyllables.setText(str(utteranceCode.WordSyllableCount))
        self.txtWords.setText(str(utteranceCode.WordCount))
        self.txtComments.setPlainText(utteranceCode.Comments)

        annotation = None

        for radio in self.nonCodableGroup.buttons():
            radio.setEnabled(False)

        for radio in self.annotationButtonGroup.buttons():
            if utteranceCode.Annotation == radio.text():
                annotation = utteranceCode.Annotation
                radio.setChecked(True)
                break

        if annotation is not None:
            return

        # If we are here, then it is a non-codable utterance.
        self.rdoNonCodable.setChecked(True)
        for radio in self.nonCodableGroup.buttons():
            radio.setEnabled(True)
            if utteranceCode.Annotation == radio.text():
                radio.setChecked(True)

        self.btnSave.setEnabled(True)
