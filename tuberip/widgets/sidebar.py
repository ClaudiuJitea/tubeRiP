from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from tuberip.theme import (
    ACCENT_HOVER,
    IC_DOWNLOAD,
    IC_HISTORY,
    IC_LOG,
    IC_QUEUE,
    IC_SLIDERS,
    TEXT_MUTED,
    app_icon,
    set_card,
    svg_icon,
)
from tuberip.widgets.common import Divider, Pill, SectionLabel

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    (IC_DOWNLOAD, "Download"),
    (IC_QUEUE, "Queue"),
    (IC_HISTORY, "History"),
    (IC_SLIDERS, "Options"),
    (IC_LOG, "Log"),
)


class NavButton(QPushButton):
    """Nav row that can show a count badge pinned to its right edge."""

    def __init__(self, icon_svg: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.icon_svg = icon_svg
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self.setMinimumHeight(36)
        self.badge = Pill("", "accent", self)
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.badge.hide()
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self.setIcon(svg_icon(self.icon_svg, ACCENT_HOVER if active else TEXT_MUTED, 18))

    def set_badge(self, count: int) -> None:
        if count > 0:
            self.badge.setText(str(count))
            self.badge.adjustSize()
            self.badge.show()
            self._place_badge()
        else:
            self.badge.hide()

    def _place_badge(self) -> None:
        self.badge.move(
            self.width() - self.badge.width() - 9,
            (self.height() - self.badge.height()) // 2,
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        super().resizeEvent(event)
        self._place_badge()


class Sidebar(QFrame):
    navigated = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_card(self, "Sidebar")
        self.setFixedWidth(206)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel()
        mark.setPixmap(app_icon().pixmap(30, 30))
        mark.setFixedSize(30, 30)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("tubeRiP")
        name.setObjectName("AppTitle")
        tagline = QLabel("yt-dlp studio")
        tagline.setObjectName("AppTagline")
        brand_text.addWidget(name)
        brand_text.addWidget(tagline)
        brand_row.addWidget(mark)
        brand_row.addLayout(brand_text, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(16)
        layout.addWidget(Divider())
        layout.addSpacing(12)

        section = SectionLabel("Workspace")
        layout.addWidget(section)
        layout.addSpacing(4)

        self.buttons: list[NavButton] = []
        for index, (icon, label) in enumerate(NAV_ITEMS):
            button = NavButton(icon, label)
            button.clicked.connect(lambda _=False, i=index: self._select(i))
            self.buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)
        layout.addWidget(Divider())
        layout.addSpacing(10)
        self.footer = QLabel("Ready")
        self.footer.setObjectName("AppTagline")
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)
        self._select(0, emit=False)

    def _select(self, index: int, emit: bool = True) -> None:
        for i, button in enumerate(self.buttons):
            button.set_active(i == index)
        if emit:
            self.navigated.emit(index)

    def set_current(self, index: int) -> None:
        self._select(index, emit=False)

    def set_queue_badge(self, count: int) -> None:
        self.buttons[1].set_badge(count)

    def set_footer(self, text: str) -> None:
        self.footer.setText(text)
