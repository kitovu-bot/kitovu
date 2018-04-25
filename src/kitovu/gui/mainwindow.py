from PyQt5.QtWidgets import QMainWindow, QStackedWidget

from kitovu.gui import startscreen, confscreen, syncscreen


class CentralWidget(QStackedWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._sync_screen = syncscreen.SyncScreen()
        self.addWidget(self._sync_screen)

        self._conf_screen = confscreen.ConfScreen()
        self.addWidget(self._conf_screen)

        self._start_screen = startscreen.StartScreen()
        self.addWidget(self._start_screen)

        self._start_screen.sync_pressed.connect(
            lambda: self.setCurrentWidget(self._sync_screen))
        self._start_screen.conf_pressed.connect(
            lambda: self.setCurrentWidget(self._conf_screen))
        self._conf_screen.close_requested.connect(
            lambda: self.setCurrentWidget(self._start_screen))

        self.setCurrentWidget(self._start_screen)


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        central = CentralWidget()
        self.statusBar().showMessage("Bereit.")
        self.setCentralWidget(central)
