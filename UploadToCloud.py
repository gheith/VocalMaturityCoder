"""
VMC Deployment

This script is used to upload the desired list of files to the AWS S3 Cloud Storage.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.3.0"
__status__ = "Production"


from CloudUpdater import loadCloudResource

# List of files to deploy to the cloud. Each element is a tuple of the form (folder, file).
applicationFiles = [("CoreLogic", "BaseCommand.py"),
                    ("CoreLogic", "UserCommand.py"),
                    ("CoreLogic", "UtteranceCommand.py"),
                    ("DataAccess", "BaseDB.py"),
                    ("DataAccess", "BaseRepository.py"),
                    ("DataAccess", "DatabaseLoggingHandler.py"),
                    ("DataAccess", "RecordingRepository.py"),
                    ("DataAccess", "SessionRepository.py"),
                    ("DataAccess", "UserRepository.py"),
                    ("DataAccess", "UtteranceRepository.py"),
                    ("Models", "UserModel.py"),
                    ("Models", "UtteranceCodeModel.py"),
                    ("Models", "UtteranceCodeConsensusModel.py"),
                    ("Models", "UtteranceModel.py"),
                    ("Presentation", "CodingGUI.py"),
                    ("Presentation", "CodingGuiBase.py"),
                    ("Presentation", "GuiResources.py"),
                    ("Presentation", "LoginForm.py"),
                    ("Presentation", "LoginFormBase.py"),
                    (None, "DirectAccess.py"),
                    (None, "log.config"),
                    (None, "MasterStyleSheet.py"),
                    (None, "release.config"),
                    (None, "VmcLoader.py"),
                    (None, "CloudUpdater.py")
]


def uploadFilesToCloud(bucketName: str, s3Resource, folder: str) -> bool:
    """
    Uploads the list of files to the cloud in the specified folder.
    """

    # Check if the folder already exists to prevent overwrites.
    vmcBucket = s3Resource.Bucket(bucketName)
    folderObjects = list(vmcBucket.objects.filter(Prefix=f"VMC/{folder}"))

    if folderObjects:
        print(f"Folder {folder} already exists. Deployment aborted.")
        return False

    for subfolder, fileName in applicationFiles:
        filePath = f"{subfolder}/{fileName}" if subfolder else f"{fileName}"
        objectPath = f"VMC/{folder}/{filePath}"

        print(f'Uploading {filePath} to {objectPath} ...', end='')
        fileObject = s3Resource.Object(bucketName, objectPath)
        fileObject.upload_file(filePath)
        print('OK!')

    return True


if __name__ == "__main__":

    targetFolder = 'v1.3.0'

    vmcBucketName = "ndd-family-lab"
    resource, _ = loadCloudResource()
    isSuccessful = uploadFilesToCloud(vmcBucketName, resource, targetFolder)

    # Update latest release information.
    if isSuccessful:
        latestConfigPath = "release.config"
        latestConfigObjectPath = f"VMC/latest.config"   # NOTE: S3 file is renamed.

        print(f'Uploading {latestConfigPath} to {latestConfigObjectPath} ...', end='')
        configObject = resource.Object(vmcBucketName, latestConfigObjectPath)
        configObject.upload_file(latestConfigPath)
        print('OK!')
