# ui.py
# TorBox Manager EchoStorm Edition
#
# MainWindow — the entire visible application.
# Layout mirrors Echo Audio Converter:
#   - Fixed left panel (~280px): add buttons, queue controls
#   - Right side: queue table (top) + log strip (bottom) via QSplitter
#   - Full-width status bar: state text | Download All | donate
#
# Threading rules (same as EAC):
#   - Workers run in QThreadPool; they never touch widgets directly.
#   - All widget updates happen in slots connected to worker signals,
#     which Qt delivers on the main thread automatically.
#
# Assumptions about TorBox API field names (verify against live responses):
#   item["id"]             — int, unique per source type
#   item["name"]           — str, display name
#   item["source_type"]    — str, injected by api.list_all()
#   item["size"]           — int, bytes (may be 0 if unknown)
#   item["progress"]       — int, 0–100
#   item["download_state"] — str, see _torbox_state_to_status() below
#   item["files"]          — list of dicts (torrents only), each with "id", "name"
#
import os
import re
import sys
from urllib.parse import unquote
import webbrowser
from datetime import datetime

from PyQt6.QtCore    import Qt, QThreadPool, QTimer
from PyQt6.QtGui     import QAction, QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QMenu,
    QMessageBox,
    QHeaderView,
)

import api
from config   import load_config, save_config, is_configured
from constants import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    BADGE_COLORS,
    COLOR_ACCENT,
    COLOR_ACCENT_DIM,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_BORDER_BRIGHT,
    COLOR_BUTTON_BG,
    COLOR_BUTTON_HOVER,
    COLOR_HEADER_BAR,
    COLOR_PANEL,
    COLOR_PANEL_ALT,
    COLOR_ROW_HOVER,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    DEFAULT_MAX_CONCURRENT_DL,
    IDLE_POLL_INTERVAL_SEC,
    STATUS_COLORS,
    STATUS_DISPLAY,
    COL_ADDED,
    COL_COUNT,
    COL_DELETE,
    COL_DOWNLOAD,
    COL_ETA,
    COL_NAME,
    COL_PEERS,
    COL_PROGRESS,
    COL_RATIO,
    COL_SEEDS,
    COL_SIZE,
    COL_STATUS,
    COL_TYPE,
    COL_HEADERS,
    COL_VISIBILITY_DEFAULTS,
    COL_VISIBILITY_KEYS,
    DOWNLOAD_CHUNK_SIZE,
    FONT_LOG_FAMILY,
    FONT_LOG_SIZE,
    FONT_UI_FAMILY,
    FONT_UI_SIZE,
    GITHUB_RELEASES_URL,
    KOFI_URL,
    STATUS_DOWNLOADING,
    STATUS_ERROR,
    STATUS_FETCHING,
    STATUS_QUEUED,
    STATUS_READY,
    TYPE_ICONS,
    TYPE_LABELS,
)
from dialogs  import AboutDialog, AddLinkDialog, AddMagnetDialog, FilePickerDialog, SettingsDialog
from worker   import AddWorker, DeleteWorker, DownloadWorker, LinkRequestWorker, PollWorker, UpdateCheckWorker


# ---------------------------------------------------------------------------
# Main stylesheet
# ---------------------------------------------------------------------------

MAIN_STYLE = f"""
    QMainWindow, QWidget {{
        background-color: {COLOR_BG};
        color: {COLOR_TEXT};
        font-family: {FONT_UI_FAMILY};
        font-size: {FONT_UI_SIZE}pt;
    }}
    QSplitter::handle {{
        background-color: {COLOR_BORDER};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}
    QTableWidget {{
        background-color: {COLOR_PANEL};
        color: {COLOR_TEXT};
        gridline-color: {COLOR_BORDER};
        border: none;
        selection-background-color: {COLOR_ROW_HOVER};
        alternate-background-color: {COLOR_PANEL_ALT};
        outline: none;
    }}
    QTableWidget::item {{
        padding: 2px 6px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: {COLOR_ROW_HOVER};
        color: {COLOR_TEXT};
    }}
    QTableWidget::item:hover {{
        background-color: {COLOR_ROW_HOVER};
    }}
    QHeaderView::section {{
        background-color: {COLOR_PANEL};
        color: {COLOR_ACCENT};
        border: none;
        border-top: 1px solid {COLOR_BORDER_BRIGHT};
        border-right: 1px solid {COLOR_BORDER};
        border-bottom: 1px solid {COLOR_BORDER_BRIGHT};
        padding: 5px 6px;
        font-size: 8pt;
        font-weight: bold;
        letter-spacing: 1px;
    }}
    QHeaderView::section:hover {{
        background-color: {COLOR_PANEL_ALT};
        color: {COLOR_ACCENT};
    }}
    QPushButton {{
        background-color: {COLOR_BUTTON_BG};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BUTTON_HOVER};
        border-color: {COLOR_ACCENT_DIM};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_ACCENT};
        color: #000000;
    }}
    QPushButton:disabled {{
        color: #3a3a3a;
        border-color: {COLOR_BORDER};
        background-color: {COLOR_BG};
    }}
    QProgressBar {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        text-align: center;
        color: {COLOR_TEXT};
        font-size: 8pt;
        font-weight: bold;
        min-height: 20px;
    }}
    QProgressBar::chunk {{
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLOR_ACCENT_DIM},
            stop:1 {COLOR_ACCENT}
        );
        border-radius: 4px;
        margin: 1px;
    }}
    QScrollBar:vertical {{
        background-color: {COLOR_BG};
        width: 8px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: #303030;
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {COLOR_ACCENT_DIM};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background-color: {COLOR_BG};
        height: 8px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background-color: #303030;
        border-radius: 4px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {COLOR_ACCENT_DIM};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
"""

_PROGRESS_BAR_DONE_STYLE = f"""
    QProgressBar {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_ACCENT};
        border-radius: 4px;
        text-align: center;
        color: #000000;
        font-size: 8pt;
        font-weight: bold;
        min-height: 20px;
    }}
    QProgressBar::chunk {{
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLOR_ACCENT_DIM}, stop:1 {COLOR_ACCENT}
        );
        border-radius: 4px;
        margin: 1px;
    }}
"""

_PROGRESS_BAR_ACTIVE_STYLE = f"""
    QProgressBar {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER_BRIGHT};
        border-radius: 4px;
        text-align: center;
        color: {COLOR_TEXT};
        font-size: 8pt;
        font-weight: bold;
        min-height: 20px;
    }}
    QProgressBar::chunk {{
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {COLOR_ACCENT_DIM}, stop:1 {COLOR_ACCENT}
        );
        border-radius: 4px;
        margin: 1px;
    }}
"""



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_size(size_bytes) -> str:
    """Convert a byte count to a human-readable string."""
    try:
        b = int(size_bytes)
    except (TypeError, ValueError):
        return "—"
    if b <= 0:
        return "—"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024 ** 3:.2f} GB"


def _parse_progress(item: dict) -> int:
    """
    Normalize TorBox progress to an integer 0–100.

    TorBox may return progress as an integer 0–100 or a float 0.0–1.0
    depending on item type and state. Values strictly between 0 and 1
    are treated as fractions and multiplied by 100. This handles both
    formats without requiring a live API check.

    Examples:
        0      → 0      (not started)
        1      → 1      (1% as integer)
        0.01   → 1      (1% as float fraction)
        0.5    → 50     (50% as float fraction)
        50     → 50     (50% as integer)
        100    → 100    (complete)
    """
    raw = item.get("progress", 0)
    try:
        p = float(raw)
        if 0 < p < 1:       # float fraction — multiply up
            p = p * 100
        return max(0, min(100, int(round(p))))
    except (TypeError, ValueError):
        return 0


def _torbox_state_to_status(item: dict) -> str:
    """
    Return the internal STATUS_* constant for an item.
    Used for logic decisions (enable Download button, etc.)
    For display text use _torbox_display_status().
    """
    if item.get("cached") is True:
        return STATUS_READY

    download_state = str(item.get("download_state", "")).lower()

    if any(s in download_state for s in ("error", "missing", "failed")):
        return STATUS_ERROR

    if any(s in download_state for s in ("downloading", "checking",
                                          "moving", "fetching", "metadl")):
        return STATUS_DOWNLOADING

    return STATUS_QUEUED


def _torbox_display_status(item: dict) -> str:
    """
    Return a human-readable compound status string for the Status column.
    Distinguishes cached+seeding from cached+idle, which STATUS_READY alone
    does not.
    """
    if item.get("cached") is True:
        state = str(item.get("download_state", "")).lower()
        if any(s in state for s in ("uploading", "seeding")):
            return STATUS_DISPLAY["cached_seeding"]
        return STATUS_DISPLAY["cached_idle"]

    download_state = str(item.get("download_state", "")).lower()

    if any(s in download_state for s in ("error", "missing", "failed")):
        return STATUS_DISPLAY["error"]

    if any(s in download_state for s in ("downloading", "checking",
                                          "moving", "fetching", "metadl")):
        return STATUS_DISPLAY["downloading"]

    return STATUS_DISPLAY["queued"]


def _row_key(item: dict) -> str:
    """Stable unique key for a queue item — used to match rows across polls."""
    return f"{item.get('source_type', 'unknown')}:{item.get('id', 0)}"


def _fmt_eta(seconds) -> str:
    """Convert ETA in seconds to a readable string."""
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return "—"
    if s <= 0:
        return "—"
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    if s < 86400:
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h}h {m}m"
    return f"{s // 86400}d"


def _fmt_added(iso_str: str) -> str:
    """Convert an ISO8601 timestamp to a short local time string."""
    if not iso_str:
        return "—"
    try:
        from datetime import timezone
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local = dt.astimezone()
        return local.strftime("%m/%d %H:%M")
    except (ValueError, OSError):
        return iso_str[:16]


def _make_badge(source_type: str) -> QLabel:
    """Return a styled QLabel badge for the Type column."""
    label_text = TYPE_ICONS.get(source_type, "?") + "  " + TYPE_LABELS.get(source_type, source_type.capitalize())
    bg, fg     = BADGE_COLORS.get(source_type, ("#333333", "#e0e0e0"))
    badge      = QLabel(label_text)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(
        f"background-color: {bg}; color: {fg}; "
        f"border-radius: 3px; padding: 2px 8px; "
        f"font-size: 8pt; font-weight: bold;"
    )
    return badge


# ---------------------------------------------------------------------------
# Left panel section label
# ---------------------------------------------------------------------------

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {COLOR_ACCENT_DIM}; font-size: 7pt; font-weight: bold; "
        f"letter-spacing: 2px; padding: 10px 0 4px 0; background: transparent;"
    )
    return lbl


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    def __init__(self, config: dict):
        super().__init__()
        self.config      = config
        self._pool       = QThreadPool.globalInstance()
        self._poll_timer = QTimer(self)
        # Maps row_key → row index in the table
        self._row_index: dict[str, int] = {}
        # Maps row_key → item dict (refreshed on every poll)
        self._row_items: dict[str, dict] = {}
        # Tracks which row_keys currently have a DownloadWorker running
        self._downloading: dict[str, int] = {}  # key -> number of active download workers
        # Pending downloads waiting for a concurrency slot (FIFO)
        self._download_queue: list[tuple[str, dict]] = []
        # Keys deleted by the user — suppressed for 2 poll cycles so they
        # don't reappear before TorBox finishes processing the delete.
        self._deleted_keys: set[str] = set()
        # All log lines stored as (level, formatted_string) for filter re-render
        self._log_lines: list[tuple[str, str]] = []

        self._build_ui()
        self._build_tray()
        self._setup_timer()

        # Open Settings immediately if API key is missing
        if not is_configured(self.config):
            self._log("No API key configured — please set one in Settings.", "WARN")
            self._on_settings()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(f"{APP_NAME} {APP_SUBTITLE}  •  v{APP_VERSION}")
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(MAIN_STYLE)

        # Restore saved geometry; fall back to maximized default
        saved_geom = self.config.get("window_geometry", "")
        if saved_geom:
            try:
                from PyQt6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromHex(saved_geom.encode()))
            except Exception:
                self.resize(1200, 700)
                self.setWindowState(Qt.WindowState.WindowMaximized)
        else:
            self.resize(1200, 700)
            self.setWindowState(Qt.WindowState.WindowMaximized)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Header bar — full width, no inset
        root_layout.addWidget(self._build_header())

        # Body: left panel + right frame side by side.
        # right_frame wraps the queue/log splitter AND the status bar widget
        # together so a single border-right runs the full height of the window.
        # The 12px right margin on body_container gives the border breathing room
        # against the window edge — mirroring the visual weight of the left panel.
        right_frame = QWidget()
        right_frame.setStyleSheet(f"""
            QWidget#right_frame {{
                border-right: 2px solid {COLOR_BORDER_BRIGHT};
                background-color: transparent;
            }}
        """)
        right_frame.setObjectName("right_frame")
        right_frame_layout = QVBoxLayout(right_frame)
        right_frame_layout.setContentsMargins(0, 0, 0, 0)
        right_frame_layout.setSpacing(0)
        right_frame_layout.addWidget(self._build_right_panel(), stretch=1)
        right_frame_layout.addWidget(self._build_status_bar())

        body_splitter = QSplitter(Qt.Orientation.Horizontal)
        body_splitter.setHandleWidth(2)
        body_splitter.addWidget(self._build_left_panel())
        body_splitter.addWidget(right_frame)
        body_splitter.setSizes([220, 980])
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)

        body_container = QWidget()
        body_container.setStyleSheet(f"background: {COLOR_PANEL};")
        body_outer = QHBoxLayout(body_container)
        body_outer.setContentsMargins(0, 0, 12, 0)
        body_outer.setSpacing(0)
        body_outer.addWidget(body_splitter)

        root_layout.addWidget(body_container, stretch=1)

    def _build_header(self) -> QWidget:
        """
        Futuristic header bar.
        Layout: [v0.2.0] ——————— | TORBOX MANAGER | ——————— [ECHOSTORM EDITION]
        Version left, subtitle right, both small and dimmed.
        Vertical bar separators flank the title.
        Full-width accent lines connect everything.
        """
        outer = QWidget()
        outer.setFixedHeight(72)
        outer.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_PANEL};
                border-top: 1px solid {COLOR_ACCENT};
                border-bottom: 2px solid {COLOR_ACCENT};
            }}
        """)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        bar = QWidget()
        bar.setStyleSheet(f"background-color: {COLOR_PANEL}; border: none;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left — version number, small, dimmed accent
        version = QLabel(f"v{APP_VERSION}")
        version.setFixedWidth(52)
        version.setStyleSheet(f"""
            color: {COLOR_ACCENT};
            font-size: 7pt;
            font-weight: bold;
            letter-spacing: 2px;
            border: none;
        """)
        version.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(version)

        # Left accent line — runs from version to left separator bar
        left_line = QWidget()
        left_line.setFixedHeight(1)
        left_line.setStyleSheet(f"background-color: {COLOR_ACCENT_DIM}; border: none;")
        layout.addWidget(left_line, stretch=1)

        # Left vertical separator bar
        left_sep = QLabel("  |  ")
        left_sep.setStyleSheet(f"""
            color: {COLOR_ACCENT_DIM};
            font-size: 16pt;
            font-weight: 100;
            border: none;
            padding: 8px 0;
            letter-spacing: 0px;
        """)
        left_sep.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(left_sep)

        # Center title — white for maximum legibility, tight tracking, heavy weight
        title = QLabel(APP_NAME.upper())
        title.setFont(QFont("Segoe UI Semibold", 32, QFont.Weight.Black))
        title.setStyleSheet(f"""
            color: #c8c8c8;
            letter-spacing: 6px;
            border: none;
            padding: 0 8px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Right vertical separator bar
        right_sep = QLabel("  |  ")
        right_sep.setStyleSheet(f"""
            color: {COLOR_ACCENT_DIM};
            font-size: 16pt;
            font-weight: 100;
            border: none;
            padding: 8px 0;
            letter-spacing: 0px;
        """)
        right_sep.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(right_sep)

        # Right accent line — runs from right separator to subtitle
        right_line = QWidget()
        right_line.setFixedHeight(1)
        right_line.setStyleSheet(f"background-color: {COLOR_ACCENT_DIM}; border: none;")
        layout.addWidget(right_line, stretch=1)

        # Right — EchoStorm Edition, small, dimmed, right-aligned
        subtitle = QLabel(APP_SUBTITLE.upper())
        subtitle.setFixedWidth(150)
        subtitle.setStyleSheet(f"""
            color: {COLOR_ACCENT_DIM};
            font-size: 6pt;
            font-weight: bold;
            letter-spacing: 3px;
            border: none;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(subtitle)

        outer_layout.addWidget(bar)
        return outer

    def _build_left_panel(self) -> QWidget:
        """Fixed-width left panel: add buttons + queue controls + settings."""
        panel = QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_PANEL};
                border-right: 1px solid {COLOR_BORDER_BRIGHT};
            }}
            QPushButton {{
                background-color: {COLOR_BUTTON_BG};
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-left: 2px solid transparent;
                border-radius: 3px;
                padding: 5px 10px 5px 10px;
                text-align: left;
                font-size: 9pt;
                margin: 0px 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PANEL_ALT};
                border: 1px solid {COLOR_BORDER_BRIGHT};
                border-left: 2px solid {COLOR_ACCENT};
                color: {COLOR_TEXT};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_BG};
                border-left: 2px solid {COLOR_ACCENT};
                color: {COLOR_ACCENT};
            }}
            QPushButton#settings_btn {{
                background-color: transparent;
                color: {COLOR_TEXT_MUTED};
                border: none;
                border-top: 1px solid {COLOR_BORDER};
                border-left: 2px solid transparent;
                border-radius: 0px;
                padding: 8px 10px 8px 12px;
                text-align: left;
                font-size: 8pt;
                margin: 0px;
            }}
            QPushButton#settings_btn:hover {{
                background-color: {COLOR_PANEL_ALT};
                border-top: 1px solid {COLOR_BORDER};
                border-left: 2px solid {COLOR_ACCENT_DIM};
                color: {COLOR_TEXT};
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(3)

        # ---- ADD ----
        layout.addWidget(_section_label("  Add"))

        for label, slot in [
            ("🧲  Add Magnet",      self._on_add_magnet),
            ("📄  Add Torrent",     self._on_add_torrent),
            ("🔗  Add Hoster Link", self._on_add_link),
            ("📰  Add NZB",         self._on_add_nzb),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(30)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        # ---- QUEUE ----
        layout.addWidget(_section_label("  Queue"))

        self._refresh_btn = QPushButton("↻  Refresh Now")
        self._refresh_btn.setMinimumHeight(28)
        self._refresh_btn.clicked.connect(self._on_refresh)
        layout.addWidget(self._refresh_btn)

        clear_done_btn = QPushButton("✓  Clear Completed")
        clear_done_btn.setMinimumHeight(28)
        clear_done_btn.clicked.connect(self._on_clear_done)
        layout.addWidget(clear_done_btn)

        clear_all_btn = QPushButton("✕  Clear All")
        clear_all_btn.setMinimumHeight(28)
        clear_all_btn.clicked.connect(self._on_clear_all)
        layout.addWidget(clear_all_btn)

        layout.addStretch()

        # ---- SETTINGS — differentiated bottom button ----
        settings_btn = QPushButton("⚙   Settings")
        settings_btn.setObjectName("settings_btn")
        settings_btn.setMinimumHeight(34)
        settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(settings_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        """Right side: queue table (top) + log strip (bottom)."""
        right = QWidget()
        right.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_queue_table(), stretch=1)

        log_strip = self._build_log_strip()
        log_strip.setFixedHeight(140)
        layout.addWidget(log_strip)
        return right

    def _build_queue_table(self) -> QWidget:
        """
        QTableWidget with one row per queued TorBox item.
        Core columns always visible. Optional columns toggled via right-click header.
        """
        self._table = QTableWidget()
        self._table.setColumnCount(COL_COUNT)
        self._table.setHorizontalHeaderLabels(COL_HEADERS)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(COL_NAME,     QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_TYPE,     QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_STATUS,   QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_SIZE,     QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_SEEDS,    QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_PEERS,    QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_RATIO,    QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_ETA,      QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_ADDED,    QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_PROGRESS, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_DOWNLOAD, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_DELETE,   QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(COL_TYPE,     110)
        self._table.setColumnWidth(COL_STATUS,   110)
        self._table.setColumnWidth(COL_SIZE,     80)
        self._table.setColumnWidth(COL_SEEDS,    60)
        self._table.setColumnWidth(COL_PEERS,    60)
        self._table.setColumnWidth(COL_RATIO,    60)
        self._table.setColumnWidth(COL_ETA,      70)
        self._table.setColumnWidth(COL_ADDED,    110)
        self._table.setColumnWidth(COL_PROGRESS, 160)
        self._table.setColumnWidth(COL_DOWNLOAD, 90)
        self._table.setColumnWidth(COL_DELETE,   62)

        self._table.verticalHeader().setDefaultSectionSize(36)

        # Right-click header for column visibility toggle
        hdr.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hdr.customContextMenuRequested.connect(self._on_header_context_menu)

        # Right-click rows for context menu
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_row_context_menu)

        # Apply saved column visibility from config
        self._apply_column_visibility()

        return self._table

    def _apply_column_visibility(self):
        """Show/hide optional columns based on config."""
        col_config = self.config.get("columns", {})
        for col_idx, config_key in COL_VISIBILITY_KEYS.items():
            visible = col_config.get(config_key,
                      COL_VISIBILITY_DEFAULTS.get(config_key, True))
            self._table.setColumnHidden(col_idx, not visible)

    def _on_header_context_menu(self, pos):
        """Right-click on column header — show checkable visibility menu."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLOR_PANEL};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
            }}
            QMenu::item {{
                padding: 4px 20px 4px 28px;
            }}
            QMenu::item:selected {{
                background-color: {COLOR_ACCENT};
                color: #000000;
            }}
            QMenu::indicator {{
                width: 14px;
                height: 14px;
                margin-left: 6px;
            }}
            QMenu::indicator:checked {{
                background-color: {COLOR_ACCENT};
                border: 1px solid {COLOR_ACCENT};
                border-radius: 2px;
            }}
            QMenu::indicator:unchecked {{
                background-color: {COLOR_PANEL};
                border: 1px solid {COLOR_BORDER};
                border-radius: 2px;
            }}
        """)

        col_config = self.config.get("columns", {})
        label_map  = {
            COL_SEEDS: "Seeds",
            COL_PEERS: "Peers",
            COL_RATIO: "Ratio",
            COL_ETA:   "ETA",
            COL_ADDED: "Added",
        }

        actions = {}
        for col_idx, label in label_map.items():
            config_key = COL_VISIBILITY_KEYS[col_idx]
            visible    = col_config.get(config_key,
                         COL_VISIBILITY_DEFAULTS.get(config_key, True))
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(visible)
            actions[action] = (col_idx, config_key)

        chosen = menu.exec(self._table.horizontalHeader().mapToGlobal(pos))
        if chosen and chosen in actions:
            col_idx, config_key = actions[chosen]
            new_visible = chosen.isChecked()
            self._table.setColumnHidden(col_idx, not new_visible)
            if "columns" not in self.config:
                self.config["columns"] = dict(COL_VISIBILITY_DEFAULTS)
            self.config["columns"][config_key] = new_visible
            save_config(self.config)
            self._log(f"Column '{chosen.text()}' {'shown' if new_visible else 'hidden'} — saved.")

    def _on_row_context_menu(self, pos):
        """Right-click on a queue row — Copy name, Copy link, Open in browser."""
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        name_cell = self._table.item(row, COL_NAME)
        if not name_cell:
            return
        key  = name_cell.data(Qt.ItemDataRole.UserRole)
        item = self._row_items.get(key)
        if not item:
            return

        name        = item.get("name", "")
        source_type = item.get("source_type", "")
        status      = _torbox_state_to_status(item)

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLOR_PANEL};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
            }}
            QMenu::item:selected {{
                background-color: {COLOR_ACCENT};
                color: #000000;
            }}
        """)

        copy_name_action = QAction("Copy Name", self)
        copy_name_action.triggered.connect(
            lambda: QApplication.clipboard().setText(name)
        )
        menu.addAction(copy_name_action)

        if status == STATUS_READY:
            copy_link_action = QAction("Copy Download Link", self)
            copy_link_action.triggered.connect(
                lambda: self._request_link(item, action="copy")
            )
            menu.addAction(copy_link_action)

            if source_type == "webdl":
                open_action = QAction("Open in Browser", self)
                open_action.triggered.connect(
                    lambda: self._request_link(item, action="open")
                )
                menu.addAction(open_action)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _request_link(self, item: dict, action: str):
        """Dispatch a LinkRequestWorker; on success copy URL or open in browser."""
        self._log(f"Requesting download link for {item.get('name', '?')}…")
        worker = LinkRequestWorker(self.config.get("api_key", ""), item)
        if action == "copy":
            worker.signals.finished.connect(
                lambda url: (
                    QApplication.clipboard().setText(url),
                    self._log(f"Link copied to clipboard.")
                )
            )
        else:
            worker.signals.finished.connect(
                lambda url: (
                    webbrowser.open(url),
                    self._log(f"Opened in browser.")
                )
            )
        worker.signals.error.connect(
            lambda msg: self._log(f"Could not get link: {msg}", "ERROR")
        )
        self._pool.start(worker)

    def _try_start_queued(self):
        """Start pending downloads from the queue as concurrency slots free up."""
        max_dl = self.config.get("max_concurrent_downloads", DEFAULT_MAX_CONCURRENT_DL)
        while self._download_queue:
            if sum(self._downloading.values()) >= max_dl:
                break
            key, _ = self._download_queue.pop(0)
            item = self._row_items.get(key)
            if not item:
                continue
            self._start_download(key, item)

    def _update_poll_interval(self):
        """Switch to idle (slow) poll when minimised with no active downloads."""
        base = self.config.get("poll_interval", 30)
        if self.isHidden() and not self._downloading:
            interval = max(base, IDLE_POLL_INTERVAL_SEC)
        else:
            interval = base
        self._poll_timer.setInterval(interval * 1000)

    def _build_log_strip(self) -> QWidget:
        """Monospace timestamped log at the bottom of the right panel."""
        container = QWidget()
        container.setObjectName("log_container")
        container.setStyleSheet(f"""
            QWidget#log_container {{
                background-color: {COLOR_PANEL};
                border-right: 2px solid {COLOR_BORDER_BRIGHT};
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Log header — same visual weight as the queue table column header bar
        header_row = QWidget()
        header_row.setObjectName("log_header_row")
        header_row.setFixedHeight(26)
        header_row.setStyleSheet(f"""
            QWidget#log_header_row {{
                background-color: {COLOR_PANEL};
                border-top: 1px solid {COLOR_BORDER_BRIGHT};
                border-bottom: 1px solid {COLOR_BORDER_BRIGHT};
            }}
        """)
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(8, 0, 8, 0)
        header_layout.setSpacing(0)

        header_label = QLabel("LOG")
        header_label.setStyleSheet(f"""
            color: {COLOR_ACCENT};
            font-size: 8pt;
            font-weight: bold;
            letter-spacing: 3px;
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        # "errors only" filter toggle — small, right-aligned, visually quiet
        self._log_filter_btn = QPushButton("errors only")
        self._log_filter_btn.setCheckable(True)
        self._log_filter_btn.setChecked(False)
        self._log_filter_btn.setFixedHeight(16)
        self._log_filter_btn.setFixedWidth(68)
        self._log_filter_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-radius: 2px;
                font-size: 7pt;
                letter-spacing: 0.5px;
                padding: 0 4px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_BORDER_BRIGHT};
                color: {COLOR_TEXT};
            }}
            QPushButton:checked {{
                color: {COLOR_ACCENT};
                border: 1px solid {COLOR_ACCENT_DIM};
            }}
        """)
        self._log_filter_btn.toggled.connect(self._on_log_filter_toggled)
        header_layout.addWidget(self._log_filter_btn)

        layout.addWidget(header_row)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont(FONT_LOG_FAMILY, FONT_LOG_SIZE))
        self._log_view.setStyleSheet(
            f"background-color: {COLOR_BG}; color: #888888; border: none;"
        )
        self._log_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self._log_view)

        return container

    def _on_log_filter_toggled(self, checked: bool):
        """Re-render the log view showing all lines or errors/warnings only."""
        self._log_view.clear()
        for level, line in self._log_lines:
            if checked and level not in ("WARN", "ERROR"):
                continue
            self._log_view.append(line)
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _build_status_bar(self) -> QWidget:
        """Status bar as a plain QWidget — returned and added to right_frame layout.

        Using a plain widget instead of QMainWindow.setStatusBar() means the
        right_frame container's border-right runs through it uninterrupted,
        giving a single continuous vertical line from header to window bottom.
        """
        bar = QWidget()
        bar.setFixedHeight(32)
        bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_PANEL};
                border-top: 1px solid {COLOR_BORDER_BRIGHT};
            }}
        """)

        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 0, 8, 0)
        bar_layout.setSpacing(0)

        # Status dot
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(
            f"color: {COLOR_ACCENT}; font-size: 8pt; background: transparent; border: none;"
        )
        bar_layout.addWidget(self._status_dot)

        # Status text — stretches to fill
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 8pt; background: transparent; "
            f"border: none; padding-left: 6px;"
        )
        bar_layout.addWidget(self._status_label, stretch=1)

        # Update available button — hidden until an update is detected
        self._update_btn = QPushButton("⬆  Update available")
        self._update_btn.setFixedHeight(22)
        self._update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT_DIM};
                color: #ffffff;
                border: none;
                border-radius: 3px;
                font-size: 8pt;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT};
                color: #000000;
            }}
        """)
        self._update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_btn.hide()
        bar_layout.addWidget(self._update_btn)
        bar_layout.addSpacing(6)

        # Download All — outline at rest, fills green on hover
        dl_all_btn = QPushButton("⬇  Download All")
        dl_all_btn.setFixedHeight(22)
        dl_all_btn.setFixedWidth(118)
        dl_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                font-size: 8pt;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT};
                color: #000000;
                border-color: {COLOR_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT};
                color: #000000;
            }}
        """)
        dl_all_btn.clicked.connect(self._on_download_all)
        bar_layout.addWidget(dl_all_btn)

        # 1px divider with breathing room either side
        bar_layout.addSpacing(8)
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setFixedHeight(16)
        sep.setStyleSheet(f"background-color: {COLOR_BORDER_BRIGHT}; border: none;")
        bar_layout.addWidget(sep)
        bar_layout.addSpacing(8)

        # Ko-fi donate link
        kofi_btn = QPushButton("♥  donate")
        kofi_btn.setFixedHeight(22)
        kofi_btn.setFixedWidth(66)
        kofi_btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLOR_ACCENT_DIM};
                font-size: 8pt;
                border: none;
                background: transparent;
                padding: 0 4px;
            }}
            QPushButton:hover {{
                color: {COLOR_ACCENT};
            }}
        """)
        kofi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kofi_btn.clicked.connect(lambda: webbrowser.open(KOFI_URL))
        bar_layout.addWidget(kofi_btn)

        return bar

    def _build_tray(self):
        """System tray icon with Open / About / Restart / Quit menu."""
        self._tray = QSystemTrayIcon(self)

        # Load icon — graceful fallback if asset is missing
        from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
        icon_path = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
                                 "assets", "tray_icon.png")
        if os.path.isfile(icon_path):
            icon = QIcon(icon_path)
        else:
            # Generate a minimal placeholder icon programmatically
            px = QPixmap(32, 32)
            px.fill(QColor("#1e1e1e"))
            painter = QPainter(px)
            painter.setPen(QColor(COLOR_ACCENT))
            painter.setFont(QFont(FONT_UI_FAMILY, 16, QFont.Weight.Bold))
            painter.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "▼")
            painter.end()
            icon = QIcon(px)

        self._tray.setIcon(icon)
        self._tray.setToolTip(f"{APP_NAME} {APP_SUBTITLE}")

        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLOR_PANEL};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
            }}
            QMenu::item:selected {{
                background-color: {COLOR_ACCENT};
                color: #000000;
            }}
        """)

        open_action    = QAction("Open",    self)
        about_action   = QAction("About",   self)
        restart_action = QAction("Restart", self)
        quit_action    = QAction("Quit",    self)

        open_action.triggered.connect(self._tray_show)
        about_action.triggered.connect(self._on_about)
        restart_action.triggered.connect(self._tray_restart)
        quit_action.triggered.connect(self._tray_quit)

        menu.addAction(open_action)
        menu.addAction(about_action)
        menu.addSeparator()
        menu.addAction(restart_action)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _setup_timer(self):
        """Start the recurring poll timer using the configured interval."""
        interval_ms = self.config.get("poll_interval", 30) * 1000
        self._poll_timer.setInterval(interval_ms)
        self._poll_timer.timeout.connect(self._submit_poll)
        self._poll_timer.start()
        # Also do an immediate poll on startup if we have a key
        if is_configured(self.config):
            QTimer.singleShot(500, self._submit_poll)
        # Check for updates a few seconds after startup — silent, background only
        QTimer.singleShot(3000, self._check_for_update)

    # -----------------------------------------------------------------------
    # Add button slots
    # -----------------------------------------------------------------------

    def _on_add_magnet(self):
        dlg = AddMagnetDialog(self)
        if dlg.exec():
            link    = dlg.magnet_link()
            api_key = self.config.get("api_key", "")
            self._log(f"Adding magnet: {link[:60]}{'...' if len(link) > 60 else ''}")
            self._submit_add(lambda: api.add_magnet(api_key, link), "magnet")

    def _on_add_torrent(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Torrent File", "", "Torrent Files (*.torrent)"
        )
        if not path:
            return
        api_key = self.config.get("api_key", "")
        self._log(f"Adding torrent: {os.path.basename(path)}")
        self._submit_add(lambda: api.add_torrent_file(api_key, path), "torrent")

    def _on_add_link(self):
        dlg = AddLinkDialog(self)
        if dlg.exec():
            api_key = self.config.get("api_key", "")
            urls = dlg.urls()
            for url in urls:
                self._log(f"Adding hoster link: {url[:60]}{'...' if len(url) > 60 else ''}")
                self._submit_add(
                    (lambda u: lambda: api.add_hoster_link(api_key, u))(url),
                    "hoster link"
                )

    def _on_add_nzb(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select NZB File", "", "NZB Files (*.nzb)"
        )
        if not path:
            return
        api_key = self.config.get("api_key", "")
        self._log(f"Adding NZB: {os.path.basename(path)}")
        self._submit_add(lambda: api.add_nzb_file(api_key, path), "NZB")

    def _submit_add(self, add_fn, item_type: str):
        """Dispatch an AddWorker to the thread pool for a single add operation."""
        self._set_status(f"Adding {item_type}...")
        worker = AddWorker(add_fn, item_type)
        worker.signals.finished.connect(
            lambda ok, detail, t=item_type: self._on_add_finished(ok, detail, t)
        )
        worker.signals.status.connect(self._set_status)
        self._pool.start(worker)

    def _on_add_finished(self, success: bool, detail: str, item_type: str):
        """Slot — called on main thread when AddWorker completes."""
        if success:
            self._log(f"{item_type.capitalize()} added successfully: {detail}")
            self._set_status(f"{item_type.capitalize()} added — refreshing queue...")
            QTimer.singleShot(4000, self._submit_poll)
            QTimer.singleShot(10000, self._submit_poll)  # second check in case TorBox is slow
        else:
            self._log(f"Failed to add {item_type}: {detail}", "ERROR")
            self._set_status(f"Error: {detail}")

    # -----------------------------------------------------------------------
    # Queue control slots
    # -----------------------------------------------------------------------

    def _on_refresh(self):
        self._submit_poll()

    def _on_clear_done(self):
        """Remove completed rows from the table (local display only — not TorBox)."""
        keys_to_remove = [
            key for key, item in self._row_items.items()
            if _torbox_state_to_status(item) == STATUS_READY
            and key not in self._downloading
        ]
        for key in keys_to_remove:
            self._remove_row(key)
        self._log(f"Cleared {len(keys_to_remove)} completed row(s) from display.")

    def _on_clear_all(self):
        """Remove all rows from the local display (does not delete from TorBox)."""
        count = self._table.rowCount()
        self._table.setRowCount(0)
        self._row_index.clear()
        self._row_items.clear()
        self._download_queue.clear()
        self._log(f"Cleared all {count} row(s) from display.")

    def _on_download_all(self):
        """Queue every Ready row for download, respecting the concurrency limit."""
        max_dl = self.config.get("max_concurrent_downloads", DEFAULT_MAX_CONCURRENT_DL)
        queued_keys = {k for k, _ in self._download_queue}
        started = queued = 0
        for key, item in self._row_items.items():
            if _torbox_state_to_status(item) != STATUS_READY:
                continue
            if key in self._downloading or key in queued_keys:
                continue
            active = sum(self._downloading.values())
            if active < max_dl:
                self._start_download(key, item)
                started += 1
            else:
                self._download_queue.append((key, item))
                queued += 1
        if started or queued:
            parts = []
            if started:
                parts.append(f"started {started}")
            if queued:
                parts.append(f"queued {queued}")
            self._log(f"Download All: {', '.join(parts)}.")
        else:
            self._log("No ready items to download.", "INFO")

    # -----------------------------------------------------------------------
    # Settings / About
    # -----------------------------------------------------------------------

    def _on_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            new_config = dlg.get_config()
            self.config = new_config
            if save_config(new_config):
                self._log("Settings saved.")
            else:
                self._log("Settings updated in memory but could not save to disk.", "WARN")
            self._update_poll_interval()

    def _on_about(self):
        AboutDialog(self).exec()

    # -----------------------------------------------------------------------
    # Update check
    # -----------------------------------------------------------------------

    def _check_for_update(self):
        """Dispatch an UpdateCheckWorker. Runs silently; errors are logged only."""
        worker = UpdateCheckWorker(APP_VERSION)
        worker.signals.update_available.connect(self._on_update_available)
        worker.signals.error.connect(
            lambda msg: self._log(f"Update check: {msg}", "WARN")
        )
        self._pool.start(worker)

    def _on_update_available(self, latest: str, url: str):
        self._log(f"Update available: v{latest} — {url}")
        self._update_btn.setText(f"⬆  v{latest} available")
        self._update_btn.setToolTip(f"Version {latest} is available on GitHub. Click to open the releases page.")
        try:
            self._update_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self._update_btn.clicked.connect(lambda: webbrowser.open(url))
        self._update_btn.show()

    # -----------------------------------------------------------------------
    # Polling
    # -----------------------------------------------------------------------

    def _submit_poll(self):
        """Create and dispatch a PollWorker to the thread pool."""
        api_key = self.config.get("api_key", "")
        if not api_key:
            return

        worker = PollWorker(api_key)
        worker.signals.finished.connect(self._on_poll_finished)
        worker.signals.error.connect(self._on_poll_error)
        worker.signals.status.connect(self._set_status)
        self._pool.start(worker)

    def _on_poll_finished(self, items: list):
        """Slot — runs on main thread — update the queue table from fresh data."""
        self._update_queue_table(items)
        # Build a breakdown: total + counts by internal status
        ready      = sum(1 for i in items if _torbox_state_to_status(i) == STATUS_READY)
        dling      = sum(1 for i in items if _torbox_state_to_status(i) == STATUS_DOWNLOADING)
        total      = len(items)
        parts = [f"{total} item{'s' if total != 1 else ''}"]
        if ready:
            parts.append(f"{ready} ready")
        if dling:
            parts.append(f"{dling} downloading")
        self._set_status("  ·  ".join(parts))

    def _on_poll_error(self, msg: str):
        self._log(f"Poll error: {msg}", "ERROR")
        self._set_status(f"Poll failed: {msg}")

    # -----------------------------------------------------------------------
    # Queue table management
    # -----------------------------------------------------------------------

    def _update_queue_table(self, items: list):
        """
        Diff incoming item list against existing rows.
        - Update rows that already exist (same row_key).
        - Add new rows for items not yet in the table.
        - Rows for items no longer in the list are left alone
          (they may be mid-download; a Clear Done or Clear All will remove them).
        """
        seen_keys = set()

        for item in items:
            key = _row_key(item)
            seen_keys.add(key)

            # Skip items the user just deleted — give TorBox time to process.
            # Keys are removed from this set after one poll cycle (below).
            if key in self._deleted_keys:
                continue

            self._row_items[key] = item

            if key in self._row_index:
                self._update_queue_row(key, item)
            else:
                self._add_queue_row(key, item)

        # Clear the deleted-keys suppression set after each poll cycle.
        # By the next poll TorBox will have finished processing the deletes.
        self._deleted_keys.clear()

    def _add_queue_row(self, key: str, item: dict):
        """Insert a new row into the queue table for the given item."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_index[key] = row

        # Name — bold font, store row key for retrieval
        raw_name  = item.get("name", "Unknown")
        name_cell = QTableWidgetItem(raw_name)
        name_cell.setData(Qt.ItemDataRole.UserRole, key)
        # Usenet items sometimes arrive with a bare hex hash before TorBox resolves
        # the real filename. Dim + italicise so users know it's a pending resolution,
        # not missing metadata on our end.
        if (item.get("source_type") == "usenet"
                and re.fullmatch(r'[0-9a-fA-F]{20,}', raw_name)):
            hash_font = QFont(FONT_UI_FAMILY, FONT_UI_SIZE)
            hash_font.setItalic(True)
            name_cell.setFont(hash_font)
            name_cell.setForeground(QColor(COLOR_TEXT_MUTED))
            name_cell.setToolTip("NZB identifier — TorBox hasn't resolved the filename yet")
        else:
            bold_font = QFont(FONT_UI_FAMILY, FONT_UI_SIZE, QFont.Weight.Bold)
            name_cell.setFont(bold_font)
        self._table.setItem(row, COL_NAME, name_cell)

        # Type — colored badge widget
        source_type = item.get("source_type", "")
        self._table.setCellWidget(row, COL_TYPE, _make_badge(source_type))

        # Size
        size_cell = QTableWidgetItem(_fmt_size(item.get("size", 0)))
        size_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        size_cell.setForeground(QColor(COLOR_TEXT_MUTED))
        self._table.setItem(row, COL_SIZE, size_cell)

        # Status — compound display text with color coding
        status      = _torbox_state_to_status(item)
        disp_status = _torbox_display_status(item)
        status_cell = QTableWidgetItem(disp_status)
        status_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_status_color(status_cell, status)
        self._table.setItem(row, COL_STATUS, status_cell)

        # Progress bar
        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(_parse_progress(item))
        pbar.setTextVisible(True)
        self._style_progress_bar(pbar, status)
        self._table.setCellWidget(row, COL_PROGRESS, pbar)

        # Download button — outline only, fills on hover
        dl_btn = QPushButton("Download")
        dl_btn.setEnabled(status == STATUS_READY)
        dl_btn.setFixedHeight(26)
        dl_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                font-size: 8pt;
                padding: 0 6px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT};
                color: #000000;
                border: 1px solid {COLOR_ACCENT};
            }}
            QPushButton:disabled {{
                color: #2e2e2e;
                border: 1px solid #242424;
                background-color: transparent;
            }}
        """)
        dl_btn.clicked.connect(lambda checked, k=key: self._on_download_clicked(k))
        self._table.setCellWidget(row, COL_DOWNLOAD, dl_btn)

        # Delete button — wrapped in a container with right padding so it
        # doesn't press against the border. The container is transparent so
        # the table's alternating row color shows through uninterrupted.
        del_btn = QPushButton("✕")
        del_btn.setFixedHeight(24)
        del_btn.setFixedWidth(28)
        del_btn.setToolTip("Remove from TorBox queue")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: #3d1a1a;
                color: #e05050;
                border-color: #8b3030;
            }}
            QPushButton:pressed {{
                background-color: #8b3030;
                color: #ffffff;
            }}
        """)
        del_btn.clicked.connect(lambda checked, k=key: self._on_delete_clicked(k))

        del_container = QWidget()
        del_container.setStyleSheet("background: transparent;")
        del_layout = QHBoxLayout(del_container)
        del_layout.setContentsMargins(4, 0, 10, 0)
        del_layout.setSpacing(0)
        del_layout.addWidget(del_btn)
        self._table.setCellWidget(row, COL_DELETE, del_container)

        # Optional columns
        self._set_optional_cells(row, item)

    def _update_queue_row(self, key: str, item: dict):
        """Refresh cells on an existing row with new data from the API."""
        row = self._row_index.get(key)
        if row is None:
            return

        status      = _torbox_state_to_status(item)
        disp_status = _torbox_display_status(item)

        # Update name cell — re-style if a previously hashed name got resolved
        name_cell = self._table.item(row, COL_NAME)
        if name_cell:
            raw_name = item.get("name", "")
            if name_cell.text() != raw_name:
                name_cell.setText(raw_name)
            is_hash = (item.get("source_type") == "usenet"
                       and re.fullmatch(r'[0-9a-fA-F]{20,}', raw_name))
            if is_hash:
                hf = QFont(FONT_UI_FAMILY, FONT_UI_SIZE)
                hf.setItalic(True)
                name_cell.setFont(hf)
                name_cell.setForeground(QColor(COLOR_TEXT_MUTED))
                name_cell.setToolTip("NZB identifier — TorBox hasn't resolved the filename yet")
            else:
                name_cell.setFont(QFont(FONT_UI_FAMILY, FONT_UI_SIZE, QFont.Weight.Bold))
                name_cell.setForeground(QColor(COLOR_TEXT))
                name_cell.setToolTip("")

        # Update status cell with compound display text and color
        status_cell = self._table.item(row, COL_STATUS)
        if status_cell:
            status_cell.setText(disp_status)
            self._apply_status_color(status_cell, status)

        # Update size cell (may arrive after initial add)
        size_cell = self._table.item(row, COL_SIZE)
        if size_cell:
            size_cell.setText(_fmt_size(item.get("size", 0)))

        # Update progress bar (only if not currently fetching locally)
        if key not in self._downloading:
            pbar = self._table.cellWidget(row, COL_PROGRESS)
            if isinstance(pbar, QProgressBar):
                # Reset to determinate range first so setValue() isn't silently
                # clipped when the bar was previously in pulse mode (range 0,0).
                pbar.setRange(0, 100)
                pbar.setValue(_parse_progress(item))
                self._style_progress_bar(pbar, status)

        # Enable/disable download button; show Retry on error rows
        dl_btn = self._table.cellWidget(row, COL_DOWNLOAD)
        if isinstance(dl_btn, QPushButton) and key not in self._downloading:
            if status == STATUS_ERROR:
                dl_btn.setText("Retry")
                dl_btn.setEnabled(True)
            elif status == STATUS_READY:
                if dl_btn.text() == "Retry":
                    dl_btn.setText("Download")
                dl_btn.setEnabled(True)
            else:
                dl_btn.setEnabled(False)

        # Refresh optional columns
        self._set_optional_cells(row, item)

    def _set_optional_cells(self, row: int, item: dict):
        """Populate Seeds, Peers, Ratio, ETA, Added cells for a given row."""
        def _cell(text: str) -> QTableWidgetItem:
            c = QTableWidgetItem(str(text))
            c.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c.setForeground(QColor(COLOR_TEXT_MUTED))
            return c

        seeds = item.get("seeds", 0) or 0
        peers = item.get("peers", 0) or 0
        ratio = item.get("ratio", 0) or 0
        eta   = item.get("eta", 0)   or 0

        self._table.setItem(row, COL_SEEDS, _cell(seeds))
        self._table.setItem(row, COL_PEERS, _cell(peers))
        self._table.setItem(row, COL_RATIO, _cell(f"{float(ratio):.2f}"))
        self._table.setItem(row, COL_ETA,   _cell(_fmt_eta(eta)))
        self._table.setItem(row, COL_ADDED, _cell(_fmt_added(item.get("created_at", ""))))

    def _remove_row(self, key: str):
        """Remove a row from the table and rebuild the row index."""
        row = self._row_index.pop(key, None)
        if row is None:
            return
        self._table.removeRow(row)
        self._row_items.pop(key, None)
        # Rebuild index — row numbers above the removed row shifted down by 1
        self._row_index = {
            k: (r - 1 if r > row else r)
            for k, r in self._row_index.items()
        }

    @staticmethod
    def _apply_status_color(cell, status: str):
        """Apply foreground color only to a status cell — no background tint."""
        colors = STATUS_COLORS.get(status, (None, None))
        _, fg = colors   # background intentionally ignored — too busy
        if fg:
            cell.setForeground(QBrush(QColor(fg)))

    @staticmethod
    def _style_progress_bar(pbar: QProgressBar, status: str):
        if status == STATUS_READY:
            pbar.setFormat("Ready")
            pbar.setValue(100)
            pbar.setStyleSheet(_PROGRESS_BAR_DONE_STYLE)
        elif status == STATUS_ERROR:
            pbar.setRange(0, 100)
            pbar.setValue(0)
            pbar.setFormat("Error")
            pbar.setStyleSheet(
                "QProgressBar { background-color: #2e1a1a; border: 1px solid #8b3030; "
                "border-radius: 2px; text-align: center; color: #e05050; font-size: 7pt; }"
                "QProgressBar::chunk { background-color: #8b3030; }"
            )
        else:
            pbar.setStyleSheet(_PROGRESS_BAR_ACTIVE_STYLE)
            if status == STATUS_DOWNLOADING:
                val = pbar.value()
                if val <= 0:
                    # TorBox hasn't reported progress yet — pulse to show activity
                    pbar.setRange(0, 0)
                    pbar.setFormat("")
                else:
                    pbar.setRange(0, 100)
                    pbar.setFormat(f"{val}%")
            else:
                pbar.setFormat("%p%")

    # -----------------------------------------------------------------------
    # Download
    # -----------------------------------------------------------------------

    def _on_download_clicked(self, key: str):
        item = self._row_items.get(key)
        if not item:
            self._log(f"Download clicked but item {key} not found.", "WARN")
            return
        self._start_download(key, item)

    def _start_download(self, key: str, item: dict):
        """
        Validate download dir, resolve which file(s) to grab, then dispatch
        one DownloadWorker per file.

        For torrents/magnets with multiple files, shows FilePickerDialog first.
        Single-file items and webdl/usenet skip the dialog entirely.
        """
        download_dir = self.config.get("download_dir", "").strip()

        if not download_dir:
            chosen = QFileDialog.getExistingDirectory(
                self, "Choose Download Directory", os.path.expanduser("~")
            )
            if not chosen:
                return
            self.config["download_dir"] = chosen
            save_config(self.config)
            download_dir = chosen

        if not os.path.isdir(download_dir):
            self._log(
                f"Download directory does not exist: {download_dir} — check Settings.",
                "ERROR"
            )
            return

        source_type = item.get("source_type", "")
        files       = item.get("files", [])

        # Decide which files to download.
        # webdl and usenet don't have a files list — pass file_id=None, one worker.
        # Torrents/magnets with one file — pass files[0]["id"] directly.
        # Torrents/magnets with multiple files — show the picker, dispatch one worker per selection.
        if source_type in ("torrent", "magnet") and len(files) > 1:
            dlg = FilePickerDialog(item.get("name", key), files, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            selected = dlg.selected_files()
            if not selected:
                return
            for f in selected:
                self._dispatch_download_worker(
                    key=key,
                    item=item,
                    download_dir=download_dir,
                    file_id=f["id"],
                    file_name=f["name"].split("/")[-1] if "/" in f["name"] else f["name"],
                )
            return

        # Single file or non-torrent — dispatch one worker
        if source_type in ("torrent", "magnet"):
            file_id   = files[0].get("id", 0) if files else 0
            file_name = None
        else:
            file_id   = None
            file_name = None

        self._dispatch_download_worker(
            key=key,
            item=item,
            download_dir=download_dir,
            file_id=file_id,
            file_name=file_name,
        )

    def _dispatch_download_worker(self, key: str, item: dict, download_dir: str,
                                   file_id, file_name):
        """
        Submit a single DownloadWorker to the thread pool.

        Handles the progress bar swap and button disable that were previously
        inline in _start_download. Extracted so multi-file dispatch can call it
        once per selected file without repeating that setup code.

        Note: for multi-file torrents, multiple workers share the same row key.
        The progress bar reflects the last worker to emit a signal — this is
        acceptable for now. A per-file sub-row is a future improvement if needed.
        """
        self._downloading[key] = self._downloading.get(key, 0) + 1
        display_name = file_name or item.get("name", key)
        self._log(f"Starting download: {display_name}")
        self._set_status(f"Downloading: {display_name}")

        row = self._row_index.get(key)
        if row is not None:
            pbar = self._table.cellWidget(row, COL_PROGRESS)
            if isinstance(pbar, QProgressBar):
                pbar.setRange(0, 100)
                pbar.setValue(0)
                pbar.setFormat("Fetching...")
                pbar.setStyleSheet(_PROGRESS_BAR_ACTIVE_STYLE)
            dl_btn = self._table.cellWidget(row, COL_DOWNLOAD)
            if isinstance(dl_btn, QPushButton):
                dl_btn.setEnabled(False)

        worker = DownloadWorker(
            api_key      = self.config.get("api_key", ""),
            item         = item,
            download_dir = download_dir,
            file_id      = file_id,
            file_name    = file_name,
        )
        worker.signals.progress.connect(
            lambda recv, total, k=key: self._on_download_progress(k, recv, total)
        )
        worker.signals.finished.connect(
            lambda fpath, k=key: self._on_download_finished(k, fpath)
        )
        worker.signals.error.connect(
            lambda msg, k=key: self._on_download_error(k, msg)
        )
        worker.signals.status.connect(self._set_status)
        self._pool.start(worker)

    def _on_download_progress(self, key: str, bytes_recv: int, total_bytes: int):
        row = self._row_index.get(key)
        if row is None:
            return
        pbar = self._table.cellWidget(row, COL_PROGRESS)
        if not isinstance(pbar, QProgressBar):
            return

        # Show percentage only — Content-Length from TorBox is unreliable
        # (sometimes reflects chunk size rather than total file size).
        # If total is known and trustworthy, show percentage.
        # Otherwise pulse the bar so it's clear something is happening.
        if total_bytes > 0 and bytes_recv <= total_bytes:
            pct = int(bytes_recv / total_bytes * 100)
            pbar.setRange(0, 100)
            pbar.setValue(pct)
            pbar.setFormat(f"{pct}%")
        else:
            pbar.setRange(0, 0)
            pbar.setFormat("")

    def _on_download_finished(self, key: str, file_path: str):
        # Decrement the in-flight counter for this row.
        # For multi-file torrents multiple workers share the same key —
        # we only update the row UI once the last one finishes.
        count = self._downloading.get(key, 1) - 1
        if count > 0:
            self._downloading[key] = count
        else:
            self._downloading.pop(key, None)
        self._try_start_queued()
        self._update_poll_interval()

        fname = unquote(os.path.basename(file_path))
        clean_path = unquote(file_path)
        self._log(f"Download complete: {fname}  ->  {clean_path}")
        self._set_status(f"Done: {fname}")

        # Tray notification — only if enabled in settings
        if self.config.get("tray_notifications", False):
            self._tray.showMessage(
                "Download complete",
                fname,
                self._tray.icon(),
                4000,
            )

        # Only update the row to Done state when all files for this key are finished
        if key in self._downloading:
            return

        row = self._row_index.get(key)
        if row is None:
            return
        pbar = self._table.cellWidget(row, COL_PROGRESS)
        if isinstance(pbar, QProgressBar):
            pbar.setRange(0, 100)
            pbar.setValue(100)
            pbar.setFormat("Done")
            pbar.setStyleSheet(_PROGRESS_BAR_DONE_STYLE)

        dl_btn = self._table.cellWidget(row, COL_DOWNLOAD)
        if isinstance(dl_btn, QPushButton):
            dl_btn.setEnabled(True)
            try:
                dl_btn.clicked.disconnect()
            except RuntimeError:
                pass

            # Multi-file torrents: keep the button as "Download" so the user
            # can open the file picker again to grab remaining files.
            item = self._row_items.get(key, {})
            is_multi_file_torrent = (
                item.get("source_type", "") in ("torrent", "magnet")
                and len(item.get("files", [])) > 1
            )
            if is_multi_file_torrent:
                dl_btn.setText("Download")
                dl_btn.clicked.connect(
                    lambda checked, k=key: self._on_download_clicked(k)
                )
            else:
                dl_btn.setText("Open")
                # Rewire the button to open the file's containing folder
                dl_btn.clicked.connect(
                    lambda checked, p=file_path: self._open_in_explorer(p)
                )

    def _on_download_error(self, key: str, msg: str):
        count = self._downloading.get(key, 1) - 1
        if count > 0:
            self._downloading[key] = count
        else:
            self._downloading.pop(key, None)
        self._try_start_queued()
        self._update_poll_interval()
        self._log(f"Download error: {msg}", "ERROR")
        self._set_status(f"Download failed — {msg}")

        row = self._row_index.get(key)
        if row is None:
            return
        pbar = self._table.cellWidget(row, COL_PROGRESS)
        if isinstance(pbar, QProgressBar):
            pbar.setRange(0, 100)
            pbar.setValue(0)
            self._style_progress_bar(pbar, STATUS_ERROR)
        dl_btn = self._table.cellWidget(row, COL_DOWNLOAD)
        if isinstance(dl_btn, QPushButton):
            dl_btn.setText("Retry")
            dl_btn.setEnabled(True)

    @staticmethod
    def _open_in_explorer(file_path: str):
        """Open the folder containing the downloaded file and select it."""
        folder = os.path.dirname(file_path)
        try:
            # explorer /select highlights the file in the folder — more useful than
            # just opening the folder. Use list form to handle paths with spaces safely.
            import subprocess
            subprocess.Popen(["explorer", f"/select,{file_path}"])
        except Exception:
            try:
                os.startfile(folder)
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------------

    def _on_delete_clicked(self, key: str):
        item = self._row_items.get(key)
        if not item:
            self._remove_row(key)
            return

        name        = item.get("name", key)
        source_type = item.get("source_type", "")
        item_id     = item.get("id")
        api_key     = self.config.get("api_key", "")

        # Confirm before doing anything — confirmation stays on main thread (correct)
        reply = QMessageBox.question(
            self,
            "Delete Item",
            f"Remove '{name}' from TorBox?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Build the delete callable based on type
        if source_type in ("torrent", "magnet"):
            delete_fn = lambda: api.delete_torrent(api_key, item_id)
        elif source_type == "webdl":
            delete_fn = lambda: api.delete_webdl(api_key, item_id)
        elif source_type == "usenet":
            delete_fn = lambda: api.delete_usenet(api_key, item_id)
        else:
            # Unknown type — just remove from display, nothing to call
            self._log(f"Unknown type '{source_type}' — removed from display only.")
            self._remove_row(key)
            return

        # Remove the row immediately so the UI feels snappy.
        # If the API call fails the row is gone but the item still exists on TorBox —
        # the next poll will bring it back. This is the least-surprising behaviour.
        self._deleted_keys.add(key)
        self._remove_row(key)
        self._download_queue = [(k, i) for k, i in self._download_queue if k != key]
        self._log(f"Deleting from TorBox: {name}")

        worker = DeleteWorker(delete_fn, key, name)
        worker.signals.finished.connect(self._on_delete_finished)
        worker.signals.status.connect(self._set_status)
        self._pool.start(worker)

    def _on_delete_finished(self, success: bool, detail: str, key: str):
        """Slot — called on main thread when DeleteWorker completes."""
        if success:
            self._log(f"Deleted from TorBox: {detail}")
        else:
            # The row is already gone from the display. Log the failure;
            # the next poll will restore the item if TorBox didn't process it.
            self._log(f"Delete API call failed: {detail} — item may reappear on next poll.", "WARN")

    # -----------------------------------------------------------------------
    # Log and status helpers
    # -----------------------------------------------------------------------

    def _log(self, msg: str, level: str = "INFO"):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"{ts} [{level}] {msg}"
        self._log_lines.append((level, line))
        # Trim oldest entries when the buffer grows too large
        if len(self._log_lines) > 500:
            self._log_lines = self._log_lines[-250:]
            self._log_view.clear()
            filter_active = getattr(self, "_log_filter_btn", None) and self._log_filter_btn.isChecked()
            for lvl, ln in self._log_lines:
                if not filter_active or lvl in ("WARN", "ERROR"):
                    self._log_view.append(ln)
        else:
            filter_active = getattr(self, "_log_filter_btn", None) and self._log_filter_btn.isChecked()
            if not filter_active or level in ("WARN", "ERROR"):
                self._log_view.append(line)
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_status(self, msg: str):
        self._status_label.setText(msg)
        # Pulse dot — amber during activity, green when idle
        if any(w in msg.lower() for w in ("error", "failed")):
            self._status_dot.setStyleSheet(
                "color: #e05050; font-size: 8pt; background: transparent;"
            )
        elif any(w in msg.lower() for w in ("downloading", "adding", "polling", "fetching")):
            self._status_dot.setStyleSheet(
                "color: #e0a030; font-size: 8pt; background: transparent;"
            )
        else:
            self._status_dot.setStyleSheet(
                f"color: {COLOR_ACCENT}; font-size: 8pt; background: transparent;"
            )

    # -----------------------------------------------------------------------
    # Tray / window close
    # -----------------------------------------------------------------------

    def closeEvent(self, event):
        """Minimize to tray or quit depending on user setting."""
        self._save_geometry()
        if self.config.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            self._update_poll_interval()
            self._tray.showMessage(
                APP_NAME,
                "Running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            self._tray_quit()

    def _save_geometry(self):
        try:
            geom_hex = self.saveGeometry().toHex().data().decode()
            self.config["window_geometry"] = geom_hex
            save_config(self.config)
        except Exception:
            pass

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._tray_show()

    def _tray_show(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._update_poll_interval()

    def _tray_restart(self):
        import sys
        self._poll_timer.stop()
        QApplication.instance().quit()
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)

    def _tray_quit(self):
        self._poll_timer.stop()
        self._tray.hide()
        QApplication.instance().quit()
