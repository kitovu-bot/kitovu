import functools

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QDialogButtonBox
from PyQt5.QtCore import pyqtSignal

from kitovu.sync import settings


class ConfScreen(QWidget):

    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._vbox = QVBoxLayout(self)
        self._edit = QTextEdit()
        self._edit.setStyleSheet("font-family: monospace;")
        self._vbox.addWidget(self._edit)

        self._conf_file = settings.get_config_file_path()
        self._edit.setPlainText(self._conf_file.read_text('utf-8'))
        self._edit.setAcceptRichText(False)

        self._buttons = QDialogButtonBox()
        self._cancel_button = self._buttons.addButton("Abbrechen", QDialogButtonBox.DestructiveRole)
        self._save_button = self._buttons.addButton("Speichern", QDialogButtonBox.ApplyRole)
        self._back_button = self._buttons.addButton("Speichern und zurück", QDialogButtonBox.AcceptRole)
        self._vbox.addWidget(self._buttons)

        self._cancel_button.clicked.connect(self.close_requested)
        self._save_button.clicked.connect(functools.partial(self.save, close=False))
        self._back_button.clicked.connect(functools.partial(self.save, close=True))

    def save(self, close):
        text = self._edit.toPlainText()
        # FIXME validate config and show errors
        self._conf_file.write_text(text, encoding='utf-8')
        if close:
            self.close_requested.emit()
