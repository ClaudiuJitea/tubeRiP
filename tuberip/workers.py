from __future__ import annotations

import time
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from tuberip.util import is_playlist, playlist_entries
from tuberip.ydl import (
    MAX_403_ATTEMPTS,
    DownloadCancelled,
    SignalLogger,
    describe_403,
    ensure_js_runtimes_on_path,
    fetch_opts_from_values,
    is_http_403,
    summarize_ydl_failure,
    used_cookies,
    ydl_opts_from_values,
    youtube_retry_values,
)


class ExtractWorker(QThread):
    log = pyqtSignal(str, str)
    finished_ok = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, urls: list[str], values: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.urls = urls
        self.values = values

    def run(self) -> None:
        try:
            import yt_dlp
        except Exception as exc:  # pragma: no cover - import error surfaces in UI
            self.failed.emit(f"yt-dlp is not available: {exc}")
            return
        try:
            ensure_js_runtimes_on_path()
            opts = fetch_opts_from_values(self.values)
            opts["logger"] = SignalLogger(lambda level, message: self.log.emit(level, message))
            results: list[dict[str, Any]] = []
            with yt_dlp.YoutubeDL(opts) as ydl:
                for url in self.urls:
                    info = ydl.extract_info(url, download=False)
                    info = ydl.sanitize_info(info) if info else {"original_url": url}
                    info["original_url"] = url
                    if is_playlist(info):
                        info["entries"] = playlist_entries(info)
                    elif not info.get("formats"):
                        deep_opts = dict(opts)
                        deep_opts["extract_flat"] = False
                        with yt_dlp.YoutubeDL(deep_opts) as deep:
                            info = deep.sanitize_info(deep.extract_info(url, download=False)) or info
                            info["original_url"] = url
                    results.append(info)
            self.finished_ok.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)


class DownloadWorker(QThread):
    log = pyqtSignal(str, str)
    progress = pyqtSignal(dict)
    finished_ok = pyqtSignal(int, str)
    failed = pyqtSignal(str)

    def __init__(self, urls: list[str], values: dict[str, Any], playlist: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.urls = urls
        self.values = values
        self.playlist = playlist
        self._cancel = False
        self._last_filename = ""

    def cancel(self) -> None:
        self._cancel = True

    def _hook(self, status: dict[str, Any]) -> None:
        if self._cancel:
            raise DownloadCancelled("Cancelled")
        filename = status.get("filename") or status.get("info_dict", {}).get("_filename") or ""
        if filename:
            self._last_filename = filename
        self.progress.emit(dict(status))

    def run(self) -> None:
        try:
            import yt_dlp
        except Exception as exc:
            self.failed.emit(f"yt-dlp is not available: {exc}")
            return
        ensure_js_runtimes_on_path()
        values = self.values
        last_error = ""
        for attempt in range(MAX_403_ATTEMPTS):
            if self._cancel:
                self.failed.emit("Cancelled")
                return
            error = self._download_once(yt_dlp, values)
            if error is None:
                self.finished_ok.emit(0, self._last_filename)
                return
            last_error = error
            if self._cancel:
                self.failed.emit("Cancelled")
                return
            if not is_http_403(error) or attempt == MAX_403_ATTEMPTS - 1:
                break
            next_values = youtube_retry_values(values, attempt + 1)
            detail = " without cookies" if used_cookies(values) and not used_cookies(next_values) else ""
            self.log.emit(
                "warning",
                f"YouTube returned HTTP 403; retrying{detail} "
                f"({attempt + 2} of {MAX_403_ATTEMPTS}) with a fresh extraction…",
            )
            values = next_values
            if not self._sleep(2 + 2 * attempt):
                self.failed.emit("Cancelled")
                return
        if is_http_403(last_error):
            last_error = describe_403(self.values, MAX_403_ATTEMPTS)
        self.failed.emit(last_error or "Download failed")

    def _sleep(self, seconds: float) -> bool:
        """Back off between retries, returning False if the job was cancelled."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._cancel:
                return False
            self.msleep(100)
        return not self._cancel

    def _download_once(self, yt_dlp, values: dict[str, Any]) -> str | None:
        try:
            opts = ydl_opts_from_values(values, playlist=self.playlist)
            logger = SignalLogger(lambda level, message: self.log.emit(level, message))
            opts["logger"] = logger
            opts["progress_hooks"] = [self._hook]
            opts["postprocessor_hooks"] = [self._hook]
            with yt_dlp.YoutubeDL(opts) as ydl:
                code = ydl.download(self.urls)
            if self._cancel:
                return "Cancelled"
            if code:
                return summarize_ydl_failure(logger, int(code))
            return None
        except DownloadCancelled:
            return "Cancelled"
        except Exception as exc:
            if self._cancel:
                return "Cancelled"
            return str(exc) or exc.__class__.__name__


class ThumbnailWorker(QThread):
    loaded = pyqtSignal(bytes)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        if not self.url:
            self.failed.emit("No thumbnail")
            return
        try:
            from urllib.request import Request, urlopen

            request = Request(self.url, headers={"User-Agent": "Mozilla/5.0 tubeRiP"})
            with urlopen(request, timeout=20) as response:
                self.loaded.emit(response.read())
        except Exception as exc:
            self.failed.emit(str(exc))
