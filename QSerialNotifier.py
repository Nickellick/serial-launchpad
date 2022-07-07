import threading

from PySide6.QtCore import QObject, Signal
from serial.tools import list_ports

from QSingleton import QMetaSingleton
from stoppablethread import StoppableThread

class SerialNotifier(QObject, StoppableThread, metaclass=QMetaSingleton):
    # Qt signal must be outside of __init__ block
    serialAdded = Signal(tuple)
    serialRemoved = Signal(tuple)

    def __init__(self, pool, poll_period=0.5):
        self._poll_period=poll_period
        QObject.__init__(self)
        StoppableThread.__init__(self, pool=pool)
        self._sleep_event = threading.Event()

    def get_serial_devices(self):
        return set(list_ports.comports())

    def check_devices_changes(self, old_devices):
        devices = self.get_serial_devices()
        added = devices.difference(old_devices)
        removed = old_devices.difference(devices)
        return devices, {'added': added, 'removed': removed}

    def run(self):
        old_devices = self.get_serial_devices()
        while not self._stop_event.is_set():
            old_devices, result = self.check_devices_changes(old_devices)
            added = []
            removed = []
            for k, v in result.items():
                if k == 'added' and v:
                    added = list(map(lambda x: x.device, v))
                elif k == 'removed' and v:
                    removed = list(map(lambda x: x.device, v))
            if added:
                self.serialAdded.emit(tuple(added))
            if removed:
                self.serialRemoved.emit(tuple(removed))
            self._sleep_event.wait(timeout=self._poll_period)
    
    def join(self, timeout=None):
        self._sleep_event.set()
        super().join(timeout)
