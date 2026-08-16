from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from tuberip.options_schema import GROUPED_OPTIONS, OPTIONS, Opt
from tuberip.widgets.common import Card

LABEL_WIDTH = 186


class PathRow(QWidget):
    changed = pyqtSignal(str)

    def __init__(self, directory: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.directory = directory
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.edit = QLineEdit()
        self.button = QPushButton("Browse")
        self.button.setObjectName("Ghost")
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self._browse)
        self.edit.textChanged.connect(self.changed.emit)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)

    def _browse(self) -> None:
        if self.directory:
            path = QFileDialog.getExistingDirectory(self, "Select folder", self.edit.text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select file", self.edit.text())
        if path:
            self.edit.setText(path)

    def value(self) -> str:
        return self.edit.text().strip()

    def set_value(self, value: str) -> None:
        self.edit.setText(value or "")


class OptionEditor(QWidget):
    changed = pyqtSignal(object)

    def __init__(self, opt: Opt, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.opt = opt
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.widget: QWidget

        if opt.kind == "bool":
            box = QCheckBox(opt.label)
            box.setCursor(Qt.CursorShape.PointingHandCursor)
            box.stateChanged.connect(lambda _: self.changed.emit(self.value()))
            self.widget = box
        elif opt.kind == "choice":
            combo = QComboBox()
            combo.setEditable(False)
            for choice in opt.choices or ("",):
                label = choice or "Default"
                combo.addItem(label, choice)
            combo.currentIndexChanged.connect(lambda _: self.changed.emit(self.value()))
            self.widget = combo
        elif opt.kind in {"text", "headers"}:
            text = QPlainTextEdit()
            text.setPlaceholderText(opt.placeholder or "One value per line")
            text.setFixedHeight(74)
            text.textChanged.connect(lambda: self.changed.emit(self.value()))
            self.widget = text
        elif opt.kind == "password":
            edit = QLineEdit()
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setPlaceholderText(opt.placeholder)
            edit.textChanged.connect(self.changed.emit)
            self.widget = edit
        elif opt.kind in {"path", "file"}:
            row = PathRow(directory=opt.kind == "path")
            row.edit.setPlaceholderText(opt.placeholder)
            row.changed.connect(self.changed.emit)
            self.widget = row
        else:
            edit = QLineEdit()
            edit.setPlaceholderText(opt.placeholder or (str(opt.default) if opt.default not in (None, "") else ""))
            edit.textChanged.connect(self.changed.emit)
            self.widget = edit
        layout.addWidget(self.widget)

    def value(self) -> Any:
        widget = self.widget
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentData()
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        if isinstance(widget, PathRow):
            return widget.value()
        if isinstance(widget, QLineEdit):
            return widget.text()
        return None

    def set_value(self, value: Any) -> None:
        widget = self.widget
        widget.blockSignals(True)
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value if value is not None else "")
            widget.setCurrentIndex(max(0, index))
        elif isinstance(widget, QPlainTextEdit):
            widget.setPlainText(str(value or ""))
        elif isinstance(widget, PathRow):
            widget.set_value(str(value or ""))
        elif isinstance(widget, QLineEdit):
            widget.setText("" if value is None else str(value))
        widget.blockSignals(False)


class OptionForm(QWidget):
    changed = pyqtSignal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.editors: dict[str, OptionEditor] = {}
        self.rows: dict[str, QWidget] = {}
        self.sections: dict[str, QWidget] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        self.inner_layout = QVBoxLayout(inner)
        self.inner_layout.setContentsMargins(0, 2, 10, 18)
        self.inner_layout.setSpacing(14)

        for group, opts in GROUPED_OPTIONS.items():
            card = Card(group, spacing=10)
            for opt in opts:
                card.add(self._build_row(opt))
            self.sections[group] = card
            self.inner_layout.addWidget(card)

        self.no_results = QLabel("No options match that search.")
        self.no_results.setObjectName("Muted")
        self.no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results.hide()
        self.inner_layout.addWidget(self.no_results)
        self.inner_layout.addStretch(1)
        scroll.setWidget(inner)
        root.addWidget(scroll)

    def _build_row(self, opt: Opt) -> QWidget:
        editor = OptionEditor(opt)
        editor.changed.connect(lambda value, key=opt.key: self.changed.emit(key, value))
        editor.setToolTip(opt.help)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 6)
        row_layout.setSpacing(14)

        value_col = QVBoxLayout()
        value_col.setContentsMargins(0, 0, 0, 0)
        value_col.setSpacing(3)
        value_col.addWidget(editor)
        hint = QLabel(opt.help)
        hint.setObjectName("FieldHint")
        hint.setWordWrap(True)
        value_col.addWidget(hint)

        if opt.kind != "bool":
            label = QLabel(opt.label)
            label.setObjectName("FieldLabel")
            label.setToolTip(opt.help)
            label.setWordWrap(True)
            label.setFixedWidth(LABEL_WIDTH)
            row_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignTop)
        row_layout.addLayout(value_col, 1)

        self.editors[opt.key] = editor
        self.rows[opt.key] = row
        return row

    def set_values(self, values: dict[str, Any]) -> None:
        for key, editor in self.editors.items():
            if key in values:
                editor.set_value(values[key])

    def values(self) -> dict[str, Any]:
        return {key: editor.value() for key, editor in self.editors.items()}

    def filter(self, query: str) -> None:
        needle = (query or "").strip().lower()
        visible_groups: dict[str, bool] = {group: False for group in self.sections}
        for opt in OPTIONS:
            match = True if not needle else needle in opt.search_blob()
            self.rows[opt.key].setVisible(match)
            if match:
                visible_groups[opt.group] = True
        for group, section in self.sections.items():
            section.setVisible(visible_groups[group])
        self.no_results.setVisible(not any(visible_groups.values()))
