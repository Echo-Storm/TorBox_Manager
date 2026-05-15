# TorBox Manager — EchoStorm Edition
# Project Specification v0.1

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
torbox_manager/
├── main.py           # QApplication entry point, tray icon setup, launch MainWindow
├── ui.py             # MainWindow: left control panel, right queue table, log strip, status bar
├── dialogs.py        # AddMagnetDialog, AddLinkDialog, SettingsDialog, AboutDialog
├── api.py            # All TorBox API calls — returns plain dicts, zero Qt imports
├── worker.py         # QRunnable workers: PollWorker (status), DownloadWorker (file fetch)
├── config.py         # load_config() / save_config() — JSON file, no logic
├── constants.py      # API base URL, version string, poll interval, theme colors, column defs
├── assets/
│   └── tray_icon.png # 32x32 tray icon (green arrow on dark bg) — placeholder OK for v0.1
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
| main.py      | App bootstrap, tray setup, top-level wiring       | Business logic         |

Workers post results back to the UI exclusively via Qt signals — never direct widget calls
from a thread. Same pattern used in EAC.

---

## UI Layout

Mirrors Echo Audio Converter's proven structure:

```
┌─────────────────────────────────────────────────────────────────┐
│  [amber top bar]   TORBOX MANAGER   [EchoStorm Edition]         │
├──────────────────┬──────────────────────────────────────────────┤
│  LEFT PANEL      │  QUEUE TABLE                                 │
│  (fixed ~280px)  │  Name | Type | Status | Size | Progress |    │
│                  │  Download | Delete                           │
│  ADD             │                                              │
│  [+ Magnet]      │  (rows populate here)                        │
│  [+ Torrent]     │                                              │
│  [+ Hoster Link] ├──────────────────────────────────────────────┤
│  [+ NZB]         │  LOG STRIP (monospace, timestamped, dark)    │
│                  │  HH:MM:SS [INFO] ...                         │
│  QUEUE           │  HH:MM:SS [ERROR] ...                        │
│  [Refresh Now]   │                                              │
│  [Clear Done]    │                                              │
│  [Clear All]     │                                              │
├──────────────────┴──────────────────────────────────────────────┤
│  Ready                          [Download All]   donate ♥ ko-fi │
└─────────────────────────────────────────────────────────────────┘
```

---

## Queue Table Columns

| Column    | Notes                                                        |
|-----------|--------------------------------------------------------------|
| Name      | Filename or magnet name from TorBox response                 |
| Type      | Icon: 🧲 Magnet / 📄 Torrent / 🔗 Link / 📰 NZB             |
| Status    | Queued / Downloading / Ready / Error                         |
| Size      | Human-readable (MB / GB)                                     |
| Progress  | QProgressBar — active during TorBox-side download, green when done |
| Download  | Button — enabled only when Status == Ready                   |
| Delete    | Button — always enabled; calls TorBox delete endpoint        |

---

## Add Inputs (four explicit buttons, no auto-detect)

- **+ Magnet** — text input dialog, accepts `magnet:?xt=...` strings
- **+ Torrent** — QFileDialog, `.torrent` filter, posts file bytes to API
- **+ Hoster Link** — text input dialog, accepts any URL
- **+ NZB** — QFileDialog, `.nzb` filter, posts file bytes to API

Each button calls a different api.py function but the result lands in the same queue table.

---

## TorBox API Endpoints (v1)

Base URL: `https://api.torbox.app/v1/api`
Auth: `Authorization: Bearer <api_key>` header on every request.

| Action              | Method | Endpoint                          |
|---------------------|--------|-----------------------------------|
| Add magnet          | POST   | /torrents/createtorrent           |
| Add torrent file    | POST   | /torrents/createtorrent           |
| Add hoster link     | POST   | /webdl/createwebdownload          |
| Add NZB             | POST   | /usenet/createusenetdownload      |
| List torrents       | GET    | /torrents/mylist                  |
| List web downloads  | GET    | /webdl/mylist                     |
| List usenet         | GET    | /usenet/mylist                    |
| Request DL link     | GET    | /torrents/requestdl               |
| Request DL link     | GET    | /webdl/requestdl                  |
| Request DL link     | GET    | /usenet/requestdl                 |
| Delete torrent      | POST   | /torrents/controltorrent          |
| Delete web DL       | POST   | /webdl/controlwebdownload         |
| Delete usenet       | POST   | /usenet/controlusenetdownload     |

All responses: `{ "success": bool, "detail": str, "data": ... }`
On `success: false`, surface `detail` string directly in the log strip and status bar.

---

## Workers

**PollWorker** (QRunnable, repeating via QTimer)
- Fires every 30 seconds (configurable in settings)
- Calls all three list endpoints
- Emits signal with unified list of queue items
- UI slot receives the list and updates table rows in place

**DownloadWorker** (QRunnable, one per download)
- Takes a queue item and a resolved download URL
- Streams the file to the configured download directory
- Emits progress signals (bytes received / total) → QProgressBar on that row
- Emits completion signal → row status updates, progress bar goes solid green

---

## System Tray

- Icon: green downward arrow on dark rounded square (32x32 PNG)
- Closing the window hides it to tray (does not quit)
- Right-click tray menu:
  - Open
  - About
  - Restart
  - Quit

---

## Settings (SettingsDialog + config.json)

| Setting       | Type   | Default          |
|---------------|--------|------------------|
| api_key       | str    | ""               |
| download_dir  | str    | ""               |
| poll_interval | int    | 30 (seconds)     |

Stored in `config.json` alongside the script files. No registry, no AppData.

---

## Theme (EchoStorm)

| Element            | Value         |
|--------------------|---------------|
| Background         | #1e1e1e       |
| Panel background   | #252525       |
| Header bar         | #3d2b00 (amber-dark) |
| Accent / text      | #7cb342 (green) |
| Muted text         | #888888       |
| Button background  | #2e2e2e       |
| Button hover       | #383838       |
| Progress (active)  | #7cb342       |
| Progress (done)    | #7cb342 solid |
| Font               | Segoe UI or system sans-serif, 9–10pt |
| Log font           | Consolas or monospace, 8pt |

---

## Status Bar

- Left: one-line status text ("Ready", "Polling...", "Downloading filename.mkv...", error detail)
- Right: `[Download All]` button (triggers DownloadWorker for all Ready items)
- Far right: `donate ♥ ko-fi` — plain text link, opens https://ko-fi.com/xechostormx in browser

---

## Error Handling Philosophy

- Every api.py function returns a dict with at minimum `success` (bool) and `detail` (str)
- No exceptions bubble up to the UI — workers catch and emit error signals
- `detail` from TorBox is shown verbatim — no translation layer needed, TorBox messages are user-friendly
- Network failures get a human-readable fallback: "Could not reach TorBox — check connection"

---

## Development Order (planned)

1. constants.py
2. config.py
3. api.py
4. worker.py
5. dialogs.py
6. ui.py
7. main.py
8. launch.bat + requirements.txt

---

## Version

v0.1.0 — initial build
