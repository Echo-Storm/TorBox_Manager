# Changelog — TorBox Manager EchoStorm Edition

---

## v0.4.0 — 2026-05-15

### Distribution
- Standalone Windows exe — no Python installation required. Built via GitHub Actions
  on a Windows runner using PyInstaller (onefile, windowed, UPX disabled).
  `config.json` and `TorBox_Manager_Log.txt` are written next to the exe, not into
  the PyInstaller temp extraction directory.
- App icon — green tech-cube icon across all sizes (16, 24, 32, 48, 64, 128, 256px
  ICO + 64px tray PNG).

### Features
- Multi-file torrent picker — torrents with more than one file now open a dialog
  before downloading. Shows all files with name and size, checkbox per file,
  Select All / Deselect All, and OK disabled until at least one file is checked.
  One DownloadWorker is dispatched per selected file. Single-file torrents and
  all webdl/usenet items skip the dialog entirely.
- Tray notification on download complete — opt-in toggle in Settings, off by default.
  Shows the filename in a brief tray popup when a file finishes downloading.
- Referral link in About dialog — unobtrusive "Get TorBox" button below the Ko-fi
  button. Opens the TorBox referral page in the browser.

### Fixes & Cleanup
- worker.py: DownloadWorker now takes an explicit file_id parameter instead of
  silently grabbing files[0]. The caller decides which file to download.
- worker.py: moved inline imports (time, urllib.parse.unquote) to top-level.
- worker.py: removed duplicate DeleteWorkerSignals class definition.
- ui.py: _open_in_explorer now uses list form for subprocess.Popen to handle
  paths with spaces correctly. Falls back to os.startfile on failure.
- api.py: added User-Agent header (TorBoxManager/x.x.x) to all API requests.
- config.py: added tray_notifications default (False).
- config.py: _config_path() now uses sys.executable when running as a frozen exe
  so config.json lands next to the exe rather than in the PyInstaller temp dir.
- main.py: log path uses the same frozen/unfrozen detection as config.py.
- constants.py: added REFERRAL_URL constant.

---

## v0.3.0 — 2026-05-15

### Features
- **Clipboard paste buttons** — Add Magnet and Add Hoster Link dialogs now have a
  📋 Paste button next to the input field. Button is green and active when clipboard
  holds content, muted/disabled when empty. Updates automatically as clipboard changes.
- **Threaded add/delete** — all four Add buttons and the Delete button now run their
  API calls on background threads (AddWorker, DeleteWorker). The UI no longer freezes
  on slow connections. Previously these blocked the main thread for up to 20 seconds.
- **Status bar breakdown** — status bar now shows item count with context, e.g.
  `8 items  ·  7 ready  ·  1 downloading` instead of a flat count.
- **Log filter toggle** — "errors only" button in the log strip header hides INFO
  messages. All lines stored internally; toggling re-renders without data loss.
- **Start maximized** — app opens maximized rather than at a fixed 1200×700 size.
- **Progress bar fix** — TorBox returns `progress` as either int 0–100 or float 0.0–1.0
  depending on item state. New `_parse_progress()` helper normalises both formats.
  Active downloads now show real percentage (e.g. "6%") instead of always pulsing.
  Indeterminate pulse reserved for items genuinely at 0% (not yet started).

### Visual
- Right content area framed by a continuous 2px vertical rule from below the header
  through the table, log strip, and status bar to the bottom of the window.
- 12px right margin gives the border breathing room, mirroring the left panel weight.
- Table background changed from #181818 to #1f1f1f (COLOR_PANEL) — empty area below
  queue rows now matches the log strip, eliminating the visible color seam.
- Delete button wrapped in a transparent padded container (4px left, 10px right) so
  it sits inset from the right border. Red hover/press state for destructive action.
- Log strip fixed height (140px) — vertical splitter removed. Non-resizable by design.
- Status bar rebuilt as a plain QWidget in the layout rather than
  QMainWindow.setStatusBar(), allowing the right border to run through it.
- 1px separator widget between Download All and donate (replaces the " | " text).

### Fixes & Cleanup
- Removed two [DEBUG] log lines emitting internal state to the visible log strip on
  every poll cycle.
- Fixed QColor/QBrush imported via __import__(...) hacks — moved to top-level import.
- Fixed DeleteWorkerSignals defined after the class that references it — moved above
  DeleteWorker and renamed to proper PascalCase.
- Removed duplicate _log_lines initialisation in _build_log_strip.
- Removed unused QStatusBar import and its dead MAIN_STYLE rule.
- Log file now opens in overwrite mode (mode='w') — each launch starts fresh.
- Fixed COLOR_ACCENT_DIM missing from dialogs.py constants import — was silently
  preventing Add Magnet and Add Hoster Link dialogs from opening.

---

## v0.2.0 — 2026-05-14

### Features
- Optional queue columns: Seeds, Peers, Ratio, ETA, Added. Right-click header to
  show/hide. Visibility persisted in config.json.
- Compound status display: "Cached · Seeding" vs "Cached · Idle".
- Auto-retry on download link errors (3 attempts, 3s delay).
- Minimize to tray toggle in Settings.
- Poll interval QIntValidator (10–300s range).
- Download button rewires to Open after successful local download.

### Fixes
- Fixed bypass_cache=true missing from list endpoint calls.
- Fixed delete API JSON body format.
- Fixed URL-encoded filenames not decoded before local file write.
- _deleted_keys suppression prevents deleted items reappearing for one poll cycle.

---

## v0.1.0 — 2026-05-14

Initial build. Confirmed working.

- Four add types: magnet, torrent file, hoster URL, NZB file
- Unified queue table with progress bars, download and delete per row
- In-app streaming download with .part rename pattern
- Auto-polling, system tray, EchoStorm dark theme
- Self-contained venv, launch.bat first-run setup
- File logging with sys.excepthook for uncaught exceptions
