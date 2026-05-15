# TorBox Manager — EchoStorm Edition
# Project Specification v0.3

---

## Purpose

A PyQt6 desktop client for the TorBox debrid service. Accepts torrents, magnet links,
hoster URLs, and NZB files; queues them on TorBox's servers; and downloads completed
files directly to a user-defined local directory. Companion tool to Echo Audio Converter
— same stack, same conventions, same EchoStorm visual identity.

---

## Tech Stack

- Python 3.10+
- PyQt6 (UI, threading, tray)
- requests (all HTTP — synchronous, called only from worker threads)
- JSON (config persistence — no database)
- Isolated venv, launched via launch.bat

---

## File Structure

```
TorBox_Manager/
├── main.py           # QApplication entry point, file logging, MainWindow launch
├── ui.py             # MainWindow: left panel, queue table, log strip, status bar widget
├── dialogs.py        # AddMagnetDialog, AddLinkDialog, SettingsDialog, AboutDialog
├── api.py            # All TorBox API calls — returns plain dicts, zero Qt imports
├── worker.py         # QRunnable workers: Poll, Download, Add, Delete
├── config.py         # load_config() / save_config() — JSON file, no logic
├── constants.py      # API base URL, version string, theme colors, column defs
├── assets/
│   └── tray_icon.png # 32x32 tray icon — auto-generated placeholder if missing
├── requirements.txt  # PyQt6, requests
└── launch.bat        # Creates venv on first run, installs deps, launches main.py
```

---

## Module Responsibilities (hard boundaries — no cross-talk)

| Module       | Owns                                              | Never touches          |
|--------------|---------------------------------------------------|------------------------|
| api.py       | HTTP requests, URL building, response parsing     | Qt, UI, threads        |
| worker.py    | QRunnable subclasses, signals, thread lifecycle   | Direct UI calls        |
| ui.py        | Widget layout, slot connections, display logic    | requests, HTTP         |
| dialogs.py   | Modal dialogs, input validation                   | API calls, workers     |
| config.py    | JSON read/write, default values                   | Qt, API                |
| constants.py | Static values only                                | Everything             |
| main.py      | App bootstrap, logging setup, top-level wiring    | Business logic         |

Workers post results back to the UI exclusively via Qt signals — never direct widget calls
from a thread.

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  v0.3.0  ─────────── | TORBOX MANAGER | ─────────── ECHOSTORM EDITION │
├──────────────────┬──────────────────────────────────────────────────┤
│  LEFT PANEL      │  QUEUE TABLE                                     │
│  (fixed 220px)   │  Name|Type|Status|Size|Seeds|Peers|Ratio|ETA|   │
│                  │  Added|Progress|Download|Delete                  │
│  ADD             │                                                  │
│  [+ Magnet]      │  (rows populate here)                            │
│  [+ Torrent]     │                                                  │
│  [+ Hoster Link] ├──────────────────────────────────────────────────┤
│  [+ NZB]         │  LOG  [errors only]                              │
│                  │  HH:MM:SS [INFO] ...                             │
│  QUEUE           │  HH:MM:SS [ERROR] ...                            │
│  [Refresh Now]   │                                                  │
│  [Clear Done]    ├──────────────────────────────────────────────────┤
│  [Clear All]     │  ● status text    [Download All] | ♥ donate      │
│                  │                                                  │
│  ⚙ Settings      │                                                  │
└──────────────────┴──────────────────────────────────────────────────┘
```

Right content area (table + log + status bar) is framed by a continuous 2px vertical
rule on the right edge, with 12px gap to the window edge.
Status bar is a plain QWidget in the layout — not QMainWindow.setStatusBar() — so the
border runs through it uninterrupted.

---

## Queue Table Columns

| Column   | Always visible | Notes |
|----------|---------------|-------|
| Name     | Yes | Bold; stores row key in UserRole |
| Type     | Yes | Colored badge widget |
| Status   | Yes | Compound display text with color coding |
| Size     | Yes | Human-readable MB/GB |
| Seeds    | Optional | Right-click header to toggle |
| Peers    | Optional | Right-click header to toggle |
| Ratio    | Optional | Right-click header to toggle |
| ETA      | Optional | Right-click header to toggle |
| Added    | Optional | Right-click header to toggle |
| Progress | Yes | QProgressBar; indeterminate when state=0, solid green when ready |
| Download | Yes | Enabled only when cached==True; rewires to "Open" after local download |
| Delete   | Yes | Always enabled; confirms then calls TorBox delete endpoint |

Column visibility is persisted in config.json under "columns".

---

## Add Inputs (four explicit buttons, no auto-detect)

- **+ Magnet** — text input dialog with clipboard paste button; validates `magnet:` prefix
- **+ Torrent** — QFileDialog, `.torrent` filter, posts file bytes to API
- **+ Hoster Link** — text input dialog with clipboard paste button; validates `http(s)://` prefix
- **+ NZB** — QFileDialog, `.nzb` filter, posts file bytes to API

All four add operations run on a background AddWorker thread. The UI is never blocked.

---

## Workers

| Worker | Type | Purpose |
|--------|------|---------|
| PollWorker | Recurring (QTimer) | Fetches all three queues, emits unified list |
| DownloadWorker | One per file | Resolves download link, streams file to disk with .part rename |
| AddWorker | One-shot | Submits a single add operation; takes a lambda, emits (success, detail) |
| DeleteWorker | One-shot | Deletes a single item; passes row_key through signal for UI removal |

All workers communicate back to the main thread exclusively via Qt signals.

### DownloadWorker detail
- Retries link resolution up to 3 times with 3s delay (TorBox transient errors)
- Writes to `filename.part` during download; renames to final name on completion
- Incomplete `.part` files are deleted on error
- Filename extracted from Content-Disposition header (RFC 5987 + plain fallback)
- Falls back to item display name; sanitises result for Windows filesystem

---

## TorBox API Endpoints (v1)

Base URL: `https://api.torbox.app/v1/api`  
Auth: `Authorization: Bearer <api_key>` header on every request.

| Action | Method | Endpoint |
|--------|--------|----------|
| Add magnet / torrent | POST | /torrents/createtorrent |
| Add hoster link | POST | /webdl/createwebdownload |
| Add NZB | POST | /usenet/createusenetdownload |
| List torrents | GET | /torrents/mylist?bypass_cache=true |
| List web downloads | GET | /webdl/mylist?bypass_cache=true |
| List usenet | GET | /usenet/mylist?bypass_cache=true |
| Request torrent DL link | GET | /torrents/requestdl |
| Request webdl DL link | GET | /webdl/requestdl |
| Request usenet DL link | GET | /usenet/requestdl |
| Delete torrent | POST | /torrents/controltorrent |
| Delete web DL | POST | /webdl/controlwebdownload |
| Delete usenet | POST | /usenet/controlusenetdownload |

All responses: `{ "success": bool, "detail": str, "data": ... }`

**Critical:** `bypass_cache=true` is required on all list endpoints. Without it TorBox
returns a stale server-side snapshot that may only contain the most recently added item.

---

## Confirmed TorBox API Field Names (verified 2026-05-15)

| Field | Type | Notes |
|---|---|---|
| `id` | int | Unique per source type |
| `name` | str | Display name |
| `size` | int | Bytes |
| `progress` | int | 0–100 |
| `download_state` | str | e.g. `"uploading (no peers)"` — not the ready signal |
| `cached` | bool | **Primary ready signal** — True means downloadable now |
| `download_finished` | bool | TorBox-side download complete |
| `magnet` | str or null | URI string for magnet adds, null for .torrent uploads |
| `files` | list | Each entry has `id` (int), `name`, `size`, `short_name` |
| `seeds`, `peers`, `ratio` | int/float | Displayed in optional columns |
| `eta` | int | Seconds; displayed in optional ETA column |
| `created_at` | str | ISO8601; displayed in optional Added column |

**Status mapping:** `cached == True` is the authoritative ready signal. `download_state`
reflects seeding activity and may read `"uploading (no peers)"` even when fully cached.

---

## System Tray

- Icon: green downward arrow on dark rounded square (32×32 PNG)
- Auto-generated programmatically if `assets/tray_icon.png` is missing
- Closing the window hides to tray (configurable — can disable in Settings)
- Double-click tray icon to restore
- Right-click menu: Open / About / Restart / Quit

---

## Settings (SettingsDialog + config.json)

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| api_key | str | "" | TorBox bearer token |
| download_dir | str | "" | Prompted on first download if empty |
| poll_interval | int | 30 | Seconds; range 10–300 |
| minimize_to_tray | bool | true | Hide vs quit on window close |
| columns | dict | all true | Per-column visibility flags |

Stored in `config.json` alongside the script files. No registry, no AppData.

---

## Logging

- File: `TorBox_Manager_Log.txt` alongside script files
- Mode: overwrite on each launch (`mode='w'`) — current session only
- Format: `YYYY-MM-DD HH:MM:SS [LEVEL] message`
- Levels used: DEBUG (file only during dev), INFO, WARN, ERROR
- `sys.excepthook` routes uncaught exceptions to the log file before the process exits
- In-app log strip mirrors the file log with an "errors only" filter toggle

---

## Theme (EchoStorm)

| Element | Value |
|---|---|
| Main background | #181818 |
| Panel background | #1f1f1f |
| Alt row background | #232323 |
| Header bar | #2d1f00 (amber-dark) |
| Accent | #7cb342 (green) |
| Accent dim | #4a6b28 |
| Primary text | #e8e8e8 |
| Muted text | #666666 |
| Button background | #282828 |
| Button hover | #323232 |
| Border | #2a2a2a |
| Border bright | #3a3a3a |
| Row hover | #252f1a |
| UI font | Segoe UI, 9pt |
| Log font | Consolas, 8pt |

---

## Error Handling Philosophy

- Every `api.py` function returns `{ "success": bool, "detail": str, "data": ... }`
- No exceptions bubble up to the UI — workers catch and emit error signals
- `detail` from TorBox is surfaced verbatim — messages are already user-friendly
- Network failures produce a human-readable fallback message
- Delete: row is removed from display immediately on confirm; if the API call fails
  the item reappears on the next poll (logged as WARN)

---

## Version

v0.3.0 — 2026-05-15
