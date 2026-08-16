from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from tuberip.models import Job
from tuberip.util import fmt_bytes, fmt_eta, fmt_speed
from tuberip.workers import DownloadWorker


class QueueManager(QObject):
    job_added = pyqtSignal(str)
    job_updated = pyqtSignal(str)
    job_finished = pyqtSignal(object)
    log = pyqtSignal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.jobs: list[Job] = []
        self._workers: dict[str, DownloadWorker] = {}
        self._concurrency = 1

    def set_concurrency(self, value: int) -> None:
        self._concurrency = max(1, min(int(value or 1), 4))
        self._pump()

    def job(self, job_id: str) -> Job | None:
        return next((item for item in self.jobs if item.id == job_id), None)

    def add(self, job: Job) -> None:
        self.jobs.insert(0, job)
        self.job_added.emit(job.id)
        self._pump()

    def cancel(self, job_id: str) -> None:
        job = self.job(job_id)
        if not job:
            return
        worker = self._workers.get(job_id)
        if worker:
            worker.cancel()
            job.status = "cancelling"
        elif job.status == "queued":
            job.status = "cancelled"
            job.finished_at = _now()
            self.job_finished.emit(job)
        self.job_updated.emit(job_id)

    def retry(self, job_id: str) -> None:
        job = self.job(job_id)
        if not job:
            return
        job.status = "queued"
        job.percent = 0
        job.error = ""
        job.speed = ""
        job.eta = ""
        self.job_updated.emit(job_id)
        self._pump()

    def clear_finished(self) -> None:
        self.jobs = [job for job in self.jobs if job.status in {"queued", "downloading", "processing", "cancelling"}]
        self.job_updated.emit("")

    def shutdown(self, wait_ms: int = 2500) -> None:
        """Ask running downloads to stop so the app can exit without killing threads."""
        for worker in list(self._workers.values()):
            worker.cancel()
        for worker in list(self._workers.values()):
            if not worker.wait(wait_ms):
                worker.terminate()
                worker.wait(500)

    def _active_count(self) -> int:
        return sum(1 for job in self.jobs if job.status in {"downloading", "processing", "cancelling"})

    def _pump(self) -> None:
        while self._active_count() < self._concurrency:
            nxt = next((job for job in reversed(self.jobs) if job.status == "queued"), None)
            if not nxt:
                return
            self._start(nxt)

    def _start(self, job: Job) -> None:
        job.status = "downloading"
        job.percent = 0
        self.job_updated.emit(job.id)
        worker = DownloadWorker(job.urls, job.values, playlist=job.playlist)
        self._workers[job.id] = worker
        worker.log.connect(self.log.emit)
        worker.progress.connect(lambda payload, job_id=job.id: self._on_progress(job_id, payload))
        worker.finished_ok.connect(lambda code, path, job_id=job.id: self._on_ok(job_id, code, path))
        worker.failed.connect(lambda message, job_id=job.id: self._on_fail(job_id, message))
        worker.finished.connect(lambda job_id=job.id: self._cleanup(job_id))
        worker.start()

    def _on_progress(self, job_id: str, payload: dict[str, Any]) -> None:
        job = self.job(job_id)
        if not job:
            return
        status = payload.get("status")
        if status == "downloading":
            job.status = "downloading"
            total = payload.get("total_bytes") or payload.get("total_bytes_estimate") or 0
            done = payload.get("downloaded_bytes") or 0
            if total:
                job.percent = max(0.0, min(100.0, done * 100.0 / total))
            elif payload.get("_percent_str"):
                text = str(payload["_percent_str"]).replace("%", "").strip()
                try:
                    job.percent = float(text)
                except ValueError:
                    pass
            job.speed = fmt_speed(payload.get("speed"))
            job.eta = fmt_eta(payload.get("eta"))
            job.downloaded = fmt_bytes(done)
            job.total = fmt_bytes(total) if total else "—"
            job.filepath = payload.get("filename") or job.filepath
        elif status in {"finished", "started"}:
            info = payload.get("info_dict") or {}
            if payload.get("postprocessor"):
                job.status = "processing"
                job.percent = 100
            elif status == "finished":
                job.percent = 100
                job.speed = ""
                job.eta = ""
            title = info.get("title")
            if title:
                job.title = title
            filename = payload.get("filename") or info.get("_filename")
            if filename:
                job.filepath = filename
        self.job_updated.emit(job_id)

    def _on_ok(self, job_id: str, code: int, path: str) -> None:
        job = self.job(job_id)
        if not job:
            return
        job.filepath = path or job.filepath
        job.percent = 100
        job.speed = ""
        job.eta = ""
        job.finished_at = _now()
        if code:
            job.status = "error"
            job.error = f"yt-dlp exited with code {code}"
        else:
            job.status = "done"
            job.error = ""
        self.job_updated.emit(job_id)
        self.job_finished.emit(job)

    def _on_fail(self, job_id: str, message: str) -> None:
        job = self.job(job_id)
        if not job:
            return
        job.finished_at = _now()
        job.speed = ""
        job.eta = ""
        if message == "Cancelled" or job.status == "cancelling":
            job.status = "cancelled"
            job.error = ""
        else:
            job.status = "error"
            job.error = message
        self.job_updated.emit(job_id)
        self.job_finished.emit(job)

    def _cleanup(self, job_id: str) -> None:
        worker = self._workers.pop(job_id, None)
        if worker:
            worker.deleteLater()
        self._pump()


def _now() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")
