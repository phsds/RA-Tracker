"""Main application window: login, fetch and display of achievements."""

import sys
import logging
from collections import OrderedDict
from pathlib import Path

import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QStatusBar,
)
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QFont, QIcon, QPixmap

from .api import RAClient
from . import credential_manager
from . import cache as cache_mgr
from .fetch_worker import FetchWorker
from .achievement_card import AchievementCard
from .achievement_dialog import AchievementDetailDialog
from .collapsible_section import CollapsibleSection

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main UI: credential inputs, fetch controls, scrollable achievement list.

    Responsible for validating the login against the API, saving/loading
    credentials, running the fetch on a background thread and rendering the
    achievements grouped by game.
    """

    @staticmethod
    def _resource_path() -> Path:
        """Return the directory with bundled resources (icon/logo).

        Adapts to PyInstaller's ``--onefile`` extraction folder (``_MEIPASS``).
        """
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS) / "ra_tracker"
        return Path(__file__).parent

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RA Tracker - RetroAchievements")
        icon_path = self._resource_path() / "images" / "RetroAchievements.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(800, 600)
        # Global dark "retro" theme applied to the main window.
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f0f23;
            }
            QLabel {
                color: #cccccc;
            }
            QLineEdit {
                background-color: #1a1a2e;
                color: #ffffff;
                border: 1px solid #3a3a5e;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #4a4a8a;
                color: white;
                border: 1px solid #5a5aaa;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5aaa;
                border: 1px solid #7a7aca;
            }
            QPushButton:pressed {
                background-color: #3a3a6a;
                border: 1px solid #2a2a5a;
            }
            QScrollArea {
                border: none;
                background-color: #0f0f23;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # -- Logo header ------------------------------------------------------
        logo_path = self._resource_path() / "images" / "RetroAchievements.png"
        logo_pixmap = QPixmap(str(logo_path))
        title_label = QLabel()
        if not logo_pixmap.isNull():
            # Keep the height proportional while fixing the display width.
            scaled = logo_pixmap.scaledToWidth(180, Qt.TransformationMode.SmoothTransformation)
            title_label.setPixmap(scaled)
        else:
            # Fallback text if the bundled PNG is missing.
            title_label.setText("RA Tracker")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # -- Credentials input panel ------------------------------------------
        input_widget = QWidget()
        input_widget.setStyleSheet("background-color: #1a1a2e; border-radius: 8px;")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(12, 10, 12, 10)
        input_layout.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self.api_key_input = QLineEdit()
        # Mask the API key so it is not readable on screen.
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("API Key")
        row1.addWidget(self.api_key_input, 1)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        row1.addWidget(self.username_input, 1)

        self.login_btn = QPushButton("Login")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self._validate_login)
        row1.addWidget(self.login_btn)

        self.login_status = QLabel("")
        self.login_status.setFont(QFont("Press Start 2P", 9, QFont.Weight.Bold))
        self.login_status.setStyleSheet("color: #888888; padding: 2px 4px;")
        row1.addWidget(self.login_status)

        input_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)

        # Invisible spacers keep the action buttons right-aligned.
        spacer1 = QWidget()
        spacer1.setFixedWidth(0)
        row2.addWidget(spacer1, 1)
        spacer2 = QWidget()
        spacer2.setFixedWidth(0)
        row2.addWidget(spacer2, 1)

        self.cache_btn = QPushButton("Clear Cache")
        self.cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cache_btn.clicked.connect(self._clear_cache)
        row2.addWidget(self.cache_btn)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.clicked.connect(self._clear_saved_credentials)
        row2.addWidget(self.logout_btn)

        input_layout.addLayout(row2)
        main_layout.addWidget(input_widget)

        # -- Scrollable results area -------------------------------------------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(12)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.results_container)
        main_layout.addWidget(self.scroll, 1)

        self.status = QStatusBar()
        self.status.setStyleSheet("color: #888888;")
        self.setStatusBar(self.status)
        self.status.showMessage("Ready. Enter your API Key and username to start.")

        self.client: RAClient | None = None
        self._logged_in = False

        # Auto-login with previously saved credentials (if any).
        self._load_saved_credentials()

    def _validate_login(self):
        """Validate the entered credentials against the API and store them."""
        api_key = self.api_key_input.text().strip()
        username = self.username_input.text().strip()

        if not api_key or not username:
            self.login_status.setStyleSheet("color: #ff6666;")
            self.login_status.setText("Fill in API Key and Username!")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Validating...")
        self.login_status.setText("")
        # Let the UI repaint the disabled button before blocking on the request.
        QApplication.processEvents()

        try:
            client = RAClient(api_key)
            # A successful summary response is our login validation.
            data = client.get_user_summary(username)
            if data:
                self.client = client
                self._logged_in = True
                self.login_status.setStyleSheet("color: #66ff66;")
                self.login_status.setText("Login OK")
                self.status.showMessage(f"Logged in as {username}.")
                # Persist the key for the next launch.
                credential_manager.encrypt_credentials(api_key, username)
                log.info("Valid login for %s", username)
                self._fetch_achievements()
            else:
                self._logged_in = False
                self.login_status.setStyleSheet("color: #ff6666;")
                self.login_status.setText("Empty response")
        except requests.RequestException as e:
            self._logged_in = False
            self.login_status.setStyleSheet("color: #ff6666;")
            resp = getattr(e, "response", None)
            if resp is not None and resp.status_code == 401:
                self.login_status.setText("Invalid API Key!")
            else:
                self.login_status.setText(f"Error: {e}")
            log.error("Login failed: %s", e)
        except Exception as e:
            self._logged_in = False
            self.login_status.setStyleSheet("color: #ff6666;")
            self.login_status.setText(f"Error: {e}")
            log.error("Unexpected login error: %s", e, exc_info=True)

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Validate Login")

    def _load_saved_credentials(self):
        """Restore saved credentials (if any) and trigger a silent auto-login."""
        creds = credential_manager.decrypt_credentials()
        if creds:
            self.api_key_input.setText(creds.get("api_key", ""))
            self.username_input.setText(creds.get("username", ""))
            self.login_status.setStyleSheet("color: #66ff66;")
            self.login_status.setText("Credentials loaded")
            self._validate_login()

    def _clear_saved_credentials(self):
        """Logout: erase stored credentials, inputs, and the results list."""
        credential_manager.clear_credentials()
        self.api_key_input.clear()
        self.username_input.clear()
        self.client = None
        self._logged_in = False
        self.login_status.setStyleSheet("color: #888888;")
        self.login_status.setText("Credentials removed")
        self.status.showMessage("Credentials cleared.")
        self._clear_results()

    def _clear_results(self):
        """Remove every widget currently shown in the results area."""
        for i in reversed(range(self.results_layout.count())):
            widget = self.results_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def _clear_cache(self):
        """Delete the on-disk cache and the in-memory badge cache."""
        count = cache_mgr.clear_cache()
        # The process-wide badge cache must be cleared too, or stale images win.
        RAClient._badge_cache.clear()
        self.status.showMessage(f"Cache cleared ({count} file(s))." if count else "Cache is empty.")

    def _fetch_achievements(self):
        """Start the API fetch on a background QThread.

        ``FetchWorker`` runs off-thread and talks back to the UI exclusively
        through signals, which Qt marshals back to the main thread.
        """
        api_key = self.api_key_input.text().strip()
        username = self.username_input.text().strip()
        log.info("Starting fetch: username=%s", username)

        if not api_key or not username:
            log.warning("Required fields not filled")
            return

        self.status.showMessage("Querying RetroAchievements API...")

        self._thread = QThread()
        self._worker = FetchWorker(self.client, username)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_fetch_finished(self, data: list):
        """Render whatever the worker fetched."""
        self._display_achievements(data)
        if not data:
            log.info("No achievements found")
            self.status.showMessage("No achievements found.")
        else:
            log.info("Displaying %d achievements", len(data))
            self.status.showMessage(f"Displaying {len(data)} achievement(s).")

    def _on_fetch_error(self, msg: str):
        log.error("Fetch error: %s", msg)
        self.status.showMessage("Query error.")

    def _display_achievements(self, achievements: list[dict]):
        """Rebuild the results area, one collapsible section per game.

        Cards are laid out in a grid whose column count adapts to the window
        width (``width() // 650`` cards per row).
        """
        self._clear_results()

        # Group achievements by game title, preserving first-seen order.
        groups: OrderedDict[str, list[dict]] = OrderedDict()
        for ach in achievements:
            game = ach.get("GameTitle", ach.get("gameTitle", "?"))
            groups.setdefault(game, []).append(ach)

        cols = max(1, self.width() // 650)

        for game_title, game_achs in groups.items():
            section = CollapsibleSection(game_title, len(game_achs))
            grid = section.grid()

            for idx, ach in enumerate(game_achs):
                card = AchievementCard(ach)
                card.clicked.connect(self._open_detail)
                row = idx // cols
                col = idx % cols
                grid.addWidget(card, row, col)

            self.results_layout.addWidget(section)

        # Push everything to the top when there is spare vertical space.
        self.results_layout.addStretch()

    def _open_detail(self, ach: dict):
        """Open the detailed achievement dialog (modal)."""
        if not self.client:
            return
        dialog = AchievementDetailDialog(ach, self.client, self)
        dialog.exec()
