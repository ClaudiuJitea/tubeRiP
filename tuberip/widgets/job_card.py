from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tuberip.models import Job
from tuberip.theme import (
    IC_FILM,
    IC_FOLDER,
    TEXT_MUTED,
    restyle,
    rounded_pixmap,
    set_card,
    svg_icon,
)
from tuberip.widgets.common import Pill
from tuberip.workers import ThumbnailWorker

THUMB_SIZE = QSize(128, 72)
ACTIVE_STATES = {"queued", "downloading", "processing", "cancelling"}
STATUS_TONES: dict[str, tuple[str, str]] = {
    "queued": ("Queued", "neutral"),
    "downloading": ("Downloading", "info"),
    "processing": ("Processing", "warning"),
    "cancelling": ("Cancelling", "warning"),
    "done": ("Done", "success"),
    "cancelled": ("Cancelled", "neutral"),
    "error": ("Failed", "error"),
}


class JobCard(QFrame):
    cancel_requested = pyqtSignal(str)
    retry_requested = pyqtSignal(str)
    open_requested = pyqtSignal(str)
    reveal_requested = pyqtSignal(str)

    def __init__(self, job: Job, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_card(self, "JobCard")
        self.job_id = job.id
        self._status = job.status
        self._thumb_url = ""
        self._thumb_worker: ThumbnailWorker | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        self.thumb = QLabel()
        set_card(self.thumb, "Inset")
        self.thumb.setFixedSize(THUMB_SIZE)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder = svg_icon(IC_FILM, TEXT_MUTED, 24).pixmap(24, 24)
        self.thumb.setPixmap(self._placeholder)
        layout.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        self.title = QLabel(job.title)
        self.title.setObjectName("CardTitle")
        self.title.setWordWrap(True)
        self.pill = Pill("Queued", "neutral")
        top_row.addWidget(self.title, 1)
        top_row.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignTop)
        body.addLayout(top_row)

        self.meta = QLabel()
        self.meta.setObjectName("Meta")
        body.addWidget(self.meta)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.percent = QLabel("0%")
        self.percent.setObjectName("Mono")
        self.percent.setFixedWidth(42)
        self.percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.percent)
        self.progress_row = QWidget()
        self.progress_row.setLayout(progress_row)
        body.addWidget(self.progress_row)

        self.error = QLabel()
        self.error.setObjectName("ErrorText")
        self.error.setWordWrap(True)
        self.error.hide()
        body.addWidget(self.error)
        layout.addLayout(body, 1)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        self.primary = QPushButton("Cancel")
        self.primary.setFixedWidth(132)
        self.secondary = QPushButton("Open")
        self.secondary.setObjectName("Ghost")
        self.secondary.setFixedWidth(94)
        self.reveal = QPushButton()
        self.reveal.setObjectName("Ghost")
        self.reveal.setIcon(svg_icon(IC_FOLDER, TEXT_MUTED, 16))
        self.reveal.setToolTip("Show the containing folder")
        self.reveal.setFixedSize(32, 32)
        for button in (self.primary, self.secondary, self.reveal):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        second_row = QHBoxLayout()
        second_row.setSpacing(6)
        second_row.addWidget(self.secondary)
        second_row.addWidget(self.reveal)
        actions.addWidget(self.primary)
        actions.addLayout(second_row)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.primary.clicked.connect(self._primary)
        self.secondary.clicked.connect(self._secondary)
        self.reveal.clicked.connect(lambda: self.reveal_requested.emit(self.job_id))
        self.update_job(job)

    def _primary(self) -> None:
        if self._status in ACTIVE_STATES:
            self.cancel_requested.emit(self.job_id)
        elif self._status == "done":
            self.open_requested.emit(self.job_id)
        else:
            self.retry_requested.emit(self.job_id)

    def _secondary(self) -> None:
        if self._status == "done":
            self.retry_requested.emit(self.job_id)
        else:
            self.open_requested.emit(self.job_id)

    def update_job(self, job: Job) -> None:
        self._status = job.status
        self.title.setText(job.title)
        label, tone = STATUS_TONES.get(job.status, (job.status.title(), "neutral"))
        self.pill.set_state(label, tone)

        bits: list[str] = []
        if job.status == "downloading":
            if job.downloaded:
                bits.append(f"{job.downloaded} / {job.total}")
            if job.speed and job.speed != "—":
                bits.append(job.speed)
            if job.eta and job.eta != "—":
                bits.append(f"ETA {job.eta}")
        elif job.status == "done" and job.filepath:
            bits.append(Path(job.filepath).name)
        elif job.status == "queued":
            bits.append("Waiting for a free slot")
        elif job.status == "processing":
            bits.append("Merging and post-processing")
        self.meta.setText("  ·  ".join(bits))
        self.meta.setVisible(bool(bits))
        self.meta.setToolTip(job.filepath or "")

        if job.error:
            self.error.setText(job.error)
            self.error.setToolTip(job.error)
            self.error.show()
        else:
            self.error.hide()

        self.progress.setValue(int(job.percent))
        self.percent.setText(f"{int(job.percent)}%")
        self.progress_row.setVisible(job.status in ACTIVE_STATES)

        has_file = bool(job.filepath) and job.status == "done"
        if job.status in ACTIVE_STATES:
            self.primary.setText("Cancel")
            self.primary.setObjectName("Danger")
            self.secondary.setText("Open")
            self.secondary.setEnabled(False)
        elif job.status == "done":
            self.primary.setText("Open file")
            self.primary.setObjectName("")
            self.primary.setEnabled(has_file)
            self.secondary.setText("Again")
            self.secondary.setEnabled(True)
        else:
            self.primary.setText("Retry")
            self.primary.setObjectName("")
            self.primary.setEnabled(True)
            self.secondary.setText("Open")
            self.secondary.setEnabled(has_file)
        restyle(self.primary)
        self.reveal.setEnabled(bool(job.filepath))

        if job.thumbnail and job.thumbnail != self._thumb_url:
            self._thumb_url = job.thumbnail
            self._load_thumb(job.thumbnail)

    def _load_thumb(self, url: str) -> None:
        self._thumb_worker = ThumbnailWorker(url, self)
        self._thumb_worker.loaded.connect(self._set_thumb)
        self._thumb_worker.start()

    def _set_thumb(self, data: bytes) -> None:
        pix = QPixmap()
        if not pix.loadFromData(data) or pix.isNull():
            return
        self.thumb.setPixmap(rounded_pixmap(pix, 10, THUMB_SIZE))
