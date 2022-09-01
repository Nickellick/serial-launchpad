########## EDIT HERE ########### 

APP_NAME = "Serial Launchpad"

RESOURCES_DIR = resources

UIC_TRANSLATOR = pyside6-uic
UI_FILES_DIR = $(RESOURCES_DIR)/ui
UI_PYFILES_DIR = forms

RCC_TRANSLATOR = pyside6-rcc
RCC_FILE = $(RESOURCES_DIR)/resources.qrc
RCC_PYFILE = $(RESOURCES_DIR)/rcc.py

ICON_PATH = $(RESOURCES_DIR)/ico/logo_256_black.ico


### END OF EDITABLE SEQUENCE ###

# Recieving ui files list without path
UI_FILES = $(notdir $(wildcard $(UI_FILES_DIR)/*.ui))
# Setting new names for py files based on ui filename
TRANSLATED_UI = $(UI_FILES:%.ui=$(UI_PYFILES_DIR)/%.py)

all: ui resources exe

# Depending on folder existence and translated file existence
# Also creating empty __init__.py file as module marker
ui: $(UI_PYFILES_DIR) $(TRANSLATED_UI)
	$(file > $(UI_PYFILES_DIR)/__init__.py,)

# Depending on changes in ui files
$(UI_PYFILES_DIR)/%.py: $(UI_FILES_DIR)/%.ui
	$(UIC_TRANSLATOR) $< -o $@

# Creating pyforms folder if not exist
$(UI_PYFILES_DIR):
	mkdir $@

# Remove precompiled files
clean:
	$(RM) $(TRANSLATED_UI) $(UI_PYFILES_DIR)/*.pyc $(UI_PYFILES_DIR)/__pycache__/*.py

resources: $(RCC_FILE) $(RESOURCES_DIR)
	pyside6-rcc $(RCC_FILE) -o $(RCC_PYFILE)

# Build exe
exe: ui resources
	pyinstaller --onefile --windowed --name=$(APP_NAME) --add-data="$(RESOURCES_DIR)/ico/logo_256_black.png;$(RESOURCES_DIR)/ico/logo_256_white.png" --icon=$(ICON_PATH) main.py