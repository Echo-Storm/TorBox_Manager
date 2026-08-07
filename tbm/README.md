<p align="center">
  <img src="../assets/banner.svg" alt="TorBox Manager — EchoStorm Edition" width="100%">
</p>

<h3 align="center">A focused Windows desktop client for TorBox — nothing more, nothing less.</h3>

<p align="center">
Add torrents, magnets, hoster links, and NZBs — watch them process on TorBox's servers —
download finished files straight to your machine. No browser tab required.
</p>

---

## Highlights

- **Pause and resume downloads** — stop a transfer mid-stream and pick it back up later without re-downloading what you already have
- **One unified queue** — torrents, magnets, hoster links, and NZBs, sorted, filtered, and multi-selected like a spreadsheet
- **Bulk everything** — select a batch of rows and download, delete, or copy links for all of them at once
- **Auto-extract, safely** — archives unpack the moment they finish downloading, with path-traversal protection so a malicious archive can't write outside your download folder
- **Watch folder** — drop a `.torrent` or `.nzb` file into a folder and it's queued automatically, no clicking required
- **Knows your account** — plan and expiration shown at a glance, so a lapsed subscription doesn't quietly break your queue
- **Stays out of your way** — lives in the tray, checks in occasionally, and can launch at Windows startup if you want it always running

---

## What it looks like

The screenshot below shows the queue in action — torrents, a magnet, a hoster link, and an NZB all managed from one window.

![TorBox Manager](../TorboxManager.jpg)

---

## What you need

- **Windows 10 or 11**
- **A TorBox account** and your API key — find it at torbox.app → Account → API

That's it. No Python, no installs, no admin rights needed.

---

## How to install

1. Download **`TorBox_Manager.exe`** from the [Releases](../../releases) page
2. Drop it anywhere you want (Desktop, `C:\Tools`, wherever)
3. Double-click it

No setup wizard. No installer. Just the one file.

---

## First launch

When the app opens it'll ask for your **API key** and a **download folder**. Fill those in, hit Save, and you're done.

`config.json` and `TorBox_Manager_Log.txt` are created next to the exe on first run.

---

## Everything it does

- **Add anything** — magnet links, .torrent files, hoster URLs (1Fichier, Mega, Pixeldrain etc.), and .nzb files; both Add Magnet and Add Hoster Link accept a batch pasted at once, one per line
- **Unified queue** — everything in one table regardless of type, with live status, size, seeds, peers, ETA, and progress bars
- **Sortable, filterable, multi-select** — click any column header to sort; the search bar filters by name, type, or status all at once (try typing "error" or "magnet"); Ctrl/Shift-click rows for bulk Download, Delete, or Copy Links from the right-click menu
- **Multi-file torrents** — pick exactly which files you want before downloading; one worker per file, all in parallel
- **Pause, resume, and cancel** — stop a download and either pick it back up later from where it left off, or cancel it outright; Pause All / Resume All handle the whole queue at once
- **Downloads to your folder** — streams directly to disk with a live progress bar and an aggregate speed/remaining-size readout; each item gets its own named subfolder automatically
- **Auto-extract** — archives (.zip, .rar, .7z, .tar.*) are extracted on a background thread immediately after download, with path-traversal protection against malicious archives; optionally deletes the archive after extraction
- **Watch folder** — drop .torrent or .nzb files into a folder and they get submitted to TorBox automatically, with a delete-after-submit option
- **Download history** — every completed download is logged; the History tab shows them all newest-first with double-click to open in Explorer and right-click to copy the path
- **Controlled downloads** — concurrency limit (default 3) keeps your connection usable; Download All (and bulk-selected downloads) warn first if there isn't enough free disk space, then queue the rest and drain as slots free up; Retry All Failed re-attempts every row that errored
- **Right-click rows** — Copy Name, Copy Magnet Link, Copy Download Link, Open in Browser (hoster links), Pause/Resume/Cancel Download — right on the row
- **Keyboard shortcuts** — Delete to remove the current selection, Ctrl+A to select every row, F5 to refresh
- **Duplicate warning** — adding a magnet already in your queue (or a batch containing one) asks first instead of silently double-submitting
- **Account at a glance** — current plan, expiration, and total downloaded (if your account exposes it) shown in the left panel
- **Settings export/import** — back up your whole configuration to a file and restore it on another machine
- **Update notifications** — checks GitHub Releases silently on startup; a button appears in the status bar if a newer version is out
- **Stays out of your way** — minimizes to the system tray, slows polling to 5-minute intervals when idle, and can launch automatically at Windows startup
- **Tray notifications** — optional popup when a download finishes (off by default); click it to jump straight to the file
- **Remembers where you left it** — window position and size restored on every launch

---

## Settings

Open via the gear icon bottom-left.

| Setting | What it does | Default |
|---|---|---|
| API Key | Your TorBox bearer token | required |
| Download Directory | Where files land | prompted on first download |
| Concurrent Downloads | Max simultaneous local downloads | 3 |
| Poll Interval | How often to check TorBox | 30 seconds |
| Minimize to Tray | Hide to tray on close instead of quitting | on |
| Run at Windows Startup | Launch automatically at login | off |
| Tray Notifications | Popup when a download finishes | off |
| Create subfolder per download | Each item gets its own named subfolder | on |
| Auto-extract archives | Extract .zip/.rar/.7z/.tar.* after download | on |
| Delete archive after extraction | Remove archive once extracted | off |
| Remove from TorBox after download | Delete remote queue entry when local download completes | off |
| Watch folder | Auto-submit .torrent/.nzb files dropped into a folder | off |
| Delete from watch folder after submit | Remove the file from the watch folder on success | on |

Config saves to `config.json` next to the exe. Nothing goes to the registry except an
optional startup entry if you enable "Run at Windows Startup."

---

## Frequently asked things

**Windows Defender flagged the exe or it was slow to open the first time**
That's normal for freshly built executables — Defender scans them on first launch. If it hard-blocks it: right-click the exe → Properties → Unblock. This is a false positive; the exe bundles Python and PyQt6 and nothing else.

**My item shows a hash instead of a name (like `694f6fe710f5...`)**
That's a TorBox thing on some usenet items — it returns the internal hash before it resolves the real name. The app renders those in italic/dimmed text so you know it's a pending resolution, not a bug. The download still works fine, and the name updates on the next poll once TorBox sorts it out.

**If I pause a download and close the app, can I resume it later?**
The paused file stays on disk (as a `.part` file), but the app doesn't currently remember it was paused across a restart — on next launch the row just looks like a fresh Ready item. Clicking Download again will restart that file from scratch rather than resuming it. Persisting pause state across restarts is on the list for a future release; for now, resume before you close the app if you want to keep the partial progress.

**How do I move my settings to another PC?**
Settings → Export Settings... saves everything (including your API key in plain text, so keep the file safe) to a JSON file. On the new machine, open Settings → Import Settings... and pick that file — it writes straight to `config.json` and asks you to restart the app to pick it up.

**Where's the log file?**
`TorBox_Manager_Log.txt` next to the exe. It gets overwritten each launch so it only covers the current session. There's also an in-app log strip at the bottom of the window with an "errors only" filter.

**Where's the download history stored?**
`download_history.json` next to the exe, same folder as `config.json`. It keeps the last 500 completed downloads. You can also view and clear it from the History tab in the app.

**I want to run from source instead**
Clone the repo, install Python 3.10+, and run `launch.bat`. It creates a venv, installs dependencies, and launches the app. Optional dependencies (py7zr, rarfile) are installed automatically if missing. See `tbm/` for source and `requirements.txt` for the full list.

**Auto-extract isn't working for .rar or .7z**
These need optional packages — `rarfile` (+ unrar.exe or WinRAR in PATH for .rar) and `py7zr` (for .7z). `launch.bat` installs them automatically. If you're running from source manually, run `pip install py7zr rarfile` in your venv. .zip and .tar.* always work with no extras.

---

## Version history

**v1.1.0** — Feature round on top of v1.0.0: multi-magnet paste (Add Magnet now takes a
batch, one per line, like Add Hoster Link), Pause All / Resume All, tray notification
click-to-open, filtering by type/status as well as name, account bandwidth stats, Settings
export/import, and Copy Magnet Link. Two full bug-sweep passes this round caught a real one:
Resume was bypassing the concurrency limit entirely (a single Resume click, or worse,
Resume All, could push active downloads past your configured limit) — fixed by routing
resume through the same queue-and-drain mechanism Download All already used.

**v1.0.0** — First stable release. Real pause/resume for downloads (HTTP Range, with
automatic fallback if a server doesn't support it), TorBox account/plan display, an
aggregate speed + remaining-size readout, Retry All Failed, bulk Copy Download Links,
keyboard shortcuts, and an optional "Run at Windows Startup" toggle. Built on top of the
v0.7.5 security fix and bugfix sweep (archive path-traversal protection, multi-select
with bulk actions, sortable columns, cancel-in-progress-download, duplicate-magnet
warning, low-disk-space warning, faster concurrent polling).

**v0.7.5** — Security fix (archive path-traversal/"Zip Slip" protection in auto-extract) and a
bugfix + feature sweep: Clear All no longer corrupts history for in-flight downloads, poll
responses can no longer race each other, items removed elsewhere on TorBox are now cleaned up
automatically, filenames are hardened against Windows reserved names and path-length limits.
New: multi-select with bulk Download/Delete, sortable columns, cancel an in-progress download,
duplicate-magnet warning, low-disk-space warning before batch downloads. Faster polling
(concurrent endpoint fetches) and less table churn on large queues.

**v0.7.4** — Sharp taskbar icon (multi-size ICO bundled and used for window icon)

**v0.7.3** — Console window eliminated (launch.bat, Explorer open, unrar.exe all suppressed)

**v0.7.2** — Settings dialog scrollable (Save always visible), .7z/.rar support in distributed exe

**v0.7.1** — Download history tab, 4 bug fixes (history table alignment, Settings delete-after toggle dependency, clear history error handling, docstring)

**v0.7.0** — Per-item subfolders, auto-extract archives, watch folder, delete from TorBox after download, queue filter bar, 4 bug fixes (startup crash from missing QLineEdit import, stale version number, tarfile deprecation warning, Explorer path quoting)

**v0.6.0** — Multi-link hoster input, update notifications, 5 bug fixes (right-click link always failed, multi-file torrent button stuck as Open, Retry wired to wrong handler, frozen Restart crash, config upgrade dropped column keys)

**v0.5.0** — Concurrency limit, right-click row menu, Retry button, polling pause when idle, window geometry persistence, usenet hash dimming, log auto-trim, 7 bug fixes

**v0.4.0** — Standalone exe build, multi-file torrent picker, tray notifications, referral link in About, User-Agent header, various fixes

**v0.3.0** — Clipboard paste buttons, threaded add/delete, log filter, status bar breakdown, layout polish

**v0.2.0** — Optional columns (Seeds, Peers, Ratio, ETA, Added), auto-retry on download errors, minimize-to-tray toggle

**v0.1.0** — Initial release

---

## Support

If this is useful, a Ko-fi helps a lot: [ko-fi.com/xechostormx](https://ko-fi.com/xechostormx) ♥

Not on TorBox yet? [referral link](https://torbox.app/subscription?referral=bd158452-a00c-4bce-be2a-593351ccaec7)

---

## License

MIT — see LICENSE
