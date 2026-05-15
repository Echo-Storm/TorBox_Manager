# TorBox Manager — EchoStorm Edition

A PyQt6 desktop client for the [TorBox](https://torbox.app) debrid service.  
Manages torrents, magnet links, hoster URLs, and NZBs from a single unified queue — with in-app file download, live progress bars, and system tray support.

> Companion tool to [Echo Audio Converter](https://github.com/xechostormx). Same stack, same conventions, same aesthetic.

---

## Features

- **Four add types** — Magnet link, Torrent file, Hoster URL, NZB file
- **Clipboard paste buttons** — one-click paste in the Magnet and Hoster Link dialogs
- **Unified queue table** — all active TorBox items in one view regardless of type
- **Optional columns** — Seeds, Peers, Ratio, ETA, Added; right-click the column header to show/hide
- **In-app download** — files stream directly to your chosen folder with a live progress bar
- **Auto-polling** — queue refreshes on a configurable interval (default 30 seconds)
- **Non-blocking UI** — add and delete operations run on background threads; the UI never freezes
- **Log strip** — timestamped event log with an "errors only" filter toggle
- **System tray** — minimizes to tray on close; Open / About / Restart / Quit menu
- **EchoStorm dark theme** — matches Echo Audio Converter's visual identity
- **Self-contained** — single folder, isolated venv, no installer, no registry

---

## Requirements

- Windows 10 / 11
- Python 3.10 or newer — [python.org](https://www.python.org/downloads/)
- A [TorBox](https://torbox.app) account and API key

---

## Quick Start

1. **Download or clone** this repository into a folder of your choice
2. **Double-click `launch.bat`**  
   On first run it creates a virtual environment and installs all dependencies automatically. This takes about a minute.
3. The app opens and immediately prompts for your **API key**  
   Find it at torbox.app → Account → API
4. Set your **download directory** in the same Settings dialog
5. Hit **Save** — you're ready

All future launches are instant: just double-click `launch.bat` (or pin it to your taskbar / desktop as a shortcut).

---

## Notes

- **Queue population** — items appear as TorBox registers each add. Adding a batch may take a few seconds per item.
- **"Found Cached Torrent"** — if TorBox already has a torrent cached it reuses it; your item will appear as Ready almost immediately.
- **Download errors** — if a torrent shows "error processing your request" on every attempt it may be a bad cache entry on TorBox's side. Delete it, re-add it, or contact TorBox support.
- **Log file** — `TorBox_Manager_Log.txt` is overwritten on each launch. It contains the current session only. For persistent history, copy it before restarting.
- **Multi-file torrents** — currently downloads the first file in a torrent's file list. A file picker dialog is planned for a future version.

---

## File Structure

```
TorBox_Manager/
├── main.py                  Entry point — logging, QApplication, MainWindow
├── ui.py                    MainWindow — left panel, queue table, log strip, status bar
├── dialogs.py               Add Magnet, Add Link, Settings, About dialogs
├── api.py                   All TorBox API calls — no Qt, no threads
├── worker.py                PollWorker, DownloadWorker, AddWorker, DeleteWorker
├── config.py                JSON config load/save
├── constants.py             API URLs, theme colors, column indices, static values
├── assets/
│   └── tray_icon.png        32×32 tray icon (auto-generated placeholder if missing)
├── requirements.txt         PyQt6, requests
├── launch.bat               First-run venv setup + app launcher
├── config.json              Created on first save — API key, download dir, settings
└── TorBox_Manager_Log.txt   Created on launch — current session events and errors
```

---

## Settings

| Setting | Description | Default |
|---|---|---|
| API Key | TorBox bearer token — required | *(empty)* |
| Download Directory | Where completed files are saved | *(prompted on first download)* |
| Poll Interval | How often to check TorBox for status updates | 30 seconds |
| Minimize to Tray | Hide to tray on close instead of quitting | Enabled |

Settings are stored in `config.json` alongside the script files. No registry, no AppData.

---

## Roadmap

### v0.1 ✓
Four add types, unified queue, in-app download, system tray, EchoStorm theme.

### v0.2 ✓
Optional queue columns (Seeds, Peers, Ratio, ETA, Added), right-click column visibility,
auto-retry on transient download link errors, minimize-to-tray setting.

### v0.3 ✓
Clipboard paste buttons, threaded add/delete, log filter, status bar breakdown,
layout polish, log file overwrite on startup.

### v0.4 (planned)
- Multi-file torrent picker dialog
- Pause polling when minimized with no active downloads

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| PyQt6 | ≥ 6.5.0 | UI framework, threading, system tray |
| requests | ≥ 2.28.0 | All HTTP communication with TorBox API |

Both are installed automatically by `launch.bat` on first run.

---

## Support

If this saves you time, a Ko-fi goes a long way:  
**[ko-fi.com/xechostormx](https://ko-fi.com/xechostormx)** ♥

---

## License

MIT License — see `LICENSE` for details.
