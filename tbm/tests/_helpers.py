# _helpers.py
# TorBox Manager EchoStorm Edition — test suite
#
# Shared fixtures for the offscreen PyQt6 test suite. Not a test module
# itself (leading underscore keeps unittest discovery from picking it up).
#
# Run the suite from tbm/:
#   venv\Scripts\python -m unittest discover -s tests -v
# or run a single file directly:
#   venv\Scripts\python tests\test_downloads.py

import os
import sys

# Must be set before QApplication is constructed.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_TBM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TBM_DIR not in sys.path:
    sys.path.insert(0, _TBM_DIR)

from PyQt6.QtWidgets import QApplication  # noqa: E402

# QApplication can only be constructed once per process — reuse if a prior
# test module in the same run already made one.
app = QApplication.instance() or QApplication(sys.argv)


def make_window(**config_overrides):
    """Build a MainWindow with a throwaway API key and no real network calls."""
    from config import DEFAULTS
    from ui import MainWindow

    config = dict(DEFAULTS)
    config["api_key"] = "test-key"
    config.update(config_overrides)
    return MainWindow(config)


def make_torrent_item(item_id, name, size=1000, cached=True,
                       download_state="seeding", files=None):
    """A minimal fake TorBox torrent item, shaped like api.list_all()'s output."""
    return {
        "id": item_id,
        "name": name,
        "source_type": "torrent",
        "size": size,
        "cached": cached,
        "download_state": download_state,
        "files": files if files is not None else [{"id": 1, "name": "a.bin", "size": size}],
    }


def always_yes(*args, **kwargs):
    """Drop-in replacement for QMessageBox.question that always confirms."""
    from PyQt6.QtWidgets import QMessageBox
    return QMessageBox.StandardButton.Yes
