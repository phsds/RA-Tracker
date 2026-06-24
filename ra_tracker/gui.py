import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase

from .main_window import MainWindow

log = logging.getLogger(__name__)


def run():
    app = QApplication(sys.argv)

    font_path = Path(__file__).parent / "fonts" / "PressStart2P-Regular.ttf"
    if font_path.exists():
        fid = QFontDatabase.addApplicationFont(str(font_path))
        if fid >= 0:
            families = QFontDatabase.applicationFontFamilies(fid)
            if families:
                app.setFont(QFont(families[0], 8))
                log.info("Font loaded: %s", families[0])
            else:
                log.warning("Font file loaded but no families found")
        else:
            log.warning("Failed to load font from %s", font_path)
    else:
        log.warning("Font file not found: %s", font_path)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
