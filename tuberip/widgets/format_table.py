from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

from tuberip.ydl import format_row


COLUMNS = ["ID", "Ext", "Resolution", "FPS", "Video", "Audio", "Size", "Bitrate", "Note", "Protocol"]


class FormatTable(QTableWidget):
    format_chosen = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSortingEnabled(False)
        self.setToolTip("Double-click a row to use that exact format")
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(30)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COLUMNS.index("Note"), QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(False)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.doubleClicked.connect(self._emit_current)
        self._rows: list[dict[str, Any]] = []

    def load(self, formats: list[dict[str, Any]] | None) -> None:
        self._rows = [format_row(item) for item in formats or [] if item.get("format_id")]
        self.setRowCount(len(self._rows))
        keys = ["id", "ext", "resolution", "fps", "vcodec", "acodec", "size", "tbr", "note", "protocol"]
        centered = {1, 3, 6, 7}
        for row, data in enumerate(self._rows):
            for column, key in enumerate(keys):
                item = QTableWidgetItem(str(data.get(key) or "—"))
                if column in centered:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, data)
                    item.setToolTip("Double-click to select this format")
                self.setItem(row, column, item)

    def selected_format(self) -> dict[str, Any] | None:
        items = self.selectedItems()
        if not items:
            return None
        item = self.item(items[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _emit_current(self) -> None:
        data = self.selected_format()
        if data:
            self.format_chosen.emit(data)
