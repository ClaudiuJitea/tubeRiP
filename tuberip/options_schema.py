from __future__ import annotations

from dataclasses import dataclass
from typing import Any


APP_KEYS = {
    "output_dir",
    "organize_playlists",
    "merge_best_audio",
    "queue_concurrency",
    "auto_fetch",
    "load_config_files",
    "extra_args",
    "quality_preset",
}

SENSITIVE_KEYS = {
    "password",
    "twofactor",
    "videopassword",
    "ap_password",
    "client_certificate_password",
}


@dataclass
class Opt:
    key: str
    group: str
    label: str
    help: str
    kind: str = "str"
    flag: str | None = None
    flag_false: str | None = None
    default: Any = None
    choices: tuple[str, ...] | None = None
    placeholder: str = ""
    repeat: bool = False
    value_flag: bool = True

    def to_argv(self, value: Any) -> list[str]:
        if self.kind == "bool":
            if bool(value) == bool(self.default):
                return []
            if value:
                return [self.flag] if self.flag else []
            return [self.flag_false] if self.flag_false else []

        if value is None:
            return []
        if isinstance(value, str) and not value.strip():
            return []
        if self.kind == "choice" and value == (self.default or ""):
            return []
        if value == self.default:
            return []

        if self.kind == "choice":
            token = str(value)
            if token.startswith("-"):
                return [token]
            if self.flag:
                return [self.flag, token]
            return []

        if self.repeat or self.kind in {"text", "headers"}:
            lines = [line.strip() for line in str(value).splitlines() if line.strip()]
            argv: list[str] = []
            for line in lines:
                if not self.flag:
                    continue
                if self.value_flag:
                    argv.extend([self.flag, line])
                else:
                    argv.append(self.flag)
            return argv

        if not self.flag:
            return []
        if not self.value_flag:
            return [self.flag]
        return [self.flag, str(value)]

    def search_blob(self) -> str:
        return " ".join(
            part.lower()
            for part in (self.key, self.group, self.label, self.help, self.flag or "", self.flag_false or "")
            if part
        )


def _b(key, group, label, help, flag, default=False, flag_false=None) -> Opt:
    return Opt(key, group, label, help, "bool", flag, flag_false, default)


def _s(key, group, label, help, flag, default="", placeholder="", kind="str", repeat=False) -> Opt:
    return Opt(key, group, label, help, kind, flag, None, default, placeholder=placeholder, repeat=repeat)


def _c(key, group, label, help, choices, default="", flag=None) -> Opt:
    return Opt(key, group, label, help, "choice", flag, None, default, choices=choices)


GROUPS = [
    "General",
    "Network",
    "Geo-restriction",
    "Video selection",
    "Download",
    "Filesystem",
    "Thumbnails",
    "Internet shortcuts",
    "Simulation",
    "Workarounds",
    "Format",
    "Subtitles",
    "Authentication",
    "Post-processing",
    "SponsorBlock",
    "Extractor",
]


OPTIONS: list[Opt] = [
    # Quick / commonly used (also bound from the download page)
    _s("format", "Format", "Format selection",
       "Video format code, e.g. bv*+ba/b or 137+140. See yt-dlp FORMAT SELECTION.",
       "-f", "bv*+ba/b", "bv*+ba/b"),
    _s("format_sort", "Format", "Format sort",
       "Sort formats by fields, e.g. res,fps,codec:h264",
       "-S"),
    _b("format_sort_force", "Format", "Force format sort",
       "Force user-specified sort order to take precedence.",
       "--format-sort-force"),
    _b("video_multistreams", "Format", "Video multistreams",
       "Allow multiple video streams to be merged.",
       "--video-multistreams", False, "--no-video-multistreams"),
    _b("audio_multistreams", "Format", "Audio multistreams",
       "Allow multiple audio streams to be merged.",
       "--audio-multistreams", False, "--no-audio-multistreams"),
    _b("prefer_free_formats", "Format", "Prefer free formats",
       "Prefer free containers of the same quality.",
       "--prefer-free-formats"),
    _c("check_formats", "Format", "Check formats",
       "Check whether selected formats are actually downloadable.",
       ("", "--check-formats", "--check-all-formats", "--no-check-formats")),
    _c("merge_output_format", "Format", "Merge container",
       "Container used when merging video+audio.",
       ("", "mp4", "mkv", "webm", "mov", "avi", "flv"), "", "--merge-output-format"),

    _s("outtmpl", "Filesystem", "Output template",
       "Filename template. See yt-dlp OUTPUT TEMPLATE.",
       "-o", "%(title)s [%(id)s].%(ext)s", "%(title)s [%(id)s].%(ext)s"),
    _s("paths_temp", "Filesystem", "Temp path",
       "Temporary directory for in-progress files.",
       "-P", placeholder="temp:/path/to/tmp"),
    _s("output_na_placeholder", "Filesystem", "NA placeholder",
       "Placeholder for unavailable output fields.",
       "--output-na-placeholder", "NA"),
    _b("restrict_filenames", "Filesystem", "Restrict filenames",
       "ASCII-only filenames, no spaces or &.",
       "--restrict-filenames"),
    _b("windows_filenames", "Filesystem", "Windows filenames",
       "Force Windows-compatible filenames.",
       "--windows-filenames", False, "--no-windows-filenames"),
    _s("trim_filenames", "Filesystem", "Trim filenames",
       "Limit filename length excluding extension.",
       "--trim-filenames", placeholder="180"),
    _c("overwrites", "Filesystem", "Overwrites",
       "Whether to overwrite existing files.",
       ("", "--no-overwrites", "--force-overwrites")),
    _b("continue_dl", "Filesystem", "Resume downloads",
       "Resume partially downloaded files.",
       "--continue", True, "--no-continue"),
    _b("part_files", "Filesystem", "Use .part files",
       "Write to .part files until the download finishes.",
       "--part", True, "--no-part"),
    _b("mtime", "Filesystem", "Set file mtime",
       "Use Last-modified header for file modification time.",
       "--mtime"),
    _b("write_description", "Filesystem", "Write description",
       "Write the video description to a .description file.",
       "--write-description"),
    _b("write_info_json", "Filesystem", "Write info JSON",
       "Write video metadata to a .info.json file.",
       "--write-info-json"),
    _b("write_playlist_metafiles", "Filesystem", "Playlist meta files",
       "Write playlist metadata along with video metadata.",
       "--write-playlist-metafiles", True, "--no-write-playlist-metafiles"),
    _b("clean_info_json", "Filesystem", "Clean info JSON",
       "Remove internal metadata from infojson.",
       "--clean-info-json", True, "--no-clean-info-json"),
    _b("write_comments", "Filesystem", "Write comments",
       "Retrieve comments into the infojson.",
       "--write-comments"),
    _s("load_info_json", "Filesystem", "Load info JSON",
       "Download using an existing .info.json file.",
       "--load-info-json", kind="file"),
    _s("cookies", "Filesystem", "Cookies file",
       "Netscape cookies.txt to read/write.",
       "--cookies", kind="file"),
    _s("cookies_from_browser", "Filesystem", "Cookies from browser",
       "Browser to load cookies from, e.g. chrome, firefox:Profile, chrome::Default",
       "--cookies-from-browser", placeholder="chrome"),
    _s("cache_dir", "Filesystem", "Cache directory",
       "Where yt-dlp stores client IDs and signatures.",
       "--cache-dir", kind="path"),
    _b("no_cache_dir", "Filesystem", "Disable cache",
       "Disable filesystem caching.",
       "--no-cache-dir"),

    # General
    _b("ignore_errors", "General", "Ignore errors",
       "Continue even if a download or postprocess step fails.",
       "--ignore-errors"),
    _b("abort_on_error", "General", "Abort on error",
       "Stop the whole queue when a video fails.",
       "--abort-on-error"),
    _s("use_extractors", "General", "Use extractors",
       "Extractor names, regexes, all, default, end. Prefix with - to exclude.",
       "--use-extractors", placeholder="default,-generic"),
    _s("default_search", "General", "Default search",
       "Prefix for unqualified URLs: auto, auto_warning, error, fixup_error, ytsearch.",
       "--default-search", "fixup_error"),
    _s("plugin_dirs", "General", "Plugin directories",
       "Additional plugin dirs, one per line. Use default to include built-in paths.",
       "--plugin-dirs", kind="text", repeat=True),
    _b("no_plugin_dirs", "General", "No plugin dirs",
       "Clear plugin directories, including defaults.",
       "--no-plugin-dirs"),
    _s("js_runtimes", "General", "JS runtimes",
       "JavaScript runtimes, one per line: deno, node, quickjs, bun[:path].",
       "--js-runtimes", kind="text", repeat=True),
    _b("no_js_runtimes", "General", "No JS runtimes",
       "Clear JavaScript runtimes including defaults.",
       "--no-js-runtimes"),
    _s("remote_components", "General", "Remote components",
       "Allow remote components, one per line: ejs:npm, ejs:github.",
       "--remote-components", kind="text", repeat=True),
    _b("no_remote_components", "General", "No remote components",
       "Disallow fetching remote components.",
       "--no-remote-components"),
    _b("flat_playlist", "General", "Flat playlist",
       "Do not fully extract playlist entries.",
       "--flat-playlist", False, "--no-flat-playlist"),
    _b("live_from_start", "General", "Live from start",
       "Download livestreams from the beginning when supported.",
       "--live-from-start"),
    _s("wait_for_video", "General", "Wait for video",
       "Wait for scheduled streams. MIN[-MAX] seconds between retries.",
       "--wait-for-video", placeholder="5-30"),
    _b("mark_watched", "General", "Mark watched",
       "Mark videos as watched on the site.",
       "--mark-watched"),
    _s("compat_options", "General", "Compat options",
       "youtube-dl compatibility flags, comma-separated.",
       "--compat-options"),
    _c("preset_alias", "General", "Preset alias",
       "Apply a built-in yt-dlp preset.",
       ("", "mp3", "aac", "mp4", "mkv", "sleep"), "", "-t"),
    _s("config_locations", "General", "Config locations",
       "Additional yt-dlp config files, one per line.",
       "--config-locations", kind="text", repeat=True),

    # Network
    _s("proxy", "Network", "Proxy",
       "HTTP/HTTPS/SOCKS proxy. Empty string forces a direct connection.",
       "--proxy", placeholder="socks5://127.0.0.1:1080"),
    _s("socket_timeout", "Network", "Socket timeout",
       "Seconds to wait before giving up.",
       "--socket-timeout", placeholder="20"),
    _s("source_address", "Network", "Source address",
       "Client-side IP to bind.",
       "--source-address"),
    _s("impersonate", "Network", "Impersonate client",
       "TLS/HTTP impersonation target, e.g. chrome, chrome-110, chrome:windows-10.",
       "--impersonate", placeholder="chrome"),
    _c("ip_version", "Network", "IP version",
       "Force IPv4 or IPv6.",
       ("", "--force-ipv4", "--force-ipv6")),
    _b("enable_file_urls", "Network", "Enable file URLs",
       "Allow file:// URLs (disabled by default).",
       "--enable-file-urls"),

    # Geo
    _s("geo_verification_proxy", "Geo-restriction", "Geo verification proxy",
       "Proxy used only to verify the IP for geo-restricted sites.",
       "--geo-verification-proxy"),
    _s("xff", "Geo-restriction", "X-Forwarded-For",
       "default, never, ISO country code, or CIDR block.",
       "--xff", placeholder="US"),

    # Video selection
    _s("playlist_items", "Video selection", "Playlist items",
       "Indexes to download, e.g. 1:3,7,-5::2",
       "--playlist-items", placeholder="1:10"),
    _s("min_filesize", "Video selection", "Min filesize",
       "Skip files smaller than this, e.g. 50k or 44.6M.",
       "--min-filesize"),
    _s("max_filesize", "Video selection", "Max filesize",
       "Skip files larger than this.",
       "--max-filesize"),
    _s("date", "Video selection", "Upload date",
       "YYYYMMDD or today/yesterday[-Nday|week|month|year].",
       "--date", placeholder="today-1week"),
    _s("datebefore", "Video selection", "Uploaded before",
       "Only videos on or before this date.",
       "--datebefore"),
    _s("dateafter", "Video selection", "Uploaded after",
       "Only videos on or after this date.",
       "--dateafter"),
    _s("match_filters", "Video selection", "Match filters",
       "Generic video filters, one per line. See yt-dlp Filtering Formats.",
       "--match-filters", kind="text", repeat=True),
    _s("break_match_filters", "Video selection", "Break match filters",
       "Stop downloading when a video is rejected by this filter.",
       "--break-match-filters", kind="text", repeat=True),
    _c("playlist_mode", "Video selection", "Video vs playlist",
       "When a URL is both a video and a playlist.",
       ("", "--yes-playlist", "--no-playlist")),
    _s("age_limit", "Video selection", "Age limit",
       "Download only videos suitable for this age.",
       "--age-limit"),
    _s("download_archive", "Video selection", "Download archive",
       "Record IDs and skip already downloaded videos.",
       "--download-archive", kind="file"),
    _s("max_downloads", "Video selection", "Max downloads",
       "Abort after this many files.",
       "--max-downloads"),
    _b("break_on_existing", "Video selection", "Break on existing",
       "Stop when a video is already in the archive.",
       "--break-on-existing"),
    _b("break_per_input", "Video selection", "Break per input",
       "Reset max-downloads / break filters per input URL.",
       "--break-per-input"),
    _s("skip_playlist_after_errors", "Video selection", "Skip playlist after errors",
       "Skip the rest of a playlist after N failures.",
       "--skip-playlist-after-errors"),

    # Download
    _s("concurrent_fragments", "Download", "Concurrent fragments",
       "Parallel fragment downloads for DASH/HLS.",
       "-N", "1"),
    _s("limit_rate", "Download", "Rate limit",
       "Maximum download rate, e.g. 4.2M or 500K.",
       "-r"),
    _s("throttled_rate", "Download", "Throttled rate",
       "Re-extract if speed stays below this.",
       "--throttled-rate"),
    _s("retries", "Download", "Retries",
       "Retry count, or infinite.",
       "-R", "10", "10 or infinite"),
    _s("file_access_retries", "Download", "File access retries",
       "Retries on file access errors, or infinite.",
       "--file-access-retries", "3"),
    _s("fragment_retries", "Download", "Fragment retries",
       "Retries per fragment, or infinite.",
       "--fragment-retries", "10"),
    _s("retry_sleep", "Download", "Retry sleep",
       "Sleep expression, one per line, e.g. linear=1::2 or fragment:exp=1:20",
       "--retry-sleep", kind="text", repeat=True),
    _b("skip_unavailable_fragments", "Download", "Skip unavailable fragments",
       "Continue when a DASH/HLS fragment is missing.",
       "--skip-unavailable-fragments", True, "--abort-on-unavailable-fragments"),
    _b("keep_fragments", "Download", "Keep fragments",
       "Keep downloaded fragments on disk.",
       "--keep-fragments"),
    _s("buffer_size", "Download", "Buffer size",
       "Download buffer size, e.g. 16K.",
       "--buffer-size", "1024"),
    _b("resize_buffer", "Download", "Auto-resize buffer",
       "Automatically resize the download buffer.",
       "--resize-buffer", True, "--no-resize-buffer"),
    _s("http_chunk_size", "Download", "HTTP chunk size",
       "Chunk size for HTTP downloads, e.g. 10M.",
       "--http-chunk-size"),
    _b("playlist_random", "Download", "Shuffle playlist",
       "Download playlist items in random order.",
       "--playlist-random"),
    _b("lazy_playlist", "Download", "Lazy playlist",
       "Process playlist entries as they arrive.",
       "--lazy-playlist"),
    _c("hls_use_mpegts", "Download", "HLS MPEG-TS",
       "Use MPEG-TS container for HLS videos.",
       ("", "--hls-use-mpegts", "--no-hls-use-mpegts")),
    _s("download_sections", "Download", "Download sections",
       "Chapter regex or *START-END time range, one per line.",
       "--download-sections", kind="text", repeat=True, placeholder="*10:15-inf"),
    _s("downloader", "Download", "External downloader",
       "native, aria2c, axel, curl, ffmpeg, httpie, wget. Optionally PROTO:NAME.",
       "--downloader", kind="text", repeat=True, placeholder="aria2c"),
    _s("downloader_args", "Download", "Downloader args",
       "NAME:ARGS, one per line.",
       "--downloader-args", kind="text", repeat=True),

    # Thumbnails
    _b("write_thumbnail", "Thumbnails", "Write thumbnail",
       "Save the thumbnail image next to the video.",
       "--write-thumbnail"),
    _b("write_all_thumbnails", "Thumbnails", "Write all thumbnails",
       "Write every available thumbnail format.",
       "--write-all-thumbnails"),

    # Shortcuts
    _b("write_link", "Internet shortcuts", "Write shortcut",
       "Write a platform internet shortcut to the video URL.",
       "--write-link"),
    _b("write_url_link", "Internet shortcuts", "Write .url",
       "Write a Windows .url shortcut.",
       "--write-url-link"),
    _b("write_webloc_link", "Internet shortcuts", "Write .webloc",
       "Write a macOS .webloc shortcut.",
       "--write-webloc-link"),
    _b("write_desktop_link", "Internet shortcuts", "Write .desktop",
       "Write a Linux .desktop shortcut.",
       "--write-desktop-link"),

    # Simulation
    _b("simulate", "Simulation", "Simulate",
       "Do not download or write files.",
       "--simulate"),
    _b("ignore_no_formats_error", "Simulation", "Ignore no-formats error",
       "Extract metadata even if no formats are available.",
       "--ignore-no-formats-error"),
    _b("skip_download", "Simulation", "Skip download",
       "Write metadata files without downloading media.",
       "--skip-download"),
    _b("force_write_archive", "Simulation", "Force write archive",
       "Write archive entries even when simulating.",
       "--force-write-archive"),
    _b("verbose", "Simulation", "Verbose",
       "Print debugging information to the log.",
       "--verbose"),
    _b("dump_pages", "Simulation", "Dump pages",
       "Print downloaded pages as base64 (very verbose).",
       "--dump-pages"),
    _b("write_pages", "Simulation", "Write pages",
       "Write intermediary pages to the current directory.",
       "--write-pages"),
    _b("print_traffic", "Simulation", "Print HTTP traffic",
       "Display sent and received HTTP traffic.",
       "--print-traffic"),
    _s("print_template", "Simulation", "Print templates",
       "Output templates to print, one per line. WHEN:TEMPLATE.",
       "--print", kind="text", repeat=True),

    # Workarounds
    _s("encoding", "Workarounds", "Encoding",
       "Force a specific encoding.",
       "--encoding"),
    _b("legacy_server_connect", "Workarounds", "Legacy server connect",
       "Allow HTTPS servers without RFC 5746 secure renegotiation.",
       "--legacy-server-connect"),
    _b("no_check_certificates", "Workarounds", "Skip certificate check",
       "Suppress HTTPS certificate validation.",
       "--no-check-certificates"),
    _b("prefer_insecure", "Workarounds", "Prefer insecure",
       "Use an unencrypted connection to retrieve video info.",
       "--prefer-insecure"),
    _s("add_headers", "Workarounds", "Custom headers",
       "FIELD: VALUE, one per line.",
       "--add-headers", kind="headers", repeat=True),
    _b("bidi_workaround", "Workarounds", "Bidi workaround",
       "Work around terminals lacking bidirectional text support.",
       "--bidi-workaround"),
    _s("sleep_requests", "Workarounds", "Sleep between requests",
       "Seconds to sleep during extraction.",
       "--sleep-requests"),
    _s("sleep_interval", "Workarounds", "Min sleep interval",
       "Minimum seconds to sleep before each download.",
       "--sleep-interval"),
    _s("max_sleep_interval", "Workarounds", "Max sleep interval",
       "Maximum seconds to sleep before each download.",
       "--max-sleep-interval"),
    _s("sleep_subtitles", "Workarounds", "Sleep before subtitles",
       "Seconds to sleep before each subtitle download.",
       "--sleep-subtitles"),

    # Subtitles
    _b("write_subs", "Subtitles", "Write subtitles",
       "Download subtitle files.",
       "--write-subs"),
    _b("write_auto_subs", "Subtitles", "Write auto subtitles",
       "Download automatically generated subtitles.",
       "--write-auto-subs"),
    _s("sub_format", "Subtitles", "Subtitle format",
       "Preference separated by /, e.g. srt or ass/srt/best.",
       "--sub-format", placeholder="best"),
    _s("sub_langs", "Subtitles", "Subtitle languages",
       "Comma-separated langs or regex, e.g. en.*,ja or all,-live_chat.",
       "--sub-langs", placeholder="en.*,-live_chat"),

    # Auth
    _s("username", "Authentication", "Username",
       "Account login.",
       "-u"),
    _s("password", "Authentication", "Password",
       "Account password.",
       "-p", kind="password"),
    _s("twofactor", "Authentication", "Two-factor code",
       "Two-factor authentication code.",
       "-2", kind="password"),
    _b("netrc", "Authentication", "Use .netrc",
       "Read credentials from .netrc.",
       "--netrc"),
    _s("netrc_location", "Authentication", ".netrc location",
       "Path to .netrc or its directory.",
       "--netrc-location", kind="file"),
    _s("netrc_cmd", "Authentication", ".netrc command",
       "Command that prints credentials for an extractor.",
       "--netrc-cmd"),
    _s("videopassword", "Authentication", "Video password",
       "Password for a locked video.",
       "--video-password", kind="password"),
    _s("ap_mso", "Authentication", "Adobe Pass MSO",
       "TV provider identifier for Adobe Pass.",
       "--ap-mso"),
    _s("ap_username", "Authentication", "Adobe Pass username",
       "MSO account login.",
       "--ap-username"),
    _s("ap_password", "Authentication", "Adobe Pass password",
       "MSO account password.",
       "--ap-password", kind="password"),
    _s("client_certificate", "Authentication", "Client certificate",
       "PEM client certificate, optionally including the key.",
       "--client-certificate", kind="file"),
    _s("client_certificate_key", "Authentication", "Client certificate key",
       "Private key for the client certificate.",
       "--client-certificate-key", kind="file"),
    _s("client_certificate_password", "Authentication", "Client cert password",
       "Password for an encrypted client certificate key.",
       "--client-certificate-password", kind="password"),

    # Post-processing
    _b("extract_audio", "Post-processing", "Extract audio",
       "Convert to an audio-only file (requires ffmpeg).",
       "-x"),
    _c("audio_format", "Post-processing", "Audio format",
       "Target audio format when extracting.",
       ("best", "aac", "alac", "flac", "m4a", "mp3", "opus", "vorbis", "wav"),
       "best", "--audio-format"),
    _s("audio_quality", "Post-processing", "Audio quality",
       "VBR 0 (best) to 10, or a bitrate like 192K.",
       "--audio-quality", "5"),
    _s("remux_video", "Post-processing", "Remux video",
       "Remux into another container, e.g. mp4 or aac>m4a/mkv.",
       "--remux-video"),
    _s("recode_video", "Post-processing", "Recode video",
       "Re-encode into another format. Same syntax as remux.",
       "--recode-video"),
    _s("postprocessor_args", "Post-processing", "Postprocessor args",
       "NAME:ARGS, one per line. See yt-dlp --postprocessor-args.",
       "--postprocessor-args", kind="text", repeat=True),
    _b("keep_video", "Post-processing", "Keep video",
       "Keep the intermediate video after extracting audio.",
       "-k"),
    _b("post_overwrites", "Post-processing", "Overwrite post-processed",
       "Overwrite post-processed files.",
       "--post-overwrites", True, "--no-post-overwrites"),
    _b("embed_subs", "Post-processing", "Embed subtitles",
       "Embed subtitles into mp4/webm/mkv.",
       "--embed-subs"),
    _b("embed_thumbnail", "Post-processing", "Embed thumbnail",
       "Embed the thumbnail as cover art.",
       "--embed-thumbnail"),
    _b("embed_metadata", "Post-processing", "Embed metadata",
       "Embed metadata, and chapters/infojson unless disabled.",
       "--embed-metadata"),
    _b("embed_chapters", "Post-processing", "Embed chapters",
       "Add chapter markers to the file.",
       "--embed-chapters"),
    _b("embed_info_json", "Post-processing", "Embed info JSON",
       "Attach infojson to mkv/mka files.",
       "--embed-info-json"),
    _s("parse_metadata", "Post-processing", "Parse metadata",
       "FROM:TO rules, one per line. Optional WHEN: prefix.",
       "--parse-metadata", kind="text", repeat=True),
    _s("replace_in_metadata", "Post-processing", "Replace in metadata",
       "FIELDS REGEX REPLACE, one per line.",
       "--replace-in-metadata", kind="text", repeat=True),
    _b("xattrs", "Post-processing", "Write xattrs",
       "Write Dublin Core / XDG metadata to xattrs.",
       "--xattrs"),
    _c("concat_playlist", "Post-processing", "Concat playlist",
       "Concatenate playlist videos: never, always, multi_video.",
       ("", "never", "always", "multi_video"), "", "--concat-playlist"),
    _c("fixup", "Post-processing", "Fixup policy",
       "Correct known file faults.",
       ("", "never", "warn", "detect_or_warn", "force"), "", "--fixup"),
    _s("ffmpeg_location", "Post-processing", "ffmpeg location",
       "Path to ffmpeg or its directory.",
       "--ffmpeg-location", kind="path"),
    _s("exec_cmd", "Post-processing", "Execute command",
       "Command after processing, one per line. Optional WHEN: prefix. Use %(filepath)q.",
       "--exec", kind="text", repeat=True),
    _c("convert_subs", "Post-processing", "Convert subtitles",
       "Convert downloaded subtitles.",
       ("", "ass", "lrc", "srt", "vtt", "none"), "", "--convert-subs"),
    _s("convert_thumbnails", "Post-processing", "Convert thumbnails",
       "Convert thumbnails, e.g. jpg or png/webp.",
       "--convert-thumbnails"),
    _b("split_chapters", "Post-processing", "Split chapters",
       "Split the video into files based on chapters.",
       "--split-chapters"),
    _s("remove_chapters", "Post-processing", "Remove chapters",
       "Regex of chapter titles to remove, one per line.",
       "--remove-chapters", kind="text", repeat=True),
    _b("force_keyframes_at_cuts", "Post-processing", "Keyframes at cuts",
       "Re-encode cuts so section boundaries are cleaner.",
       "--force-keyframes-at-cuts"),
    _s("use_postprocessor", "Post-processing", "Plugin postprocessors",
       "NAME[:ARGS], one per line.",
       "--use-postprocessor", kind="text", repeat=True),

    # SponsorBlock
    _s("sponsorblock_mark", "SponsorBlock", "Mark categories",
       "Create chapters for these categories, e.g. all,-preview.",
       "--sponsorblock-mark", placeholder="all,-preview"),
    _s("sponsorblock_remove", "SponsorBlock", "Remove categories",
       "Cut these categories from the file, e.g. sponsor,selfpromo,interaction.",
       "--sponsorblock-remove", placeholder="sponsor,selfpromo,interaction"),
    _s("sponsorblock_chapter_title", "SponsorBlock", "Chapter title template",
       "Template for generated SponsorBlock chapters.",
       "--sponsorblock-chapter-title"),
    _b("no_sponsorblock", "SponsorBlock", "Disable SponsorBlock",
       "Disable both mark and remove.",
       "--no-sponsorblock"),
    _s("sponsorblock_api", "SponsorBlock", "SponsorBlock API",
       "SponsorBlock API URL.",
       "--sponsorblock-api", "https://sponsor.ajay.app"),

    # Extractor
    _s("extractor_retries", "Extractor", "Extractor retries",
       "Retries for known extractor errors, or infinite.",
       "--extractor-retries", "3"),
    _b("allow_dynamic_mpd", "Extractor", "Dynamic DASH MPD",
       "Process dynamic DASH manifests.",
       "--allow-dynamic-mpd", True, "--ignore-dynamic-mpd"),
    _b("hls_split_discontinuity", "Extractor", "Split HLS discontinuities",
       "Split HLS playlists at discontinuities such as ad breaks.",
       "--hls-split-discontinuity"),
    _s("extractor_args", "Extractor", "Extractor args",
       "IE_KEY:ARGS, one per line. Example: youtube:player_client=default,ios",
       "--extractor-args", kind="text", repeat=True,
       placeholder="youtube:player_client=default,ios"),
]


QUALITY_PRESETS: list[dict[str, Any]] = [
    {"id": "best", "label": "Best", "format": "bv*+ba/b", "extract_audio": False},
    {"id": "2160", "label": "4K", "format": "bv*[height<=2160]+ba/b", "extract_audio": False},
    {"id": "1440", "label": "1440p", "format": "bv*[height<=1440]+ba/b", "extract_audio": False},
    {"id": "1080", "label": "1080p", "format": "bv*[height<=1080]+ba/b", "extract_audio": False},
    {"id": "720", "label": "720p", "format": "bv*[height<=720]+ba/b", "extract_audio": False},
    {"id": "480", "label": "480p", "format": "bv*[height<=480]+ba/b", "extract_audio": False},
    {"id": "audio", "label": "Audio", "format": "ba/b", "extract_audio": False},
    {"id": "mp3", "label": "MP3", "format": "ba[acodec^=mp3]/ba/b", "extract_audio": True, "audio_format": "mp3"},
    {"id": "m4a", "label": "M4A", "format": "ba[acodec^=aac]/ba[acodec^=mp4a.40.]/ba/b", "extract_audio": True, "audio_format": "m4a"},
    {"id": "opus", "label": "Opus", "format": "ba[acodec^=opus]/ba/b", "extract_audio": True, "audio_format": "opus"},
    {"id": "flac", "label": "FLAC", "format": "ba/b", "extract_audio": True, "audio_format": "flac"},
    {"id": "custom", "label": "Custom", "format": None},
]


OPTIONS_BY_KEY = {opt.key: opt for opt in OPTIONS}
GROUPED_OPTIONS: dict[str, list[Opt]] = {group: [] for group in GROUPS}
for _opt in OPTIONS:
    GROUPED_OPTIONS.setdefault(_opt.group, []).append(_opt)
GROUPED_OPTIONS = {group: opts for group, opts in GROUPED_OPTIONS.items() if opts}


def default_values() -> dict[str, Any]:
    from tuberip.util import default_output_dir

    values = {opt.key: opt.default for opt in OPTIONS}
    values.update(
        {
            "output_dir": default_output_dir(),
            "organize_playlists": True,
            "merge_best_audio": True,
            "queue_concurrency": 1,
            "auto_fetch": True,
            "load_config_files": False,
            "extra_args": "",
            "quality_preset": "best",
        }
    )
    return values
