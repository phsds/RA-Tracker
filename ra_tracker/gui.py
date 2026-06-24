import sys
import logging

from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow

log = logging.getLogger(__name__)


def run():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
