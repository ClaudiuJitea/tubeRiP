from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tuberip.models import Job, OptionsModel
from tuberip.options_schema import QUALITY_PRESETS
from tuberip.theme import (
    IC_DOWNLOAD,
    IC_FILM,
    IC_PASTE,
    IC_SEARCH,
    TEXT_MUTED,
    add_shadow,
    rounded_pixmap,
    set_card,
    svg_icon,
)
from tuberip.util import (
    best_thumbnail,
    display_title,
    fmt_count,
    fmt_duration,
    is_playlist,
    looks_like_source,
    playlist_entries,
    split_sources,
)
from tuberip.widgets.common import Card, FieldLabel, FlowLayout, PageHeader, Pill, SectionLabel
from tuberip.widgets.format_table import FormatTable
from tuberip.widgets.option_form import PathRow
from tuberip.workers import ExtractWorker, ThumbnailWorker
from tuberip.ydl import apply_quality_preset, is_video_only

PREVIEW_SIZE = QSize(248, 140)
LABEL_WIDTH = 74


class Chip(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("Chip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class DownloadPage(QWidget):
    enqueue_job = pyqtSignal(object, bool)
    log = pyqtSignal(str, str)
    status = pyqtSignal(str)

    def __init__(self, model: OptionsModel, parent=None) -> None:
        super().__init__(parent)
        self.model = model
        self._infos: list[dict[str, Any]] = []
        self._extract: ExtractWorker | None = None
        self._thumb: ThumbnailWorker | None = None
        self._fetch_timer = QTimer(self)
        self._fetch_timer.setSingleShot(True)
        self._fetch_timer.setInterval(700)
        self._fetch_timer.timeout.connect(self.fetch)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(16)
        root.addWidget(self._build_header())
        root.addWidget(self._build_source_card())

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 2, 8, 8)
        body_layout.setSpacing(14)
        body_layout.addWidget(self._build_media_card())
        body_layout.addWidget(self._build_quality_card())
        body_layout.addWidget(self._build_tabs(), 1)
        self.scroll.setWidget(body)
        root.addWidget(self.scroll, 1)

        self.model.changed.connect(self._on_model_changed)
        self.model.reloaded.connect(self._sync_from_model)
        self._sync_from_model()
        self._set_busy(False)
        self._update_source_pill()

    # ---------- construction ----------

    def _build_header(self) -> QWidget:
        header = PageHeader(
            "Download",
            "Paste a video, playlist, or several URLs. Fetch details, pick a quality, then download.",
        )
        self.source_pill = Pill("No links", "neutral")
        header.add_action(self.source_pill)
        return header

    def _build_source_card(self) -> QWidget:
        card = Card("Source", name="HeroCard", margins=(18, 14, 18, 16), spacing=10)
        add_shadow(card, blur=26, y_offset=5, alpha=90)

        self.url_input = QPlainTextEdit()
        self.url_input.setObjectName("UrlInput")
        self.url_input.setPlaceholderText(
            "https://www.youtube.com/watch?v=…\n"
            "https://www.youtube.com/playlist?list=…\n"
            "ytsearch10:lofi mix"
        )
        self.url_input.setFixedHeight(72)
        self.url_input.textChanged.connect(self._on_url_changed)
        card.add(self.url_input)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setObjectName("Ghost")
        self.paste_btn.setIcon(svg_icon(IC_PASTE, TEXT_MUTED, 16))
        self.fetch_btn = QPushButton("Fetch info")
        self.fetch_btn.setIcon(svg_icon(IC_SEARCH, TEXT_MUTED, 16))
        self.queue_btn = QPushButton("Add to queue")
        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("Primary")
        self.download_btn.setIcon(svg_icon(IC_DOWNLOAD, "#ffffff", 16))
        shortcut_hint = QLabel("Ctrl+Return to fetch")
        shortcut_hint.setObjectName("FieldHint")
        for button in (self.paste_btn, self.fetch_btn, self.queue_btn, self.download_btn):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.paste_btn.clicked.connect(self._paste)
        self.fetch_btn.clicked.connect(self.fetch)
        self.download_btn.clicked.connect(lambda: self._submit(switch=True))
        self.queue_btn.clicked.connect(lambda: self._submit(switch=False))
        buttons.addWidget(self.paste_btn)
        buttons.addWidget(self.fetch_btn)
        buttons.addSpacing(6)
        buttons.addWidget(shortcut_hint)
        buttons.addStretch(1)
        buttons.addWidget(self.queue_btn)
        buttons.addWidget(self.download_btn)
        card.add_layout(buttons)
        return card

    def _build_media_card(self) -> QWidget:
        self.media_card = QFrame()
        set_card(self.media_card, "MediaCard")
        media = QHBoxLayout(self.media_card)
        media.setContentsMargins(14, 14, 16, 14)
        media.setSpacing(14)

        self.thumb = QLabel()
        set_card(self.thumb, "Inset")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setFixedSize(PREVIEW_SIZE)
        self._thumb_placeholder = svg_icon(IC_FILM, TEXT_MUTED, 34).pixmap(34, 34)
        self.thumb.setPixmap(self._thumb_placeholder)

        info_col = QVBoxLayout()
        info_col.setSpacing(9)
        self.media_title = QLabel("Nothing fetched yet")
        self.media_title.setObjectName("CardTitle")
        self.media_title.setWordWrap(True)

        self.badge_host = QWidget()
        self.badge_layout = FlowLayout(self.badge_host, spacing=6, line_spacing=6)

        self.media_meta = QLabel(
            "Paste a URL and press Fetch info to inspect formats, subtitles, and chapters."
        )
        self.media_meta.setObjectName("Muted")
        self.media_meta.setWordWrap(True)
        self.media_desc = QLabel("")
        self.media_desc.setObjectName("Meta")
        self.media_desc.setWordWrap(True)
        self.media_desc.hide()
        info_col.addWidget(self.media_title)
        info_col.addWidget(self.badge_host)
        info_col.addWidget(self.media_meta)
        info_col.addWidget(self.media_desc)
        info_col.addStretch(1)

        media.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignTop)
        media.addLayout(info_col, 1)
        return self.media_card

    def _build_quality_card(self) -> QWidget:
        card = Card("Quality", spacing=14)

        chip_host = QWidget()
        chip_flow = FlowLayout(chip_host, spacing=8, line_spacing=8)
        self.quality_group = QButtonGroup(self)
        self.quality_group.setExclusive(True)
        self.quality_chips: dict[str, Chip] = {}
        for preset in QUALITY_PRESETS:
            chip = Chip(preset["label"])
            chip.setToolTip(str(preset.get("format") or preset.get("hint") or preset["label"]))
            chip.clicked.connect(lambda _=False, pid=preset["id"]: self._apply_preset(pid))
            self.quality_group.addButton(chip)
            self.quality_chips[preset["id"]] = chip
            chip_flow.addWidget(chip)
        card.add(chip_host)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        self.format_edit = QLineEdit()
        self.format_edit.setPlaceholderText("bv*+ba/b   ·   or double-click a row in Formats")
        self.format_edit.textChanged.connect(self._format_typed)
        self.cookie_combo = QComboBox()
        self.cookie_combo.setMinimumWidth(140)
        self.cookie_combo.setToolTip("Read cookies from a local browser profile for private or age-gated media")
        for label, value in (
            ("No cookies", ""),
            ("Chrome", "chrome"),
            ("Chromium", "chromium"),
            ("Firefox", "firefox"),
            ("Brave", "brave"),
            ("Edge", "edge"),
            ("Opera", "opera"),
            ("Vivaldi", "vivaldi"),
        ):
            self.cookie_combo.addItem(label, value)
        self.cookie_combo.currentIndexChanged.connect(
            lambda _: self.model.set("cookies_from_browser", self.cookie_combo.currentData() or "")
        )
        self.out_path = PathRow(directory=True)
        self.out_path.edit.setPlaceholderText("Where finished files land")
        self.out_path.changed.connect(lambda path: self.model.set("output_dir", path))

        grid.addWidget(FieldLabel("Format", LABEL_WIDTH), 0, 0)
        grid.addWidget(self.format_edit, 0, 1)
        grid.addWidget(FieldLabel("Cookies"), 0, 2)
        grid.addWidget(self.cookie_combo, 0, 3)
        grid.addWidget(FieldLabel("Save to", LABEL_WIDTH), 1, 0)
        grid.addWidget(self.out_path, 1, 1, 1, 3)
        card.add_layout(grid)

        extras_title = SectionLabel("Extras")
        card.add(extras_title)
        extras_host = QWidget()
        extras_flow = FlowLayout(extras_host, spacing=18, line_spacing=4)
        self.sub_chk = QCheckBox("Subtitles")
        self.auto_sub_chk = QCheckBox("Auto-captions")
        self.thumb_chk = QCheckBox("Cover art")
        self.meta_chk = QCheckBox("Metadata")
        self.sponsor_chk = QCheckBox("Skip sponsors")
        self.merge_chk = QCheckBox("Merge best audio")
        self.organize_chk = QCheckBox("Folder per playlist")
        hints = {
            self.sub_chk: "Download subtitle files alongside the media",
            self.auto_sub_chk: "Include machine-generated captions",
            self.thumb_chk: "Embed the thumbnail as cover art",
            self.meta_chk: "Embed title, artist, and description tags",
            self.sponsor_chk: "Remove sponsor, intro, and self-promo segments",
            self.merge_chk: "Pair a video-only format with the best audio",
            self.organize_chk: "Create one subfolder per playlist",
        }
        for box in (
            self.sub_chk,
            self.auto_sub_chk,
            self.thumb_chk,
            self.meta_chk,
            self.sponsor_chk,
            self.merge_chk,
            self.organize_chk,
        ):
            box.setCursor(Qt.CursorShape.PointingHandCursor)
            box.setToolTip(hints[box])
            extras_flow.addWidget(box)
        for box, key in (
            (self.sub_chk, "write_subs"),
            (self.auto_sub_chk, "write_auto_subs"),
            (self.thumb_chk, "embed_thumbnail"),
            (self.meta_chk, "embed_metadata"),
            (self.merge_chk, "merge_best_audio"),
            (self.organize_chk, "organize_playlists"),
        ):
            box.toggled.connect(lambda checked, k=key: self.model.set(k, checked))
        self.sponsor_chk.toggled.connect(self._toggle_sponsor)
        card.add(extras_host)
        return card

    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.format_table = FormatTable()
        self.format_table.setObjectName("Flat")
        self.format_table.format_chosen.connect(self._choose_format)
        self.sub_list = QListWidget()
        self.sub_list.setObjectName("Flat")
        self.sub_list.itemChanged.connect(self._sync_sub_langs)
        self.chapter_list = QListWidget()
        self.chapter_list.setObjectName("Flat")
        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("Flat")
        self.playlist_list.itemChanged.connect(lambda _: self._refresh_playlist_count())

        pl_btns = QHBoxLayout()
        pl_btns.setSpacing(8)
        sel_all = QPushButton("Select all")
        sel_none = QPushButton("Select none")
        for button in (sel_all, sel_none):
            button.setObjectName("Ghost")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_all.clicked.connect(lambda: self._set_playlist_checks(True))
        sel_none.clicked.connect(lambda: self._set_playlist_checks(False))
        self.playlist_count = QLabel("")
        self.playlist_count.setObjectName("FieldHint")
        pl_btns.addWidget(sel_all)
        pl_btns.addWidget(sel_none)
        pl_btns.addWidget(self.playlist_count)
        pl_btns.addStretch(1)

        self.tabs.addTab(self._tab_page(self.format_table), "Formats")
        self.tabs.addTab(self._tab_page(self.sub_list), "Subtitles")
        self.tabs.addTab(self._tab_page(self.chapter_list), "Chapters")
        self.tabs.addTab(self._tab_page(self.playlist_list, pl_btns), "Playlist")
        self.tabs.setMinimumHeight(260)
        return self.tabs

    @staticmethod
    def _tab_page(widget: QWidget, toolbar: QHBoxLayout | None = None) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        if toolbar is not None:
            layout.addLayout(toolbar)
        layout.addWidget(widget, 1)
        return page

    # ---------- model sync ----------

    def _on_model_changed(self, key: str, value: Any) -> None:
        mapping = {
            "write_subs": self.sub_chk,
            "write_auto_subs": self.auto_sub_chk,
            "embed_thumbnail": self.thumb_chk,
            "embed_metadata": self.meta_chk,
            "merge_best_audio": self.merge_chk,
            "organize_playlists": self.organize_chk,
        }
        if key in mapping:
            box = mapping[key]
            box.blockSignals(True)
            box.setChecked(bool(value))
            box.blockSignals(False)
        if key == "output_dir":
            self.out_path.set_value(str(value or ""))
        if key == "format":
            if self.format_edit.text() != str(value or ""):
                self.format_edit.blockSignals(True)
                self.format_edit.setText(str(value or ""))
                self.format_edit.blockSignals(False)
        if key == "cookies_from_browser":
            token = str(value or "").split(":")[0]
            index = self.cookie_combo.findData(token)
            if index < 0:
                index = 0
            self.cookie_combo.blockSignals(True)
            self.cookie_combo.setCurrentIndex(index)
            self.cookie_combo.blockSignals(False)
        if key == "quality_preset":
            chip = self.quality_chips.get(str(value))
            if chip:
                chip.setChecked(True)
        if key == "sponsorblock_remove":
            self.sponsor_chk.blockSignals(True)
            self.sponsor_chk.setChecked(bool(value))
            self.sponsor_chk.blockSignals(False)

    def _sync_from_model(self) -> None:
        values = self.model.values()
        for key in (
            "write_subs",
            "write_auto_subs",
            "embed_thumbnail",
            "embed_metadata",
            "merge_best_audio",
            "organize_playlists",
            "output_dir",
            "format",
            "cookies_from_browser",
            "quality_preset",
            "sponsorblock_remove",
        ):
            self._on_model_changed(key, values.get(key))

    def _format_typed(self, text: str) -> None:
        self.model.set("format", text)
        match = next((preset["id"] for preset in QUALITY_PRESETS if preset.get("format") == text), "custom")
        self.model.set("quality_preset", match)

    def _toggle_sponsor(self, checked: bool) -> None:
        self.model.set("sponsorblock_remove", "sponsor,selfpromo,interaction,intro,outro" if checked else "")

    def _apply_preset(self, preset_id: str) -> None:
        self.model.set_many(apply_quality_preset(self.model.values(), preset_id))
        chip = self.quality_chips.get(preset_id)
        if chip:
            chip.setChecked(True)

    # ---------- sources ----------

    def _paste(self) -> None:
        text = self.clipboard_text()
        if text:
            self.url_input.setPlainText(text.strip())
            if self.model.get("auto_fetch"):
                self.fetch()

    def clipboard_text(self) -> str:
        from PyQt6.QtWidgets import QApplication

        return QApplication.clipboard().text()

    def _on_url_changed(self) -> None:
        self._update_source_pill()
        if not self.model.get("auto_fetch"):
            return
        if looks_like_source(self.url_input.toPlainText()):
            self._fetch_timer.start()

    def _update_source_pill(self) -> None:
        count = len(self.current_urls())
        if not count:
            self.source_pill.set_state("No links", "neutral")
        elif count == 1:
            self.source_pill.set_state("1 link", "accent")
        else:
            self.source_pill.set_state(f"{count} links", "accent")

    def current_urls(self) -> list[str]:
        return split_sources(self.url_input.toPlainText())

    def fetch(self) -> None:
        urls = self.current_urls()
        if not urls:
            self.status.emit("Paste a URL first")
            return
        if self._extract and self._extract.isRunning():
            return
        self._set_busy(True)
        self.status.emit("Fetching media info…")
        self._extract = ExtractWorker(urls, self.model.values(), self)
        self._extract.log.connect(self.log.emit)
        self._extract.finished_ok.connect(self._on_fetched)
        self._extract.failed.connect(self._on_fetch_failed)
        self._extract.finished.connect(lambda: self._set_busy(False))
        self._extract.start()

    def _on_fetch_failed(self, message: str) -> None:
        self.status.emit(message)
        self.media_title.setText("Could not fetch that URL")
        self._set_badges([])
        self.media_meta.setText(message)
        self.media_desc.hide()

    def _on_fetched(self, infos: list[dict[str, Any]]) -> None:
        self._infos = infos
        info = infos[0]
        title = display_title(info)
        self.media_title.setText(title)

        badges: list[tuple[str, str]] = []
        if len(infos) > 1:
            badges.append((f"{len(infos)} sources", "accent"))
        if is_playlist(info):
            badges.append((f"Playlist · {len(playlist_entries(info))} items", "accent"))
        else:
            badges.append(("Single video", "info"))
        if info.get("duration"):
            badges.append((fmt_duration(info.get("duration")), "neutral"))
        if info.get("view_count") is not None:
            badges.append((f"{fmt_count(info.get('view_count'))} views", "neutral"))
        if info.get("extractor_key"):
            badges.append((str(info.get("extractor_key")), "neutral"))
        self._set_badges(badges)

        uploader = info.get("uploader") or info.get("channel") or ""
        self.media_meta.setText(str(uploader) or "Ready to download")
        description = (info.get("description") or "").strip().replace("\n", " ")
        if description:
            self.media_desc.setText(description[:280] + ("…" if len(description) > 280 else ""))
            self.media_desc.show()
        else:
            self.media_desc.hide()

        self._load_thumb(best_thumbnail(info))
        formats = info.get("formats") or []
        self.format_table.load(formats)
        self._set_tab_count(0, "Formats", self.format_table.rowCount())
        self._load_subs(info)
        self._load_chapters(info)
        self._load_playlist(info)
        if is_playlist(info):
            self.tabs.setCurrentIndex(3)
        elif formats:
            self.tabs.setCurrentIndex(0)
        self.status.emit("Ready")
        QTimer.singleShot(0, self._reveal_tabs)

    def _reveal_tabs(self) -> None:
        """Nudge the page down just enough to show the tab bar and a few rows."""
        self.scroll.ensureWidgetVisible(self.tabs.tabBar(), 0, 130)

    def _set_badges(self, badges: list[tuple[str, str]]) -> None:
        while self.badge_layout.count():
            item = self.badge_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        for text, tone in badges:
            self.badge_layout.addWidget(Pill(text, tone, self.badge_host))
        self.badge_host.setVisible(bool(badges))
        self.badge_host.updateGeometry()

    def _load_thumb(self, url: str) -> None:
        self.thumb.setPixmap(self._thumb_placeholder)
        if not url:
            return
        self._thumb = ThumbnailWorker(url, self)
        self._thumb.loaded.connect(self._set_thumb)
        self._thumb.start()

    def _set_thumb(self, data: bytes) -> None:
        pix = QPixmap()
        if not pix.loadFromData(data) or pix.isNull():
            return
        self.thumb.setPixmap(rounded_pixmap(pix, 12, PREVIEW_SIZE))

    # ---------- detail tabs ----------

    @staticmethod
    def _placeholder_item(target: QListWidget, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setForeground(QColor(TEXT_MUTED))
        target.addItem(item)

    def _set_tab_count(self, index: int, base: str, count: int) -> None:
        self.tabs.setTabText(index, f"{base}  {count}" if count else base)

    def _load_subs(self, info: dict[str, Any]) -> None:
        self.sub_list.blockSignals(True)
        self.sub_list.clear()
        langs: dict[str, str] = {}
        for collection, suffix in ((info.get("subtitles") or {}, ""), (info.get("automatic_captions") or {}, " (auto)")):
            for lang, tracks in collection.items():
                name = lang
                if tracks and isinstance(tracks, list) and tracks[0].get("name"):
                    name = str(tracks[0]["name"])
                langs[lang] = f"{lang}  ·  {name}{suffix}"
        selected = {part.strip() for part in str(self.model.get("sub_langs") or "").split(",") if part.strip()}
        for lang, label in sorted(langs.items()):
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, lang)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if lang in selected else Qt.CheckState.Unchecked)
            self.sub_list.addItem(item)
        self.sub_list.blockSignals(False)
        if not langs:
            self._placeholder_item(self.sub_list, "No subtitles reported for this media")
        self._set_tab_count(1, "Subtitles", len(langs))

    def _sync_sub_langs(self) -> None:
        langs = []
        for index in range(self.sub_list.count()):
            item = self.sub_list.item(index)
            if item.checkState() == Qt.CheckState.Checked and item.data(Qt.ItemDataRole.UserRole):
                langs.append(str(item.data(Qt.ItemDataRole.UserRole)))
        if langs:
            self.model.set("sub_langs", ",".join(langs))
            self.model.set("write_subs", True)

    def _load_chapters(self, info: dict[str, Any]) -> None:
        self.chapter_list.clear()
        chapters = info.get("chapters") or []
        if not chapters:
            self._placeholder_item(self.chapter_list, "No chapters in this media")
            self._set_tab_count(2, "Chapters", 0)
            return
        for chapter in chapters:
            start = fmt_duration(chapter.get("start_time"))
            title = chapter.get("title") or "Chapter"
            self.chapter_list.addItem(f"{start}   {title}")
        self._set_tab_count(2, "Chapters", len(chapters))

    def _load_playlist(self, info: dict[str, Any]) -> None:
        self.playlist_list.clear()
        entries = playlist_entries(info) if is_playlist(info) else []
        if not entries:
            self._placeholder_item(self.playlist_list, "This URL is a single video")
            self.playlist_count.setText("")
            self._set_tab_count(3, "Playlist", 0)
            return
        for index, entry in enumerate(entries, start=1):
            if not entry:
                continue
            title = display_title(entry, fallback=f"Item {index}")
            duration = fmt_duration(entry.get("duration"))
            item = QListWidgetItem(f"{index:03d}   {title}   ·   {duration}")
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.playlist_list.addItem(item)
        self._set_tab_count(3, "Playlist", self.playlist_list.count())
        self._refresh_playlist_count()

    def _selected_playlist_items(self) -> str:
        indexes = []
        for index in range(self.playlist_list.count()):
            item = self.playlist_list.item(index)
            if item.checkState() == Qt.CheckState.Checked and item.data(Qt.ItemDataRole.UserRole):
                indexes.append(str(item.data(Qt.ItemDataRole.UserRole)))
        return ",".join(indexes)

    def _set_playlist_checks(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for index in range(self.playlist_list.count()):
            item = self.playlist_list.item(index)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(state)
        self._refresh_playlist_count()

    def _refresh_playlist_count(self) -> None:
        total = sum(
            1
            for index in range(self.playlist_list.count())
            if self.playlist_list.item(index).flags() & Qt.ItemFlag.ItemIsUserCheckable
        )
        if not total:
            self.playlist_count.setText("")
            return
        picked = len([part for part in self._selected_playlist_items().split(",") if part])
        self.playlist_count.setText(f"{picked} of {total} selected")

    def _choose_format(self, data: dict[str, Any]) -> None:
        fmt_id = data.get("id") or ""
        if not fmt_id:
            return
        raw = data.get("raw") or {}
        if self.model.get("merge_best_audio") and is_video_only(raw):
            fmt_id = f"{fmt_id}+ba/b"
        self.model.set_many({"quality_preset": "custom", "format": fmt_id, "extract_audio": False})
        self.quality_chips["custom"].setChecked(True)
        self.status.emit(f"Format {fmt_id}")

    # ---------- submit ----------

    def _submit(self, switch: bool = True) -> None:
        urls = self.current_urls()
        if not urls:
            self.status.emit("Paste a URL first")
            return
        values = self.model.values()
        playlist = bool(self._infos and is_playlist(self._infos[0]))
        items = self._selected_playlist_items()
        if playlist:
            if not items:
                self.status.emit("Select at least one playlist item")
                return
            values["playlist_items"] = items
        info = self._infos[0] if self._infos else {}
        job = Job.create(
            urls,
            values,
            title=display_title(info, fallback=urls[0]),
            thumbnail=best_thumbnail(info),
            playlist=playlist or len(urls) > 1,
        )
        self.enqueue_job.emit(job, switch)
        self.status.emit(f"Queued {job.title}")

    def _set_busy(self, busy: bool) -> None:
        self.fetch_btn.setEnabled(not busy)
        self.fetch_btn.setText("Fetching…" if busy else "Fetch info")

    def set_urls(self, text: str) -> None:
        self.url_input.setPlainText(text)
        if looks_like_source(text):
            self.fetch()
