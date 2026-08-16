from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QByteArray, QRectF, Qt, QSize
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPixmap,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QLabel, QWidget


ASSETS = Path(__file__).resolve().parent / "assets"
ICON_SVG = ASSETS / "icon.svg"

BG = "#0b0d13"
BG_RAISED = "#11141c"
BG_CARD = "#161a24"
BG_CARD_HI = "#1b2030"
BG_INPUT = "#1c2130"
BG_HOVER = "#232a3a"
BG_SUNKEN = "#0e1118"
BORDER = "#272e3e"
BORDER_STRONG = "#39425a"
TEXT = "#f3f5fa"
TEXT_MUTED = "#8d95ab"
TEXT_SOFT = "#c4cad8"
ACCENT = "#ff4d6d"
ACCENT_HOVER = "#ff6b85"
ACCENT_PRESSED = "#e83f5d"
ACCENT_SOFT = "rgba(255, 77, 109, 0.14)"
ACCENT_LINE = "rgba(255, 77, 109, 0.32)"
SUCCESS = "#3dd68c"
WARNING = "#ffc14d"
ERROR = "#ff6b7a"
INFO = "#7aa2ff"
FOCUS = "#7aa2ff"


_IC_CHECK_MARK = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 13l4.5 4.5L19 7" fill="none" stroke="currentColor" stroke-width="3"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
_IC_CHEVRON_DOWN = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 9.5l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.4"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
_IC_CHEVRON_UP = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 14.5l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2.4"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
_IC_DASH = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 12h12" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
</svg>"""


def _render_svg_file(svg: str, color: str, size: int, name: str) -> str:
    """Rasterise a small control glyph so QSS can reference it with url()."""
    cache = Path(tempfile.gettempdir()) / "tuberip-theme"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / name
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.replace("currentColor", color).encode("utf-8")))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    pixmap.save(str(target), "PNG")
    return target.as_posix()


def _glyphs() -> dict[str, str]:
    wanted = {
        "check": (_IC_CHECK_MARK, "#ffffff", 16, "check.png"),
        "dash": (_IC_DASH, "#ffffff", 16, "dash.png"),
        "down": (_IC_CHEVRON_DOWN, TEXT_MUTED, 14, "chevron-down.png"),
        "down_hi": (_IC_CHEVRON_DOWN, TEXT, 14, "chevron-down-hi.png"),
        "up": (_IC_CHEVRON_UP, TEXT_MUTED, 14, "chevron-up.png"),
    }
    glyphs: dict[str, str] = {}
    for key, (svg, color, size, name) in wanted.items():
        try:
            glyphs[key] = _render_svg_file(svg, color, size, name)
        except OSError:
            # Without a writable cache the controls simply keep the platform arrows.
            glyphs[key] = ""
    return glyphs


def build_qss() -> str:
    g = _glyphs()
    return f"""
QWidget {{
    color: {TEXT};
    font-size: 13px;
    font-family: "Inter", "Segoe UI", "SF Pro Text", "Ubuntu", "Cantarell", sans-serif;
}}
QMainWindow, QDialog, QWidget#Root {{
    background: {BG};
}}

/* ---------- typography ---------- */
QLabel#AppTitle {{
    font-size: 17px;
    font-weight: 700;
}}
QLabel#AppTagline {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}
QLabel#PageTitle {{
    font-size: 23px;
    font-weight: 700;
}}
QLabel#PageHint, QLabel#Muted, QLabel#Meta, QLabel#FieldHint {{
    color: {TEXT_MUTED};
}}
QLabel#FieldHint {{
    font-size: 12px;
}}
QLabel#ErrorText {{
    color: {ERROR};
}}
QLabel#CardTitle {{
    font-size: 15px;
    font-weight: 600;
}}
QLabel#SectionTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {TEXT_MUTED};
}}
QLabel#FieldLabel {{
    color: {TEXT_SOFT};
    font-weight: 500;
}}
QLabel#EmptyTitle {{
    font-size: 15px;
    font-weight: 600;
    color: {TEXT_SOFT};
}}
QLabel#StatValue {{
    font-size: 19px;
    font-weight: 700;
}}
QLabel#Mono {{
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Mono", "DejaVu Sans Mono", monospace;
    color: {TEXT_SOFT};
}}

/* ---------- surfaces ---------- */
QFrame#Sidebar {{
    background: {BG_RAISED};
    border: none;
    border-right: 1px solid {BORDER};
}}
QFrame#Card, QFrame#JobCard, QFrame#MediaCard, QFrame#EmptyState {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#JobCard:hover {{
    border-color: {BORDER_STRONG};
    background: {BG_CARD_HI};
}}
QFrame#HeroCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1b2134, stop:1 #14171f);
    border: 1px solid {BORDER_STRONG};
    border-radius: 16px;
}}
QFrame#Inset, QLabel#Inset {{
    background: {BG_SUNKEN};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#Divider {{
    background: {BORDER};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
QFrame#VDivider {{
    background: {BORDER};
    border: none;
    max-width: 1px;
    min-width: 1px;
}}

/* ---------- buttons ---------- */
QPushButton {{
    background: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 7px 14px;
    min-height: 20px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {BORDER_STRONG};
}}
QPushButton:pressed {{
    background: #191e2a;
}}
QPushButton:disabled {{
    color: #5c657b;
    background: #151924;
    border-color: #1f2532;
}}
QPushButton:focus {{
    border-color: {FOCUS};
}}
QPushButton#Primary {{
    background: {ACCENT};
    color: #ffffff;
    border: 1px solid {ACCENT};
    padding: 8px 20px;
    font-weight: 600;
}}
QPushButton#Primary:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#Primary:pressed {{
    background: {ACCENT_PRESSED};
    border-color: {ACCENT_PRESSED};
}}
QPushButton#Primary:disabled {{
    background: #4d2b36;
    border-color: #4d2b36;
    color: #b98d99;
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {TEXT_SOFT};
}}
QPushButton#Ghost:hover {{
    background: {BG_HOVER};
    color: {TEXT};
}}
QPushButton#Quiet {{
    background: transparent;
    border: 1px solid transparent;
    color: {TEXT_MUTED};
    padding: 6px 10px;
}}
QPushButton#Quiet:hover {{
    background: {BG_HOVER};
    color: {TEXT};
}}
QPushButton#Danger {{
    background: rgba(255, 107, 122, 0.10);
    color: {ERROR};
    border: 1px solid rgba(255, 107, 122, 0.28);
}}
QPushButton#Danger:hover {{
    background: rgba(255, 107, 122, 0.18);
    border-color: rgba(255, 107, 122, 0.45);
}}
QPushButton#Chip {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 999px;
    padding: 6px 14px;
    color: {TEXT_SOFT};
    font-weight: 500;
}}
QPushButton#Chip:hover {{
    background: {BG_HOVER};
    border-color: {BORDER_STRONG};
    color: {TEXT};
}}
QPushButton#Chip:checked {{
    background: {ACCENT_SOFT};
    color: {ACCENT_HOVER};
    border: 1px solid {ACCENT_LINE};
    font-weight: 600;
}}
QPushButton#Toggle {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}
QPushButton#Toggle:checked {{
    background: {ACCENT_SOFT};
    border-color: {ACCENT_LINE};
    color: {ACCENT_HOVER};
    font-weight: 600;
}}
QPushButton#NavButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 8px 10px;
    text-align: left;
    color: {TEXT_MUTED};
    font-weight: 500;
}}
QPushButton#NavButton:hover {{
    background: {BG_HOVER};
    color: {TEXT};
}}
QPushButton#NavButton:checked {{
    background: {ACCENT_SOFT};
    color: #ffffff;
    border: 1px solid {ACCENT_LINE};
    font-weight: 600;
}}

/* ---------- inputs ---------- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 7px 10px;
    min-height: 20px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
}}
QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: {BORDER_STRONG};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QComboBox:on {{
    border-color: {FOCUS};
    background: {BG_HOVER};
}}
QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: #5c657b;
    background: #151924;
}}
QPlainTextEdit#UrlInput {{
    font-size: 14px;
    padding: 10px 12px;
    background: rgba(10, 12, 18, 0.55);
    border: 1px solid {BORDER};
}}
QPlainTextEdit#UrlInput:focus {{
    background: rgba(10, 12, 18, 0.75);
    border-color: {ACCENT_LINE};
}}
QLineEdit#Search {{
    padding-left: 32px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
QComboBox::down-arrow {{
    image: url("{g['down']}");
    width: 14px;
    height: 14px;
}}
QComboBox::down-arrow:hover, QComboBox::down-arrow:on {{
    image: url("{g['down_hi']}");
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 10px;
    padding: 4px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
    outline: none;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border: none;
    border-top-right-radius: 8px;
    background: transparent;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border: none;
    border-bottom-right-radius: 8px;
    background: transparent;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {BG_HOVER};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{g['up']}");
    width: 12px;
    height: 12px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{g['down']}");
    width: 12px;
    height: 12px;
}}

/* ---------- check / radio ---------- */
QCheckBox, QRadioButton {{
    spacing: 9px;
    color: {TEXT_SOFT};
    padding: 3px 0;
}}
QCheckBox:hover, QRadioButton:hover {{
    color: {TEXT};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 17px;
    height: 17px;
    border: 1px solid {BORDER_STRONG};
    background: {BG_INPUT};
}}
QCheckBox::indicator {{
    border-radius: 5px;
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {ACCENT};
    background: {BG_HOVER};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url("{g['check']}");
}}
QCheckBox::indicator:indeterminate {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: url("{g['dash']}");
}}
QRadioButton::indicator:checked {{
    background: {ACCENT};
    border: 5px solid {BG_INPUT};
}}
QCheckBox:disabled, QRadioButton:disabled {{
    color: #5c657b;
}}

/* ---------- scroll ---------- */
QScrollArea, QScrollArea > QWidget > QWidget {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: transparent;
    border: none;
    margin: 2px;
}}
QScrollBar:vertical {{ width: 11px; }}
QScrollBar:horizontal {{ height: 11px; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: #2e3648;
    border-radius: 4px;
    min-height: 28px;
    min-width: 28px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: #3f4a63;
}}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
    border: none;
    height: 0;
    width: 0;
}}

/* ---------- progress ---------- */
QProgressBar {{
    background: {BG_SUNKEN};
    border: none;
    border-radius: 5px;
    text-align: center;
    color: transparent;
    max-height: 6px;
    min-height: 6px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT}, stop:1 #ff9db0);
    border-radius: 5px;
}}

/* ---------- tables / lists ---------- */
QTableWidget, QTableView, QListWidget, QTreeWidget {{
    background: {BG_CARD};
    alternate-background-color: #191d29;
    border: 1px solid {BORDER};
    border-radius: 12px;
    gridline-color: transparent;
    outline: none;
}}
QTableView::item, QListWidget::item, QTreeWidget::item {{
    border: none;
    padding: 4px 6px;
}}
QListWidget::item {{
    border-radius: 7px;
    margin: 1px 3px;
}}
QTableView::item:hover, QListWidget::item:hover, QTreeWidget::item:hover {{
    background: {BG_HOVER};
}}
QTableView::item:selected, QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {ACCENT_SOFT};
    color: {TEXT};
}}
QTableView#Flat, QListWidget#Flat, QTreeWidget#Flat, QPlainTextEdit#Flat {{
    border: none;
    border-radius: 0;
    background: transparent;
    alternate-background-color: #1a1f2b;
}}
QHeaderView {{
    background: transparent;
}}
QTableView#Flat QHeaderView::section {{
    background: transparent;
}}
QHeaderView::section {{
    background: {BG_RAISED};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 6px;
    font-size: 12px;
    font-weight: 600;
}}
QHeaderView::section:hover {{
    color: {TEXT_SOFT};
}}
QTableCornerButton::section {{
    background: {BG_RAISED};
    border: none;
}}

/* ---------- tabs ---------- */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    background: {BG_CARD};
    top: -1px;
}}
QTabBar {{
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 7px 15px;
    margin-right: 3px;
    margin-bottom: 2px;
    border: 1px solid transparent;
    border-radius: 9px;
    font-weight: 500;
}}
QTabBar::tab:hover {{
    background: {BG_HOVER};
    color: {TEXT_SOFT};
}}
QTabBar::tab:selected {{
    color: {TEXT};
    background: {ACCENT_SOFT};
    border: 1px solid {ACCENT_LINE};
    font-weight: 600;
}}

/* ---------- pills ---------- */
QLabel#Pill {{
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
    background: {BG_INPUT};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
}}
QLabel#Pill[tone="accent"] {{
    background: {ACCENT_SOFT};
    color: {ACCENT_HOVER};
    border-color: {ACCENT_LINE};
}}
QLabel#Pill[tone="success"] {{
    background: rgba(61, 214, 140, 0.12);
    color: {SUCCESS};
    border-color: rgba(61, 214, 140, 0.30);
}}
QLabel#Pill[tone="warning"] {{
    background: rgba(255, 193, 77, 0.12);
    color: {WARNING};
    border-color: rgba(255, 193, 77, 0.30);
}}
QLabel#Pill[tone="error"] {{
    background: rgba(255, 107, 122, 0.12);
    color: {ERROR};
    border-color: rgba(255, 107, 122, 0.30);
}}
QLabel#Pill[tone="info"] {{
    background: rgba(122, 162, 255, 0.12);
    color: {INFO};
    border-color: rgba(122, 162, 255, 0.30);
}}

/* ---------- chrome ---------- */
QSplitter::handle {{
    background: {BORDER};
}}
QMenuBar {{
    background: {BG_RAISED};
    color: {TEXT_SOFT};
    border-bottom: 1px solid {BORDER};
    padding: 2px 6px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
    border-radius: 7px;
}}
QMenuBar::item:selected {{
    background: {BG_HOVER};
    color: {TEXT};
}}
QStatusBar {{
    background: {BG_RAISED};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    padding: 2px 8px;
}}
QStatusBar::item {{
    border: none;
}}
QMenu {{
    background: {BG_CARD};
    border: 1px solid {BORDER_STRONG};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 7px;
    color: {TEXT_SOFT};
}}
QMenu::item:selected {{
    background: {ACCENT_SOFT};
    color: {TEXT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 5px 8px;
}}
QToolTip {{
    background: {BG_SUNKEN};
    color: {TEXT_SOFT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 6px 8px;
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {TEXT_SOFT};
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(BG_CARD))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(BG_INPUT))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(BG_SUNKEN))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT_SOFT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#5c657b"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#5c657b"))
    app.setPalette(palette)
    app.setStyleSheet(build_qss())


def app_icon(size: int = 128) -> QIcon:
    renderer = QSvgRenderer(str(ICON_SVG))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QIcon(pixmap)


def svg_icon(svg: str, color: str = TEXT, size: int = 20) -> QIcon:
    colored = svg.replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(colored.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QIcon(pixmap)


def rounded_pixmap(source: QPixmap, radius: int = 12, size: QSize | None = None) -> QPixmap:
    if source.isNull():
        return source
    target_size = size or source.size()
    scaled = source.scaled(
        target_size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - target_size.width()) // 2)
    y = max(0, (scaled.height() - target_size.height()) // 2)
    cropped = scaled.copy(x, y, target_size.width(), target_size.height())
    out = QPixmap(target_size)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(out.rect()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return out


def set_card(widget: QWidget, name: str = "Card") -> None:
    widget.setObjectName(name)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


def restyle(widget: QWidget) -> None:
    """Re-evaluate the stylesheet after an object name or property change."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def add_shadow(widget: QWidget, blur: int = 28, y_offset: int = 6, alpha: int = 110) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setXOffset(0)
    effect.setYOffset(y_offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


def track_label(label: QLabel, spacing: float = 1.4) -> None:
    """Widen letter spacing; QSS ignores letter-spacing so it is applied on the font."""
    font = label.font()
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    label.setFont(font)


def elide(text: str, widget: QWidget, width: int | None = None) -> str:
    metrics = QFontMetrics(widget.font())
    limit = width if width is not None else max(80, widget.width())
    return metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, limit)


IC_DOWNLOAD = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 4v12m0 0-5-5m5 5 5-5M5 20h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
IC_QUEUE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 6h16M4 12h10M4 18h16M18 10v8m0 0-3-3m3 3 3-3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
IC_HISTORY = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 12a8 8 0 1 0 2.3-5.7M4 4v5h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M12 8v5l3 2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
IC_SLIDERS = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 7h16M4 17h16M8 7v.01M16 17v.01M14 4v6M10 14v6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""
IC_LOG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M7 7h10M7 12h6M7 17h8M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""
IC_FOLDER = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
</svg>"""
IC_SEARCH = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="11" cy="11" r="6.5" stroke="currentColor" stroke-width="1.8"/>
  <path d="M16 16l4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""
IC_PASTE = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M8 6h8M9 4h6a1 1 0 0 1 1 1v2H8V5a1 1 0 0 1 1-1z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
  <rect x="6" y="7" width="12" height="13" rx="2" stroke="currentColor" stroke-width="1.8"/>
</svg>"""
IC_FILM = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="5" width="18" height="14" rx="2.5" stroke="currentColor" stroke-width="1.7"/>
  <path d="M8 5v14M16 5v14M3 12h18" stroke="currentColor" stroke-width="1.4"/>
</svg>"""
IC_PLAY = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M9 7.5v9l7.5-4.5L9 7.5z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
  <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5"/>
</svg>"""
IC_TRASH = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12M11 11v5M14 11v5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
IC_REFRESH = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v4h-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
IC_LIST = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 7h14M5 12h14M5 17h9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""
IC_CAPTION = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="5" width="18" height="14" rx="2.5" stroke="currentColor" stroke-width="1.7"/>
  <path d="M8.5 11.5a2 2 0 1 0 0 2M15.5 11.5a2 2 0 1 0 0 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>"""
IC_INBOX = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 13l2-7h12l2 7v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
  <path d="M4 13h4l1 2h6l1-2h4" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
</svg>"""
