import logging
from datetime import datetime
from io import BytesIO

from PIL import Image
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGridLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QColor

from .api import RAClient
from . import cache as cache_mgr

log = logging.getLogger(__name__)


class AchievementDetailDialog(QDialog):
    def __init__(self, ach: dict, client: RAClient, parent=None):
        super().__init__(parent)
        self.ach = ach
        self.client = client
        self.setWindowTitle(ach.get("Title", ach.get("title", "Achievement")))
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f0f23;
            }
            QLabel {
                color: #cccccc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        badge_name = ach.get("BadgeName", ach.get("badgeName", ""))
        pixmap = self._load_badge_pixmap(badge_name)
        badge_label = QLabel()
        badge_label.setPixmap(pixmap)
        badge_label.setFixedSize(80, 80)
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(badge_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title = ach.get("Title", ach.get("title", "?"))
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 4px 0px;")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)

        description = ach.get("Description", ach.get("description", ""))
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Light))
        desc_label.setStyleSheet("color: #bbbbbb; font-style: italic; padding: 2px 0px;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)

        game = ach.get("GameTitle", ach.get("gameTitle", ""))
        console = ach.get("ConsoleName", ach.get("consoleName", ""))
        game_text = game
        if console:
            game_text += f"  |  {console}"
        game_label = QLabel(game_text)
        game_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        game_label.setStyleSheet("color: #88aaff; padding: 2px 0px;")
        info_layout.addWidget(game_label)

        points = ach.get("Points", ach.get("points", 0))
        true_ratio = ach.get("TrueRatio", ach.get("trueRatio", 0))
        is_hardcore = ach.get("HardcoreMode", 0) == 1 or ach.get("hardcoreMode", False)
        date_raw = ach.get("Date", ach.get("date", ""))
        date_str = ""
        if date_raw:
            try:
                dt = datetime.strptime(date_raw, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                date_str = date_raw

        meta_widget = QWidget()
        meta_widget.setStyleSheet("background-color: #2a2a4e; border-radius: 6px; padding: 0px;")
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(12, 6, 12, 6)
        meta_layout.setSpacing(12)

        pts_label = QLabel(f"⚡ {points} pts")
        pts_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        pts_label.setStyleSheet("color: #ffd700;")
        meta_layout.addWidget(pts_label)

        if true_ratio:
            tr_label = QLabel(f"🎯 {true_ratio}")
            tr_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            tr_label.setStyleSheet("color: #66ff66;")
            meta_layout.addWidget(tr_label)

        if is_hardcore:
            hc_label = QLabel("💀 HARDCORE")
            hc_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            hc_label.setStyleSheet("color: #ff4444;")
            meta_layout.addWidget(hc_label)

        if date_str:
            dt_label = QLabel(f"📅 {date_str}")
            dt_label.setFont(QFont("Segoe UI", 10))
            dt_label.setStyleSheet("color: #aaaaaa;")
            meta_layout.addWidget(dt_label)

        meta_layout.addStretch()
        info_layout.addWidget(meta_widget)

        top_layout.addLayout(info_layout, 1)
        layout.addLayout(top_layout)

        game_id = ach.get("GameID", ach.get("gameId"))
        if game_id:
            self._load_game_info(game_id)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a8a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5aaa;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _load_badge_pixmap(self, badge_name: str) -> QPixmap:
        if not badge_name:
            pixmap = QPixmap(80, 80)
            pixmap.fill(QColor("#333333"))
            return pixmap
        try:
            img = RAClient.load_badge(badge_name)
            if img:
                img = img.resize((80, 80), Image.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                buffer.seek(0)
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())
                return pixmap
        except Exception:
            pass
        pixmap = QPixmap(80, 80)
        pixmap.fill(QColor("#333333"))
        return pixmap

    def _load_game_info(self, game_id: int):
        try:
            data = cache_mgr.load_game_data(game_id)
            if data is None:
                data = self.client.get_game_extended(game_id)
                cache_mgr.save_game_data(game_id, data)
        except Exception:
            return

        info_widget = QWidget()
        info_widget.setStyleSheet("background-color: #1a1a2e; border-radius: 10px;")
        outer_layout = QHBoxLayout(info_widget)
        outer_layout.setContentsMargins(16, 16, 16, 16)
        outer_layout.setSpacing(20)

        def _load_image_pixmap(path: str, size: tuple[int, int]) -> QPixmap | None:
            img = RAClient.load_image(path)
            if not img:
                return None
            img = img.resize(size, Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            return pixmap

        cover_path = data.get("ImageBoxArt", data.get("imageBoxArt", ""))
        if cover_path:
            pixmap = _load_image_pixmap(cover_path, (180, 252))
            if pixmap:
                cover_label = QLabel()
                cover_label.setPixmap(pixmap)
                cover_label.setFixedSize(180, 252)
                cover_label.setStyleSheet("border: 2px solid #3a3a5e; border-radius: 6px;")
                cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                outer_layout.addWidget(cover_label)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        section_title = QLabel("📊 Game Statistics")
        section_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #ffd700; padding-bottom: 4px;")
        right_layout.addWidget(section_title)

        num_achs = data.get("NumAchievements", data.get("numAchievements", 0))
        players = data.get("NumDistinctPlayers", data.get("numDistinctPlayersCasual", 0))
        players_hc = data.get("NumDistinctPlayersHardcore", data.get("numDistinctPlayersHardcore", 0))

        publisher = data.get("Publisher", data.get("publisher", ""))
        developer = data.get("Developer", data.get("developer", ""))
        genre = data.get("Genre", data.get("genre", ""))
        released = data.get("Released", data.get("released", ""))

        stats_grid = QGridLayout()
        stats_grid.setSpacing(6)
        row = 0

        stat_items = [
            ("🏆 Achievements", str(num_achs), "#ffd700"),
            ("👥 Players", str(players), "#66ff66"),
            ("💀 Hardcore", str(players_hc), "#ff4444"),
        ]
        for label_text, value, color in stat_items:
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            lbl.setStyleSheet("color: #888888;")
            stats_grid.addWidget(lbl, row, 0)
            val = QLabel(value)
            val.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            val.setStyleSheet(f"color: {color};")
            stats_grid.addWidget(val, row, 1)
            row += 1

        right_layout.addLayout(stats_grid)

        info_lines = []
        if publisher:
            info_lines.append(("🏢 Publisher", publisher))
        if developer:
            info_lines.append(("👨‍💻 Developer", developer))
        if genre:
            info_lines.append(("🎮 Genre", genre))
        if released:
            info_lines.append(("📅 Release", released[:4] if len(released) > 4 else released))

        if info_lines:
            info_grid = QGridLayout()
            info_grid.setSpacing(4)
            for i, (lbl, val) in enumerate(info_lines):
                l = QLabel(lbl)
                l.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
                l.setStyleSheet("color: #888888;")
                info_grid.addWidget(l, i, 0)
                v = QLabel(val)
                v.setFont(QFont("Segoe UI", 9))
                v.setStyleSheet("color: #cccccc;")
                info_grid.addWidget(v, i, 1)
            right_layout.addLayout(info_grid)

        achs = data.get("Achievements", data.get("achievements", {}))
        ach_id = str(self.ach.get("AchievementID", self.ach.get("achievementId", "")))
        ach_data = achs.get(ach_id)
        if ach_data:
            right_layout.addWidget(QLabel(""))

            ach_title = QLabel("📈 Achievement Stats")
            ach_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            ach_title.setStyleSheet("color: #88aaff; padding-bottom: 2px;")
            right_layout.addWidget(ach_title)

            num_awarded = ach_data.get("NumAwarded", ach_data.get("numAwarded", 0))
            num_awarded_hc = ach_data.get("NumAwardedHardcore", ach_data.get("numAwardedHardcore", 0))
            author = ach_data.get("Author", ach_data.get("author", ""))

            ach_grid = QGridLayout()
            ach_grid.setSpacing(4)
            ach_items = [
                ("🎖️ Earned by", str(num_awarded), "#66ff66"),
                ("💀 Hardcore", str(num_awarded_hc), "#ff4444"),
            ]
            if author:
                ach_items.append(("✍️ Author", author, "#88aaff"))
            for i, (lbl, val, color) in enumerate(ach_items):
                l = QLabel(lbl)
                l.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
                l.setStyleSheet("color: #888888;")
                ach_grid.addWidget(l, i, 0)
                v = QLabel(val)
                v.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                v.setStyleSheet(f"color: {color};")
                ach_grid.addWidget(v, i, 1)
            right_layout.addLayout(ach_grid)

        right_layout.addStretch()
        outer_layout.addLayout(right_layout, 1)
        self.layout().insertWidget(1, info_widget)
