from __future__ import annotations

import shutil
from pathlib import Path

from PyQt6.QtCore import QThread, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDropEvent, QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from tuberip.models import OptionsModel
from tuberip.pages.download import DownloadPage
from tuberip.pages.history import HistoryPage
from tuberip.pages.log import LogPage
from tuberip.pages.options import OptionsPage
from tuberip.pages.queue import QueuePage
from tuberip.queue_manager import QueueManager
from tuberip.theme import app_icon
from tuberip.util import ensure_dir, looks_like_source, split_sources
from tuberip.widgets.common import Divider, SearchEdit
from tuberip.widgets.job_card import ACTIVE_STATES
from tuberip.widgets.sidebar import NAV_ITEMS, Sidebar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("tubeRiP")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1100, 720)
        self.resize(1280, 840)
        self.setAcceptDrops(True)

        self.model = OptionsModel(self)
        self.queue = QueueManager(self)
        self.queue.set_concurrency(int(self.model.get("queue_concurrency") or 1))

        root = QWidget()
        root.setObjectName("Root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.stack = QStackedWidget()
        self.download_page = DownloadPage(self.model)
        self.queue_page = QueuePage(self.queue)
        self.history_page = HistoryPage()
        self.options_page = OptionsPage(self.model)
        self.log_page = LogPage()
        for page in (
            self.download_page,
            self.queue_page,
            self.history_page,
            self.options_page,
            self.log_page,
        ):
            self.stack.addWidget(page)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.setStatusBar(self.status)
        self.version_label = QLabel()
        self.status.addPermanentWidget(Divider(vertical=True))
        self.status.addPermanentWidget(self.version_label)
        self._refresh_status_versions()

        self.sidebar.navigated.connect(self.stack.setCurrentIndex)
        self.download_page.enqueue_job.connect(self._enqueue)
        self.download_page.log.connect(self.log_page.append)
        self.download_page.status.connect(self.status.showMessage)
        self.queue.log.connect(self.log_page.append)
        self.queue.job_added.connect(self._refresh_queue_badge)
        self.queue.job_updated.connect(self._refresh_queue_badge)
        self.queue.job_finished.connect(self._on_job_finished)
        self.model.changed.connect(self._on_option_changed)
        self.queue_page.open_file.connect(self._open_path)
        self.queue_page.open_folder.connect(self._open_path)
        self.history_page.open_file.connect(self._open_path)
        self.history_page.redownload.connect(self._redownload)
        self.history_page.items_cleared.connect(lambda: self.model.save_history([]))
        self.history_page.set_items(self.model.load_history())

        self._build_menu()
        geometry = self.model.settings().value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        open_batch = QAction("Open URL list…", self)
        open_batch.setShortcut(QKeySequence("Ctrl+O"))
        open_batch.triggered.connect(self._open_batch)
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(open_batch)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        tools = self.menuBar().addMenu("&Tools")
        extractors = QAction("Supported sites…", self)
        extractors.triggered.connect(self._show_extractors)
        open_out = QAction("Open download folder", self)
        open_out.triggered.connect(lambda: self._open_path(str(self.model.get("output_dir"))))
        tools.addAction(extractors)
        tools.addAction(open_out)

        view = self.menuBar().addMenu("&View")
        for index, (_, label) in enumerate(NAV_ITEMS):
            action = QAction(label, self)
            action.setShortcut(QKeySequence(f"Ctrl+{index + 1}"))
            action.triggered.connect(lambda _=False, i=index: self._go_to(i))
            view.addAction(action)
            self.addAction(action)

        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("About tubeRiP", self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)

        fetch = QAction("Fetch info", self)
        fetch.setShortcut(QKeySequence("Ctrl+Return"))
        fetch.triggered.connect(self.download_page.fetch)
        self.addAction(fetch)

    def _go_to(self, index: int) -> None:
        self.sidebar.set_current(index)
        self.stack.setCurrentIndex(index)

    def _enqueue(self, job, switch: bool = True) -> None:
        ensure_dir(str(job.values.get("output_dir") or self.model.get("output_dir")))
        self.queue.add(job)
        if switch:
            self._go_to(1)
        self.status.showMessage(f"Queued {job.title}", 4000)

    def _refresh_queue_badge(self, *_: object) -> None:
        jobs = self.queue.jobs
        active = sum(1 for job in jobs if job.status in ACTIVE_STATES)
        self.sidebar.set_queue_badge(active)
        if active:
            running = next((job for job in jobs if job.status == "downloading"), None)
            if running:
                self.sidebar.set_footer(f"{int(running.percent)}%  ·  {running.speed or 'starting…'}")
            else:
                self.sidebar.set_footer(f"{active} in progress")
        else:
            self.sidebar.set_footer("Idle")

    def _on_job_finished(self, job) -> None:
        history = self.model.load_history()
        history.insert(0, job.to_history())
        self.model.save_history(history)
        self.history_page.set_items(history)
        if job.status == "done":
            self.status.showMessage(f"Finished {job.title}", 5000)
        elif job.status == "cancelled":
            self.status.showMessage(f"Cancelled {job.title}", 4000)
        else:
            self.status.showMessage(job.error or f"Failed {job.title}", 8000)

    def _on_option_changed(self, key: str, value) -> None:
        if key == "queue_concurrency":
            self.queue.set_concurrency(int(value or 1))
        self.model.save()

    def _open_path(self, path: str) -> None:
        if not path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _redownload(self, text: str) -> None:
        self._go_to(0)
        self.download_page.set_urls(text)

    def _open_batch(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open URL list", str(Path.home()), "Text (*.txt);;All files (*)")
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        self.download_page.set_urls(text)

    def _show_extractors(self) -> None:
        try:
            import yt_dlp.extractor as extractor
        except Exception as exc:
            QMessageBox.warning(self, "yt-dlp missing", str(exc))
            return
        names = sorted({getattr(ie, "IE_NAME", "") for ie in extractor.gen_extractor_classes() if getattr(ie, "IE_NAME", "")})
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Supported sites ({len(names)})")
        dialog.resize(480, 560)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        search = SearchEdit("Filter extractors…")
        listing = QListWidget()
        listing.addItems(names)
        search.textChanged.connect(
            lambda text: (
                listing.clear(),
                listing.addItems([name for name in names if text.lower() in name.lower()]),
            )
        )
        layout.addWidget(search)
        layout.addWidget(listing, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _about(self) -> None:
        yt_ver = "not installed"
        try:
            import yt_dlp

            yt_ver = getattr(yt_dlp.version, "__version__", "unknown")
        except Exception:
            pass
        ffmpeg = shutil.which("ffmpeg") or "not found"
        QMessageBox.about(
            self,
            "About tubeRiP",
            "tubeRiP is a modern PyQt6 frontend for yt-dlp.\n\n"
            f"yt-dlp {yt_ver}\n"
            f"ffmpeg: {ffmpeg}\n\n"
            "Use it only with media you have the right to download. "
            "Site terms and copyright still apply.",
        )

    def _refresh_status_versions(self) -> None:
        yt_ver = "yt-dlp missing"
        try:
            import yt_dlp

            yt_ver = f"yt-dlp {yt_dlp.version.__version__}"
        except Exception:
            pass
        ffmpeg = "ffmpeg ready" if shutil.which("ffmpeg") else "ffmpeg not found"
        self.version_label.setText(f"{yt_ver}   ·   {ffmpeg}")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        chunks: list[str] = []
        if mime.hasUrls():
            for url in mime.urls():
                local = url.toLocalFile()
                if local and Path(local).is_file():
                    chunks.append(Path(local).read_text(encoding="utf-8", errors="replace"))
                else:
                    chunks.append(url.toString())
        elif mime.hasText():
            chunks.append(mime.text())
        text = "\n".join(chunks).strip()
        if looks_like_source(text) or split_sources(text):
            self._go_to(0)
            self.download_page.set_urls(text)
            event.acceptProposedAction()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.model.settings().setValue("geometry", self.saveGeometry())
        self.model.save()
        self.queue.shutdown()
        self._stop_page_threads()
        super().closeEvent(event)

    def _stop_page_threads(self) -> None:
        """Extract and thumbnail threads are fire-and-forget; join them before teardown."""
        for thread in self.findChildren(QThread):
            if thread.isRunning():
                thread.requestInterruption()
                if not thread.wait(1500):
                    thread.terminate()
                    thread.wait(500)
