from __future__ import annotations

import os
import re
import shlex
import shutil
from pathlib import Path
from typing import Any

from tuberip.options_schema import OPTIONS, OPTIONS_BY_KEY, default_values
from tuberip.util import default_output_dir

_JS_RUNTIME_BINS = (
    ("deno", ("deno",)),
    ("node", ("node",)),
    ("bun", ("bun",)),
    ("quickjs", ("qjs", "quickjs")),
)


class DownloadCancelled(Exception):
    """Raised from a progress hook to abort a running yt-dlp job."""


def effective_outtmpl(values: dict[str, Any], playlist: bool = False) -> str:
    template = (values.get("outtmpl") or "").strip() or OPTIONS_BY_KEY["outtmpl"].default
    default = OPTIONS_BY_KEY["outtmpl"].default
    if playlist and values.get("organize_playlists") and template == default:
        return "%(playlist_title)s/%(playlist_index)03d - %(title)s [%(id)s].%(ext)s"
    return template


def build_argv(values: dict[str, Any], *, playlist: bool = False) -> list[str]:
    merged = default_values()
    merged.update(values or {})
    argv: list[str] = []

    if not merged.get("load_config_files"):
        argv.append("--ignore-config")

    output_dir = (merged.get("output_dir") or "").strip() or default_output_dir()
    argv.extend(["-P", output_dir])

    temp = (merged.get("paths_temp") or "").strip()
    if temp:
        prefixes = (
            "temp:",
            "home:",
            "subtitle:",
            "thumbnail:",
            "description:",
            "infojson:",
            "pl_thumbnail:",
            "pl_description:",
            "pl_infojson:",
            "chapter:",
        )
        if not temp.startswith(prefixes):
            temp = f"temp:{temp}"
        argv.extend(["-P", temp])

    skip_keys = {"paths_temp", "outtmpl"}
    for opt in OPTIONS:
        if opt.key in skip_keys:
            continue
        argv.extend(opt.to_argv(merged.get(opt.key, opt.default)))

    argv.extend(["-o", effective_outtmpl(merged, playlist=playlist)])
    inject_js_runtimes(argv, merged)
    inject_youtube_defaults(argv, merged)

    extra = (merged.get("extra_args") or "").strip()
    if extra:
        argv.extend(shlex.split(extra, posix=True))
    return argv


def detect_js_runtimes() -> list[str]:
    found: dict[str, str] = {}
    for runtime, binaries in _JS_RUNTIME_BINS:
        for binary in binaries:
            path = shutil.which(binary)
            if path:
                found[runtime] = str(Path(path).resolve())
                break
    home = Path.home()
    extra_candidates: list[tuple[str, Path]] = []
    extra_candidates.extend(("node", path) for path in sorted(home.glob(".nvm/versions/node/*/bin/node"), reverse=True))
    extra_candidates.extend(("node", path) for path in home.glob(".fnm/node-versions/*/installation/bin/node"))
    extra_candidates.extend(("node", path) for path in home.glob(".local/share/fnm/node-versions/*/installation/bin/node"))
    extra_candidates.append(("node", home / ".volta/bin/node"))
    extra_candidates.append(("deno", home / ".deno/bin/deno"))
    extra_candidates.append(("bun", home / ".bun/bin/bun"))
    conda = os.environ.get("CONDA_PREFIX")
    if conda:
        extra_candidates.append(("node", Path(conda) / "bin" / "node"))
        extra_candidates.append(("deno", Path(conda) / "bin" / "deno"))
    for runtime, path in extra_candidates:
        if runtime in found:
            continue
        if path.is_file() and os.access(path, os.X_OK):
            found[runtime] = str(path.resolve())
    return [f"{runtime}:{path}" for runtime, path in found.items()]


def ensure_js_runtimes_on_path() -> None:
    dirs: list[str] = []
    for spec in detect_js_runtimes():
        path = spec.split(":", 1)[-1]
        bindir = str(Path(path).parent)
        if bindir not in dirs:
            dirs.append(bindir)
    if not dirs:
        return
    current = os.environ.get("PATH", "")
    prefix = os.pathsep.join(dirs)
    if current.startswith(prefix):
        return
    os.environ["PATH"] = prefix + os.pathsep + current if current else prefix


def inject_js_runtimes(argv: list[str], values: dict[str, Any]) -> None:
    if values.get("no_js_runtimes"):
        return
    if (values.get("js_runtimes") or "").strip():
        return
    if "--js-runtimes" in argv or "--no-js-runtimes" in argv:
        return
    extra = values.get("extra_args") or ""
    if "--js-runtimes" in extra or "--no-js-runtimes" in extra:
        return
    specs = detect_js_runtimes()
    if not specs:
        return
    # Deno is already the default; enable every other available runtime too.
    for spec in specs:
        argv.extend(["--js-runtimes", spec])


def inject_youtube_defaults(argv: list[str], values: dict[str, Any]) -> None:
    extra = values.get("extra_args") or ""
    if values.get("remote_components") or values.get("no_remote_components"):
        return
    if "--remote-components" in argv or "--no-remote-components" in extra or "--no-remote-components" in argv:
        return
    try:
        import yt_dlp.dependencies as deps

        if getattr(deps, "yt_dlp_ejs", None):
            return
    except Exception:
        pass
    argv.extend(["--remote-components", "ejs:github"])


def parse_ydl_opts(argv: list[str]) -> dict[str, Any]:
    import yt_dlp

    parse_options = getattr(yt_dlp, "parse_options", None)
    if parse_options is not None:
        parsed = parse_options(argv)
        if hasattr(parsed, "ydl_opts"):
            return dict(parsed.ydl_opts)
        return dict(parsed[3])

    parse_opts = getattr(yt_dlp, "parseOpts")
    parsed = parse_opts(argv)
    return dict(parsed[3])


def ydl_opts_from_values(
    values: dict[str, Any],
    *,
    playlist: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    argv = build_argv(values, playlist=playlist)
    opts = parse_ydl_opts(argv)
    # `color` is already set by the parser; adding `no_color` makes yt-dlp warn.
    opts["color"] = {"stdout": "no_color", "stderr": "no_color"}
    opts["noprogress"] = True
    if extra:
        opts.update(extra)
    return opts


def fetch_opts_from_values(values: dict[str, Any]) -> dict[str, Any]:
    subset_keys = {
        "proxy",
        "socket_timeout",
        "source_address",
        "impersonate",
        "ip_version",
        "cookies",
        "cookies_from_browser",
        "username",
        "password",
        "twofactor",
        "netrc",
        "netrc_location",
        "videopassword",
        "geo_verification_proxy",
        "xff",
        "extractor_args",
        "extractor_retries",
        "js_runtimes",
        "no_js_runtimes",
        "remote_components",
        "no_check_certificates",
        "legacy_server_connect",
        "add_headers",
        "sleep_requests",
        "age_limit",
        "default_search",
        "use_extractors",
        "verbose",
        "load_config_files",
        "extra_args",
        "ffmpeg_location",
        "cache_dir",
        "no_cache_dir",
        "playlist_items",
        "flat_playlist",
        "playlist_mode",
        "compat_options",
        "encoding",
        "enable_file_urls",
        "client_certificate",
        "client_certificate_key",
        "client_certificate_password",
        "ap_mso",
        "ap_username",
        "ap_password",
    }
    argv = ["--ignore-config"] if not values.get("load_config_files") else []
    for opt in OPTIONS:
        if opt.key not in subset_keys:
            continue
        argv.extend(opt.to_argv(values.get(opt.key, opt.default)))
    inject_js_runtimes(argv, values)
    inject_youtube_defaults(argv, values)
    extra = (values.get("extra_args") or "").strip()
    if extra:
        argv.extend(shlex.split(extra, posix=True))
    opts = parse_ydl_opts(argv or ["--ignore-config"])
    opts.update(
        {
            "skip_download": True,
            "quiet": True,
            "color": {"stdout": "no_color", "stderr": "no_color"},
            "noprogress": True,
            "extract_flat": "in_playlist",
            "noplaylist": False,
        }
    )
    return opts


def apply_quality_preset(values: dict[str, Any], preset_id: str) -> dict[str, Any]:
    from tuberip.options_schema import QUALITY_PRESETS

    updated = dict(values)
    updated["quality_preset"] = preset_id
    for preset in QUALITY_PRESETS:
        if preset["id"] != preset_id:
            continue
        if preset.get("format"):
            updated["format"] = preset["format"]
        if "extract_audio" in preset:
            updated["extract_audio"] = preset["extract_audio"]
        if preset.get("audio_format"):
            updated["audio_format"] = preset["audio_format"]
        if preset_id in {"mp3", "m4a", "opus", "flac", "audio"}:
            updated["merge_output_format"] = ""
        elif preset_id != "custom" and not updated.get("merge_output_format"):
            updated["merge_output_format"] = "mp4"
        break
    return updated


def format_row(fmt: dict[str, Any]) -> dict[str, Any]:
    from tuberip.util import codec_name, fmt_bytes

    height = fmt.get("height")
    width = fmt.get("width")
    if height and width:
        resolution = f"{width}x{height}"
    elif height:
        resolution = f"{height}p"
    elif fmt.get("acodec") not in (None, "none") and fmt.get("vcodec") in (None, "none"):
        resolution = "audio"
    else:
        resolution = fmt.get("resolution") or "—"

    size = fmt.get("filesize") or fmt.get("filesize_approx")
    return {
        "id": str(fmt.get("format_id") or ""),
        "ext": str(fmt.get("ext") or "—"),
        "resolution": resolution,
        "fps": fmt.get("fps") or "",
        "vcodec": codec_name(fmt.get("vcodec")),
        "acodec": codec_name(fmt.get("acodec")),
        "size": fmt_bytes(size),
        "tbr": f"{fmt['tbr']:.0f}k" if fmt.get("tbr") else "—",
        "note": str(fmt.get("format_note") or fmt.get("dynamic_range") or ""),
        "protocol": str(fmt.get("protocol") or ""),
        "raw": fmt,
    }


def is_http_403(message: str) -> bool:
    text = (message or "").lower()
    return "403" in text or "forbidden" in text


#: A 403 on the media URL is usually transient: YouTube hands out a signed URL
#: that it then rejects. yt-dlp only retries 5xx responses, so the whole job has
#: to run again to force a fresh extraction with new URLs.
MAX_403_ATTEMPTS = 3


def youtube_retry_values(values: dict[str, Any], attempt: int = 1) -> dict[str, Any]:
    """Options for retry `attempt` after a 403; attempt 1 is the first retry."""
    retry = dict(values)
    # Signed-in requests are pinned to clients that often need a PO token, so the
    # first retry drops cookies. Later retries just re-extract for fresh URLs.
    if used_cookies(values):
        retry["cookies"] = ""
        retry["cookies_from_browser"] = ""
    return retry


def used_cookies(values: dict[str, Any]) -> bool:
    return bool((values.get("cookies") or "").strip() or (values.get("cookies_from_browser") or "").strip())


def describe_403(values: dict[str, Any], attempts: int) -> str:
    """Explain a 403 that survived every retry, based on the actual environment."""
    tries = "try" if attempts == 1 else f"{attempts} tries"
    if not detect_js_runtimes():
        return (
            f"YouTube refused the media URL (HTTP 403) after {tries}. No JavaScript runtime was found - "
            "install Node.js or Deno so yt-dlp can solve YouTube's signature challenge."
        )
    if used_cookies(values):
        return (
            f"YouTube refused the media URL (HTTP 403) after {tries}, including one without cookies. "
            "This is usually temporary; wait a moment and retry, or set Cookies to 'No cookies'."
        )
    return (
        f"YouTube refused the media URL (HTTP 403) after {tries}. "
        "This is usually temporary - wait a moment and retry the job."
    )


def is_video_only(fmt: dict[str, Any]) -> bool:
    return fmt.get("vcodec") not in (None, "none") and fmt.get("acodec") in (None, "none")


def is_audio_only(fmt: dict[str, Any]) -> bool:
    return fmt.get("acodec") not in (None, "none") and fmt.get("vcodec") in (None, "none")


class SignalLogger:
    def __init__(self, emit) -> None:
        self._emit = emit
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def debug(self, msg: str) -> None:
        text = str(msg)
        level = "debug" if text.startswith("[debug] ") else "info"
        self._emit(level, text)

    def info(self, msg: str) -> None:
        self._emit("info", str(msg))

    def warning(self, msg: str) -> None:
        text = str(msg)
        self.warnings.append(text)
        self._emit("warning", text)

    def error(self, msg: str) -> None:
        text = str(msg)
        self.errors.append(text)
        self._emit("error", text)


def summarize_ydl_failure(logger: SignalLogger, code: int | None = None) -> str:
    for raw in reversed(logger.errors):
        text = re.sub(r"\x1b\[[0-9;]*m", "", raw).strip()
        text = re.sub(r"^ERROR:\s*", "", text)
        if text:
            return text
    for raw in reversed(logger.warnings):
        text = re.sub(r"\x1b\[[0-9;]*m", "", raw).strip()
        text = re.sub(r"^WARNING:\s*", "", text)
        if text and "javascript runtime" in text.lower():
            return "No JavaScript runtime was found; install Node.js or Deno so YouTube formats stay available."
        if text:
            return text
    if code:
        return f"yt-dlp exited with code {code}"
    return "Download failed"
