from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPushButton, QScrollArea, QVBoxLayout, QWidget

from tuberip.queue_manager import QueueManager
from tuberip.theme import IC_INBOX, IC_TRASH, TEXT_MUTED, svg_icon
from tuberip.widgets.common import EmptyState, PageHeader, Pill
from tuberip.widgets.job_card import ACTIVE_STATES, JobCard


class QueuePage(QWidget):
    open_file = pyqtSignal(str)
    open_folder = pyqtSignal(str)

    def __init__(self, queue: QueueManager, parent=None) -> None:
        super().__init__(parent)
        self.queue = queue
        self.cards: dict[str, JobCard] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(16)

        self.header = PageHeader(
            "Queue",
            "Downloads run in the background. Cancel, retry, or open finished files from here.",
        )
        self.active_pill = Pill("0 active", "info")
        self.done_pill = Pill("0 done", "success")
        self.clear_btn = QPushButton("Clear finished")
        self.clear_btn.setObjectName("Ghost")
        self.clear_btn.setIcon(svg_icon(IC_TRASH, TEXT_MUTED, 15))
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear)
        self.header.add_action(self.active_pill)
        self.header.add_action(self.done_pill)
        self.header.add_action(self.clear_btn)
        root.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        self.list_layout = QVBoxLayout(inner)
        self.list_layout.setContentsMargins(0, 0, 8, 8)
        self.list_layout.setSpacing(10)
        self.empty = EmptyState(
            IC_INBOX,
            "Nothing in the queue",
            "Paste a link on the Download page, then send it here with Download or Add to queue.",
        )
        self.list_layout.addWidget(self.empty)
        self.list_layout.addStretch(1)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        queue.job_added.connect(self._add)
        queue.job_updated.connect(self._update)
        self._refresh_summary()

    def _add(self, job_id: str) -> None:
        job = self.queue.job(job_id)
        if not job:
            return
        self.empty.hide()
        card = JobCard(job)
        card.cancel_requested.connect(self.queue.cancel)
        card.retry_requested.connect(self.queue.retry)
        card.open_requested.connect(self._open)
        card.reveal_requested.connect(self._reveal)
        self.cards[job_id] = card
        self.list_layout.insertWidget(0, card)
        self._refresh_summary()

    def _update(self, job_id: str) -> None:
        if not job_id:
            self._rebuild()
            return
        job = self.queue.job(job_id)
        card = self.cards.get(job_id)
        if job and card:
            card.update_job(job)
        self._refresh_summary()

    def _rebuild(self) -> None:
        for card in list(self.cards.values()):
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        for job in reversed(self.queue.jobs):
            self._add(job.id)
        self.empty.setVisible(not self.queue.jobs)
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        jobs = self.queue.jobs
        active = sum(1 for job in jobs if job.status in ACTIVE_STATES)
        done = sum(1 for job in jobs if job.status == "done")
        failed = sum(1 for job in jobs if job.status == "error")
        self.active_pill.set_state(f"{active} active", "info" if active else "neutral")
        if failed:
            self.done_pill.set_state(f"{failed} failed", "error")
        else:
            self.done_pill.set_state(f"{done} done", "success" if done else "neutral")
        self.clear_btn.setEnabled(any(job.status not in ACTIVE_STATES for job in jobs))

    def _clear(self) -> None:
        self.queue.clear_finished()
        self._rebuild()

    def _open(self, job_id: str) -> None:
        job = self.queue.job(job_id)
        if job and job.filepath:
            self.open_file.emit(job.filepath)

    def _reveal(self, job_id: str) -> None:
        job = self.queue.job(job_id)
        if job and job.filepath:
            self.open_folder.emit(str(Path(job.filepath).parent))
