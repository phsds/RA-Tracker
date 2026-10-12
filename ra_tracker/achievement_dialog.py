"""Detail dialog for a single achievement, with game stats and a comparison bar."""

import logging
from datetime import datetime
from io import BytesIO

from PIL import Image
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGridLayout,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter, QBrush, QPen

from .api import RAClient
from . import cache as cache_mgr

log = logging.getLogger(__name__)


class ComparisonBar(QWidget):
    """Horizontal bar showing the softcore vs. hardcore earning split.

    The green slice represents softcore earns (``soft_value``) and the red
    slice represents hardcore earns (``hard_value``), with each percentage
    label drawn inside its own slice when there is room.
    """

    def __init__(self, soft_value: int, hard_value: int, parent=None):
        super().__init__(parent)
        self._soft = soft_value
        self._hard = hard_value
        self._total = soft_value + hard_value
        self._soft_pct = f"{soft_value * 100 // self._total}%" if self._total else "0%"
        self._hard_pct = f"{hard_value * 100 // self._total}%" if self._total else "0%"
        self.setFixedHeight(22)
        self.setMinimumWidth(120)

    def sizeHint(self):
        return QSize(200, 22)

    def paintEvent(self, event):
        """Draw the two colored slices and the border in one painter pass."""
        if self._total == 0:
            # Nothing earned yet: leave the bar blank.
            return
        p = QPainter(self)
        w = self.width()
        h = self.height()
        # Width of each slice is proportional to its share of the total.
        soft_w = int(w * self._soft / self._total)
        hard_w = w - soft_w  # remainder to avoid rounding gaps

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#66ff66")))
        p.drawRect(0, 0, soft_w, h)
        p.setBrush(QBrush(QColor("#ff4444")))
        p.drawRect(soft_w, 0, hard_w, h)

        font = QFont("Press Start 2P", 8)
        p.setFont(font)
        # Text color contrasts against the opposite slice: dark-on-green uses
        # the hardcore red pen, and vice versa.
        if soft_w > 40:
            p.setPen(QPen(QColor("#ff4444")))
            p.drawText(4, 0, soft_w - 4, h, Qt.AlignmentFlag.AlignVCenter, self._soft_pct)
        if hard_w > 40:
            p.setPen(QPen(QColor("#66ff66")))
            p.drawText(soft_w + 4, 0, hard_w - 4, h, Qt.AlignmentFlag.AlignVCenter, self._hard_pct)

        p.setPen(QPen(QColor("#3a3a5e"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(0, 0, w - 1, h - 1)
        p.end()


class AchievementDetailDialog(QDialog):
    """Modal dialog showing full details for one achievement.

    Includes the badge, title/description, points, true ratio, earned date,
    and (when available) the game cover plus softcore/hardcore stats for that
    achievement.
    """

    def __init__(self, ach: dict, client: RAClient, parent=None):
        super().__init__(parent)
        self.ach = ach
        self.client = client
        self.setWindowTitle(ach.get("Title", ach.get("title", "Achievement")))
        self.setMinimumSize(500, 400)
        # Dark theme matching the main window.
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

        # -- Top row: badge + summary -----------------------------
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
        title_label.setFont(QFont("Press Start 2P", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 4px 0px;")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)

        description = ach.get("Description", ach.get("description", ""))
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Press Start 2P", 11, QFont.Weight.Light))
        desc_label.setStyleSheet("color: #bbbbbb; font-style: italic; padding: 2px 0px;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)

        game = ach.get("GameTitle", ach.get("gameTitle", ""))
        console = ach.get("ConsoleName", ach.get("consoleName", ""))
        game_text = game
        if console:
            game_text += f"  |  {console}"
        game_label = QLabel(game_text)
        game_label.setFont(QFont("Press Start 2P", 10, QFont.Weight.DemiBold))
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
                # Fall back to the raw string when the format is unexpected.
                date_str = date_raw

        # -- Meta pills: points / true ratio / hardcore / date ------
        meta_widget = QWidget()
        meta_widget.setStyleSheet("background-color: #2a2a4e; border-radius: 6px; padding: 0px;")
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(12, 6, 12, 6)
        meta_layout.setSpacing(12)

        pts_label = QLabel(f"⚡ {points} pts")
        pts_label.setFont(QFont("Press Start 2P", 10, QFont.Weight.Bold))
        pts_label.setStyleSheet("color: #ffd700;")
        meta_layout.addWidget(pts_label)

        if true_ratio:
            tr_label = QLabel(f"🎯 {true_ratio}")
            tr_label.setFont(QFont("Press Start 2P", 10, QFont.Weight.Bold))
            tr_label.setStyleSheet("color: #66ff66;")
            meta_layout.addWidget(tr_label)

        if is_hardcore:
            hc_label = QLabel("💀 HARDCORE")
            hc_label.setFont(QFont("Press Start 2P", 10, QFont.Weight.Bold))
            hc_label.setStyleSheet("color: #ff4444;")
            meta_layout.addWidget(hc_label)

        if date_str:
            dt_label = QLabel(f"📅 {date_str}")
            dt_label.setFont(QFont("Press Start 2P", 10))
            dt_label.setStyleSheet("color: #aaaaaa;")
            meta_layout.addWidget(dt_label)

        meta_layout.addStretch()
        info_layout.addWidget(meta_widget)

        top_layout.addLayout(info_layout, 1)
        layout.addLayout(top_layout)

        # Fetch game info lazily; only when the achievement has a game id.
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
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5aaa;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _load_badge_pixmap(self, badge_name: str) -> QPixmap:
        """Load and resize the badge to 80x80, with a gray placeholder fallback."""
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
        """Fetch game metadata and insert a stats panel (cover + info).

        Uses the disk cache first; on a miss it queries the API and saves the
        result for next time. Any failure simply skips the panel.
        """
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
            """Download a site image at ``path`` and resize it to ``size``."""
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

        # -- Box-art cover ----------------------------------------------------
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
        section_title.setFont(QFont("Press Start 2P", 12, QFont.Weight.Bold))
        section_title.setStyleSheet("color: #ffd700; padding-bottom: 4px;")
        right_layout.addWidget(section_title)

        num_achs = data.get("NumAchievements", data.get("numAchievements", 0))

        publisher = data.get("Publisher", data.get("publisher", ""))
        developer = data.get("Developer", data.get("developer", ""))
        genre = data.get("Genre", data.get("genre", ""))
        released = data.get("Released", data.get("released", ""))

        achs_label = QLabel(f"🏆 Achievements:  {num_achs}")
        achs_label.setFont(QFont("Press Start 2P", 10, QFont.Weight.Bold))
        achs_label.setStyleSheet("color: #ffd700; padding: 4px 0px;")
        right_layout.addWidget(achs_label)

        # Build label/value rows only for fields the API actually filled in.
        info_lines = []
        if publisher:
            info_lines.append(("🏢 Publisher", publisher))
        if developer:
            info_lines.append(("👨‍💻 Developer", developer))
        if genre:
            info_lines.append(("🎮 Genre", genre))
        if released:
            # "<date>" would be nicer, but years like "2016" are already fine.
            info_lines.append(("📅 Release", released[:4] if len(released) > 4 else released))

        if info_lines:
            info_grid = QGridLayout()
            info_grid.setSpacing(4)
            for i, (lbl, val) in enumerate(info_lines):
                l = QLabel(lbl)
                l.setFont(QFont("Press Start 2P", 9, QFont.Weight.DemiBold))
                l.setStyleSheet("color: #888888;")
                info_grid.addWidget(l, i, 0)
                v = QLabel(val)
                v.setFont(QFont("Press Start 2P", 9))
                v.setStyleSheet("color: #cccccc;")
                info_grid.addWidget(v, i, 1)
            right_layout.addLayout(info_grid)

        # -- Per-achievement stats (softcore/hardcore earn split) ------------
        achs = data.get("Achievements", data.get("achievements", {}))
        ach_id = str(self.ach.get("AchievementID", self.ach.get("achievementId", "")))
        ach_data = achs.get(ach_id)
        if ach_data:
            right_layout.addWidget(QLabel(""))

            ach_title = QLabel("📈 Achievement Stats")
            ach_title.setFont(QFont("Press Start 2P", 11, QFont.Weight.Bold))
            ach_title.setStyleSheet("color: #88aaff; padding-bottom: 2px;")
            right_layout.addWidget(ach_title)

            num_awarded = ach_data.get("NumAwarded", ach_data.get("numAwarded", 0))
            num_awarded_hc = ach_data.get("NumAwardedHardcore", ach_data.get("numAwardedHardcore", 0))
            total_awarded = num_awarded + num_awarded_hc
            author = ach_data.get("Author", ach_data.get("author", ""))

            ach_grid = QGridLayout()
            ach_grid.setSpacing(4)
            ach_items = [
                ("🎖️ Softcore", str(num_awarded), "#66ff66"),
                ("💀 Hardcore", str(num_awarded_hc), "#ff4444"),
            ]
            if author:
                ach_items.append(("✍️ Author", author, "#88aaff"))
            for i, (lbl, val, color) in enumerate(ach_items):
                l = QLabel(lbl)
                l.setFont(QFont("Press Start 2P", 9, QFont.Weight.DemiBold))
                l.setStyleSheet("color: #888888;")
                ach_grid.addWidget(l, i, 0)
                v = QLabel(val)
                v.setFont(QFont("Press Start 2P", 9, QFont.Weight.Bold))
                v.setStyleSheet(f"color: {color};")
                ach_grid.addWidget(v, i, 1)
            right_layout.addLayout(ach_grid)

            # Only show the visual split bar when there is data to draw.
            if num_awarded or num_awarded_hc:
                ach_bar_row = QHBoxLayout()
                ach_bar_row.setSpacing(8)
                ach_bar_label = QLabel("Earned Split:")
                ach_bar_label.setFont(QFont("Press Start 2P", 8))
                ach_bar_label.setStyleSheet("color: #888888;")
                ach_bar_row.addWidget(ach_bar_label)
                ach_bar_row.addWidget(ComparisonBar(num_awarded, num_awarded_hc), 1)
                right_layout.addLayout(ach_bar_row)

        right_layout.addStretch()
        outer_layout.addLayout(right_layout, 1)
        # Insert the panel after the top summary (index 1), before the close
        # button currently at the end of the dialog's main layout.
        self.layout().insertWidget(1, info_widget)
