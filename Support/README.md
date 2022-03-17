# VMC
Vocal Maturity Coding for NDD Lab, Purdue University.

# Support Folder
The documentation files and files needed for deployment.

# Capture PIP dependencies.
"VirtualEnvironment/Scripts/python" -m pip freeze > requirements.txt

# Install PIP requirements.
"VirtualEnvironment/Scripts/python" -m pip install -r requirements.txt

# Generate PostgreSQL classes.
-- AWS DB
"VirtualEnvironment/Scripts/sqlacodegen" "postgresql://<UserName>:<Password>@<Server>:5432/VocalMaturityDB" --schema Main --outfile "DataAccess/BaseDB.py"

# Convert UI to PY
"VirtualEnvironment/Scripts/pyrcc5" "Presentation/Resources/GuiResources.qrc" -o "Presentation/GuiResources.py"
"VirtualEnvironment/Scripts/pyuic5" "Presentation/LoginForm.ui" -o "Presentation/LoginFormBase.py" --import-from=Presentation --resource-suffix=
"VirtualEnvironment/Scripts/pyuic5" "Presentation/CodingGUI.ui" -o "Presentation/CodingGuiBase.py" --import-from=Presentation --resource-suffix=

