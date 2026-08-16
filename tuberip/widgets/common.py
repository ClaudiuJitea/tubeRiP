from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tuberip.theme import (
    IC_SEARCH,
    TEXT_MUTED,
    restyle,
    set_card,
    svg_icon,
    track_label,
)


class FlowLayout(QLayout):
    """Left-to-right layout that wraps onto new lines, used for chip rows."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 8, line_spacing: int = 8) -> None:
        super().__init__(parent)
        self._items: list = []
        self._spacing = spacing
        self._line_spacing = line_spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:  # noqa: N802 - Qt signature
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802 - Qt signature
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # noqa: N802 - Qt signature
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # noqa: N802 - Qt signature
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt signature
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt signature
        return self._arrange(QRect(0, 0, width, 0), measure_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802 - Qt signature
        super().setGeometry(rect)
        self._arrange(rect, measure_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt signature
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802 - Qt signature
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _arrange(self, rect: QRect, measure_only: bool) -> int:
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = area.x()
        y = area.y()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._spacing
            if next_x - self._spacing > area.right() and line_height > 0:
                x = area.x()
                y = y + line_height + self._line_spacing
                next_x = x + hint.width() + self._spacing
                line_height = 0
            if not measure_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


class Pill(QLabel):
    """Small status badge; tone maps to a colour in the stylesheet."""

    def __init__(self, text: str = "", tone: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("Pill")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        restyle(self)

    def set_state(self, text: str, tone: str) -> None:
        self.setText(text)
        self.set_tone(tone)


class Divider(QFrame):
    def __init__(self, vertical: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        set_card(self, "VDivider" if vertical else "Divider")
        if vertical:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class SectionLabel(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text.upper(), parent)
        self.setObjectName("SectionTitle")
        track_label(self, 1.2)


class FieldLabel(QLabel):
    def __init__(self, text: str, width: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("FieldLabel")
        if width:
            self.setFixedWidth(width)


class Card(QFrame):
    """Titled surface with a header row that callers can extend."""

    def __init__(
        self,
        title: str = "",
        parent: QWidget | None = None,
        name: str = "Card",
        margins: tuple[int, int, int, int] = (18, 16, 18, 18),
        spacing: int = 12,
    ) -> None:
        super().__init__(parent)
        set_card(self, name)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(*margins)
        self.outer.setSpacing(spacing)
        self.header = QHBoxLayout()
        self.header.setSpacing(10)
        self.title_label = SectionLabel(title)
        self.header.addWidget(self.title_label)
        self.header.addStretch(1)
        if title:
            self.outer.addLayout(self.header)
        else:
            self.title_label.hide()
        self.body = QVBoxLayout()
        self.body.setSpacing(spacing)
        self.outer.addLayout(self.body)

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        self.body.addWidget(widget, stretch)

    def add_layout(self, layout) -> None:
        self.body.addLayout(layout)

    def add_header_widget(self, widget: QWidget) -> None:
        self.header.addWidget(widget)


class PageHeader(QWidget):
    """Title, supporting line, and an optional right-hand action area."""

    def __init__(self, title: str, hint: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.title = QLabel(title)
        self.title.setObjectName("PageTitle")
        self.hint = QLabel(hint)
        self.hint.setObjectName("PageHint")
        self.hint.setWordWrap(True)
        text_col.addWidget(self.title)
        text_col.addWidget(self.hint)
        if not hint:
            self.hint.hide()
        layout.addLayout(text_col, 1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        self.actions.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(self.actions)

    def add_action(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)

    def set_hint(self, text: str) -> None:
        self.hint.setText(text)
        self.hint.setVisible(bool(text))


class SearchEdit(QLineEdit):
    """Line edit with a magnifier glyph rendered inside the left padding."""

    def __init__(self, placeholder: str = "Search…", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Search")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self._icon = QLabel(self)
        self._icon.setPixmap(svg_icon(IC_SEARCH, TEXT_MUTED, 16).pixmap(16, 16))
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._icon.setFixedSize(16, 16)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        super().resizeEvent(event)
        self._icon.move(11, (self.height() - self._icon.height()) // 2)


class EmptyState(QFrame):
    """Centred icon + copy shown when a list has nothing in it."""

    def __init__(
        self,
        icon_svg: str,
        title: str,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        set_card(self, "EmptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 34, 24, 34)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel()
        icon.setPixmap(svg_icon(icon_svg, TEXT_MUTED, 34).pixmap(34, 34))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel(title)
        self.title.setObjectName("EmptyTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint = QLabel(hint)
        self.hint.setObjectName("Muted")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        layout.addWidget(icon)
        layout.addWidget(self.title)
        layout.addWidget(self.hint)
        if not hint:
            self.hint.hide()
