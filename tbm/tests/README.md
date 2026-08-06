# Tests

Offscreen PyQt6 unit tests — stdlib `unittest`, no extra dependency. They
build a real `MainWindow` against a fake config/queue data and exercise the
UI logic directly (no real network calls, no visible window), so they run
headless in CI or a plain terminal.

## Running

From `tbm/`:

```bash
venv\Scripts\python -m unittest discover -s tests -v
```

Or run a single file directly:

```bash
venv\Scripts\python tests\test_downloads.py
```

`QT_QPA_PLATFORM=offscreen` is set automatically by each test module — you
don't need to set it yourself, and no window will actually appear on screen.

## What's covered

| File | Covers |
|---|---|
| `test_security.py` | Zip Slip path-traversal guard (zip/7z/rar/tar extraction), filename sanitizing (reserved Windows names, path length) |
| `test_queue.py` | Poll diffing, stale-row cleanup, poll-overlap guard, sortable-table row-index self-healing (`_find_row`), Clear All/Clear Done preserving active & paused rows, magnet dedupe |
| `test_downloads.py` | Cancel, pause/resume (including the multi-file-torrent timing fix), Retry All Failed, bulk delete/download/copy-links, the disk-space confirmation guard, error-state button wiring after cancel/discard |
| `test_shortcuts.py` | Delete / Ctrl+A keyboard shortcuts, scoped correctly to the Queue tab |
| `test_settings.py` | `SettingsDialog` construction, `FilePickerDialog`'s checkbox wrapper, the Windows startup registry toggle (mocked for the "enabled" case — never writes to the real registry) |
| `test_speed_display.py` | Aggregate download speed / remaining-size status bar display |

## Notes for anyone extending this

- `_helpers.py` (leading underscore) is shared fixtures, not a test module —
  `unittest discover` skips it automatically.
- Registry-touching code (`_apply_startup_setting`) is tested for real only
  on the safe, idempotent "disabled" path; the "enabled" path is verified
  against a mocked `winreg` so the suite never leaves a startup entry behind
  on the machine that runs it.
- Network-touching workers (`DeleteWorker`, `LinkRequestWorker`,
  `DownloadWorker`) are replaced with small fakes rather than hit for real —
  these are unit tests of the UI's state machine, not integration tests
  against the live TorBox API.
- These tests were written incrementally alongside the v1.0.0 feature/bugfix
  sweep; if you fix a bug here, add a regression test the same way (see the
  `_row_index`-after-sort and multi-file-pause-timing tests for the pattern —
  reproduce the bug first, confirm the assertion fails on the old code, then
  fix it).
