from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit

from kitovu.sync import settings


class ConfScreen(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._vbox = QVBoxLayout(self)
        self._edit = QTextEdit()
        self._vbox.addWidget(self._edit)

        conf_file = settings.get_config_file_path()
        self._edit.setText(conf_file.read_text('utf-8'))
