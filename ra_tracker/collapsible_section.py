import logging

from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QGridLayout, QPushButton,
)
from PyQt6.QtCore import Qt

log = logging.getLogger(__name__)


class CollapsibleSection(QFrame):
    def __init__(self, title: str, count: int, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            CollapsibleSection {
                background-color: #1a1a2e;
                border: 1px solid #3a3a5e;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._header_text = title
        self._count = count
        self._header = QPushButton()
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffd700;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a2a4e;
            }
        """)
        self._header.clicked.connect(self._toggle)
        main_layout.addWidget(self._header)

        self._content = QWidget()
        self._content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(12, 0, 12, 12)
        content_layout.setSpacing(6)
        self._content_grid = QGridLayout()
        content_layout.addLayout(self._content_grid)
        main_layout.addWidget(self._content)

        self._expanded = True
        self._update_header()

    def grid(self) -> QGridLayout:
        return self._content_grid

    def _update_header(self):
        arrow = "▼" if self._expanded else "▶"
        self._header.setText(f"{arrow}  {self._header_text}  ({self._count})")

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._update_header()

    def set_collapsed(self):
        self._expanded = False
        self._content.setVisible(False)
        self._update_header()
