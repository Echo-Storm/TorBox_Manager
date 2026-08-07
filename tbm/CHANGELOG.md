# Changelog — TorBox Manager EchoStorm Edition

---

## v1.1.0 — 2026-08-06

Additive feature round on top of v1.0.0 — no architecture changes, just rounding out
what's there. Two full bug-sweep passes this cycle (up from one last time).

### Features
- **Multi-magnet paste** — Add Magnet now accepts multiple links at once, one per line,
  matching Add Hoster Link's existing multi-line UX. A single combined prompt handles it
  if any of the pasted links are already in your queue, rather than one popup per link.
- **Pause All / Resume All** — left-panel buttons alongside Retry All Failed.
- **Tray notification click-to-open** — clicking a "download complete" balloon opens that
  file's folder in Explorer.
- **Filter by type and status** — the queue filter bar now matches Type and Status text
  too, not just Name (e.g. typing "error" or "magnet" filters the queue).
- **Account bandwidth stats** — total downloaded shown in the Account panel, if TorBox's
  API exposes it for your account.
- **Settings export/import** — back up config.json (including your API key in plain text —
  it's called out explicitly in the dialog) to a file and restore it on another machine.
- **Copy Magnet Link** — right-click a magnet-added row to copy the original magnet URI,
  separate from the existing "Copy Download Link" (TorBox's resolved URL).

### Fixed (bug sweep #1 — new features)
- **Resume bypassed the concurrency limit entirely.** `_resume_download` dispatched
  straight to a new `DownloadWorker` regardless of `max_concurrent_downloads` — a single
  Resume click could already push active workers past the limit, and "Resume All" on a
  handful of paused rows made it obvious immediately. Resume now goes through the same
  queue-and-drain mechanism `Download All` already used, via a new `_resume_queue`.

### Fixed (bug sweep #2 — comprehensive pass)
- **Left panel could overflow at the documented minimum window size (1000×600).** The
  button list has grown release over release with no scroll area to absorb it; the two
  new Pause All/Resume All buttons pushed the arithmetic over the ~496px actually available
  at minimum size. The Add/Queue button list now scrolls independently, with the Account
  panel and Settings button pinned below it so they're always reachable without scrolling.

---

## v1.0.0 — 2026-08-06

First stable release. Built directly on top of v0.7.5's security fix and bugfix sweep,
adding the feature set that makes this a complete desktop debrid client rather than a
bare-bones queue viewer.

### Features
- **Real pause/resume for downloads** — pausing keeps the `.part` file instead of deleting
  it; resuming sends an HTTP `Range` request and appends rather than restarting. If a
  server/CDN ignores the Range request (no `206 Partial Content`), the download
  transparently falls back to starting fresh instead of corrupting the file. Available from
  the row's Download button (relabels to "Resume") and the right-click menu ("Pause
  Download" / "Cancel Download" while active, "Resume Download" / "Discard Paused
  Download" while paused).
  **Known limitation**: pause state doesn't survive an app restart — see the README FAQ.
- **TorBox account info** — plan and expiration shown in the left panel, so a lapsed
  subscription doesn't silently break the queue. Fetched on startup and after Settings is
  saved; every field is treated as optional since the exact API shape isn't verified
  against every plan tier.
- **Aggregate speed / remaining-size display** — the status bar shows combined download
  speed and remaining bytes across all active downloads while any are running.
- **Retry All Failed** — left-panel button re-attempts every row with a local download
  error in one click.
- **Bulk Copy Download Links** — multi-select context menu can resolve and copy every
  selected Ready item's download link at once, one per line.
- **Keyboard shortcuts** — `Delete` removes the current selection, `Ctrl+A` selects every
  row, `F5` refreshes — all scoped to the Queue tab.
- **Run at Windows Startup** — optional Settings toggle; off by default.
- **Open Config Folder** — tray menu quick-access to `config.json` / history / log.

### Fixes (found during this release's bug sweep)
- A multi-file torrent pausing could briefly publish resume metadata for the wrong file
  before all of its workers had actually paused.
- Cancelling or discarding a paused download while TorBox now reports the item as errored
  left the row showing a disabled "Download" instead of an enabled "Retry".

### Documentation
- README rewritten: frontloaded feature highlights, new SVG banner, no more references to
  other debrid clients — this app now describes itself on its own terms.
- Added `tbm/tests/` — a real, committed `unittest` suite (offscreen PyQt6, no live network
  calls) replacing this project's previous session-only scratch verification scripts.

---

## v0.7.5 — 2026-08-06

### Security
- **Zip Slip path traversal in auto-extract** — `.zip`, `.7z`, and `.rar` extraction
  trusted archive member paths and extracted them unchecked; since `auto_extract`
  defaults to on and archives come from arbitrary torrents/hosters, a malicious
  archive could write files outside the download folder. All four formats
  (including the tar fallback on Python < 3.12) now validate every member's
  resolved path stays inside the destination directory before extracting
  anything; a violation aborts the whole extraction instead of extracting
  partially.

### Fixes
- **Clear All corrupted history for in-flight downloads** — clearing the queue
  while a download was still running wiped the item data a moment later needed
  to record it in history, producing a blank-name history entry. Clear All now
  asks for confirmation and leaves rows with an active local download in place.
- **Poll responses could race** — a new poll was submitted every tick even if
  the previous one hadn't returned, so a slow/degraded API response could let
  a stale poll overwrite fresher table state. A new poll is now skipped while
  one is already in flight.
- **Items removed on TorBox's side lingered forever** — if an item was deleted
  via the TorBox web UI (or expired) it previously stayed in the table
  indefinitely. Rows missing for 3 consecutive polls are now dropped
  automatically; a single missed poll is treated as a transient blip and left
  alone. Rows with an active local download are never auto-dropped.
- **Filenames could hit Windows reserved device names or MAX_PATH** —
  downloaded filenames are now checked against reserved names (`CON`, `NUL`,
  `COM1`, etc.) and the stem is truncated when combined with a per-item
  subfolder would risk exceeding Windows' path length limit.

### Features
- **Multi-select + bulk actions** — the queue table now supports selecting
  multiple rows (Ctrl/Shift-click) with "Download Selected" (also covered by
  the low-disk-space check below) and "Delete Selected" in the right-click
  menu.
- **Sortable queue table** — click any column header to sort. Row lookups now
  self-heal on every access (`_find_row`) instead of trusting a cache that a
  live sort click can invalidate between polls, so Delete/Download/Cancel and
  in-progress download updates always target the correct row even immediately
  after re-sorting.
- **Cancel an in-progress download** — right-click a row that's actively
  downloading locally for a "Cancel Download" action. Cleans up the partial
  `.part` file; the item goes back to a normal Ready state since it's untouched
  on TorBox's side.
- **Duplicate-magnet warning** — adding a magnet link already present in the
  queue now asks for confirmation first.
- **Low disk space warning on Download All** — estimates total size against
  free space in the download directory and confirms before proceeding if
  there isn't enough room.

### Performance
- **Faster polling** — the three TorBox list endpoints (torrents/webdl/usenet)
  are now fetched concurrently instead of sequentially, so a slow response
  from one no longer multiplies total poll latency.
- **Fewer redundant table updates** — Seeds/Peers/Ratio/ETA/Added cells now
  only get a `setText()` call when their value actually changed, instead of a
  fresh cell being allocated every poll regardless.

### Cleanup
- Consolidated duplicated status-classification logic in `ui.py` behind a
  single `_classify_download_state()` helper.
- `FilePickerDialog`'s checkbox cell no longer misuses `QLabel` as a generic
  layout container — now a plain `QWidget`.
- `SettingsDialog._build_ui` split into one helper method per settings
  section instead of one ~190-line function.
- `_scan_watch_folder` no longer raises on a transiently unavailable folder
  (e.g. a network share hiccup) — logs a warning and retries next scan instead.

---

## v0.7.4 — 2026-06-11

### Fixes
- **Taskbar icon low quality** — the app was loading the 64×64 PNG for the Qt
  window icon, resulting in a blurry taskbar button and title bar icon at various
  DPI settings. Now loads the multi-size ICO (16–256px) so Windows picks the
  correct resolution for each context. ICO also bundled in the exe build so it
  is available at runtime in the frozen app.

---

## v0.7.3 — 2026-06-11

### Fixes
- **Console window visible when using the app** — three sources eliminated:
  - `launch.bat` now uses `pythonw.exe` via `start` so the cmd window closes
    immediately after launch instead of staying open for the app's lifetime.
  - Open in Explorer and Restart tray action now pass `CREATE_NO_WINDOW` to
    `subprocess.Popen` so no console flashes on those actions.
  - `rarfile.OPEN_ARGS` set to `CREATE_NO_WINDOW` so `unrar.exe` runs hidden
    when extracting .rar archives.

---

## v0.7.2 — 2026-06-11

### Fixes
- **Settings dialog cut off on smaller screens** — the dialog had no scroll area, so
  on shorter displays the Save button and lower sections were unreachable. The form
  content now scrolls; Save/Cancel are pinned below the scroll area and always visible.
- **Build missing py7zr and rarfile** — optional extraction packages were not installed
  during the GitHub Actions build, so the distributed exe couldn't handle .7z or .rar
  files. Both packages are now included in the build step.

---

## v0.7.1 — 2026-06-11

### Features
- **Download history** — completed downloads are recorded to `download_history.json`
  alongside `config.json`. A new History tab in the right panel shows all downloads
  newest-first: time, item name, filename, type badge, and size. Double-click any row to
  open the file location in Explorer. Right-click for Copy Path or Open in Explorer.
  Clear History button (with confirmation). History tab auto-refreshes from disk each time
  it is opened.

### Fixes
- **History table Name/File columns center-aligned** — long names were horizontally
  centered making them hard to read. Name is now left-aligned bold, File is left-aligned
  muted.
- **`history.load()` docstring said "newest-first"** — it returns oldest-first; the UI
  reverses for display. Docstring corrected.
- **Clear History silently failed** — `hist.clear()` return value was not checked. If the
  write failed the table would be visually emptied but data would reappear on next tab
  switch. Now shows a warning if the file could not be written.
- **"Delete archive after extraction" always enabled in Settings** — the checkbox was
  active even when "Auto-extract" was unchecked, implying it did something it couldn't do.
  It now grays out automatically when auto-extract is off.

---

## v0.7.0 — 2026-06-11

### Features
- **Per-item download subfolders** — each download is placed into a subfolder named after
  the item, inside the configured download directory. Sanitises illegal Windows characters
  automatically. Toggle in Settings (on by default). Multi-file torrents share the same
  subfolder so all their files land together.
- **Auto-extract archives** — after a local download completes, archives (.zip, .tar,
  .tar.gz, .tar.bz2, .tar.xz, .tgz, .7z, .rar) are automatically extracted to the same
  folder on a background thread. Toggle in Settings (on by default). py7zr and rarfile are
  optional pip packages; the app installs them silently via launch.bat and fails gracefully
  with a clear message if they're missing for a specific format.
- **Delete archive after extraction** — optionally remove the original archive file once
  extraction succeeds. Off by default. Separate toggle from auto-extract so you can extract
  without deleting.
- **Watch folder** — point the app at a folder and any .torrent or .nzb file dropped into
  it is automatically submitted to TorBox. Uses Qt's `QFileSystemWatcher` with a 1-second
  debounce so partially-copied files aren't read mid-write. Optionally deletes the file
  from the folder after a successful submission. Existing files in the folder are processed
  on startup. Toggle in Settings (off by default).
- **Remove from TorBox after download** — once all local files for an item are downloaded,
  optionally fire a delete call to TorBox to clean up the remote queue entry. Off by default.
  Toggle in Settings.
- **Queue filter bar** — a search bar above the queue table filters rows by name in real
  time. Shows a live count of visible vs. total items. Filter persists across poll cycles
  so it stays active while the queue refreshes. ✕ button clears the filter.

### Fixes
- **Crash on startup** — `QLineEdit` was used in the new filter bar but missing from the
  PyQt6 imports, causing a `NameError` every time the app launched. Fixed. (Also removed
  the unused `QScrollArea` import left over from an earlier draft.)
- **Version number not bumped** — `APP_VERSION` in constants.py still read `"0.6.0"`.
  Fixed to `"0.7.0"`. The header bar, About dialog, and update checker now show the
  correct version.
- **tarfile deprecation warning** — `tarfile.extractall()` without `filter=` generates a
  `DeprecationWarning` in Python 3.12+ and will become an error in a future version. Now
  passes `filter="data"` (which also blocks path-traversal entries) with a graceful fallback
  for Python < 3.12.
- **Explorer /select path not quoted** — `_open_in_explorer` passed the path unquoted in
  the `/select,<path>` argument. Paths containing commas would confuse Explorer's argument
  parser. Now quotes the path inside the argument string.

### Dependencies
- **launch.bat** now checks for `py7zr` and `rarfile` on every startup (near-instant import
  check; pip only runs if something is missing). These are listed in requirements.txt as
  optional and are not required for core functionality.

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
