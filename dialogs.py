# dialogs.py
# TorBox Manager EchoStorm Edition
#
# All modal dialogs. No API calls, no worker threads — dialogs collect
# input and return it. The caller (ui.py) decides what to do with it.
#
# Dialogs defined here:
#   AddMagnetDialog   — text input for a magnet:// link
#   AddLinkDialog     — text input for a hoster URL
#   SettingsDialog    — API key, download directory, poll interval
#   AboutDialog       — version, description, Ko-fi link
#
# File picker dialogs for .torrent and .nzb are single QFileDialog calls
# and live inline in ui.py — no class needed for those.
#
# Styling mirrors EAC: dark background, #7cb342 green accents, Segoe UI.
# A shared _apply_dialog_style() helper keeps it consistent across all dialogs.

import os
import webbrowser

from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
)
from PyQt6.QtGui import QIntValidator

from constants import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    COLOR_ACCENT,
    COLOR_ACCENT_DIM,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_BUTTON_BG,
    COLOR_BUTTON_HOVER,
    COLOR_PANEL,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    FONT_UI_FAMILY,
    FONT_UI_SIZE,
    KOFI_URL,
    MAX_POLL_INTERVAL_SEC,
    MIN_POLL_INTERVAL_SEC,
)


# ---------------------------------------------------------------------------
# Shared styling
# ---------------------------------------------------------------------------

_DIALOG_STYLE = f"""
    QDialog {{
        background-color: {COLOR_BG};
        color: {COLOR_TEXT};
    }}
    QLabel {{
        color: {COLOR_TEXT};
    }}
    QLabel#muted {{
        color: {COLOR_TEXT_MUTED};
        font-size: 8pt;
    }}
    QLineEdit {{
        background-color: {COLOR_PANEL};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        padding: 4px 6px;
        selection-background-color: {COLOR_ACCENT};
    }}
    QLineEdit:focus {{
        border: 1px solid {COLOR_ACCENT};
    }}
    QPushButton {{
        background-color: {COLOR_BUTTON_BG};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        padding: 5px 14px;
        min-width: 64px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BUTTON_HOVER};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_ACCENT};
        color: #000000;
    }}
    QPushButton#accent {{
        background-color: {COLOR_ACCENT};
        color: #000000;
        font-weight: bold;
        border: none;
    }}
    QPushButton#accent:hover {{
        background-color: #8ecf4a;
    }}
    QDialogButtonBox QPushButton {{
        min-width: 72px;
    }}
    QCheckBox {{
        color: {COLOR_TEXT};
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {COLOR_BORDER};
        border-radius: 2px;
        background-color: {COLOR_PANEL};
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLOR_ACCENT};
        border-color: {COLOR_ACCENT};
    }}
    QTextBrowser {{
        background-color: {COLOR_PANEL};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
    }}
"""


def _apply_dialog_style(dialog: QDialog):
    """Apply the EchoStorm stylesheet and base font to a dialog."""
    dialog.setStyleSheet(_DIALOG_STYLE)
    dialog.setFont(QFont(FONT_UI_FAMILY, FONT_UI_SIZE))


def _make_paste_btn(target_input: QLineEdit) -> QPushButton:
    """
    Return a small Paste button that writes clipboard text into target_input.

    Styled to sit flush against the input field without drawing attention —
    muted border at rest, accent on hover, same height as the input.
    The button is disabled when the clipboard contains no text.
    """
    btn = QPushButton("📋 Paste")
    btn.setFixedHeight(30)
    btn.setFixedWidth(72)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent;
            color: {COLOR_ACCENT};
            border: 1px solid {COLOR_ACCENT_DIM};
            border-radius: 3px;
            font-size: 8pt;
            padding: 0 6px;
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
        QPushButton:disabled {{
            color: #333333;
            border-color: {COLOR_BORDER};
        }}
    """)

    def _do_paste():
        cb   = QApplication.clipboard()
        text = cb.text().strip()
        if text:
            target_input.setText(text)
            target_input.setFocus()

    def _update_state():
        btn.setEnabled(bool(QApplication.clipboard().text().strip()))

    btn.clicked.connect(_do_paste)
    # Re-check enabled state every time the clipboard changes
    QApplication.clipboard().dataChanged.connect(_update_state)
    # Set initial state
    _update_state()

    return btn


def _section_label(text: str) -> QLabel:
    """Return a small green uppercase section label, matching EAC's style."""
    label = QLabel(text.upper())
    label.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 8pt; font-weight: bold;")
    return label


def _muted_label(text: str) -> QLabel:
    """Return a small muted helper/hint label."""
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label


# ---------------------------------------------------------------------------
# AddMagnetDialog
# ---------------------------------------------------------------------------

class AddMagnetDialog(QDialog):
    """
    Single-field dialog for pasting a magnet:// link.

    Usage:
        dlg = AddMagnetDialog(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            magnet_link = dlg.magnet_link()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Magnet Link")
        self.setMinimumWidth(520)
        self.setModal(True)
        _apply_dialog_style(self)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(_section_label("Magnet Link"))

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("magnet:?xt=urn:btih:...")
        self._input.setMinimumHeight(30)
        input_row.addWidget(self._input)
        input_row.addWidget(_make_paste_btn(self._input))
        layout.addLayout(input_row)

        layout.addWidget(_muted_label(
            "Paste a full magnet link. TorBox will queue it and begin caching."
        ))

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"color: #e05050; font-size: 8pt;")
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._input.returnPressed.connect(self._validate_and_accept)

    def _validate_and_accept(self):
        text = self._input.text().strip()
        if not text:
            self._error_label.setText("Please paste a magnet link.")
            return
        if not text.startswith("magnet:"):
            self._error_label.setText("That doesn't look like a magnet link (should start with magnet:).")
            return
        self.accept()

    def magnet_link(self) -> str:
        """Return the validated magnet link. Call only after exec() == Accepted."""
        return self._input.text().strip()


# ---------------------------------------------------------------------------
# AddLinkDialog
# ---------------------------------------------------------------------------

class AddLinkDialog(QDialog):
    """
    Single-field dialog for pasting a hoster URL.

    Usage:
        dlg = AddLinkDialog(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            url = dlg.url()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Hoster Link")
        self.setMinimumWidth(520)
        self.setModal(True)
        _apply_dialog_style(self)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(_section_label("Hoster URL"))

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("https://1fichier.com/?abc123  or  https://mega.nz/...")
        self._input.setMinimumHeight(30)
        input_row.addWidget(self._input)
        input_row.addWidget(_make_paste_btn(self._input))
        layout.addLayout(input_row)

        layout.addWidget(_muted_label(
            "Paste a link from any supported hoster (1Fichier, Mega, Pixeldrain, etc.). "
            "TorBox will cache it. If the hoster isn't supported, TorBox will say so."
        ))

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e05050; font-size: 8pt;")
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._input.returnPressed.connect(self._validate_and_accept)

    def _validate_and_accept(self):
        text = self._input.text().strip()
        if not text:
            self._error_label.setText("Please paste a URL.")
            return
        if not (text.startswith("http://") or text.startswith("https://")):
            self._error_label.setText("URL should start with http:// or https://")
            return
        self.accept()

    def url(self) -> str:
        """Return the validated URL. Call only after exec() == Accepted."""
        return self._input.text().strip()


# ---------------------------------------------------------------------------
# SettingsDialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    """
    Settings dialog: API key, download directory, poll interval.

    Reads the current config dict on open; returns an updated dict on accept.
    Does not call save_config() itself — the caller (ui.py) saves after accept.

    Usage:
        dlg = SettingsDialog(current_config, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_config = dlg.get_config()
            save_config(new_config)
    """

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self.setModal(True)
        _apply_dialog_style(self)
        self._config = dict(config)   # work on a copy
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        # ---- API Key ----
        layout.addWidget(_section_label("TorBox API Key"))

        key_row = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("Paste your TorBox API key here")
        self._key_input.setMinimumHeight(30)
        self._key_input.setText(self._config.get("api_key", ""))
        key_row.addWidget(self._key_input)

        self._show_key_cb = QCheckBox("Show")
        self._show_key_cb.toggled.connect(self._toggle_key_visibility)
        key_row.addWidget(self._show_key_cb)
        layout.addLayout(key_row)

        layout.addWidget(_muted_label(
            "Found at torbox.app → Account → API. Stored locally in config.json."
        ))

        # ---- Download Directory ----
        layout.addWidget(_section_label("Download Directory"))

        dir_row = QHBoxLayout()
        self._dir_input = QLineEdit()
        self._dir_input.setPlaceholderText("Select a folder for downloaded files...")
        self._dir_input.setMinimumHeight(30)
        self._dir_input.setText(self._config.get("download_dir", ""))
        dir_row.addWidget(self._dir_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_directory)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        layout.addWidget(_muted_label(
            "All downloaded files will be saved here. "
            "Leave blank to be prompted on first download."
        ))

        # ---- Minimize to Tray ----
        layout.addWidget(_section_label("Behaviour"))

        self._tray_cb = QCheckBox("Minimize to system tray on close")
        self._tray_cb.setChecked(self._config.get("minimize_to_tray", True))
        layout.addWidget(self._tray_cb)

        layout.addWidget(_muted_label(
            "When enabled, closing the window hides it to the tray instead of quitting. "
            "Use Quit from the tray menu to fully exit."
        ))

        # ---- Poll Interval ----
        layout.addWidget(_section_label("Queue Refresh Interval"))

        poll_row = QHBoxLayout()
        self._poll_input = QLineEdit()
        self._poll_input.setValidator(
            QIntValidator(MIN_POLL_INTERVAL_SEC, MAX_POLL_INTERVAL_SEC)
        )
        self._poll_input.setText(str(self._config.get("poll_interval", 30)))
        self._poll_input.setFixedWidth(80)
        self._poll_input.setPlaceholderText("30")
        poll_row.addWidget(self._poll_input)
        sec_label = QLabel("sec")
        sec_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding-left: 4px;")
        poll_row.addWidget(sec_label)
        poll_row.addStretch()
        layout.addLayout(poll_row)

        layout.addWidget(_muted_label(
            f"How often to check TorBox for status updates. "
            f"({MIN_POLL_INTERVAL_SEC}–{MAX_POLL_INTERVAL_SEC} seconds)"
        ))

        # ---- Error label ----
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e05050; font-size: 8pt;")
        layout.addWidget(self._error_label)

        layout.addStretch()

        # ---- Buttons ----
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_key_visibility(self, checked: bool):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._key_input.setEchoMode(mode)

    def _browse_directory(self):
        current = self._dir_input.text().strip()
        start   = current if os.path.isdir(current) else os.path.expanduser("~")
        chosen  = QFileDialog.getExistingDirectory(self, "Select Download Directory", start)
        if chosen:
            self._dir_input.setText(chosen)

    def _validate_and_accept(self):
        api_key = self._key_input.text().strip()
        if not api_key:
            self._error_label.setText("API key is required.")
            return
        self.accept()

    def get_config(self) -> dict:
        """
        Return the updated config dict. Call only after exec() == Accepted.
        Returns a full dict — callers can pass it straight to save_config().
        Preserves any keys not managed by this dialog (e.g. columns visibility).
        """
        updated = dict(self._config)
        updated["api_key"]          = self._key_input.text().strip()
        updated["download_dir"]     = self._dir_input.text().strip()
        try:
            poll_val = int(self._poll_input.text())
            poll_val = max(MIN_POLL_INTERVAL_SEC, min(MAX_POLL_INTERVAL_SEC, poll_val))
        except ValueError:
            poll_val = 30
        updated["poll_interval"] = poll_val
        updated["minimize_to_tray"] = self._tray_cb.isChecked()
        return updated


# ---------------------------------------------------------------------------
# AboutDialog
# ---------------------------------------------------------------------------

class AboutDialog(QDialog):
    """
    About dialog: app name, version, brief description, Ko-fi link.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(400)
        self.setFixedHeight(260)
        self.setModal(True)
        _apply_dialog_style(self)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # App name
        name_label = QLabel(APP_NAME)
        name_label.setStyleSheet(
            f"color: {COLOR_ACCENT}; font-size: 16pt; font-weight: bold;"
        )
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # Subtitle + version
        sub_label = QLabel(f"{APP_SUBTITLE}  •  v{APP_VERSION}")
        sub_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 9pt;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_label)

        # Divider
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {COLOR_BORDER};")
        layout.addWidget(line)

        # Description
        desc = QLabel(
            "PyQt6 desktop client for TorBox debrid service.\n"
            "Manage torrents, magnets, hoster links, and NZBs\n"
            "from a single unified queue."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 9pt;")
        layout.addWidget(desc)

        layout.addStretch()

        # Ko-fi link
        kofi_btn = QPushButton("♥  Support on Ko-fi")
        kofi_btn.setObjectName("accent")
        kofi_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kofi_btn.clicked.connect(lambda: webbrowser.open(KOFI_URL))
        kofi_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(kofi_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
