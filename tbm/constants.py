# constants.py
# TorBox Manager EchoStorm Edition
# Static values only — no logic, no imports, no side effects.
# If a value might change per-run, it belongs in config.py instead.

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------

APP_NAME        = "TorBox Manager"
APP_SUBTITLE    = "EchoStorm Edition"
APP_VERSION     = "0.6.0"
LOG_FILENAME    = "TorBox_Manager_Log.txt"
CONFIG_FILENAME = "config.json"

# ---------------------------------------------------------------------------
# TorBox API
# ---------------------------------------------------------------------------

API_BASE_URL = "https://api.torbox.app/v1/api"

# Endpoint paths (appended to API_BASE_URL)
ENDPOINT_ADD_TORRENT    = "/torrents/createtorrent"
ENDPOINT_ADD_WEBDL      = "/webdl/createwebdownload"
ENDPOINT_ADD_USENET     = "/usenet/createusenetdownload"

ENDPOINT_LIST_TORRENTS  = "/torrents/mylist"
ENDPOINT_LIST_WEBDL     = "/webdl/mylist"
ENDPOINT_LIST_USENET    = "/usenet/mylist"

ENDPOINT_DL_TORRENT     = "/torrents/requestdl"
ENDPOINT_DL_WEBDL       = "/webdl/requestdl"
ENDPOINT_DL_USENET      = "/usenet/requestdl"

ENDPOINT_DEL_TORRENT    = "/torrents/controltorrent"
ENDPOINT_DEL_WEBDL      = "/webdl/controlwebdownload"
ENDPOINT_DEL_USENET     = "/usenet/controlusenetdownload"

# ---------------------------------------------------------------------------
# Queue item types
# These are the internal string keys used throughout the app.
# UI display labels and icons are defined separately below.
# ---------------------------------------------------------------------------

TYPE_TORRENT = "torrent"
TYPE_MAGNET  = "magnet"
TYPE_WEBDL   = "webdl"
TYPE_USENET  = "usenet"

# Human-readable labels for each type (used in the Type column)
TYPE_LABELS = {
    TYPE_TORRENT: "Torrent",
    TYPE_MAGNET:  "Magnet",
    TYPE_WEBDL:   "Hoster Link",
    TYPE_USENET:  "NZB",
}

# Display icons for each type (Unicode, fits any font)
TYPE_ICONS = {
    TYPE_TORRENT: "📄",
    TYPE_MAGNET:  "🧲",
    TYPE_WEBDL:   "🔗",
    TYPE_USENET:  "📰",
}

# ---------------------------------------------------------------------------
# Queue item statuses — internal flags used for logic (Download button, etc.)
# ---------------------------------------------------------------------------

STATUS_QUEUED      = "Queued"
STATUS_DOWNLOADING = "Downloading"
STATUS_READY       = "Ready"
STATUS_ERROR       = "Error"
STATUS_FETCHING    = "Fetching"   # local download in progress (worker pulling file)

# Display strings for the Status column — richer than the internal flags.
# These are what the user actually sees in the table.
STATUS_DISPLAY = {
    "cached_seeding": "Cached · Seeding",
    "cached_idle":    "Cached · Idle",
    "downloading":    "Downloading",
    "queued":         "Queued",
    "error":          "Error",
    "fetching":       "Fetching…",
}

# Status cell colors — (background, foreground) pairs
STATUS_COLORS = {
    STATUS_READY:       ("#1a3d1a", "#7cb342"),   # dark green bg, green text
    STATUS_DOWNLOADING: ("#1a2d3d", "#4a9edd"),   # dark blue bg, blue text
    STATUS_QUEUED:      ("#2a2a2a", "#888888"),   # neutral, muted
    STATUS_ERROR:       ("#3d1a1a", "#e05050"),   # dark red bg, red text
    STATUS_FETCHING:    ("#1a3d2d", "#50c8a0"),   # teal tint for local fetch
}

# ---------------------------------------------------------------------------
# Queue table column indices
# Keep these in sync with the column order defined in ui.py.
# Using named constants avoids magic numbers scattered through the codebase.
# ---------------------------------------------------------------------------

# Column indices — info columns first, action columns at the right edge.
# Change these values here only; all code uses the named constants.
COL_NAME      = 0
COL_TYPE      = 1
COL_STATUS    = 2
COL_SIZE      = 3
COL_SEEDS     = 4   # optional
COL_PEERS     = 5   # optional
COL_RATIO     = 6   # optional
COL_ETA       = 7   # optional
COL_ADDED     = 8   # optional
COL_PROGRESS  = 9
COL_DOWNLOAD  = 10
COL_DELETE    = 11

# Total column count
COL_COUNT     = 12

# Config keys for column visibility persistence
# These are the exact strings stored in config.json under "columns"
COL_VISIBILITY_KEYS = {
    COL_SEEDS:  "col_seeds",
    COL_PEERS:  "col_peers",
    COL_RATIO:  "col_ratio",
    COL_ETA:    "col_eta",
    COL_ADDED:  "col_added",
}

# Default visibility for optional columns (all on by default)
COL_VISIBILITY_DEFAULTS = {
    "col_seeds": True,
    "col_peers": True,
    "col_ratio": True,
    "col_eta":   True,
    "col_added": True,
}

# Human-readable header labels for all columns
COL_HEADERS = [
    "Name", "Type", "Status", "Size",
    "Seeds", "Peers", "Ratio", "ETA", "Added",
    "Progress", "Download", "Delete",
]

# Badge colors for Type column — dark, premium, EchoStorm palette
BADGE_COLORS = {
    "torrent": ("#1a3a5c", "#e0e0e0"),   # deep navy, light text
    "magnet":  ("#1a6b3a", "#e0e0e0"),   # hunter green, light text
    "webdl":   ("#4a2d6b", "#e0e0e0"),   # deep purple, light text
    "usenet":  ("#6b4a1a", "#e0e0e0"),   # dark amber, light text
}

# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

DEFAULT_POLL_INTERVAL_SEC     = 30   # how often PollWorker refreshes the queue
MIN_POLL_INTERVAL_SEC         = 10   # lower bound exposed in Settings dialog
MAX_POLL_INTERVAL_SEC         = 300  # upper bound exposed in Settings dialog
IDLE_POLL_INTERVAL_SEC        = 300  # interval used when window is hidden and nothing is downloading

DEFAULT_MAX_CONCURRENT_DL     = 3    # simultaneous local downloads

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

DOWNLOAD_CHUNK_SIZE = 1024 * 1024   # 1 MB — stream chunk size for DownloadWorker

# ---------------------------------------------------------------------------
# EchoStorm theme colors
# All colors are hex strings. Apply via Qt stylesheets in ui.py.
# ---------------------------------------------------------------------------

COLOR_BG            = "#181818"   # main window background — deeper black
COLOR_PANEL         = "#1f1f1f"   # left panel, log strip background
COLOR_PANEL_ALT     = "#232323"   # alternate row / subtle contrast surface
COLOR_HEADER_BAR    = "#2d1f00"   # amber-dark title bar — richer, deeper
COLOR_ACCENT        = "#7cb342"   # green — primary accent, section labels, progress
COLOR_ACCENT_DIM    = "#4a6b28"   # dimmed accent for subtle highlights
COLOR_TEXT          = "#e8e8e8"   # primary text — slightly brighter
COLOR_TEXT_MUTED    = "#666666"   # secondary / placeholder text — deeper mute
COLOR_BUTTON_BG     = "#282828"   # normal button background
COLOR_BUTTON_HOVER  = "#323232"   # button hover state
COLOR_BORDER        = "#2a2a2a"   # subtle dividers — tighter
COLOR_BORDER_BRIGHT = "#3a3a3a"   # brighter border for focused elements
COLOR_ROW_HOVER     = "#252f1a"   # row hover — very subtle green tint

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

FONT_UI_FAMILY  = "Segoe UI"
FONT_UI_SIZE    = 9            # pt — general UI
FONT_LOG_FAMILY = "Consolas"
FONT_LOG_SIZE   = 8            # pt — log strip

# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

KOFI_URL     = "https://ko-fi.com/xechostormx"
REFERRAL_URL = "https://torbox.app/subscription?referral=bd158452-a00c-4bce-be2a-593351ccaec7"

GITHUB_RELEASES_URL     = "https://github.com/Echo-Storm/TorBox_Manager/releases/latest"
GITHUB_API_LATEST_URL   = "https://api.github.com/repos/Echo-Storm/TorBox_Manager/releases/latest"
