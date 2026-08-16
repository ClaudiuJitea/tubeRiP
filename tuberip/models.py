from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from tuberip.options_schema import SENSITIVE_KEYS, default_values
from tuberip.util import default_output_dir, ensure_dir


@dataclass
class Job:
    id: str
    urls: list[str]
    title: str = "Queued download"
    thumbnail: str = ""
    status: str = "queued"
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    downloaded: str = ""
    total: str = ""
    filepath: str = ""
    error: str = ""
    values: dict[str, Any] = field(default_factory=dict)
    playlist: bool = False
    added_at: str = ""
    finished_at: str = ""

    @classmethod
    def create(cls, urls: list[str], values: dict[str, Any], **kwargs: Any) -> "Job":
        return cls(
            id=uuid4().hex[:10],
            urls=urls,
            values=copy.deepcopy(values),
            added_at=datetime.now().isoformat(timespec="seconds"),
            **kwargs,
        )

    def to_history(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "urls": self.urls,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "status": self.status,
            "filepath": self.filepath,
            "error": self.error,
            "added_at": self.added_at,
            "finished_at": self.finished_at,
        }


class OptionsModel(QObject):
    changed = pyqtSignal(str, object)
    reloaded = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings("tubeRiP", "tubeRiP")
        self._values = default_values()
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if self._values.get(key) == value:
            return
        self._values[key] = value
        self.changed.emit(key, value)

    def set_many(self, updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            self.set(key, value)

    def values(self) -> dict[str, Any]:
        return copy.deepcopy(self._values)

    def reset(self) -> None:
        self._values = default_values()
        self.reloaded.emit()

    def persistable(self) -> dict[str, Any]:
        data = self.values()
        for key in SENSITIVE_KEYS:
            data.pop(key, None)
        return data

    def load(self) -> None:
        raw = self._settings.value("options_json", "")
        if not raw:
            output = self._values.get("output_dir") or default_output_dir()
            ensure_dir(output)
            return
        try:
            loaded = json.loads(str(raw))
        except json.JSONDecodeError:
            return
        if isinstance(loaded, dict):
            self._values.update(loaded)
        ensure_dir(self._values.get("output_dir") or default_output_dir())

    def save(self) -> None:
        self._settings.setValue("options_json", json.dumps(self.persistable()))
        self._settings.setValue("geometry", self._settings.value("geometry"))

    def settings(self) -> QSettings:
        return self._settings

    def load_history(self) -> list[dict[str, Any]]:
        raw = self._settings.value("history_json", "[]")
        try:
            data = json.loads(str(raw))
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def save_history(self, items: list[dict[str, Any]]) -> None:
        self._settings.setValue("history_json", json.dumps(items[:250]))
