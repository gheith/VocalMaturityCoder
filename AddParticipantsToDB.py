"""
AddParticipantsToDB

A script that checks the Participants metadata file, which must be located in the data folder, where ".csv", ".its" and
".wav" files are present. This is an admin script that checks for and adds new participants to the DB.

Note that this script does NOT add new Genetic Risks.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.2.0"
__status__ = "Production"


from os.path import join
from datetime import datetime
from typing import List
from csv import DictReader

from VmcLoader import getConnectionInformation, ConnectionType, DataFolder

from DataAccess.BaseDB import *
from sqlalchemy.orm.session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def loadSourceDataFile(filePath: str) -> List[dict]:
    """
    Reads the CSV file from the path given, and returns a list of rows, as ordered dictionaries, as defined by the
    Python CSV module.

    :param filePath: Full path for the CSV file.
    :return: Rows as Ordered Dictionaries.
    """

    rows = []

    with open(filePath, "r") as csvFile:
        reader = DictReader(csvFile)

        for row in reader:
            resultMap = {}

            for k, v in row.items():

                if k is None:
                    continue

                resultMap[k.strip()] = v.strip() if v.strip() else None

            rows.append(resultMap)

    return rows


def addNewParticipantsToDB(dbSession: Session) -> None:
    """
    Checks the reference Participants file for new additions, and loads them into the DB.
    """
    filePath = join(DataFolder, "Participant.csv")

    rows = loadSourceDataFile(filePath)

    # Identify new participants by ID.
    fileParticipants = {row["ChildID"] for row in rows}

    # Get the list of current recordings to identify what is missing.
    dbParticipants = [p.ChildID for p in dbSession.query(Participant).all()]

    newParticipants = sorted(fileParticipants - set(dbParticipants))

    if not newParticipants:
        print('No new participant have been found.')
        return

    print(f'The following {len(newParticipants)} participant(s) have been identified:\n')
    print(", ".join([f"{childID}" for childID in newParticipants]))

    # Load support tables.
    sexMap = {record.Description: record.SexID for record in dbSession.query(Sex).all()}
    riskMap = {record.Description: record.GeneticRiskID for record in dbSession.query(GeneticRisk).all()}

    for row in rows:

        current = row["ChildID"]

        if current not in newParticipants:
            continue

        print(f'Working on {current} ...')

        entry = Participant(
            DateOfBirth=row["DateOfBirth"],
            ChildID=row["ChildID"],
            SexID=sexMap[row["Sex"]],
            GeneticRiskID=riskMap[row["GeneticRisk"]],
        )
        dbSession.add(entry)


if __name__ == "__main__":

    print(f"Starting @ {datetime.now()} ... \n")

    cType = ConnectionType.Production
    connectionStr, encKey = getConnectionInformation(cType)

    engine = create_engine(connectionStr, isolation_level="READ_COMMITTED")
    SessionMaker = sessionmaker(bind=engine, expire_on_commit=False)
    localSession = SessionMaker()

    addNewParticipantsToDB(localSession)

    localSession.commit()
    localSession.close()

    print()
    print(f"End @ {datetime.now()} ... \n")
