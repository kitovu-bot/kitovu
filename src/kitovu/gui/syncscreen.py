import sys

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QProgressBar
from PyQt5.QtCore import pyqtSlot, QProcess


class SyncScreen(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._vbox = QVBoxLayout(self)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._vbox.addWidget(self._output)

        self._progress = QProgressBar()
        self._vbox.addWidget(self._progress)

        self._process = QProcess()
        self._process.readyRead.connect(self.on_process_ready_read)
        self._process.finished.connect(self.on_process_finished)

        # FIXME
        self.start_sync()

    @pyqtSlot()
    def on_process_ready_read(self):
        if self._process.canReadLine():
            data: bytes = bytes(self._process.readLine())
            self._output.append(data.decode('utf-8'))

    @pyqtSlot(int, QProcess.ExitStatus)
    def on_process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        self._output.append('\n\n')
        self._output.append('Process finished!')
        self._output.append(f'Exit code: {exit_code}')
        self._output.append(f'Exit status: {exit_status}')

    def start_sync(self):
        self._process.start(sys.executable, ['-m', 'kitovu', 'sync'])
