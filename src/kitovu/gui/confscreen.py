import functools
import pathlib

import yaml

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QDialogButtonBox, QPushButton,
                             QMessageBox)
from PyQt5.QtCore import pyqtSignal

from kitovu import utils
from kitovu.sync import settings, syncing


class ConfScreen(QWidget):

    close_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._vbox = QVBoxLayout(self)
        self._edit = QTextEdit()
        self._edit.setStyleSheet("font-family: monospace;")
        self._edit.setAcceptRichText(False)
        self._vbox.addWidget(self._edit)

        self._conf_file: pathlib.Path = settings.get_config_file_path()

        self._buttons = QDialogButtonBox()
        self._cancel_button: QPushButton = self._buttons.addButton(
            "Abbrechen", QDialogButtonBox.DestructiveRole)
        self._save_button: QPushButton = self._buttons.addButton(
            "Speichern", QDialogButtonBox.ApplyRole)
        self._back_button: QPushButton = self._buttons.addButton(
            "Speichern und zurück", QDialogButtonBox.AcceptRole)
        self._vbox.addWidget(self._buttons)

        self._cancel_button.clicked.connect(self.close_requested)
        self._save_button.clicked.connect(functools.partial(self.save, close=False))
        self._back_button.clicked.connect(functools.partial(self.save, close=True))

    def load_file(self) -> None:
        try:
            self._edit.setPlainText(self._conf_file.read_text('utf-8'))
        except FileNotFoundError:
            pass

    def save(self, close: bool) -> None:
        text: str = self._edit.toPlainText()
        self._conf_file.write_text(text, encoding='utf-8')

        try:
            syncing.validate_config(self._conf_file)
        except (utils.InvalidSettingsError, yaml.YAMLError) as ex:
            QMessageBox.critical(self, "Failed to validate config", str(ex))
            return

        if close:
            self.close_requested.emit()
