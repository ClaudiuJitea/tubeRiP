from __future__ import annotations

from datetime import datetime
from html import escape

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import QCheckBox, QFrame, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from tuberip.theme import (
    ERROR,
    IC_TRASH,
    INFO,
    TEXT_MUTED,
    TEXT_SOFT,
    WARNING,
    set_card,
    svg_icon,
)
from tuberip.widgets.common import PageHeader, Pill

LEVEL_COLORS = {"error": ERROR, "warning": WARNING, "info": INFO, "debug": TEXT_MUTED}


class LogPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._lines = 0
        self._errors = 0
        self._warnings = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(16)

        header = PageHeader("Log", "yt-dlp messages from fetch and download jobs.")
        self.count_pill = Pill("0 lines", "neutral")
        self.issue_pill = Pill("", "error")
        self.issue_pill.hide()
        self.autoscroll = QCheckBox("Follow output")
        self.autoscroll.setChecked(True)
        self.autoscroll.setCursor(Qt.CursorShape.PointingHandCursor)
        clear = QPushButton("Clear")
        clear.setObjectName("Ghost")
        clear.setIcon(svg_icon(IC_TRASH, TEXT_MUTED, 15))
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(self.clear)
        header.add_action(self.issue_pill)
        header.add_action(self.count_pill)
        header.add_action(self.autoscroll)
        header.add_action(clear)
        root.addWidget(header)

        shell = QFrame()
        set_card(shell, "Inset")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(10, 10, 10, 10)
        self.view = QPlainTextEdit()
        self.view.setObjectName("Flat")
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.view.setMaximumBlockCount(5000)
        self.view.setPlaceholderText("Nothing logged yet. Fetch or download something to see yt-dlp output.")
        font = QFont("JetBrains Mono")
        if not font.exactMatch():
            font = QFont("monospace")
        font.setPointSize(10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.view.setFont(font)
        shell_layout.addWidget(self.view)
        root.addWidget(shell, 1)

    def append(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        key = level.lower()
        color = LEVEL_COLORS.get(key, TEXT_SOFT)
        body_color = color if key in {"error", "warning"} else TEXT_SOFT
        tag = escape(level.upper()).ljust(7).replace(" ", "&nbsp;")
        body = escape(message.rstrip()).replace("  ", "&nbsp;&nbsp;")
        self.view.appendHtml(
            f'<span style="color:{TEXT_MUTED};">{stamp}</span>&nbsp;&nbsp;'
            f'<span style="color:{color};">{tag}</span>&nbsp;'
            f'<span style="color:{body_color};">{body}</span>'
        )
        self._lines += 1
        self.count_pill.setText(f"{self._lines} lines")
        if key == "error":
            self._errors += 1
        elif key == "warning":
            self._warnings += 1
        self._refresh_issues()
        if self.autoscroll.isChecked():
            self.view.moveCursor(QTextCursor.MoveOperation.End)

    def _refresh_issues(self) -> None:
        if self._errors:
            self.issue_pill.set_state(
                f"{self._errors} error" + ("s" if self._errors > 1 else ""), "error"
            )
            self.issue_pill.show()
        elif self._warnings:
            self.issue_pill.set_state(
                f"{self._warnings} warning" + ("s" if self._warnings > 1 else ""), "warning"
            )
            self.issue_pill.show()
        else:
            self.issue_pill.hide()

    def clear(self) -> None:
        self.view.clear()
        self._lines = 0
        self._errors = 0
        self._warnings = 0
        self.count_pill.set_state("0 lines", "neutral")
        self._refresh_issues()
