# TorBox Manager — EchoStorm Edition

A PyQt6 desktop client for the [TorBox](https://torbox.app) debrid service.  
Manages torrents, magnet links, hoster URLs, and NZBs from a single unified queue — with in-app file download, live progress bars, and system tray support.

> Companion tool to [Echo Audio Converter](https://github.com/xechostormx). Same stack, same conventions, same aesthetic.

---

## Screenshot

*(coming soon — v0.1 first build)*

---

## Features

- **Four add types** — Magnet link, Torrent file, Hoster URL, NZB file
- **Unified queue table** — all active TorBox items in one view regardless of type
- **In-app download** — files stream directly to your chosen folder with a live progress bar
- **Auto-polling** — queue refreshes on a configurable interval (default 30 seconds)
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

- **Queue population** — items appear one at a time as TorBox registers each add. This is normal. Adding a batch of torrents takes a few seconds per item to appear.
- **"Found Cached Torrent"** — if TorBox already has a torrent cached, it reuses it. Your item will appear as Ready almost immediately.
- **Download errors** — if a specific torrent shows "error processing your request" on every attempt, it may be a bad cache entry on TorBox's side. Delete it and try re-adding, or report it to TorBox support.
- **Debug logging** — the log strip shows `[DEBUG]` lines during polling. This is intentional during v0.1 development and will be cleaned up for v1.0.

---

## File Structure

```
torbox_manager/
├── main.py              Entry point — logging, QApplication, MainWindow
├── ui.py                MainWindow — left panel, queue table, log strip, status bar
├── dialogs.py           Add Magnet, Add Link, Settings, About dialogs
├── api.py               All TorBox API calls — no Qt, no threads
├── worker.py            PollWorker (queue refresh) + DownloadWorker (file fetch)
├── config.py            JSON config load/save
├── constants.py         API URLs, theme colors, column indices, static values
├── assets/
│   └── tray_icon.png    32×32 tray icon (auto-generated placeholder if missing)
├── requirements.txt     PyQt6, requests
├── launch.bat           First-run venv setup + app launcher
├── config.json          Created on first save — API key, download dir, poll interval
└── TorBox_Manager_Log.txt  Created on first launch — all events and errors
```

---

## Settings

| Setting | Description | Default |
|---|---|---|
| API Key | TorBox bearer token — required | *(empty)* |
| Download Directory | Where completed files are saved | *(prompted on first download)* |
| Poll Interval | How often to check TorBox for status updates | 30 seconds |

Settings are stored in `config.json` alongside the script files. No registry, no AppData.

---

## Roadmap

### v0.1 (this build)
- Four add types, unified queue, in-app download, system tray, EchoStorm theme

### v0.2 (planned)
- Additional queue columns: Seeders, Peers, Ratio, Added time, ETA (all confirmed in API)
- Right-click header to show/hide optional columns
- Multi-file torrent support (file picker dialog before download)
- Add operations moved off the main thread (prevents brief UI freeze on slow connections)
- Auto-retry on transient download link errors
- Settings dialog polish

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
