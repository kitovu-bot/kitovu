import sys

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QProgressBar, QPushButton
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QProcess


class ProgressBar(QProgressBar):

    def show_empty(self) -> None:
        self.setMinimum(0)
        self.setMaximum(1)
        self.setValue(0)

    def show_full(self) -> None:
        self.setMinimum(0)
        self.setMaximum(1)
        self.setValue(1)

    def show_pulse(self) -> None:
        self.setMinimum(0)
        self.setMaximum(0)
        self.setValue(0)


class SyncScreen(QWidget):

    PYTHON_ARGS = ['-m', 'kitovu', 'sync']
    status_message = pyqtSignal(str)
    close_requested = pyqtSignal()
    finished = pyqtSignal(int, QProcess.ExitStatus)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._vbox = QVBoxLayout(self)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._vbox.addWidget(self._output)

        self._progress = ProgressBar()
        self._progress.show_empty()
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
    def on_process_started(self) -> None:
        self._cancel_button.setText("Abbrechen")
        self._progress.show_pulse()
        self.status_message.emit("Synchronisation läuft...")

    @pyqtSlot()
    def on_process_ready_read(self) -> None:
        if self._process.canReadLine():
            data: bytes = bytes(self._process.readLine())
            self._output.append(data.decode('utf-8'))

    @pyqtSlot(int, QProcess.ExitStatus)
    def on_process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._cancel_button.setText("Zurück")
        self._progress.show_full()

        data: bytes = bytes(self._process.readAll())
        self._output.append(data.decode('utf-8'))

        if exit_status == QProcess.CrashExit:
            self.status_message.emit("Fehler: Kitovu-Prozess ist abgestürzt.")
        elif exit_code != 0:
            self.status_message.emit(f"Fehler: Kitovu-Prozess wurde mit Status {exit_code} "
                                     "beendet.")
        else:
            self.status_message.emit("Synchronisation erfolgreich beendet.")

        self.finished.emit(exit_code, exit_status)

    @pyqtSlot(str)
    def on_status_message(self, message: str) -> None:
        self._output.append(message)

    @pyqtSlot()
    def on_cancel_clicked(self) -> None:
        if self._process.state() != QProcess.NotRunning:
            if sys.platform.startswith('win'):  # pragma: no cover
                self._process.kill()
            else:
                self._process.terminate()

        self.close_requested.emit()

    def start_sync(self) -> None:
        self._output.setPlainText("")
        self._progress.show_empty()
        self._process.start(sys.executable, self.PYTHON_ARGS)
