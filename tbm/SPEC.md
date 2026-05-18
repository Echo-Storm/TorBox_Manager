# TorBox Manager — EchoStorm Edition
# Project Specification v0.5

---

## Purpose

A PyQt6 desktop client for the TorBox debrid service. Accepts torrents, magnet links,
hoster URLs, and NZB files; queues them on TorBox's servers; and downloads completed
files directly to a user-defined local directory. Companion tool to Echo Audio Converter
— same stack, same conventions, same EchoStorm visual identity.

---

## Distribution

Primary distribution is a standalone Windows exe built via GitHub Actions. No Python
installation required on the end user's machine.

- **Build:** PyInstaller onefile + windowed, UPX disabled (avoids AV false positives)
- **Runner:** `windows-latest` GitHub Actions runner — produces a genuine Windows PE
  executable, not a Linux ELF binary
- **Trigger:** workflow fires on push to `main` (build only) and on Release publish
  (build + upload exe as release asset)
- **Spec:** `.github/workflows/build.yml` at repo root; source lives under `tbm/`

Source-only users can still run via `launch.bat` (Python 3.10+, self-contained venv).

---

## Frozen Path Handling

PyInstaller onefile extracts to a temporary directory at runtime (`sys._MEIPASS`).
Without correction, `config.json` and the log file would be written there and lost
on each launch.

**Fix applied in v0.4.0:**

`config.py` — `_config_path()`:
```python
if getattr(sys, "frozen", False):
    here = os.path.dirname(os.path.abspath(sys.executable))
else:
    here = os.path.dirname(os.path.abspath(__file__))
```

`main.py` — `_setup_logging()`: identical frozen/unfrozen detection for `log_dir`.

Both `config.json` and `TorBox_Manager_Log.txt` land next to the exe in all cases.

---

## Tech Stack

- Python 3.10+
- PyQt6 (UI, threading, tray)
- requests (all HTTP — synchronous, called only from worker threads)
- JSON (config persistence — no database)
- PyInstaller (exe packaging — build-time only, not a runtime dependency)
- Isolated venv for source runs, launched via `launch.bat`

---

## Repo Structure

```
TorBox_Manager/               ← repo root
├── .github/
│   └── workflows/
│       └── build.yml         ← GitHub Actions: builds exe, uploads to release
├── tbm/                      ← all source
│   ├── assets/
│   │   ├── TorBox_Manager.ico  ← 7-size ICO (16–256px, 32bpp) — exe + taskbar icon
│   │   └── tray_icon.png       ← 64×64 PNG — system tray icon
│   ├── main.py
│   ├── ui.py
│   ├── dialogs.py
│   ├── api.py
│   ├── worker.py
│   ├── config.py
│   ├── constants.py
│   ├── requirements.txt
│   ├── launch.bat
│   ├── README.md
│   ├── CHANGELOG.md
│   └── SPEC.md
└── README.md                 ← repo-level, shown on GitHub; targets exe users
```

Files created at runtime (next to exe or next to source, depending on run mode):
- `config.json` — written on first Settings save
- `TorBox_Manager_Log.txt` — overwritten on each launch (current session only)

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
│  v0.4.0  ─────────── | TORBOX MANAGER | ─────────── ECHOSTORM EDITION │
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
| LinkRequestWorker | On-demand | Fetches a time-limited download URL without streaming; used by right-click context menu for Copy Link / Open in Browser |

All workers communicate back to the main thread exclusively via Qt signals.

### DownloadWorker detail
- Takes an explicit `file_id` parameter — caller decides which file to download
- Retries link resolution up to 3 times with 3s delay (TorBox transient errors)
- Writes to `filename.part` during download; renames to final name on completion
- Incomplete `.part` files are deleted on error
- Filename extracted from Content-Disposition header (RFC 5987 + plain fallback)
- Falls back to item display name; sanitises result for Windows filesystem

### Multi-file torrent flow
1. User clicks Download on a torrent row
2. `ui.py` checks `len(item["files"]) > 1`
3. If true: open `FilePickerDialog` (modal) — table of files with name, size, checkbox
4. Select All / Deselect All buttons; OK disabled until at least one file checked
5. On OK: one `DownloadWorker` dispatched per checked file
6. Single-file torrents and all webdl/usenet items skip the dialog entirely

---

## TorBox API Endpoints (v1)

Base URL: `https://api.torbox.app/v1/api`
Auth: `Authorization: Bearer <api_key>` header on every request.
User-Agent: `TorBoxManager/<version>` on every request.

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
| `progress` | int or float | 0–100 (int) or 0.0–1.0 (float) depending on state — normalised by `_parse_progress()` |
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

- Icon: `assets/tray_icon.png` — 64×64 green tech-cube PNG
- Auto-generated programmatically if file is missing
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
| max_concurrent_downloads | int | 3 | Range 1–10; Download All queues excess items |
| minimize_to_tray | bool | true | Hide vs quit on window close |
| tray_notifications | bool | false | Tray popup on download complete |
| columns | dict | all true | Per-column visibility flags |
| window_geometry | str | "" | Hex-encoded QByteArray from saveGeometry() |

Stored in `config.json` next to the exe (frozen) or next to the source files (dev).
No registry, no AppData.

---

## Logging

- File: `TorBox_Manager_Log.txt` next to exe (frozen) or source files (dev)
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

## Download Concurrency

`_downloading: dict[str, int]` tracks in-flight workers (key → count, >1 for multi-file
torrents). `_download_queue: list[tuple[str, dict]]` is the FIFO pending queue.

`_on_download_all()` starts up to `max_concurrent_downloads` items immediately and appends
the rest to `_download_queue`. `_try_start_queued()` is called from `_on_download_finished`
and `_on_download_error` to drain the queue as slots free up. Items are looked up fresh from
`_row_items` at dequeue time so stale snapshots are never used.

`_update_poll_interval()` checks `isHidden()` and `not _downloading`; if both are true it
sets the timer to `max(poll_interval, IDLE_POLL_INTERVAL_SEC)` (300 s). Restores to
`poll_interval` the moment a download starts or the window is shown.

## Row Context Menu

Right-click any row → `_on_row_context_menu()`. Dispatches a `LinkRequestWorker` for Copy
Download Link and Open in Browser actions. Worker emits the URL on success; the slot then
writes clipboard or calls `webbrowser.open()`. All three actions (Copy Name, Copy Link,
Open in Browser) are shown/hidden based on item type and status.

## Usenet Hash Names

`_add_queue_row()` and `_update_queue_row()` both run `re.fullmatch(r'[0-9a-fA-F]{20,}',
name)` on usenet items. Match → italic + COLOR_TEXT_MUTED + tooltip. No match (or name
changes on a later poll) → bold + COLOR_TEXT + tooltip cleared.

---

## Version

v0.5.0 — 2026-05-18
