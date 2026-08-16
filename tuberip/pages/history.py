from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tuberip.theme import (
    ERROR,
    IC_DOWNLOAD,
    IC_FOLDER,
    IC_HISTORY,
    IC_PLAY,
    IC_TRASH,
    SUCCESS,
    TEXT_MUTED,
    svg_icon,
)
from tuberip.widgets.common import EmptyState, PageHeader, Pill

COLUMNS = ["Title", "Status", "Finished", "File", "URL"]
STATUS_COLORS = {"done": SUCCESS, "error": ERROR, "cancelled": TEXT_MUTED}


class HistoryPage(QWidget):
    open_file = pyqtSignal(str)
    redownload = pyqtSignal(str)
    items_cleared = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(16)

        header = PageHeader(
            "History",
            "Completed, cancelled, and failed jobs. Open a file or send the URL back to Download.",
        )
        self.count_pill = Pill("0 entries", "neutral")
        header.add_action(self.count_pill)
        root.addWidget(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.open_btn = QPushButton("Open file")
        self.open_btn.setIcon(svg_icon(IC_PLAY, TEXT_MUTED, 15))
        self.folder_btn = QPushButton("Open folder")
        self.folder_btn.setIcon(svg_icon(IC_FOLDER, TEXT_MUTED, 15))
        self.again_btn = QPushButton("Download again")
        self.again_btn.setIcon(svg_icon(IC_DOWNLOAD, TEXT_MUTED, 15))
        self.clear_btn = QPushButton("Clear history")
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.setIcon(svg_icon(IC_TRASH, TEXT_MUTED, 15))
        for button in (self.open_btn, self.folder_btn, self.again_btn, self.clear_btn):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar.addWidget(self.open_btn)
        toolbar.addWidget(self.folder_btn)
        toolbar.addWidget(self.again_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.clear_btn)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header_view.setHighlightSections(False)
        header_view.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.setColumnWidth(3, 240)
        self.table.setColumnWidth(4, 220)
        self.table.itemSelectionChanged.connect(self._refresh_actions)
        self.table.doubleClicked.connect(self._open_file)

        self.empty = EmptyState(
            IC_HISTORY,
            "No history yet",
            "Finished downloads land here so you can reopen files or grab the URL again.",
        )
        self.stack = QStackedWidget()
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.table)
        root.addWidget(self.stack, 1)

        self.open_btn.clicked.connect(self._open_file)
        self.folder_btn.clicked.connect(self._open_folder)
        self.again_btn.clicked.connect(self._again)
        self.clear_btn.clicked.connect(self._clear)
        self.set_items([])

    def set_items(self, items: list[dict]) -> None:
        self._items = list(items)
        self.table.setRowCount(len(self._items))
        for row, item in enumerate(self._items):
            urls = item.get("urls") or []
            status = str(item.get("status") or "")
            values = [
                item.get("title") or "Untitled",
                status.title(),
                _pretty_stamp(str(item.get("finished_at") or "")),
                item.get("filepath") or "",
                urls[0] if urls else "",
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setToolTip(str(value))
                if column == 1 and status in STATUS_COLORS:
                    cell.setForeground(QColor(STATUS_COLORS[status]))
                self.table.setItem(row, column, cell)
        count = len(self._items)
        self.count_pill.set_state(f"{count} entries" if count != 1 else "1 entry", "neutral")
        self.stack.setCurrentIndex(1 if count else 0)
        self.clear_btn.setEnabled(bool(count))
        self._refresh_actions()

    def _refresh_actions(self) -> None:
        item = self._current()
        has_file = bool((item or {}).get("filepath"))
        has_url = bool((item or {}).get("urls"))
        self.open_btn.setEnabled(has_file)
        self.folder_btn.setEnabled(has_file)
        self.again_btn.setEnabled(has_url)

    def _current(self) -> dict | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        index = rows[0].row()
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def _open_file(self) -> None:
        item = self._current()
        if item and item.get("filepath"):
            self.open_file.emit(item["filepath"])

    def _open_folder(self) -> None:
        item = self._current()
        path = item.get("filepath") if item else ""
        if path:
            self.open_file.emit(str(Path(path).parent))

    def _again(self) -> None:
        item = self._current()
        urls = (item or {}).get("urls") or []
        if urls:
            self.redownload.emit("\n".join(urls))

    def _clear(self) -> None:
        self.set_items([])
        self.items_cleared.emit()


def _pretty_stamp(value: str) -> str:
    if not value:
        return ""
    return value.replace("T", "  ")
