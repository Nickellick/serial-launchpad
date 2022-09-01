from collections import namedtuple
from functools import partial
import json
import logging
import os
import subprocess
import sys

import darkdetect
from PySide6 import QtCore
from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
from PySide6.QtWidgets import QSystemTrayIcon, QTableWidgetItem, QWidget
from serial.tools import list_ports

from forms.SettingsForm import Ui_Form as SettingsForm
from forms.ConnectionForm import Ui_Form as ConnectionForm
from forms.TerminalSettingsAddForm import Ui_Form as AddTerminalForm
from forms.TerminalSettingsForm import Ui_Form as SetupTerminalForm
from QSerialNotifier import SerialNotifier
import resources.rcc

THREAD_POOL = []

SERIAL_BAUD = [
    9600,
    115200,
    921600
]

TerminalSetting = namedtuple('TerminalSetting', ['alias', 'path', 'arguments'])


class CommandLauncher:
    @staticmethod
    def parse_arg_string(port, baud, string):
        return string.replace('::port::', port).replace('::baud::', baud)

    @staticmethod
    def launch_term(command, args=None):
        if args:
            command = f'{command} {args}'
        subprocess.Popen(command)

    @staticmethod
    def parse_and_launch(port, baud, command, arg):
        arg = __class__.parse_arg_string(port, baud, arg)
        __class__.launch_term(command, arg)


class ConnectionWindow(QWidget, ConnectionForm):
    def __init__(self):
        super(ConnectionWindow, self).__init__()
        self.setupUi(self)
        self.pushButton_cancel.clicked.connect(self.close)
        self.comboBox_baud.clear()
        self.comboBox_baud.addItems(map(str, SERIAL_BAUD))
        self.pushButton_ok.clicked.connect(self._ok_clicked)
        self.pushButton_cancel.clicked.connect(self.close)
        self.pushButton_ok_save.clicked.connect(self._save_clicked)

    def keyPressEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_Return:
                self.pushButton_ok_save.click()
                return
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
            return
        if event.key() == QtCore.Qt.Key_Return:
            self.pushButton_ok.click()
            return

    def show(self, selected_comport, all_comports):
        logging.debug(f'Selected port: {selected_comport}')
        logging.debug(all_comports)
        self.comboBox_comport.clear()
        self.comboBox_comport.addItems(all_comports)
        current_comport_index = all_comports.index(selected_comport)
        self.comboBox_comport.setCurrentIndex(current_comport_index)
        app_instance = MainApplication.instance()
        try:
            baud = app_instance.settings[selected_comport]['baud']
            app = app_instance.settings[selected_comport]['app']
            self.comboBox_baud.setCurrentIndex(SERIAL_BAUD.index(int(baud)))
            # self.comboBox_app.setCurrentIndex[]
        except KeyError:
            pass
        super().show()

    def _ok_clicked(self):
        current_comport = self.comboBox_baud.currentText()
        args = f'-serial {self.comboBox_comport.currentText()} '\
            '-sercfg {current_comport},8,n,1,N'
        CommandLauncher.launch_term('putty', args)
        self.close()

    def _save_clicked(self):
        current_port = self.comboBox_comport.currentText()
        setting = {
            'baud': int(self.comboBox_baud.currentText()),
            'app': self.comboBox_default_terminal.currentText()
        }
        app_instance = MainApplication.instance()
        app_instance.settings['ports'][current_port] = setting
        app_instance.save_settings()
        self._ok_clicked()


class SettingsWindow(QWidget, SettingsForm):
    def __init__(self):
        super(SettingsWindow, self).__init__()
        self.setupUi(self)
        self._software_settings_window = SetupTerminalWindow()
        self.pushButton_manage.clicked.connect(
            self._software_settings_window.show
        )


class SetupTerminalWindow(QWidget, SetupTerminalForm):
    def __init__(self):
        super(SetupTerminalWindow, self).__init__()
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.settings_window = AddTerminalWindow()
        self.pushButton_add.clicked.connect(self._add_clicked)

    def _add_clicked(self):
        self.settings_window.show()

    @Slot(TerminalSetting)
    def _item_added(self, setting):
        item = QTableWidgetItem(setting.alias, setting.path, setting.arguments)
        self.tableWidget.setItem(0, 0, item)


class MainApplication(QApplication):
    def __init__(self, *args, **kwargs):
        try:
            self._settings_path = kwargs.pop('settings_path')
        except KeyError:
            self._settings_path = None
        super(MainApplication, self).__init__(*args, **kwargs)
        self.load_settings()

    def load_settings(self, settings_path=None):
        if settings_path is not None:
            self._settings_path = settings_path
        if self._settings_path is None:
            self.init_settings()
            return
        try:
            with open(self._settings_path, 'r') as settings_file:
                self.settings = json.loads(settings_file.read())
        except FileNotFoundError:
            self.init_settings()

    def save_settings(self, settings_path=None):
        if settings_path is not None:
            self._settings_path = settings_path
        if self._settings_path is None:
            raise ValueError('Can\'t save!')
        with open(self._settings_path, 'w') as settings_file:
            settings_file.write(json.dumps(self.settings, indent=2))

    def init_settings(self):
        self.settings = {}
        self.settings['ports'] = {}
        self.settings['apps'] = {}

    def quit(self, *args, **kwargs):
        for thr in THREAD_POOL:
            thr.join()
        super().quit(*args, **kwargs)


class AddTerminalWindow(QWidget, AddTerminalForm):
    def __init__(self, term_setting=None):
        super(AddTerminalWindow, self).__init__()
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.term_setting = None
        if term_setting:
            self._preload_fields(term_setting)
        self.msgbox = QMessageBox()
        self.pushButton_ok.clicked.connect(self._ok_clicked)

    def _preload_fields(self):
        self.lineEdit_alias.setText(self.term_setting.alias)
        self.lineEdit_arguments.setText(self.term_setting.arguments)
        self.lineEdit_path.setText(self.term_setting.path)

    def _ok_clicked(self):
        if not self.lineEdit_alias.text():
            self.msgbox.setText('Empty alias')
            self.msgbox.setInformativeText('Alias line can\'t be empty!')
            self.msgbox.setIcon(QMessageBox.Warning)
            self.msgbox.setWindowTitle('Error')
            self.msgbox.show()
            return
        alias = self.lineEdit_alias.text()
        path = self.lineEdit_path.text()
        arguments = self.lineEdit_arguments.text()
        term_setting = TerminalSetting(alias, path, arguments)

    def exec(self):
        super().exec()
        return self.term_setting


class TrayApplication(QSystemTrayIcon):
    def __init__(self, icon):
        super(TrayApplication, self).__init__()
        self._comports_actions = {}
        self._last_connected_device = None
        self._connection_window = ConnectionWindow()
        self._settings_window = SettingsWindow()

        self.setIcon(icon)
        self._serial_notifier = SerialNotifier(THREAD_POOL)
        self._init_notifier()
        self._init_menu()
        self._serial_notifier.start()
        self.setVisible(True)

        for dev, obj in self._comports_actions.items():
            obj = QAction()
            logging.debug(f'{dev} - {obj.text()}')

    def _init_notifier(self):
        self._serial_notifier.serialAdded.connect(self._notifier_on_added)
        self._serial_notifier.serialRemoved.connect(self._notifier_on_removed)
        self.messageClicked.connect(self._notifier_on_message_clicked)

    def _init_menu(self):
        self.comports_menu = QMenu('COM devices')
        for dev in list_ports.comports():
            device_action = QAction(dev.device)
            # f = lambda: self.show_connection_window(dev.device)
            # Not working inside loop!
            f = partial(self.show_connection_window, dev.device)
            device_action.triggered.connect(f)
            self._comports_actions[dev.device] = device_action
            self.comports_menu.addAction(device_action)
            logging.debug(
                f'id QAction: {id(device_action)}; id lambda: {id(f)}'
            )
        self.setContextMenu(QMenu())
        self.contextMenu().addMenu(self.comports_menu)
        self.contextMenu().addSeparator()
        settings = self.contextMenu().addAction('Settings')
        settings.triggered.connect(self._on_settings_clicked)
        self.contextMenu().addSeparator()
        quit = self.contextMenu().addAction('Quit')
        quit.triggered.connect(MainApplication.instance().quit)

    def _notifier_on_added(self, devices):
        for dev in devices:
            logging.debug(f'{dev} added')
            action = QAction(dev)
            action.triggered.connect(lambda: self.show_connection_window(dev))
            self._comports_actions[dev] = action
            self.comports_menu.addAction(action)
            self._last_connected_device = dev
            self.showMessage(f'{dev} is added', 'Click to open terminal')

    def _notifier_on_removed(self, devices):
        for dev in devices:
            logging.debug(f'{dev} removed')
            action = self._comports_actions.pop(dev)
            self.comports_menu.removeAction(action)
            self._last_connected_device = None
            self.showMessage(f'{dev} is removed', 'Click to dismiss')

    def _notifier_on_message_clicked(self):
        if self._last_connected_device:
            self.show_connection_window(self._last_connected_device)

    def _on_settings_clicked(self):
        self._settings_window.show()

    def show_connection_window(self, selected_port):
        self._connection_window.show(
            selected_port,
            list(self._comports_actions.keys())
        )


def normalize_path(path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, path)
    else:
        return path


def main():
    logging.basicConfig(
        format='%(asctime)s\t[%(levelname)s]: %(message)s',
        stream=sys.stdout,
        level=logging.DEBUG
    )
    app = MainApplication(settings_path='settings.json')
    app.setQuitOnLastWindowClosed(False)

    # Adding an icon
    if darkdetect.isLight():
        # icon = QIcon(normalize_path("resources/ico/logo_256_black.png"))
        icon = QIcon(':icons/logo_black.png')
    else:
        # icon = QIcon(normalize_path("resources/ico/logo_256_white.png"))
        icon = QIcon(':icons/logo_white.png')
    icon.setIsMask(True)
    logging.debug(f'Is icon mask? {icon.isMask()}')

    # Adding item on the menu bar
    logging.debug('Creating system tray object...')
    tray = TrayApplication(icon)
    logging.debug('Showing...')
    tray.setVisible(True)

    logging.debug('Executing app...')
    app.exec()


if __name__ == '__main__':
    main()
