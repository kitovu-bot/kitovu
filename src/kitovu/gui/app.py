import sys

from PyQt5.QtWidgets import QApplication

from kitovu.gui import mainwindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QPushButton {
            padding: 20px;
        }
    """)
    main = mainwindow.MainWindow()
    main.show()
    status: int = app.exec_()
    return status


if __name__ == '__main__':
    sys.exit(run())
