from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QWidget
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from kitovu.gui import startscreen, confscreen, syncscreen


class CentralWidget(QStackedWidget):

    status_message = pyqtSignal(str)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._sync_screen = syncscreen.SyncScreen()
        self.addWidget(self._sync_screen)

        self._conf_screen = confscreen.ConfScreen()
        self.addWidget(self._conf_screen)

        self._start_screen = startscreen.StartScreen()
        self.addWidget(self._start_screen)

        self._start_screen.sync_pressed.connect(self.on_sync_pressed)
        self._start_screen.conf_pressed.connect(self.on_conf_pressed)

        self._conf_screen.close_requested.connect(
            lambda: self.setCurrentWidget(self._start_screen))
        self._sync_screen.close_requested.connect(  # pragma: no branch
            lambda: self.setCurrentWidget(self._start_screen))

        self._sync_screen.status_message.connect(self.status_message)

        self.setCurrentWidget(self._start_screen)

    @pyqtSlot()
    def on_sync_pressed(self) -> None:
        self.setCurrentWidget(self._sync_screen)
        self._sync_screen.start_sync()

    @pyqtSlot()
    def on_conf_pressed(self) -> None:
        self._conf_screen.load_file()
        self.setCurrentWidget(self._conf_screen)


class MainWindow(QMainWindow):

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        central = CentralWidget()
        self.statusBar().showMessage("Bereit.")
        self.setCentralWidget(central)
        central.status_message.connect(self.statusBar().showMessage)
