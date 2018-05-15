import pathlib

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSignal, Qt


class LogoWidget(QLabel):

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        # FIXME how to load this properly?
        # This will work for now, but once we package kitovu as a Python
        # package, we'll need to use e.g. pkg_resources
        logo_path = pathlib.Path(__file__).parent / 'kitovu.png'
        self._pixmap: QPixmap = QPixmap(str(logo_path)).scaledToWidth(500)
        self.setPixmap(self._pixmap)
        self.setAlignment(Qt.AlignCenter)


class StartScreen(QWidget):

    sync_pressed = pyqtSignal()
    conf_pressed = pyqtSignal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                margin: 10px;
            }
        """)

        self._vbox = QVBoxLayout(self)

        self._logo = LogoWidget(self)
        self._vbox.addWidget(self._logo)

        self._sync_button = QPushButton("Dateien synchronisieren")
        self._sync_button.pressed.connect(self.sync_pressed)
        self._vbox.addWidget(self._sync_button)

        self._conf_button = QPushButton("Konfiguration verwalten")
        self._conf_button.pressed.connect(self.conf_pressed)
        self._vbox.addWidget(self._conf_button)
