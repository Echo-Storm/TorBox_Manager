# config.py
# TorBox Manager EchoStorm Edition
#
# Pure read/write JSON config. No Qt imports. No business logic.
# All other modules call load_config() and save_config() — nothing
# reads config.json directly.
#
# Config file is stored alongside the script files (same directory),
# so the whole folder stays self-contained and portable.

import json
import os

from constants import (
    CONFIG_FILENAME,
    COL_VISIBILITY_DEFAULTS,
    DEFAULT_POLL_INTERVAL_SEC,
)

# ---------------------------------------------------------------------------
# Default values
# These are used when config.json doesn't exist yet (first run)
# or when a key is missing (new setting added in a later version).
# ---------------------------------------------------------------------------

DEFAULTS = {
    "api_key":          "",    # TorBox bearer token — required before any API call
    "download_dir":     "",    # absolute path; empty means user hasn't configured it yet
    "poll_interval":    DEFAULT_POLL_INTERVAL_SEC,
    "columns":          dict(COL_VISIBILITY_DEFAULTS),  # optional column visibility
    "minimize_to_tray": True,  # hide to tray on close vs quit
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config_path() -> str:
    """Return the absolute path to config.json, always next to this script."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, CONFIG_FILENAME)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """
    Load config from disk and return a complete settings dict.

    - If the file doesn't exist, returns a copy of DEFAULTS (no file is written yet).
    - If the file exists but is missing keys (upgrade scenario), fills gaps from DEFAULTS.
    - If the file is malformed JSON, logs a warning and returns DEFAULTS.

    Never raises — callers can always expect a valid dict back.
    """
    path = _config_path()

    if not os.path.exists(path):
        return dict(DEFAULTS)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        # Don't crash the app over a bad config file; fall back to defaults.
        # The caller (main.py) will log this via the app logger.
        print(f"[config] WARNING: Could not read {path}: {exc} — using defaults.")
        return dict(DEFAULTS)

    # Fill in any keys that exist in DEFAULTS but not in the saved file.
    # This handles the case where a new setting is added in a later version.
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save_config(config: dict) -> bool:
    """
    Write the given config dict to disk as formatted JSON.

    Returns True on success, False on failure.
    Never raises — callers check the return value if they care.
    """
    path = _config_path()

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except OSError as exc:
        print(f"[config] ERROR: Could not write {path}: {exc}")
        return False


def is_configured(config: dict) -> bool:
    """
    Return True only if the minimum required settings are present.
    Used by the app at startup to decide whether to open Settings immediately.

    Required: api_key must be non-empty.
    download_dir is technically optional (user will be prompted on first download),
    but api_key is hard-required — nothing works without it.
    """
    return bool(config.get("api_key", "").strip())
