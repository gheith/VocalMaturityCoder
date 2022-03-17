"""
User Model

Represents all the information needed for the User (Coder, Admin) to use the application, along with some
additional attributes.
"""

__copyright__ = "Copyright 2022, Neurodevelopmental Family Lab, Purdue University"
__credits__ = ["Alex Gheith", "Lisa Hammrick", "Prof. Bridgette Keheller", "Prof. Amanda Seidl"]
__author__ = "Alex Gheith"
__version__ = "1.1.0"
__status__ = "Production"

import attr
from attr.validators import instance_of


@attr.s
class UserModel(object):

    UserID = attr.ib(validator=instance_of(int))
    UserName = attr.ib(validator=instance_of(str))
    DbPassword = attr.ib()
    NewPassword = attr.ib(validator=instance_of(str))
    FirstName = attr.ib(validator=instance_of(str))
    MiddleName = attr.ib()
    LastName = attr.ib(validator=instance_of(str))
    Email = attr.ib(validator=instance_of(str))
    UserType = attr.ib(validator=instance_of(str))
    UserTypeID = attr.ib(validator=instance_of(int))
    IsActive = attr.ib(validator=instance_of(bool))
    IsAdmin = attr.ib(validator=instance_of(bool))
    IsLocked = attr.ib(validator=instance_of(bool))
