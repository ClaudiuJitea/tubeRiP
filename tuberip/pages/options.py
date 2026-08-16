from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from tuberip.models import OptionsModel
from tuberip.options_schema import default_values
from tuberip.theme import IC_FOLDER, IC_REFRESH, TEXT_MUTED, svg_icon
from tuberip.widgets.common import Card, FieldLabel, PageHeader, SearchEdit
from tuberip.widgets.option_form import OptionForm


class OptionsPage(QWidget):
    def __init__(self, model: OptionsModel, parent=None) -> None:
        super().__init__(parent)
        self.model = model

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(16)

        header = PageHeader(
            "Options",
            "Every yt-dlp switch, grouped the same way as the CLI. Search, then save a profile if you reuse a setup.",
        )
        reset = QPushButton("Reset")
        reset.setObjectName("Ghost")
        reset.setIcon(svg_icon(IC_REFRESH, TEXT_MUTED, 15))
        load = QPushButton("Load profile")
        load.setIcon(svg_icon(IC_FOLDER, TEXT_MUTED, 15))
        save = QPushButton("Save profile")
        for button in (reset, load, save):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(self._reset)
        save.clicked.connect(self._save_profile)
        load.clicked.connect(self._load_profile)
        header.add_action(reset)
        header.add_action(load)
        header.add_action(save)
        root.addWidget(header)

        app_card = Card("App behaviour", spacing=12)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(4, 1)

        self.workers = QSpinBox()
        self.workers.setRange(1, 4)
        self.workers.setFixedWidth(72)
        self.workers.setValue(int(model.get("queue_concurrency") or 1))
        self.workers.valueChanged.connect(lambda value: model.set("queue_concurrency", int(value)))
        self.auto = QPushButton("Auto-fetch URLs")
        self.auto.setObjectName("Toggle")
        self.auto.setCheckable(True)
        self.auto.setChecked(bool(model.get("auto_fetch")))
        self.auto.setToolTip("Fetch media info as soon as a link is pasted")
        self.auto.toggled.connect(lambda checked: model.set("auto_fetch", checked))
        self.cfg = QPushButton("Use yt-dlp config files")
        self.cfg.setObjectName("Toggle")
        self.cfg.setCheckable(True)
        self.cfg.setChecked(bool(model.get("load_config_files")))
        self.cfg.setToolTip("Let yt-dlp read its own config files in addition to these settings")
        self.cfg.toggled.connect(lambda checked: model.set("load_config_files", checked))
        for button in (self.auto, self.cfg):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        grid.addWidget(FieldLabel("Parallel downloads"), 0, 0)
        grid.addWidget(self.workers, 0, 1)
        grid.addWidget(self.auto, 0, 2)
        grid.addWidget(self.cfg, 0, 3)
        app_card.add_layout(grid)

        self.extra = QLineEdit()
        self.extra.setPlaceholderText('Anything the form misses, e.g.  --alias get-audio "-x -f ba"')
        self.extra.setText(str(model.get("extra_args") or ""))
        self.extra.textChanged.connect(lambda text: model.set("extra_args", text))
        extra_row = QHBoxLayout()
        extra_row.setSpacing(12)
        extra_row.addWidget(FieldLabel("Extra arguments", 126))
        extra_row.addWidget(self.extra, 1)
        app_card.add_layout(extra_row)
        root.addWidget(app_card)

        self.search = SearchEdit("Search options, flags, or help text…")
        self.search.textChanged.connect(self._filter)
        root.addWidget(self.search)

        self.form = OptionForm()
        self.form.set_values(model.values())
        self.form.changed.connect(model.set)
        model.changed.connect(self._sync_one)
        model.reloaded.connect(lambda: self.form.set_values(model.values()))
        root.addWidget(self.form, 1)

    def _filter(self, text: str) -> None:
        self.form.filter(text)

    def _sync_one(self, key: str, value) -> None:
        editor = self.form.editors.get(key)
        if editor:
            editor.set_value(value)
        if key == "extra_args" and self.extra.text() != str(value or ""):
            self.extra.setText(str(value or ""))
        if key == "queue_concurrency":
            self.workers.setValue(int(value or 1))
        if key == "auto_fetch":
            self.auto.setChecked(bool(value))
        if key == "load_config_files":
            self.cfg.setChecked(bool(value))

    def _reset(self) -> None:
        confirm = QMessageBox.question(self, "Reset options", "Restore every option to its default?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.model.reset()
        self.form.set_values(self.model.values())
        self.extra.setText("")
        self.workers.setValue(1)

    def _save_profile(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save profile", str(Path.home() / "tuberip-profile.json"), "JSON (*.json)"
        )
        if not path:
            return
        Path(path).write_text(json.dumps(self.model.persistable(), indent=2), encoding="utf-8")

    def _load_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load profile", str(Path.home()), "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.warning(self, "Load failed", str(exc))
            return
        if not isinstance(data, dict):
            QMessageBox.warning(self, "Load failed", "Profile must be a JSON object")
            return
        merged = default_values()
        merged.update(data)
        self.model.set_many(merged)
        self.form.set_values(self.model.values())
