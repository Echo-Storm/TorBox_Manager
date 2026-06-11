# TorBox Manager — EchoStorm Edition
# Project Specification v0.7.2

---

## Purpose

A PyQt6 desktop client for the TorBox debrid service. Accepts torrents, magnet links,
hoster URLs, and NZB files; queues them on TorBox's servers; downloads completed files
directly to a local directory; and maintains a persistent download history.

---

## Distribution

Primary: standalone Windows exe via GitHub Actions. No Python required on the end user's machine.

- **Build:** PyInstaller onefile + windowed, UPX disabled (avoids AV false positives)
- **Runner:** `windows-latest` GitHub Actions
- **Trigger:** push to `main` (build only); Release publish (build + upload exe as asset)
- **Spec:** `.github/workflows/build.yml`; source lives under `tbm/`

Source users: Python 3.10+, run `launch.bat` (self-contained venv, auto-installs deps).

---

## Frozen Path Handling

PyInstaller onefile extracts to a temp dir (`sys._MEIPASS`) at runtime. Without correction
`config.json` and the log would be written there and lost on each launch.

`config.py`, `history.py`, and `main.py` all use the same pattern:

```python
if getattr(sys, "frozen", False):
    here = os.path.dirname(sys.executable)
else:
    here = os.path.dirname(os.path.abspath(__file__))
```

All persistent files (`config.json`, `download_history.json`, `TorBox_Manager_Log.txt`)
land next to the exe in all run modes.

---

## Tech Stack

| Package | Purpose |
|---------|---------|
| Python 3.10+ | Language |
| PyQt6 | UI, threading model, system tray, file system watcher |
| requests | HTTP — synchronous, called only from worker threads |
| py7zr | .7z extraction (optional pip dep; pure Python) |
| rarfile | .rar extraction (optional pip dep; requires unrar binary) |
| JSON / stdlib | Config and history persistence — no database |
| PyInstaller | Exe packaging — build-time only |

---

## Repo Structure

```
TorBox_Manager/
├── .github/
│   └── workflows/
│       └── build.yml          ← GitHub Actions: builds exe, uploads to release
├── tbm/                       ← all source
│   ├── assets/
│   │   ├── TorBox_Manager.ico ← 7-size ICO (16–256px) — exe + taskbar icon
│   │   └── tray_icon.png      ← 64×64 PNG — system tray icon
│   ├── main.py                ← bootstrap, logging, sys.excepthook
│   ├── ui.py                  ← MainWindow, all widget layout and slots
│   ├── dialogs.py             ← all modal dialogs
│   ├── api.py                 ← TorBox HTTP communication only
│   ├── worker.py              ← QRunnable workers and their signal classes
│   ├── config.py              ← config.json read/write
│   ├── history.py             ← download_history.json read/write
│   ├── constants.py           ← static values only
│   ├── requirements.txt
│   ├── launch.bat
│   ├── README.md
│   ├── CHANGELOG.md
│   └── SPEC.md
└── README.md                  ← repo-level, shown on GitHub; targets exe users
```

Runtime files (written next to exe or next to source):
- `config.json` — created on first Settings save
- `download_history.json` — created on first completed download
- `TorBox_Manager_Log.txt` — overwritten each launch (current session only)

---

## Module Responsibilities (hard boundaries — no cross-talk)

| Module | Owns | Never touches |
|--------|------|---------------|
| `api.py` | HTTP requests, URL building, response parsing | Qt, UI, threads |
| `worker.py` | QRunnable subclasses, signals, thread lifecycle | Direct UI calls |
| `ui.py` | Widget layout, slot connections, display logic | requests, HTTP |
| `dialogs.py` | Modal dialogs, input validation | API calls, workers |
| `config.py` | config.json read/write, default values | Qt, API |
| `history.py` | download_history.json read/write | Qt, API |
| `constants.py` | Static values only | Everything |
| `main.py` | App bootstrap, logging setup | Business logic |

Workers post results back to the UI exclusively via Qt signals — never direct widget
calls from a background thread.

---

## UI Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  v0.7.1  ────────── | TORBOX MANAGER | ────────── ECHOSTORM EDITION       │
├──────────────────┬───────────────────────────────────────────────────────┤
│  LEFT PANEL      │  [Queue] [History]          ← tab bar                 │
│  (fixed 220px)   ├───────────────────────────────────────────────────────┤
│                  │  [Filter queue…]  ✕  n items  ← filter bar (Queue tab)│
│  ADD             ├───────────────────────────────────────────────────────┤
│  [+ Magnet]      │  QUEUE TABLE (Queue tab)                              │
│  [+ Torrent]     │  Name|Type|Status|Size|Seeds|Peers|Ratio|ETA|        │
│  [+ Hoster Link] │  Added|Progress|Download|Delete                       │
│  [+ NZB]         │                                                       │
│                  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│  QUEUE           │  HISTORY TABLE (History tab)                          │
│  [Refresh Now]   │  [n downloads]  [Clear History]  ← header             │
│  [Clear Done]    │  Time|Name|File|Type|Size                             │
│  [Clear All]     │                                                       │
│                  ├───────────────────────────────────────────────────────┤
│                  │  LOG  [errors only]                                   │
│  ⚙ Settings      │  HH:MM:SS [INFO] ...                                  │
│                  │  HH:MM:SS [ERROR] ...                                 │
│                  ├───────────────────────────────────────────────────────┤
│                  │  ● status   [⬆ update]  [⬇ Download All] | ♥ donate  │
└──────────────────┴───────────────────────────────────────────────────────┘
```

Right content area (tabs + log + status bar) is framed by a continuous 2px vertical rule
on the right edge, with 12px gap to the window edge. Status bar is a plain QWidget in the
layout, not `QMainWindow.setStatusBar()`, so the border runs through it uninterrupted.

---

## Queue Table Columns

| Column | Always visible | Notes |
|--------|---------------|-------|
| Name | Yes | Bold; stores row key in UserRole |
| Type | Yes | Colored badge widget (Torrent / Magnet / Hoster Link / NZB) |
| Status | Yes | Compound display: "Cached · Seeding", "Downloading", etc. |
| Size | Yes | Human-readable MB / GB |
| Seeds | Optional | Right-click header to toggle; persisted in config |
| Peers | Optional | Right-click header to toggle |
| Ratio | Optional | Right-click header to toggle |
| ETA | Optional | Right-click header to toggle |
| Added | Optional | Right-click header to toggle |
| Progress | Yes | QProgressBar; indeterminate at 0%, solid green when Ready |
| Download | Yes | Enabled when status=Ready; becomes "Open" after local download; "Retry" on error |
| Delete | Yes | Confirms then calls TorBox delete API; row removed optimistically |

---

## History Table Columns

| Column | Notes |
|--------|-------|
| Time | ISO-8601 local time, truncated to minute |
| Name | TorBox item name; left-aligned bold |
| File | Actual downloaded filename; left-aligned |
| Type | Badge widget matching queue table |
| Size | File size from disk at completion; falls back to TorBox API size |

Double-click any row → opens containing folder in Explorer and selects the file.
Right-click → Copy Path or Open in Explorer.

---

## Workers

| Worker | Trigger | Purpose |
|--------|---------|---------|
| `PollWorker` | QTimer (every N sec) | Fetches all three queues, emits unified list |
| `DownloadWorker` | Download button / Download All | Resolves link, streams file to disk with .part rename |
| `AddWorker` | Add buttons / watch folder | Submits a single add operation (lambda in, success+detail out) |
| `DeleteWorker` | Delete button / auto-delete | Deletes a single item; passes row_key through signal |
| `LinkRequestWorker` | Right-click Copy Link / Open in Browser | Fetches time-limited URL without streaming |
| `UpdateCheckWorker` | 3 s after startup | Checks GitHub Releases API for newer version; silent on error |
| `ExtractWorker` | After DownloadWorker.finished (if auto_extract=True) | Extracts archive on background thread; optional delete-after |

All workers communicate back to the main thread via Qt signals only.

### DownloadWorker detail
- Takes explicit `file_id` — caller decides which file; no silent fallback to files[0]
- Retries link resolution up to 3 times with 3 s delay (TorBox transient errors)
- Writes to `filename.part` during download; renames to final name on completion
- Incomplete `.part` files deleted on error
- Filename from Content-Disposition (RFC 5987 + plain fallback); URL-decoded and sanitised

### Multi-file torrent flow
1. User clicks Download on a torrent row
2. `ui.py` checks `len(item["files"]) > 1`
3. If true: `FilePickerDialog` — table of files with name, size, checkbox per file
4. One `DownloadWorker` dispatched per selected file; all share the same row key
5. Progress bar reflects last worker to emit; Download button shows "Download" (not "Open")
   until all files are complete

### Concurrency
- `_downloading: dict[str, int]` — maps row_key to count of active workers
- `_download_queue: list[tuple[str, dict]]` — FIFO queue for pending downloads
- On each worker finish/error: decrement count; drain queue up to the concurrency limit

---

## Add Inputs

| Button | Dialog | Validation |
|--------|--------|-----------|
| + Magnet | Text input + Paste button | `magnet:` prefix |
| + Torrent | QFileDialog `.torrent` | File must exist |
| + Hoster Link | Multi-line text input + Paste | `http(s)://` prefix; one URL per line |
| + NZB | QFileDialog `.nzb` | File must exist |

All four run on a background `AddWorker` thread — the UI is never blocked.

---

## Watch Folder

- `QFileSystemWatcher` monitors a single directory for changes
- 1-second `QTimer.singleShot` debounce on `directoryChanged` signal to allow file copies to finish
- Scans for `.torrent` and `.nzb` files on startup and on every directory change
- `_watch_submitted: set[str]` — tracks paths submitted this session to prevent double-submission
- On failure: path removed from set so retry is possible on next scan
- Optionally deletes the source file from the watch folder on successful submission

---

## Auto-Extract

- Triggered in `_on_download_finished` when `auto_extract=True` and file extension is recognized
- Supported: `.zip` (stdlib), `.tar` / `.tar.gz` / `.tgz` / `.tar.bz2` / `.tar.xz` (stdlib),
  `.7z` (py7zr, optional), `.rar` (rarfile + unrar, optional)
- Runs on `ExtractWorker` background thread — UI never blocks during extraction
- `filter="data"` passed to `tarfile.extractall` on Python 3.12+ to suppress deprecation
  warning and block path-traversal entries; falls back gracefully on older Python
- Optionally deletes the archive file after successful extraction (`delete_after_extract`)

---

## Download History

- `history.py` — pure stdlib, no Qt imports
- Stores to `download_history.json` next to the exe/source
- Capped at 500 entries; oldest entries trimmed when exceeded
- Each entry: `ts` (ISO-8601 local), `name` (TorBox item name), `file` (basename),
  `path` (full local path), `size_bytes` (from disk; fallback to API size), `source_type`
- `hist.append()` called in `_on_download_finished` for every completed file
- History tab auto-refreshes from disk when switched to; displayed newest-first

---

## Polling

- `QTimer` drives `PollWorker` at the configured interval (default 30 s, range 10–300 s)
- `bypass_cache=true` on all list endpoints — required to get fresh data instead of TorBox's
  server-side cached snapshot
- Idle slowdown: when window is hidden to tray and no downloads are active, interval rises
  to `max(configured, 300)` seconds to reduce API load
- `_deleted_keys: set[str]` — suppresses items for one poll cycle after user deletes them
  so they don't flicker back before TorBox finishes processing the delete

---

## Config Keys (config.json)

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `api_key` | str | `""` | TorBox bearer token |
| `download_dir` | str | `""` | Absolute path; prompted on first download if empty |
| `poll_interval` | int | `30` | Seconds; clamped 10–300 |
| `max_concurrent_downloads` | int | `3` | Clamped 1–10 |
| `minimize_to_tray` | bool | `true` | Hide to tray on close |
| `tray_notifications` | bool | `false` | Popup on download complete |
| `window_geometry` | str | `""` | Hex-encoded QByteArray |
| `columns` | dict | all true | Per-column visibility flags |
| `create_subfolder` | bool | `true` | Named subfolder per download |
| `auto_extract` | bool | `true` | Extract archives after download |
| `delete_after_extract` | bool | `false` | Remove archive after extraction |
| `watch_folder_enabled` | bool | `false` | Enable watch folder |
| `watch_folder` | str | `""` | Absolute path to watch |
| `watch_folder_delete` | bool | `true` | Delete file from watch folder on success |
| `delete_from_torbox` | bool | `false` | Delete TorBox entry after local download |

`config.py` deep-merges saved values over `DEFAULTS` on load so new keys added in later
versions are never silently missing for users upgrading from an older config file.
