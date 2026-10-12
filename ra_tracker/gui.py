"""Qt application bootstrap: creates the QApplication, loads the pixel font
and shows the main window."""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase

from .main_window import MainWindow

log = logging.getLogger(__name__)


def _resource_path() -> Path:
    """Return the directory containing bundled resources (fonts/images).

    When running as a PyInstaller ``--onefile`` executable, assets are
    unpacked to ``sys._MEIPASS`` instead of the source tree, so the lookup
    path has to change accordingly.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "ra_tracker"
    return Path(__file__).parent


def run():
    """Start the Qt event loop and block until the window is closed."""
    app = QApplication(sys.argv)

    # Load the 'Press Start 2P' pixel font used across the whole UI.
    # If it is missing, the app silently falls back to the system font.
    font_path = _resource_path() / "fonts" / "PressStart2P-Regular.ttf"
    if font_path.exists():
        fid = QFontDatabase.addApplicationFont(str(font_path))
        if fid >= 0:
            families = QFontDatabase.applicationFontFamilies(fid)
            if families:
                app.setFont(QFont(families[0], 10))
                log.info("Font loaded: %s from %s", families[0], font_path)
            else:
                log.warning("Font file loaded but no families found")
        else:
            log.warning("Failed to load font from %s", font_path)
    else:
        log.warning("Font file not found: %s", font_path)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
