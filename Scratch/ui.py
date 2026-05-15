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
# TODO v0.2: add Seeders, Age/Added Time, ETA columns if exposed by TorBox API.
#            Right-click header → Show/Hide Columns for optional fields.

import os
import webbrowser
from datetime import datetime

from PyQt6.QtCore    import Qt, QThreadPool, QTimer
from PyQt6.QtGui     import QFont, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
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
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_BUTTON_BG,
    COLOR_BUTTON_HOVER,
    COLOR_HEADER_BAR,
    COLOR_PANEL,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COL_DELETE,
    COL_DOWNLOAD,
    COL_NAME,
    COL_PROGRESS,
    COL_SIZE,
    COL_STATUS,
    COL_TYPE,
    DOWNLOAD_CHUNK_SIZE,
    FONT_LOG_FAMILY,
    FONT_LOG_SIZE,
    FONT_UI_FAMILY,
    FONT_UI_SIZE,
    KOFI_URL,
    STATUS_DOWNLOADING,
    STATUS_ERROR,
    STATUS_FETCHING,
    STATUS_QUEUED,
    STATUS_READY,
    TYPE_ICONS,
)
from dialogs  import AboutDialog, AddLinkDialog, AddMagnetDialog, SettingsDialog
from worker   import DownloadWorker, PollWorker


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
        background-color: {COLOR_BG};
        color: {COLOR_TEXT};
        gridline-color: {COLOR_BORDER};
        border: none;
        selection-background-color: #2a3a1a;
        outline: none;
    }}
    QTableWidget::item {{
        padding: 2px 6px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: #2a3a1a;
        color: {COLOR_TEXT};
    }}
    QHeaderView::section {{
        background-color: {COLOR_PANEL};
        color: {COLOR_ACCENT};
        border: none;
        border-right: 1px solid {COLOR_BORDER};
        border-bottom: 1px solid {COLOR_BORDER};
        padding: 4px 6px;
        font-size: 8pt;
        font-weight: bold;
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
        border-color: {COLOR_ACCENT};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_ACCENT};
        color: #000000;
    }}
    QPushButton:disabled {{
        color: #555555;
        border-color: #333333;
    }}
    QProgressBar {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        border-radius: 2px;
        text-align: center;
        color: {COLOR_TEXT};
        font-size: 7pt;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_ACCENT};
        border-radius: 2px;
    }}
    QStatusBar {{
        background-color: {COLOR_PANEL};
        color: {COLOR_TEXT_MUTED};
        border-top: 1px solid {COLOR_BORDER};
        font-size: 8pt;
    }}
    QScrollBar:vertical {{
        background-color: {COLOR_BG};
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: #444444;
        border-radius: 5px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {COLOR_ACCENT};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background-color: {COLOR_BG};
        height: 10px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background-color: #444444;
        border-radius: 5px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {COLOR_ACCENT};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
"""

_PROGRESS_BAR_DONE_STYLE = f"""
    QProgressBar {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_ACCENT};
        border-radius: 2px;
        text-align: center;
        color: #000000;
        font-size: 7pt;
        font-weight: bold;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_ACCENT};
        border-radius: 2px;
    }}
"""

_PROGRESS_BAR_ACTIVE_STYLE = f"""
    QProgressBar {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        border-radius: 2px;
        text-align: center;
        color: {COLOR_TEXT};
        font-size: 7pt;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_ACCENT};
        border-radius: 2px;
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


def _torbox_state_to_status(download_state: str) -> str:
    """
    Map a TorBox download_state string to one of our STATUS_* constants.

    Assumption: these are the states TorBox returns. Verify against live
    API responses — field name may differ (e.g. 'status' instead of
    'download_state'). Add new mappings here as discovered.
    """
    s = str(download_state).lower()
    if s in ("completed", "seeding", "cached", "paused_upload"):
        return STATUS_READY
    if s in ("downloading", "uploading", "checking", "checkingresumedata",
             "moving", "fetching"):
        return STATUS_DOWNLOADING
    if s in ("error", "missingfiles", "failed"):
        return STATUS_ERROR
    # Everything else (queued, waiting, stalled, paused, metadl, etc.)
    return STATUS_QUEUED


def _row_key(item: dict) -> str:
    """Stable unique key for a queue item — used to match rows across polls."""
    return f"{item.get('source_type', 'unknown')}:{item.get('id', 0)}"


# ---------------------------------------------------------------------------
# Left panel section label
# ---------------------------------------------------------------------------

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {COLOR_ACCENT}; font-size: 8pt; font-weight: bold; "
        f"padding-top: 8px; padding-bottom: 2px;"
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
        self._downloading: set[str] = set()

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
        self.resize(1200, 700)
        self.setStyleSheet(MAIN_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Header bar
        root_layout.addWidget(self._build_header())

        # Body: left panel + right content side by side
        body_splitter = QSplitter(Qt.Orientation.Horizontal)
        body_splitter.setHandleWidth(2)
        body_splitter.addWidget(self._build_left_panel())
        body_splitter.addWidget(self._build_right_panel())
        body_splitter.setSizes([280, 920])
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        root_layout.addWidget(body_splitter, stretch=1)

        # Status bar
        self._build_status_bar()

    def _build_header(self) -> QWidget:
        """Amber header bar with centred app title — matches EAC."""
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"background-color: {COLOR_HEADER_BAR};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)

        # Decorative left ticks (purely cosmetic, mirrors EAC)
        left_deco = QLabel("/ /")
        left_deco.setStyleSheet(f"color: #5a4010; font-size: 14pt;")
        layout.addWidget(left_deco)

        # Thin green line left
        left_line = QWidget()
        left_line.setFixedHeight(2)
        left_line.setStyleSheet(f"background-color: {COLOR_ACCENT};")
        layout.addWidget(left_line, stretch=1)

        title = QLabel(APP_NAME.upper())
        title.setFont(QFont(FONT_UI_FAMILY, 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_ACCENT}; letter-spacing: 4px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        right_line = QWidget()
        right_line.setFixedHeight(2)
        right_line.setStyleSheet(f"background-color: {COLOR_ACCENT};")
        layout.addWidget(right_line, stretch=1)

        right_deco = QLabel("\\ \\")
        right_deco.setStyleSheet(f"color: #5a4010; font-size: 14pt;")
        layout.addWidget(right_deco)

        return bar

    def _build_left_panel(self) -> QWidget:
        """Fixed-width left panel: add buttons + queue controls + settings."""
        panel = QWidget()
        panel.setFixedWidth(280)
        panel.setStyleSheet(f"background-color: {COLOR_PANEL};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(4)

        # ---- ADD ----
        layout.addWidget(_section_label("Add"))

        for label, slot in [
            ("🧲  Add Magnet",      self._on_add_magnet),
            ("📄  Add Torrent",     self._on_add_torrent),
            ("🔗  Add Hoster Link", self._on_add_link),
            ("📰  Add NZB",         self._on_add_nzb),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(32)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        # ---- QUEUE ----
        layout.addWidget(_section_label("Queue"))

        self._refresh_btn = QPushButton("↻  Refresh Now")
        self._refresh_btn.setMinimumHeight(30)
        self._refresh_btn.clicked.connect(self._on_refresh)
        layout.addWidget(self._refresh_btn)

        clear_done_btn = QPushButton("Clear Completed")
        clear_done_btn.setMinimumHeight(30)
        clear_done_btn.clicked.connect(self._on_clear_done)
        layout.addWidget(clear_done_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setMinimumHeight(30)
        clear_all_btn.clicked.connect(self._on_clear_all)
        layout.addWidget(clear_all_btn)

        # ---- SETTINGS ----
        layout.addWidget(_section_label(""))
        layout.addStretch()

        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setMinimumHeight(30)
        settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(settings_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        """Right side: queue table (top) + log strip (bottom)."""
        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(3)

        # Queue table
        splitter.addWidget(self._build_queue_table())

        # Log strip
        splitter.addWidget(self._build_log_strip())

        splitter.setSizes([480, 140])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        layout.addWidget(splitter)
        return right

    def _build_queue_table(self) -> QWidget:
        """
        QTableWidget with one row per queued TorBox item.
        Columns: Name | Type | Status | Size | Progress | Download | Delete
        # TODO v0.2: Seeders, Added, ETA columns (right-click header to show/hide)
        """
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Name", "Type", "Status", "Size", "Progress", "Download", "Delete"
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(COL_NAME,     QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_TYPE,     QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_STATUS,   QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_SIZE,     QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_PROGRESS, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_DOWNLOAD, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(COL_DELETE,   QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(COL_TYPE,     90)
        self._table.setColumnWidth(COL_STATUS,   110)
        self._table.setColumnWidth(COL_SIZE,     80)
        self._table.setColumnWidth(COL_PROGRESS, 130)
        self._table.setColumnWidth(COL_DOWNLOAD, 90)
        self._table.setColumnWidth(COL_DELETE,   70)

        self._table.verticalHeader().setDefaultSectionSize(32)

        return self._table

    def _build_log_strip(self) -> QWidget:
        """Monospace timestamped log at the bottom of the right panel."""
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_PANEL};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Thin label header
        header = QLabel("  LOG")
        header.setFixedHeight(18)
        header.setStyleSheet(
            f"background-color: #1a1a1a; color: {COLOR_TEXT_MUTED}; "
            f"font-size: 7pt; font-weight: bold; letter-spacing: 2px;"
        )
        layout.addWidget(header)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont(FONT_LOG_FAMILY, FONT_LOG_SIZE))
        self._log_view.setStyleSheet(
            f"background-color: {COLOR_PANEL}; color: #aaaaaa; "
            f"border: none; border-top: 1px solid {COLOR_BORDER};"
        )
        self._log_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self._log_view)

        return container

    def _build_status_bar(self):
        """Status text left | Download All centre-right | donate far right."""
        bar = QStatusBar()
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)

        self._status_label = QLabel("Ready")
        bar.addWidget(self._status_label, stretch=1)

        dl_all_btn = QPushButton("Download All")
        dl_all_btn.setFixedHeight(22)
        dl_all_btn.clicked.connect(self._on_download_all)
        bar.addPermanentWidget(dl_all_btn)

        spacer = QLabel("  ")
        bar.addPermanentWidget(spacer)

        kofi_btn = QPushButton("donate ♥ ko-fi")
        kofi_btn.setFixedHeight(22)
        kofi_btn.setFlat(True)
        kofi_btn.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: 8pt; border: none; "
            f"padding: 0 6px;"
        )
        kofi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kofi_btn.clicked.connect(lambda: webbrowser.open(KOFI_URL))
        bar.addPermanentWidget(kofi_btn)

    def _build_tray(self):
        """System tray icon with Open / About / Restart / Quit menu."""
        self._tray = QSystemTrayIcon(self)

        # Load icon — graceful fallback if asset is missing
        from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
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

    # -----------------------------------------------------------------------
    # Add button slots
    # -----------------------------------------------------------------------

    def _on_add_magnet(self):
        dlg = AddMagnetDialog(self)
        if dlg.exec():
            link = dlg.magnet_link()
            self._log(f"Adding magnet: {link[:60]}{'...' if len(link) > 60 else ''}")
            self._set_status("Adding magnet...")
            result = api.add_magnet(self.config.get("api_key", ""), link)
            self._handle_add_result(result, "magnet")

    def _on_add_torrent(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Torrent File", "", "Torrent Files (*.torrent)"
        )
        if not path:
            return
        self._log(f"Adding torrent: {os.path.basename(path)}")
        self._set_status("Adding torrent...")
        result = api.add_torrent_file(self.config.get("api_key", ""), path)
        self._handle_add_result(result, "torrent")

    def _on_add_link(self):
        dlg = AddLinkDialog(self)
        if dlg.exec():
            url = dlg.url()
            self._log(f"Adding hoster link: {url[:60]}{'...' if len(url) > 60 else ''}")
            self._set_status("Adding hoster link...")
            result = api.add_hoster_link(self.config.get("api_key", ""), url)
            self._handle_add_result(result, "hoster link")

    def _on_add_nzb(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select NZB File", "", "NZB Files (*.nzb)"
        )
        if not path:
            return
        self._log(f"Adding NZB: {os.path.basename(path)}")
        self._set_status("Adding NZB...")
        result = api.add_nzb_file(self.config.get("api_key", ""), path)
        self._handle_add_result(result, "NZB")

    def _handle_add_result(self, result: dict, item_type: str):
        """Log the result of an add operation and trigger a refresh."""
        if result["success"]:
            self._log(f"{item_type.capitalize()} added successfully: {result['detail']}")
            self._set_status(f"{item_type.capitalize()} added — refreshing queue...")
            QTimer.singleShot(1500, self._submit_poll)
        else:
            self._log(f"Failed to add {item_type}: {result['detail']}", "ERROR")
            self._set_status(f"Error: {result['detail']}")

    # -----------------------------------------------------------------------
    # Queue control slots
    # -----------------------------------------------------------------------

    def _on_refresh(self):
        self._submit_poll()

    def _on_clear_done(self):
        """Remove completed rows from the table (local display only — not TorBox)."""
        keys_to_remove = [
            key for key, item in self._row_items.items()
            if _torbox_state_to_status(item.get("download_state", "")) == STATUS_READY
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
        self._log(f"Cleared all {count} row(s) from display.")

    def _on_download_all(self):
        """Trigger a download for every Ready row that isn't already downloading."""
        started = 0
        for key, item in self._row_items.items():
            status = _torbox_state_to_status(item.get("download_state", ""))
            if status == STATUS_READY and key not in self._downloading:
                self._start_download(key, item)
                started += 1
        if started:
            self._log(f"Started download for {started} ready item(s).")
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
            # Restart the timer with the (possibly new) interval
            self._poll_timer.setInterval(new_config.get("poll_interval", 30) * 1000)

    def _on_about(self):
        AboutDialog(self).exec()

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
        self._set_status(f"Ready — {len(items)} item(s) in queue")

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
            self._row_items[key] = item

            if key in self._row_index:
                self._update_queue_row(key, item)
            else:
                self._add_queue_row(key, item)

    def _add_queue_row(self, key: str, item: dict):
        """Insert a new row into the queue table for the given item."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_index[key] = row

        # Name — store the full item dict here for later retrieval
        name_cell = QTableWidgetItem(item.get("name", "Unknown"))
        name_cell.setData(Qt.ItemDataRole.UserRole, key)
        self._table.setItem(row, COL_NAME, name_cell)

        # Type icon
        source_type = item.get("source_type", "")
        type_cell   = QTableWidgetItem(
            f"  {TYPE_ICONS.get(source_type, '?')}  {source_type.capitalize()}"
        )
        type_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_TYPE, type_cell)

        # Size
        size_cell = QTableWidgetItem(_fmt_size(item.get("size", 0)))
        size_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_SIZE, size_cell)

        # Status (cell — text only; progress bar handles the visual for progress)
        status = _torbox_state_to_status(item.get("download_state", ""))
        status_cell = QTableWidgetItem(status)
        status_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_STATUS, status_cell)

        # Progress bar
        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(int(item.get("progress", 0)))
        pbar.setTextVisible(True)
        self._style_progress_bar(pbar, status)
        self._table.setCellWidget(row, COL_PROGRESS, pbar)

        # Download button
        dl_btn = QPushButton("Download")
        dl_btn.setEnabled(status == STATUS_READY)
        dl_btn.setFixedHeight(26)
        dl_btn.clicked.connect(lambda checked, k=key: self._on_download_clicked(k))
        self._table.setCellWidget(row, COL_DOWNLOAD, dl_btn)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setFixedHeight(26)
        del_btn.setToolTip("Remove from TorBox queue")
        del_btn.clicked.connect(lambda checked, k=key: self._on_delete_clicked(k))
        self._table.setCellWidget(row, COL_DELETE, del_btn)

    def _update_queue_row(self, key: str, item: dict):
        """Refresh cells on an existing row with new data from the API."""
        row = self._row_index.get(key)
        if row is None:
            return

        status = _torbox_state_to_status(item.get("download_state", ""))

        # Update status cell
        status_cell = self._table.item(row, COL_STATUS)
        if status_cell:
            status_cell.setText(status)

        # Update size cell (may arrive after initial add)
        size_cell = self._table.item(row, COL_SIZE)
        if size_cell:
            size_cell.setText(_fmt_size(item.get("size", 0)))

        # Update progress bar (only if not currently fetching locally)
        if key not in self._downloading:
            pbar = self._table.cellWidget(row, COL_PROGRESS)
            if isinstance(pbar, QProgressBar):
                pbar.setValue(int(item.get("progress", 0)))
                self._style_progress_bar(pbar, status)

        # Enable/disable download button
        dl_btn = self._table.cellWidget(row, COL_DOWNLOAD)
        if isinstance(dl_btn, QPushButton):
            dl_btn.setEnabled(status == STATUS_READY and key not in self._downloading)

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
    def _style_progress_bar(pbar: QProgressBar, status: str):
        if status == STATUS_READY:
            pbar.setFormat("Ready")
            pbar.setValue(100)
            pbar.setStyleSheet(_PROGRESS_BAR_DONE_STYLE)
        elif status == STATUS_ERROR:
            pbar.setFormat("Error")
            pbar.setStyleSheet(
                "QProgressBar { background-color: #2e1a1a; border: 1px solid #8b3030; "
                "border-radius: 2px; text-align: center; color: #e05050; font-size: 7pt; }"
                "QProgressBar::chunk { background-color: #8b3030; }"
            )
        else:
            pbar.setFormat("%p%")
            pbar.setStyleSheet(_PROGRESS_BAR_ACTIVE_STYLE)
            if status == STATUS_DOWNLOADING:
                # Indeterminate if progress is 0 (TorBox hasn't reported yet)
                if pbar.value() == 0:
                    pbar.setRange(0, 0)
                else:
                    pbar.setRange(0, 100)

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
        """Validate download dir then submit a DownloadWorker."""
        download_dir = self.config.get("download_dir", "").strip()

        if not download_dir:
            # Prompt user to choose a directory now
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

        self._downloading.add(key)
        name = item.get("name", key)
        self._log(f"Starting download: {name}")
        self._set_status(f"Downloading: {name}")

        # Swap progress bar to fetching state
        row = self._row_index.get(key)
        if row is not None:
            pbar = self._table.cellWidget(row, COL_PROGRESS)
            if isinstance(pbar, QProgressBar):
                pbar.setRange(0, 100)
                pbar.setValue(0)
                pbar.setFormat("Fetching…")
                pbar.setStyleSheet(_PROGRESS_BAR_ACTIVE_STYLE)
            dl_btn = self._table.cellWidget(row, COL_DOWNLOAD)
            if isinstance(dl_btn, QPushButton):
                dl_btn.setEnabled(False)

        worker = DownloadWorker(
            api_key      = self.config.get("api_key", ""),
            item         = item,
            download_dir = download_dir,
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
        if total_bytes > 0:
            pct = int(bytes_recv / total_bytes * 100)
            pbar.setRange(0, 100)
            pbar.setValue(pct)
            pbar.setFormat(
                f"{_fmt_size(bytes_recv)} / {_fmt_size(total_bytes)}"
            )
        else:
            # Unknown total — show bytes received, indeterminate bar
            pbar.setRange(0, 0)
            pbar.setFormat(f"{_fmt_size(bytes_recv)}")

    def _on_download_finished(self, key: str, file_path: str):
        self._downloading.discard(key)
        fname = os.path.basename(file_path)
        self._log(f"Download complete: {fname}  →  {file_path}")
        self._set_status(f"Done: {fname}")

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
            dl_btn.setText("Open")
            dl_btn.setEnabled(True)
            # Rewire the button to open the file's containing folder
            try:
                dl_btn.clicked.disconnect()
            except RuntimeError:
                pass
            dl_btn.clicked.connect(
                lambda checked, p=file_path: self._open_in_explorer(p)
            )

    def _on_download_error(self, key: str, msg: str):
        self._downloading.discard(key)
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
            dl_btn.setEnabled(True)   # let them retry

    @staticmethod
    def _open_in_explorer(file_path: str):
        """Open the folder containing the downloaded file."""
        import subprocess
        folder = os.path.dirname(file_path)
        try:
            subprocess.Popen(f'explorer /select,"{file_path}"')
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

        # Confirm
        reply = QMessageBox.question(
            self,
            "Delete Item",
            f"Remove '{name}' from TorBox?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if source_type in ("torrent", "magnet"):
            result = api.delete_torrent(api_key, item_id)
        elif source_type == "webdl":
            result = api.delete_webdl(api_key, item_id)
        elif source_type == "usenet":
            result = api.delete_usenet(api_key, item_id)
        else:
            result = {"success": False, "detail": "Unknown type — removed from display only."}

        if result["success"]:
            self._log(f"Deleted from TorBox: {name}")
            self._remove_row(key)
        else:
            self._log(f"Delete failed for '{name}': {result['detail']}", "ERROR")

    # -----------------------------------------------------------------------
    # Log and status helpers
    # -----------------------------------------------------------------------

    def _log(self, msg: str, level: str = "INFO"):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"{ts} [{level}] {msg}"
        self._log_view.append(line)
        # Auto-scroll to the bottom
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _set_status(self, msg: str):
        self._status_label.setText(msg)

    # -----------------------------------------------------------------------
    # Tray / window close
    # -----------------------------------------------------------------------

    def closeEvent(self, event):
        """Minimize to tray instead of closing."""
        event.ignore()
        self.hide()
        self._tray.showMessage(
            APP_NAME,
            "Running in the system tray.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._tray_show()

    def _tray_show(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

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
