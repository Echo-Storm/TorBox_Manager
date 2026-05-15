# TorBox Manager — EchoStorm Edition

![TorBox Manager](TorboxManager.jpg)

A desktop queue manager for [TorBox](https://torbox.app) debrid. Add torrents, magnets, hoster links, and NZBs — watch them process on TorBox's servers — download finished files straight to your machine. No browser tab required.

Built for people coming from Real-Debrid who want that same familiar desktop workflow on TorBox.

---

## What it looks like

The screenshot above is a real session. Eight items in the queue — torrents, a magnet, a hoster link, and an NZB — all managed from one window. The MAME set is actively downloading at 6%. Everything else is cached and ready to grab.

---

## What you need

- **Windows 10 or 11**
- **Python 3.10 or newer** — if you don't have it, grab it from [python.org/downloads](https://www.python.org/downloads/)
  - On the installer's first screen, **check the box that says "Add Python to PATH"** before you click Install. Easy to miss, breaks everything if you skip it.
- **A TorBox account** and your API key — find it at torbox.app → Account → API

That's it. No other installs, no admin rights needed.

---

## How to install

**Option 1 — Download the zip (easiest)**

1. Click the green **Code** button at the top of this page → **Download ZIP**
2. Unzip it anywhere you want (Desktop, C:\Tools, wherever)
3. Open the folder and double-click **`launch.bat`**

**Option 2 — Git clone**

```
git clone https://github.com/Echo-Storm/TorBox_Manager
cd TorBox_Manager
launch.bat
```

---

## First launch

The first time you run `launch.bat` it sets up a virtual environment and downloads the two dependencies (PyQt6 and requests). This takes about a minute and only happens once. After that, launches are instant.

When the app opens it'll ask for your **API key** and a **download folder**. Fill those in, hit Save, and you're done.

Pin `launch.bat` to your taskbar or make a desktop shortcut for easy access later.

---

## What it does

- **Add anything** — magnet links, .torrent files, hoster URLs (1Fichier, Mega, Pixeldrain etc.), and .nzb files
- **Unified queue** — everything in one table regardless of type, with status, size, seeds, peers, progress
- **Multi-file torrents** — picks which files you want before downloading, so you're not stuck grabbing the whole set
- **Downloads to your folder** — streams directly to wherever you set, with a live progress bar per file
- **Stays out of your way** — minimizes to the system tray, polls in the background, log strip at the bottom if you want to see what's happening
- **Tray notifications** — optional popup when a download finishes (off by default, toggle in Settings)

---

## Settings

Open via the gear icon bottom-left.

| Setting | What it does | Default |
|---|---|---|
| API Key | Your TorBox bearer token | required |
| Download Directory | Where files land | prompted on first download |
| Poll Interval | How often to check TorBox | 30 seconds |
| Minimize to Tray | Hide to tray on close instead of quitting | on |
| Tray Notifications | Popup when a download finishes | off |

Config saves to `config.json` in the app folder. Nothing goes to the registry or AppData.

---

## Frequently asked things

**It said "Python was not found" when I ran the bat file**
You either don't have Python installed or you forgot to check "Add Python to PATH" during install. Reinstall Python from python.org and make sure that box is checked.

**The window opened and closed immediately**
Something went wrong during setup. Open a command prompt in the app folder and run `launch.bat` from there — you'll see the actual error message.

**My item shows a hash instead of a name (like `694f6fe710f5...`)**
That's a TorBox thing on some usenet items — it's returning the internal hash as the name. Nothing we can fix on this end, but the download still works fine.

**Where's the log file?**
`TorBox_Manager_Log.txt` in the app folder. It gets overwritten each launch so it only has the current session.

---

## Files in the folder

```
TorBox_Manager/
├── launch.bat          Double-click this to run the app
├── main.py             
├── ui.py               
├── dialogs.py          
├── api.py              
├── worker.py           
├── config.py           
├── constants.py        
├── assets/
│   └── tray_icon.png   
├── requirements.txt    
├── config.json         Created on first launch
└── TorBox_Manager_Log.txt  Created on first launch
```

---

## Version history

**v0.4.0** — Multi-file torrent picker, tray notifications, referral link in About, User-Agent header, various fixes

**v0.3.0** — Clipboard paste buttons, threaded add/delete, log filter, status bar breakdown, layout polish

**v0.2.0** — Optional columns (Seeds, Peers, Ratio, ETA, Added), auto-retry on download errors, minimize-to-tray toggle

**v0.1.0** — Initial release

---

## Support

If this is useful, a Ko-fi helps a lot: [ko-fi.com/xechostormx](https://ko-fi.com/xechostormx) ♥

Not on TorBox yet: [referral link](https://torbox.app/subscription?referral=bd158452-a00c-4bce-be2a-593351ccaec7)

---

## License

MIT — see LICENSE
