import sys

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QProgressBar, QPushButton
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QProcess


class SyncScreen(QWidget):

    status_message = pyqtSignal(str)
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._vbox = QVBoxLayout(self)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._vbox.addWidget(self._output)

        self._progress = QProgressBar()
        self._progress.setMinimum(0)
        self._progress.setMaximum(0)
        self._vbox.addWidget(self._progress)

        self._cancel_button = QPushButton("Zurück")
        self._cancel_button.clicked.connect(self.on_cancel_clicked)
        self._vbox.addWidget(self._cancel_button)

        self._process = QProcess()
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyRead.connect(self.on_process_ready_read)
        self._process.started.connect(self.on_process_started)
        self._process.finished.connect(self.on_process_finished)

        self.status_message.connect(self.on_status_message)

    @pyqtSlot()
    def on_process_started(self):
        self._cancel_button.setText("Abbrechen")
        self._progress.setValue(0)
        self.status_message.emit("Sychronisation läuft...")

    @pyqtSlot()
    def on_process_ready_read(self):
        if self._process.canReadLine():
            data: bytes = bytes(self._process.readLine())
            self._output.append(data.decode('utf-8'))

    @pyqtSlot(int, QProcess.ExitStatus)
    def on_process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        self._cancel_button.setText("Zurück")
        self._progress.setValue(-1)

        data: bytes = bytes(self._process.readAll())
        self._output.append(data.decode('utf-8'))

        if exit_status == QProcess.CrashExit:
            self.status_message.emit("Fehler: Kitovu-Prozess ist abgestürzt")
        elif exit_code != 0:
            self.status_message.emit(f"Fehler: Kitovu-Prozess wurde mit Status {exit_code} beendet.")
        else:
            self.status_message.emit("Synchronisation erfolgreich beendet.")

    @pyqtSlot(str)
    def on_status_message(self, message):
        if self._output.toPlainText():
            self._output.append('\n\n')
        self._output.append(message)

    @pyqtSlot()
    def on_cancel_clicked(self):
        if self._process.state() != QProcess.NotRunning:
            if sys.platform.startswith('win'):
                self._process.kill()
            else:
                self._process.terminate()

        self.close_requested.emit()

    def start_sync(self):
        self._output.setPlainText("")
        self._process.start(sys.executable, ['-m', 'kitovu', 'sync'])
