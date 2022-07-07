########## EDIT HERE ########### 

UIC_TRANSLATOR = pyside6-uic
UI_FILES_DIR = resources/ui
UI_PYFILES_DIR = forms

### END OF EDITABLE SEQUENCE ###

# Recieving ui files list without path
UI_FILES = $(notdir $(wildcard $(UI_FILES_DIR)/*.ui))
# Setting new names for py files based on ui filename
TRANSLATED_UI = $(UI_FILES:%.ui=$(UI_PYFILES_DIR)/%.py)

all: ui

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