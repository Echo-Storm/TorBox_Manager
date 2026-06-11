# history.py
# TorBox Manager EchoStorm Edition
#
# Persistent download history. Stores completed downloads as a JSON array
# capped at MAX_ENTRIES. No Qt imports, no business logic — pure read/write.
#
# Each entry dict:
#   {
#     "ts":          "2026-06-11T14:22:00",   # ISO-8601, local time
#     "name":        "My Linux ISO",            # TorBox item name
#     "file":        "debian-12.iso",           # actual downloaded filename
#     "path":        "C:\\Downloads\\...",       # full local path
#     "size_bytes":  1234567890,                # from disk after download
#     "source_type": "torrent"                  # torrent/magnet/webdl/usenet
#   }

import json
import os
import sys
from datetime import datetime

HISTORY_FILENAME = "download_history.json"
MAX_ENTRIES      = 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _history_path() -> str:
    if getattr(sys, "frozen", False):
        here = os.path.dirname(sys.executable)
    else:
        here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, HISTORY_FILENAME)


def _safe_filesize(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load() -> list:
    """Return the full history list, newest-first. Never raises."""
    path = _history_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def append(item: dict, file_path: str) -> bool:
    """
    Build a history entry from the queue item dict and the local file path,
    append it to the history file, and trim to MAX_ENTRIES.

    Returns True on success, False if the file could not be written.
    """
    entry = {
        "ts":          datetime.now().isoformat(timespec="seconds"),
        "name":        item.get("name", ""),
        "file":        os.path.basename(file_path),
        "path":        file_path,
        "size_bytes":  _safe_filesize(file_path) or item.get("size", 0),
        "source_type": item.get("source_type", ""),
    }

    history = load()
    history.append(entry)
    if len(history) > MAX_ENTRIES:
        history = history[-MAX_ENTRIES:]

    path = _history_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        return True
    except OSError as exc:
        print(f"[history] WARNING: Could not write {path}: {exc}")
        return False


def clear() -> bool:
    """Wipe all history entries. Returns True on success."""
    path = _history_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return True
    except OSError as exc:
        print(f"[history] WARNING: Could not clear {path}: {exc}")
        return False
