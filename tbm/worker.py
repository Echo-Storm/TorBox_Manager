# worker.py
# TorBox Manager EchoStorm Edition
#
# QRunnable workers for background operations. No UI code, no direct widget
# calls. All results are communicated back to the main thread exclusively
# via Qt signals — the same safe pattern used in EAC.
#
# Four workers:
#
#   PollWorker      — fetches all three TorBox queues, emits unified list
#   DownloadWorker  — requests a download link then streams the file to disk
#   AddWorker       — submits a single add operation (magnet/torrent/link/nzb)
#   DeleteWorker    — deletes a single item from the TorBox queue
#
# Threading model:
#   - A QTimer in ui.py fires every poll_interval seconds and submits a
#     fresh PollWorker to QThreadPool. The timer owns the schedule;
#     the worker just does one run and finishes.
#   - A DownloadWorker is submitted once per file when the user clicks
#     Download (or Download All). One worker per file — they run in parallel
#     up to QThreadPool's default thread limit.
#   - AddWorker and DeleteWorker are one-shot: submitted on button click,
#     emit finished/error, done. Keeps the main thread free during API calls.
#
# Assumption about TorBox API field names (verify against live responses):
#   id, name, size, progress (0-100 int), download_state, magnet,
#   files (list, each with id and name)
#   These are noted where used so they are easy to find and fix if off.

import os
import re
import time
from urllib.parse import unquote

import requests

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

import api
from constants import DOWNLOAD_CHUNK_SIZE


# ---------------------------------------------------------------------------
# Signal containers
#
# QRunnable doesn't inherit QObject so it can't define signals directly.
# The standard PyQt6 pattern is a separate QObject subclass that holds
# the signals. Each worker instantiates one and exposes it as .signals.
# ---------------------------------------------------------------------------

class PollSignals(QObject):
    """Signals emitted by PollWorker."""
    finished = pyqtSignal(list)   # unified list of queue items
    error    = pyqtSignal(str)    # human-readable error string
    status   = pyqtSignal(str)    # log-ready status string


class DownloadSignals(QObject):
    """Signals emitted by DownloadWorker."""
    progress = pyqtSignal(int, int)  # (bytes_received, total_bytes)
    finished = pyqtSignal(str)       # full local file path
    error    = pyqtSignal(str)       # human-readable error string
    status   = pyqtSignal(str)       # log-ready status string


class AddSignals(QObject):
    """Signals emitted by AddWorker."""
    finished = pyqtSignal(bool, str)  # (success, detail)
    status   = pyqtSignal(str)


class DeleteWorkerSignals(QObject):
    """Signals emitted by DeleteWorker."""
    finished = pyqtSignal(bool, str, str)  # (success, detail, row_key)
    status   = pyqtSignal(str)


# ---------------------------------------------------------------------------
# PollWorker
# ---------------------------------------------------------------------------

class PollWorker(QRunnable):
    """
    Fetches all three TorBox queues in a single background run.

    Lifecycle:
        1. ui.py's QTimer fires -> submits PollWorker to QThreadPool
        2. run() calls api.list_all()
        3. Emits signals.finished(items) or signals.error(msg)
        4. Worker is done — QThreadPool recycles the thread

    The UI slot connected to signals.finished is responsible for
    diffing the new list against existing table rows and updating in place.
    """

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.signals = PollSignals()

    def run(self):
        self.signals.status.emit("Polling TorBox queue...")
        result = api.list_all(self.api_key)
        self.signals.status.emit(result["detail"])
        if result["success"]:
            items = result["data"] if isinstance(result["data"], list) else []
            self.signals.finished.emit(items)
        else:
            self.signals.error.emit(result["detail"])


# ---------------------------------------------------------------------------
# AddWorker
# ---------------------------------------------------------------------------

class AddWorker(QRunnable):
    """
    Submits a single add operation to TorBox on a background thread.

    add_fn: a callable that takes no arguments and returns an api result dict.
            Construct it as a lambda in the caller:
                lambda: api.add_magnet(api_key, link)
            This keeps AddWorker generic — it doesn't need to know which
            endpoint or arguments are involved.

    item_type: human-readable label for log messages ("magnet", "torrent", etc.)
    """

    def __init__(self, add_fn, item_type: str):
        super().__init__()
        self._add_fn    = add_fn
        self._item_type = item_type
        self.signals    = AddSignals()

    def run(self):
        self.signals.status.emit(f"Adding {self._item_type}...")
        result = self._add_fn()
        self.signals.finished.emit(result["success"], result["detail"])


# ---------------------------------------------------------------------------
# DeleteWorker
# ---------------------------------------------------------------------------

class DeleteWorker(QRunnable):
    """
    Deletes a single item from the TorBox queue on a background thread.

    delete_fn: callable -> api result dict, constructed as a lambda in the caller.
    row_key:   the item's row key, passed through to the finished signal so
               the UI slot knows which row to remove.
    item_name: human-readable name for log messages.
    """

    def __init__(self, delete_fn, row_key: str, item_name: str):
        super().__init__()
        self._delete_fn  = delete_fn
        self._row_key    = row_key
        self._item_name  = item_name
        self.signals     = DeleteWorkerSignals()

    def run(self):
        self.signals.status.emit(f"Deleting: {self._item_name}...")
        result = self._delete_fn()
        self.signals.finished.emit(result["success"], result["detail"], self._row_key)


# ---------------------------------------------------------------------------
# DownloadWorker
# ---------------------------------------------------------------------------

class DownloadWorker(QRunnable):
    """
    Resolves a download link for a completed TorBox item, then streams
    the file to the configured download directory.

    Steps:
        1. Call the appropriate api.request_download_link_*() function
        2. Open a streaming GET to the returned URL
        3. Emit progress signals as chunks arrive
        4. Write chunks to a .part file; rename to final name on completion
        5. Emit finished(file_path) or error(msg)

    The .part extension during download means a partially-written file is
    never mistaken for a complete one if the app is closed mid-download.

    Arguments:
        api_key     : TorBox bearer token
        item        : dict — one item from the unified queue list (from PollWorker)
        download_dir: absolute path to the user's download directory
        file_id     : specific file ID to download (torrents/magnets only).
                      The caller resolves this — files[0]["id"] for single-file
                      items, or the ID chosen in FilePickerDialog for multi-file.
                      Pass None for webdl and usenet (no file_id needed).
        file_name   : optional display name for this specific file within a
                      multi-file torrent. Used in log messages and as the
                      fallback filename if Content-Disposition is absent.

    NOTE: "torrent" and "magnet" both use the torrent download endpoint.
    The source_type distinction is only for display; the API path is the same.
    """

    def __init__(self, api_key: str, item: dict, download_dir: str,
                 file_id: int = None, file_name: str = None):
        super().__init__()
        self.api_key      = api_key
        self.item         = item
        self.download_dir = download_dir
        self.file_id      = file_id    # explicit file to download; None for webdl/usenet
        self.file_name    = file_name  # optional per-file name for multi-file torrents
        self.signals      = DownloadSignals()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self):
        # Use the specific file name if provided (multi-file picker gave us one),
        # otherwise fall back to the item's top-level name.
        item_name   = self.file_name or self.item.get("name", "unknown")
        source_type = self.item.get("source_type", "")
        item_id     = self.item.get("id")

        if not item_id:
            self.signals.error.emit(f"Cannot download '{item_name}': missing item ID.")
            return

        if not self.download_dir or not os.path.isdir(self.download_dir):
            self.signals.error.emit(
                "Download directory is not set or does not exist. "
                "Set it in Settings before downloading."
            )
            return

        self.signals.status.emit(f"Requesting download link for: {item_name}")

        # Resolve the download URL from TorBox.
        # Retry up to 3 times with a short delay — TorBox occasionally returns
        # transient "error processing your request" responses on link generation.
        url_result   = None
        last_detail  = ""
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            url_result  = self._request_link(source_type, item_id)
            last_detail = url_result.get("detail", "")
            if url_result["success"]:
                break
            if attempt < max_attempts:
                self.signals.status.emit(
                    f"Link request failed (attempt {attempt}/{max_attempts}), "
                    f"retrying in 3s... — {last_detail}"
                )
                time.sleep(3)

        if not url_result["success"]:
            self.signals.error.emit(
                f"Could not get download link for '{item_name}' "
                f"after {max_attempts} attempts: {last_detail}"
            )
            return

        download_url = url_result["data"]
        if not download_url or not isinstance(download_url, str):
            self.signals.error.emit(
                f"TorBox returned an empty download URL for '{item_name}'."
            )
            return

        self._stream_to_disk(download_url, item_name)

    # ------------------------------------------------------------------
    # Link resolution
    # ------------------------------------------------------------------

    def _request_link(self, source_type: str, item_id: int) -> dict:
        """
        Call the correct api.request_download_link_*() based on source_type.

        For torrents and magnets, self.file_id must be set by the caller.
        The old behaviour of silently grabbing files[0] is gone — the caller
        owns that decision now (single-file: pass files[0]["id"];
        multi-file: pass the ID chosen in FilePickerDialog).
        """
        if source_type in ("torrent", "magnet"):
            fid = self.file_id if self.file_id is not None else 0
            return api.request_download_link_torrent(self.api_key, item_id, fid)

        elif source_type == "webdl":
            return api.request_download_link_webdl(self.api_key, item_id)

        elif source_type == "usenet":
            return api.request_download_link_usenet(self.api_key, item_id)

        else:
            return {"success": False, "detail": f"Unknown source type: {source_type}", "data": None}

    # ------------------------------------------------------------------
    # File streaming
    # ------------------------------------------------------------------

    def _stream_to_disk(self, url: str, fallback_name: str):
        """
        Stream the file at `url` to self.download_dir.

        Uses a .part file during download; renames on completion.
        Emits progress(bytes_received, total_bytes) as chunks arrive.
        Emits finished(file_path) on success or error(msg) on failure.
        """
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            self.signals.error.emit(f"Download failed for '{fallback_name}': {exc}")
            return

        # Determine filename — prefer Content-Disposition, fall back to item name
        final_name = self._extract_filename(response, fallback_name)
        part_path  = os.path.join(self.download_dir, final_name + ".part")
        final_path = os.path.join(self.download_dir, final_name)

        # Total size may be absent — progress will pulse if so
        total_bytes    = int(response.headers.get("Content-Length", 0))
        received_bytes = 0

        self.signals.status.emit(f"Downloading: {final_name}")

        try:
            with open(part_path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        fh.write(chunk)
                        received_bytes += len(chunk)
                        self.signals.progress.emit(received_bytes, total_bytes)
        except OSError as exc:
            self.signals.error.emit(f"Could not write file '{final_name}': {exc}")
            try:
                os.remove(part_path)
            except OSError:
                pass
            return
        except requests.exceptions.RequestException as exc:
            self.signals.error.emit(f"Download interrupted for '{final_name}': {exc}")
            try:
                os.remove(part_path)
            except OSError:
                pass
            return

        # Rename .part -> final only after a clean write
        try:
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(part_path, final_path)
        except OSError as exc:
            self.signals.error.emit(
                f"Download complete but could not rename '{final_name}.part': {exc}"
            )
            return

        self.signals.status.emit(f"Download complete: {final_name}")
        self.signals.finished.emit(final_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_filename(response: requests.Response, fallback: str) -> str:
        """
        Try to pull a clean filename from the Content-Disposition header.
        Fall back to the item's display name if the header is absent or unparseable.

        Sanitises the result so it's safe to use as a filename on Windows.
        """
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = None

        if content_disposition:
            # Try RFC 5987 encoded name first (filename*=UTF-8''...)
            match = re.search(r"filename\*=UTF-8''([^\s;]+)", content_disposition, re.IGNORECASE)
            if match:
                filename = unquote(match.group(1))
            else:
                # Fall back to plain filename="..."
                match = re.search(r'filename=["\']?([^"\';\r\n]+)["\']?', content_disposition)
                if match:
                    filename = match.group(1).strip()

        if not filename:
            filename = fallback

        # URL-decode before sanitising — TorBox sometimes returns
        # percent-encoded filenames (e.g. Atari%207800%20Box%20Art.rar)
        filename = unquote(filename)

        # Sanitise: remove characters Windows won't allow in filenames
        filename = re.sub(r'[\\/:*?"<>|]', "_", filename)
        filename = filename.strip(". ")

        return filename or "download"


# ---------------------------------------------------------------------------
# LinkRequestWorker — request a TorBox download URL without streaming the file
# ---------------------------------------------------------------------------

class LinkRequestSignals(QObject):
    finished = pyqtSignal(str)   # the resolved download URL
    error    = pyqtSignal(str)   # human-readable error


class LinkRequestWorker(QRunnable):
    """Fetch a time-limited TorBox download link for a single item/file."""

    def __init__(self, api_key: str, item: dict, file_id=None):
        super().__init__()
        self.signals   = LinkRequestSignals()
        self._api_key  = api_key
        self._item     = item
        self._file_id  = file_id

    def run(self):
        item        = self._item
        source_type = item.get("source_type", "")
        item_id     = item.get("id")

        if source_type in ("torrent", "magnet"):
            fid    = self._file_id
            if fid is None:
                files = item.get("files", [])
                fid   = files[0].get("id", 0) if files else 0
            result = api.request_download_link_torrent(self._api_key, item_id, fid)
        elif source_type == "webdl":
            result = api.request_download_link_webdl(self._api_key, item_id)
        elif source_type == "usenet":
            result = api.request_download_link_usenet(self._api_key, item_id)
        else:
            self.signals.error.emit(f"Unknown source type: {source_type}")
            return

        if result.get("ok"):
            url = result.get("data", "")
            if url:
                self.signals.finished.emit(url)
            else:
                self.signals.error.emit("No URL in response")
        else:
            self.signals.error.emit(result.get("detail", "Failed to get link"))
