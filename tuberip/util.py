from __future__ import annotations

import re
from pathlib import Path
from typing import Any


URL_PREFIXES = (
    "http://",
    "https://",
    "ytsearch:",
    "ytsearchdate:",
    "ytsearchall:",
    "scsearch:",
    "nicosearch:",
    "bvsearch:",
    "gvsearch:",
)


def looks_like_source(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return False
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return bool(lines) and all(_looks_like_one(line) for line in lines)


def _looks_like_one(value: str) -> bool:
    if value.startswith(URL_PREFIXES):
        return True
    return bool(re.match(r"^[A-Za-z][\w+-]*:", value))


def split_sources(text: str) -> list[str]:
    sources: list[str] = []
    for raw in (text or "").replace(",", "\n").splitlines():
        item = raw.strip()
        if not item or item.startswith(("#", ";", "]")):
            continue
        sources.append(item)
    return sources


def fmt_duration(seconds: Any) -> str:
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return "—"
    hours, rem = divmod(max(total, 0), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def fmt_count(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    abs_number = abs(number)
    if abs_number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs_number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return str(int(number))


def fmt_bytes(value: Any) -> str:
    try:
        size = float(value)
    except (TypeError, ValueError):
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return "—"


def fmt_speed(value: Any) -> str:
    rendered = fmt_bytes(value)
    return "—" if rendered == "—" else f"{rendered}/s"


def fmt_eta(seconds: Any) -> str:
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return "—"
    if total < 0:
        return "—"
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def codec_name(value: Any) -> str:
    if not value or value == "none":
        return "—"
    return str(value).split(".")[0]


def best_thumbnail(info: dict[str, Any] | None) -> str:
    if not info:
        return ""
    thumb = info.get("thumbnail")
    if thumb:
        return str(thumb)
    thumbs = info.get("thumbnails") or []
    if not thumbs:
        return ""
    chosen = max(thumbs, key=lambda item: item.get("preference") or item.get("width") or 0)
    return str(chosen.get("url") or "")


def display_title(info: dict[str, Any] | None, fallback: str = "Untitled") -> str:
    if not info:
        return fallback
    return str(info.get("title") or info.get("id") or fallback)


def is_playlist(info: dict[str, Any] | None) -> bool:
    return bool(info) and info.get("_type") in {"playlist", "multi_video"}


def playlist_entries(info: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not info:
        return []
    entries = info.get("entries") or []
    return [entry for entry in entries if entry]


def default_output_dir() -> str:
    return str(Path.home() / "Downloads" / "tubeRiP")


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
