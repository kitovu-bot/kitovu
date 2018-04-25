import sys
import pathlib

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QProgressBar, QStackedWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QProcess

from kitovu.sync import settings


class LogoWidget(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        # FIXME how to load this properly?
        logo_path = pathlib.Path(__file__).parent / 'kitovu.jpg'
        self._pixmap = QPixmap(str(logo_path))
        self.setPixmap(self._pixmap)


class StartScreen(QWidget):

    sync_pressed = pyqtSignal()
    conf_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vbox = QVBoxLayout(self)

        self._logo = LogoWidget(self)
        self._vbox.addWidget(self._logo)

        self._sync_button = QPushButton("Dateien synchronisieren")
        self._sync_button.pressed.connect(self.sync_pressed)
        self._vbox.addWidget(self._sync_button)

        self._conf_button = QPushButton("Konfiguration verwalten")
        self._conf_button.pressed.connect(self.conf_pressed)
        self._vbox.addWidget(self._conf_button)


class ConfScreen(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._vbox = QVBoxLayout(self)
        self._edit = QTextEdit()
        self._vbox.addWidget(self._edit)

        conf_file = settings.get_config_file_path()
        self._edit.setText(conf_file.read_text('utf-8'))


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


class CentralWidget(QStackedWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._sync_screen = SyncScreen()
        self.addWidget(self._sync_screen)

        self._conf_screen = ConfScreen()
        self.addWidget(self._conf_screen)

        self._start_screen = StartScreen()
        self.addWidget(self._start_screen)
        self._start_screen.sync_pressed.connect(
            lambda: self.setCurrentWidget(self._sync_screen))
        self._start_screen.conf_pressed.connect(
            lambda: self.setCurrentWidget(self._conf_screen))

        self.setCurrentWidget(self._start_screen)


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        central = CentralWidget()
        self.statusBar().showMessage("Bereit.")
        self.setCentralWidget(central)
