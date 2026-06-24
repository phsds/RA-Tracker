import logging
from datetime import datetime
from io import BytesIO

from PIL import Image
from PyQt6.QtWidgets import (
    QFrame, QLabel, QHBoxLayout, QVBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QColor

from .api import RAClient

log = logging.getLogger(__name__)


class AchievementCard(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, ach: dict, parent=None):
        super().__init__(parent)
        self.ach = ach
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(90)
        self.setMaximumHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        is_hardcore = ach.get("HardcoreMode", 0) == 1 or ach.get("hardcoreMode", False)

        if is_hardcore:
            self.setStyleSheet("""
                AchievementCard {
                    background-color: #1a1a2e;
                    border: 2px solid #ffd700;
                    border-radius: 8px;
                    padding: 4px;
                }
                AchievementCard:hover {
                    border: 2px solid #ffaa00;
                    background-color: #222244;
                }
            """)
        else:
            self.setStyleSheet("""
                AchievementCard {
                    background-color: #1a1a2e;
                    border: 1px solid #3a3a5e;
                    border-radius: 8px;
                    padding: 4px;
                }
                AchievementCard:hover {
                    border: 1px solid #5a5a8e;
                    background-color: #222244;
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        badge_name = ach.get("BadgeName", ach.get("badgeName", ""))
        pixmap = self._load_badge_pixmap(badge_name)

        badge_label = QLabel()
        badge_label.setPixmap(pixmap)
        badge_label.setFixedSize(64, 64)
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title = ach.get("Title", ach.get("title", "?"))
        title_label = QLabel(title)
        title_label.setFont(QFont("Press Start 2P", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff;")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)

        description = ach.get("Description", ach.get("description", ""))
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Press Start 2P", 9))
        desc_label.setStyleSheet("color: #aaaaaa;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)

        game = ach.get("GameTitle", ach.get("gameTitle", ""))
        console = ach.get("ConsoleName", ach.get("consoleName", ""))
        game_text = f"{game}"
        if console:
            game_text += f"  |  {console}"
        game_label = QLabel(game_text)
        game_label.setFont(QFont("Press Start 2P", 8))
        game_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(game_label)

        points = ach.get("Points", ach.get("points", 0))
        date_raw = ach.get("Date", ach.get("date", ""))
        date_str = ""
        if date_raw:
            try:
                dt = datetime.strptime(date_raw, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                date_str = date_raw

        meta_text = f"{points} pts"
        if is_hardcore:
            meta_text += "  [HARDCORE]"
        if date_str:
            meta_text += f"  |  {date_str}"
        meta_label = QLabel(meta_text)
        meta_label.setFont(QFont("Press Start 2P", 8))
        if is_hardcore:
            meta_label.setStyleSheet("color: #ffd700;")
        else:
            meta_label.setStyleSheet("color: #666666;")
        info_layout.addWidget(meta_label)

        layout.addLayout(info_layout, 1)

    def mousePressEvent(self, event):
        self.clicked.emit(self.ach)
        super().mousePressEvent(event)

    def _load_badge_pixmap(self, badge_name: str) -> QPixmap:
        if not badge_name:
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor("#333333"))
            return pixmap
        try:
            img = RAClient.load_badge(badge_name)
            if img:
                img = img.resize((64, 64), Image.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())
                return pixmap
        except Exception:
            pass
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#333333"))
        return pixmap
