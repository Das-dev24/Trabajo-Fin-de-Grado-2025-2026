from PyQt6.QtCore import QThread, pyqtSignal

from hives.core.sensor import SerialReader


class SerialWorker(QThread):
    data_received  = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, reader: SerialReader):
        super().__init__()
        self.reader   = reader
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            data = self.reader.read_data()
            if data and len(data) == 18:
                self.data_received.emit(data)
            self.msleep(50)

    def stop(self):
        self._running = False
        self.wait(2000)
