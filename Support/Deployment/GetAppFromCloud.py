"""
VMC Updater File

This file checks the VMC release for the latest one. If the current installation is the latest, the application
continues, otherwise, the latest is downloaded to keep the codebase up-to-date.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.3.0"
__status__ = "Production"


from io import BytesIO
from os import rename, mkdir, remove
from os.path import exists, join, dirname, abspath, split, splitext
from glob import glob
from shutil import copy, rmtree
from typing import Optional
from configparser import ConfigParser
from datetime import datetime
import logging
from logging import getLogger
import py_compile

import boto3
import attr
from attr.validators import instance_of


@attr.s
class VersionInformation:
    Major = attr.ib(validator=instance_of(int))
    Minor = attr.ib(validator=instance_of(int))
    Build = attr.ib(validator=instance_of(int))

    def asVersionString(self):
        return f'v{self.Major}.{self.Minor}.{self.Build}'


def loadCloudResource():
    """
    Extracts and returns the cloud resource service using the necessary credentials from the given INI string.
    """

    cloudFilePath = join(dirname(abspath(__file__)), 'cloud.config')
    if not exists(cloudFilePath):
        return None, None

    # Get current version information.
    config = ConfigParser()
    config.read(cloudFilePath)

    # Also, load the cloud credentials to be persisted in the target folder.
    with open(cloudFilePath, 'r') as cloudFile:
        cloudCredentials = cloudFile.read()

    info = config['AWS']
    accessKeyID = info['AccessKeyID']
    secretAccessKey = info['SecretAccessKey']

    s3Resource = boto3.resource('s3', aws_access_key_id=accessKeyID, aws_secret_access_key=secretAccessKey)

    return s3Resource, cloudCredentials


def downloadCloudFile(s3Resource, bucketName: str, fileKey: str) -> str:
    """
    Connects to the remote release location and downloads the file as a str.
    """

    with BytesIO() as inMemoryFile:
        cloudObject = s3Resource.Object(bucketName, fileKey)
        cloudObject.download_fileobj(inMemoryFile)
        objectBytes = inMemoryFile.getvalue()
        objectString = str(objectBytes, 'utf-8')

    return objectString


def parseReleaseConfiguration(configStr: str) -> VersionInformation:
    """
    Extracts and returns the version and date values from the given INI string.
    """

    # Get current version information.
    config = ConfigParser()
    config.read_string(configStr)
    info = config['Release']

    major, minor, build = info['Version'].split('.')
    # releaseDate = datetime.strptime(info['ReleasedOn'], '%m/%d/%Y').date()

    releaseInfo = VersionInformation(Major=int(major), Minor=int(minor), Build=int(build))

    return releaseInfo


def getLocalVersion() -> Optional[VersionInformation]:
    """
    Reads the local release information.
    """

    releaseFilePath = join(dirname(abspath(__file__)), 'release.config')
    if not exists(releaseFilePath):
        return None

    try:
        # Read current version information.
        with open(releaseFilePath, 'r') as rFile:
            currentConfigStr = rFile.read()

        localReleaseInfo = parseReleaseConfiguration(currentConfigStr)

        return localReleaseInfo
    except:
        return None


def getLatestVersion(s3Resource, bucketName: str) -> Optional[VersionInformation]:
    """
    Connects to the remote release location
    """

    try:
        configFileKey = 'VMC/latest.config'
        configString = downloadCloudFile(s3Resource, bucketName, configFileKey)
        s3Version = parseReleaseConfiguration(configString)

        return s3Version
    except:
        return None


def deployVmcApplication(s3Resource, bucketName: str, sourceFolder: str, targetFolder="Application") -> bool:
    """
    Copies and compiles the latest release from the cloud to the target application.
    """
    cloudPrefix = f"VMC/{sourceFolder}/"

    # Check if the cloud folder already exists.
    vmcBucket = s3Resource.Bucket(bucketName)
    cloudObjects = list(vmcBucket.objects.filter(Prefix=cloudPrefix))

    if not cloudObjects:
        print(f"Cloud folder {sourceFolder} does not exist. Deployment aborted.")
        return False

    # Begin the deployment with folder creation.
    try:
        for cloudObject in cloudObjects:
            sourcePath = cloudObject.key
            targetSubfolder, fileName = split(sourcePath.replace(cloudPrefix, ''))
            fileContent = downloadCloudFile(s3Resource, bucketName, sourcePath)

            baseName, fileExtension = splitext(fileName)

            # Determine if there is a subfolder to add.
            if targetSubfolder:
                targetBaseFolder = join(targetFolder, targetSubfolder)

                if not exists(targetBaseFolder):
                    mkdir(targetBaseFolder)
            else:
                targetBaseFolder = targetFolder

            # Compile python files, and save other file types.
            if fileExtension == ".py":

                # Create temp source file.
                tempPythonSourcePath = join(targetFolder, 'temporary_file')
                with open(tempPythonSourcePath, 'w', newline='\n') as tempFile:
                    tempFile.write(fileContent)

                targetFilePath = join(targetBaseFolder, f"{baseName}.pyc")
                py_compile.compile(tempPythonSourcePath, cfile=targetFilePath)

                remove(tempPythonSourcePath)

            else:
                targetFilePath = join(targetBaseFolder, fileName)
                with open(targetFilePath, "w", newline="\n") as targetFile:
                    targetFile.write(fileContent)
        return True
    except:
        return False


def performApplicationUpdate() -> bool:
    """
    Updates the application when starting from the loader script.

    returns: A flag to indicate if an update has occurred or not. This will be used to require a restart
             in case the loaded objects are required to change.
    """

    targetFolder = dirname(abspath(__file__))
    logger = getLogger()

    message = f'Attempting to check for a new version.'
    logger.info(message, extra={"UserID": 0, "SessionID": 0})

    # Get latest information from S3.
    vmcBucketName = "ndd-family-lab"
    resource, cloudFileContent = loadCloudResource()

    latestVersion = getLatestVersion(resource, vmcBucketName)
    currentVersion = getLocalVersion()

    if currentVersion is None:
        message = ('Error checking "release.config" for version information. '
                   'Verify that the file exists and is properly formatted. Aborting updating.')
        logger.error(message, extra={"UserID": 0, "SessionID": 0})
        return False

    if latestVersion is None:
        message = f'Unable to retrieve latest release information from the cloud. Aborting updating.'
        logger.error(message, extra={"UserID": 0, "SessionID": 0})
        return False

    isRequired = latestVersion > currentVersion
    message = (f'Current Version = {currentVersion.asVersionString()}, '
               f'Latest Version = {latestVersion.asVersionString()}')

    if not isRequired:
        message = f'{message} => Application is up-to-date.'
        logger.info(message, extra={"UserID": 0, "SessionID": 0})
        return False

    # Update is required!
    message = f'{message} => Update is REQUIRED.'
    logger.info(message, extra={"UserID": 0, "SessionID": 0})

    # Create a backup.
    baseFolder = join(targetFolder, '..')
    now = datetime.now()
    backupFolder = join(baseFolder, f'Backup_{now:%Y-%m-%d-%H-%M-%S}')
    rename(targetFolder, backupFolder)
    mkdir(targetFolder)

    sourceFolder = f"{latestVersion.asVersionString()}"
    isSuccessful = deployVmcApplication(resource, vmcBucketName, sourceFolder, targetFolder)

    if isSuccessful:
        message = f'Deployment of VMC Application, version {latestVersion.asVersionString()}, was successful.'
        logger.info(message, extra={"UserID": 0, "SessionID": 0})

        # Persist the cloud credentials.
        cloudConfigPath = join(targetFolder, "cloud.config")
        with open(cloudConfigPath, "w") as cloudFile:
            cloudFile.write(cloudFileContent)

    else:
        message = f'Deployment of VMC Application failed.'
        logger.error(message, extra={"UserID": 0, "SessionID": 0})

        if exists(targetFolder):
            rmtree(targetFolder)
        rename(backupFolder, targetFolder)

        message = f'Reverting completed.'
        logger.info(message, extra={"UserID": 0, "SessionID": 0})

    return isSuccessful


def performInitialDeployment(cloudFolder=None, targetFolder="Application"):
    """
    Obtain the application from the cloud.
    """
    # This basic setup is needed because the logger would not be available before the application is deployed.
    logging.basicConfig(level=logging.INFO)
    logger = getLogger()

    message = f'Deployment a new instance of the VMC Application.'
    logger.info(message, extra={"UserID": 0, "SessionID": 0})

    # Get latest information from S3.
    vmcBucketName = "ndd-family-lab"
    resource, cloudFileContent = loadCloudResource()

    latestVersion = getLatestVersion(resource, vmcBucketName)

    if latestVersion is None:
        message = f'Unable to retrieve latest release information from the cloud. Aborting updating.'
        logger.error(message, extra={"UserID": 0, "SessionID": 0})
        return

    # Check that the folder does NOT exist, or it exists and it is empty.
    if glob(f"{targetFolder}/*"):
        message = f"Folder {targetFolder} exists and it is NOT empty. Deployment aborted."
        logger.error(message, extra={"UserID": 0, "SessionID": 0})
        return False

    if not exists(targetFolder):
        mkdir(targetFolder)

    cloudFolder = f"{latestVersion.asVersionString()}" if cloudFolder is None else cloudFolder
    isSuccessful = deployVmcApplication(resource, vmcBucketName, cloudFolder, targetFolder)

    if isSuccessful:
        message = f'Deployment of VMC Application, version {latestVersion.asVersionString()}, was successful.'
        logger.info(message, extra={"UserID": 0, "SessionID": 0})

        # Persist the cloud credentials.
        cloudConfigPath = join(targetFolder, "cloud.config")
        with open(cloudConfigPath, "w") as cloudFile:
            cloudFile.write(cloudFileContent)
    else:
        message = f'Deployment of VMC Application failed. Please check the log for more information.'
        logger.error(message, extra={"UserID": 0, "SessionID": 0})

        if exists(targetFolder):
            rmtree(targetFolder)


if __name__ == "__main__":

    performInitialDeployment()
