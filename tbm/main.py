# main.py
# TorBox Manager EchoStorm Edition
#
# Entry point. Responsibilities:
#   - Configure file logging (Python logging module → TorBox_Manager_Log.txt)
#   - Install a sys.excepthook so uncaught exceptions land in the log file
#     rather than silently disappearing when run via pythonw
#   - Load config
#   - Create QApplication and MainWindow
#   - Start the Qt event loop
#
# This file should contain no business logic.
# If you find yourself adding feature code here, it belongs in ui.py instead.

import logging
import os
import sys


# ---------------------------------------------------------------------------
# File logging — set up before anything else so even import errors are caught
# ---------------------------------------------------------------------------

def _setup_logging() -> logging.Logger:
    """
    Configure root logger to write timestamped entries to TorBox_Manager_Log.txt
    alongside the script files, plus stderr for console visibility during dev.

    Returns the logger so main() can write its own startup entry.
    """
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(log_dir, "TorBox_Manager_Log.txt")

    fmt     = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                 datefmt="%Y-%m-%d %H:%M:%S")
    logger  = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # File handler — always on
    try:
        fh = logging.FileHandler(log_path, mode='w', encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:
        # Can't write log file — not fatal, just carry on
        print(f"WARNING: Could not open log file {log_path}: {exc}", file=sys.stderr)

    # Console handler — useful when running python.exe rather than pythonw.exe
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


def _install_excepthook(logger: logging.Logger):
    """
    Route uncaught exceptions to the log file.

    Without this, exceptions that occur after the Qt event loop starts
    are silently swallowed by pythonw.exe. This ensures they leave a
    trace in TorBox_Manager_Log.txt so they're diagnosable.
    """
    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _hook


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    logger = _setup_logging()
    _install_excepthook(logger)

    from constants import APP_NAME, APP_SUBTITLE, APP_VERSION
    _app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Logging initialized: {os.path.join(_app_dir, 'TorBox_Manager_Log.txt')}")
    logger.info(f"{APP_NAME} {APP_SUBTITLE} v{APP_VERSION} starting")

    # Qt must be imported after logging is set up so any import errors are logged
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui     import QIcon
    from PyQt6.QtCore    import Qt

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # High-DPI is on by default in Qt6 — no extra flags needed.
    # Keeping this comment here as a reminder that AA_EnableHighDpiScaling
    # is not valid in PyQt6 and will raise an AttributeError if used.

    # App icon (window + taskbar) — same asset as tray icon if present
    _asset_base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(_asset_base, "assets", "tray_icon.png")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Don't quit when the last window is hidden (we hide to tray on close)
    app.setQuitOnLastWindowClosed(False)

    # Load config — never raises, always returns a valid dict
    from config import load_config
    config = load_config()
    logger.info(
        f"Config loaded — "
        f"api_key: {'set' if config.get('api_key') else 'NOT SET'}, "
        f"download_dir: '{config.get('download_dir', '')}', "
        f"poll_interval: {config.get('poll_interval')}s"
    )

    # Build and show the main window
    from ui import MainWindow
    window = MainWindow(config)
    window.show()

    logger.info("MainWindow shown — entering event loop")
    exit_code = app.exec()

    logger.info(f"{APP_NAME} exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
