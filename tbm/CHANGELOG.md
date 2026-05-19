# Changelog — TorBox Manager EchoStorm Edition

---

## v0.6.0 — 2026-05-19

### Features
- **Multi-link hoster support** — Add Hoster Link dialog now accepts multiple URLs at once,
  one per line. Paste a batch, hit OK, and each URL gets its own background worker. Previously
  limited to one URL per dialog open.
- **Update notifications** — the app silently checks GitHub Releases on startup and shows a
  small "⬆ v0.x.x available" button in the status bar if a newer version is out. Clicking it
  opens the releases page in the browser. No data is written to disk; the check runs fresh
  each launch and errors are logged only, never surfaced to the user.

### Fixes
- **Right-click Copy Link / Open in Browser always failed** — `LinkRequestWorker` checked
  `result.get("ok")` but `api.py` returns `{"success": ..., "detail": ..., "data": ...}`.
  No `"ok"` key exists, so the worker always emitted the error signal even on success.
  Fixed: check `result.get("success")`.
- **Multi-file torrent Download button stuck as "Open"** — after downloading one file from a
  multi-file torrent the Download button permanently rewired to "Open", blocking further file
  selections from the same row until restart. Now stays as "Download" so the file picker
  remains accessible for remaining files.
- **Retry button wired to wrong handler after prior success** — `_on_download_error` enabled
  the Retry button without disconnecting it first. If the row had a previously successful
  download (button wired to `_open_in_explorer`), clicking Retry opened Explorer instead of
  retrying. Fixed: disconnect + reconnect to `_on_download_clicked` in both the error handler
  and the poll-update path.
- **Tray → Restart duplicated exe path as argument** — `subprocess.Popen([sys.executable] +
  sys.argv)` in a frozen exe passes the exe path twice (once as the exe, once as argv[0]),
  causing an invalid invocation. Fixed: frozen mode uses `[sys.executable]` only; source mode
  keeps both.
- **Config upgrade silently dropped new column keys** — `load_config` used a shallow
  `merged.update(data)` which replaced the entire `columns` sub-dict with whatever was saved,
  discarding any new column keys added in later versions. Fixed: nested dicts are deep-merged
  (defaults first, saved values overlay).

---

## v0.5.0 — 2026-05-18

### Features
- **Download concurrency limit** — new "Concurrent Downloads" setting (default 3, range 1–10).
  Download All now starts up to the limit immediately and queues the rest in a FIFO queue.
  Each time a local download finishes or errors, the next queued item starts automatically.
- **Right-click context menu on rows** — right-click any queue row for: Copy Name (always),
  Copy Download Link (Ready items — async request, copies the time-limited TorBox URL to
  clipboard), Open in Browser (webdl Ready items). Link request runs on a background worker
  so the UI never blocks.
- **Retry button on error rows** — the Download button now reads "Retry" on rows where the
  local download failed. Clicking it re-attempts the download immediately without needing a
  poll cycle. Reverts to "Download" if TorBox reports the item ready again on the next poll.
- **Polling pause when minimized** — when the window is hidden to the tray and no local
  downloads are active, the poll interval drops to 5 minutes (configurable base interval is
  still respected if it's already ≥ 5 min). Polling restores to the configured rate the
  moment a download starts or the window is restored.
- **Window geometry persistence** — position and size are saved to config.json on close and
  restored on next launch. Falls back to maximized if no saved geometry exists.
- **Usenet hash name handling** — NZB items whose names are bare hex hashes (≥ 20 hex chars)
  now render in italic muted text with a tooltip: "NZB identifier — TorBox hasn't resolved
  the filename yet". When TorBox provides a real name on a later poll, the cell re-styles
  itself to the normal bold font automatically.
- **Log strip auto-trim** — the in-app log buffer is capped at 500 lines. When it overflows,
  the oldest 250 are dropped and the visible log view is rebuilt. Prevents unbounded memory
  growth in long-running sessions.

### Fixes
- **Crash on multi-file torrent download** — `QDialog` was missing from the PyQt6 imports.
  Any click on Download for a torrent with more than one file raised `NameError` at runtime.
- **Progress bar stuck in pulse mode** — `_update_queue_row` called `pbar.setValue()` while
  the bar was in indeterminate mode (range 0, 0), so Qt silently clipped the value and the
  bar stayed pulsing even after TorBox reported real progress. Range is now reset to (0, 100)
  before every value update.
- **Error state left progress bar pulsing** — `_style_progress_bar` for STATUS_ERROR never
  called `setRange(0, 100)`, so a bar that was pulsing when the error hit remained in
  indeterminate mode. Now forces deterministic range and value 0 before applying the red style.
- **Download queue used stale item data** — `_try_start_queued` passed the item snapshot
  captured at queue time to `_start_download`. If the API data changed between queue and
  dequeue, the download used old field values. Now looks up the item fresh from `_row_items`.
- **Settings save bypassed idle-poll logic** — saving Settings set the poll timer interval
  directly, ignoring the idle (window hidden + no downloads) slowdown. Now routes through
  `_update_poll_interval()`.
- **Clear All left download queue populated** — queued items lingered in `_download_queue`
  after the table was cleared, causing silent no-ops on every subsequent download finish.
- **Delete didn't prune download queue** — deleting an item while it was queued for download
  left the entry in `_download_queue`. Now filters it out immediately on delete.
- **Type badge showed wrong label** — the Type column badge used `source_type.capitalize()`
  which rendered "Webdl" and "Usenet" instead of "Hoster Link" and "NZB". Now uses
  `TYPE_LABELS` from constants for all four types.
- **Frozen exe path fix** (v0.4 regression) — `tray_icon.png` is now bundled into the exe
  via `--add-data` in build.yml and resolved via `sys._MEIPASS` at runtime. Previously the
  icon was missing on all frozen builds that didn't have the assets folder next to the exe.

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
