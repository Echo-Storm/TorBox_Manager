# constants.py
# TorBox Manager EchoStorm Edition
# Static values only — no logic, no imports, no side effects.
# If a value might change per-run, it belongs in config.py instead.

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------

APP_NAME        = "TorBox Manager"
APP_SUBTITLE    = "EchoStorm Edition"
APP_VERSION     = "0.1.0"
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
# Queue item statuses
# These mirror the language TorBox uses in its API responses where possible.
# ---------------------------------------------------------------------------

STATUS_QUEUED      = "Queued"
STATUS_DOWNLOADING = "Downloading"
STATUS_READY       = "Ready"
STATUS_ERROR       = "Error"
STATUS_FETCHING    = "Fetching"   # local download in progress (worker pulling file)

# ---------------------------------------------------------------------------
# Queue table column indices
# Keep these in sync with the column order defined in ui.py.
# Using named constants avoids magic numbers scattered through the codebase.
# ---------------------------------------------------------------------------

COL_NAME      = 0
COL_TYPE      = 1
COL_STATUS    = 2
COL_SIZE      = 3
COL_PROGRESS  = 4
COL_DOWNLOAD  = 5
COL_DELETE    = 6

# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

DEFAULT_POLL_INTERVAL_SEC = 30   # how often PollWorker refreshes the queue
MIN_POLL_INTERVAL_SEC     = 10   # lower bound exposed in Settings dialog
MAX_POLL_INTERVAL_SEC     = 300  # upper bound exposed in Settings dialog

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

DOWNLOAD_CHUNK_SIZE = 1024 * 1024   # 1 MB — stream chunk size for DownloadWorker

# ---------------------------------------------------------------------------
# EchoStorm theme colors
# All colors are hex strings. Apply via Qt stylesheets in ui.py.
# ---------------------------------------------------------------------------

COLOR_BG            = "#1e1e1e"   # main window background
COLOR_PANEL         = "#252525"   # left panel, log strip background
COLOR_HEADER_BAR    = "#3d2b00"   # amber-dark title bar
COLOR_ACCENT        = "#7cb342"   # green — primary accent, section labels, progress
COLOR_TEXT          = "#e0e0e0"   # primary text
COLOR_TEXT_MUTED    = "#888888"   # secondary / placeholder text
COLOR_BUTTON_BG     = "#2e2e2e"   # normal button background
COLOR_BUTTON_HOVER  = "#383838"   # button hover state
COLOR_BORDER        = "#333333"   # subtle dividers

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

KOFI_URL = "https://ko-fi.com/xechostormx"
