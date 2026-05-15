# api.py
# TorBox Manager EchoStorm Edition
#
# All TorBox API communication lives here. No Qt imports, no UI references,
# no threading — this module is called exclusively from worker threads.
#
# Every public function returns a dict with this guaranteed shape:
#
#   {
#       "success": bool,
#       "detail":  str,   # human-readable message, safe to show in the UI
#       "data":    ...    # endpoint-specific payload, or None on failure
#   }
#
# Callers only need to check ["success"] and can always read ["detail"] for
# a loggable / displayable message regardless of outcome.
#
# Network exceptions are caught here and converted to the same dict shape —
# nothing raises out of this module.

import os
import requests

from constants import (
    API_BASE_URL,
    ENDPOINT_ADD_TORRENT,
    ENDPOINT_ADD_WEBDL,
    ENDPOINT_ADD_USENET,
    ENDPOINT_LIST_TORRENTS,
    ENDPOINT_LIST_WEBDL,
    ENDPOINT_LIST_USENET,
    ENDPOINT_DL_TORRENT,
    ENDPOINT_DL_WEBDL,
    ENDPOINT_DL_USENET,
    ENDPOINT_DEL_TORRENT,
    ENDPOINT_DEL_WEBDL,
    ENDPOINT_DEL_USENET,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Timeout for all API calls except file downloads (which use their own stream).
# 20 seconds is generous for a REST call; avoids hanging the worker thread forever.
_REQUEST_TIMEOUT = 20


def _headers(api_key: str) -> dict:
    """Build the auth header required by every TorBox endpoint."""
    return {"Authorization": f"Bearer {api_key}"}


def _url(endpoint: str) -> str:
    """Concatenate base URL and endpoint path."""
    return f"{API_BASE_URL}{endpoint}"


def _ok(data) -> dict:
    """Wrap a successful result in the standard return shape."""
    return {"success": True, "detail": "OK", "data": data}


def _err(detail: str) -> dict:
    """Wrap a failure message in the standard return shape."""
    return {"success": False, "detail": detail, "data": None}


def _parse(response: requests.Response) -> dict:
    """
    Parse a TorBox API response into our standard return shape.

    TorBox always returns JSON with at minimum:
        { "success": bool, "detail": str, "data": ... }

    We pass that through directly so the UI can surface TorBox's own
    messages verbatim — they are already user-friendly.
    """
    try:
        body = response.json()
    except ValueError:
        return _err(f"Non-JSON response from TorBox (HTTP {response.status_code})")

    # Normalise: TorBox sometimes omits "data" on error responses.
    return {
        "success": bool(body.get("success", False)),
        "detail":  str(body.get("detail", "No detail provided")),
        "data":    body.get("data", None),
    }


def _request(method: str, endpoint: str, api_key: str, **kwargs) -> dict:
    """
    Central HTTP dispatcher. All public functions route through here.

    Handles:
    - Auth header injection
    - Timeout
    - requests exceptions → _err() so nothing raises out of api.py
    - HTTP error status codes (4xx / 5xx that TorBox didn't wrap in JSON)
    """
    try:
        resp = requests.request(
            method,
            _url(endpoint),
            headers=_headers(api_key),
            timeout=_REQUEST_TIMEOUT,
            **kwargs,
        )
    except requests.exceptions.ConnectionError:
        return _err("Could not reach TorBox — check your internet connection.")
    except requests.exceptions.Timeout:
        return _err("TorBox did not respond in time — try again.")
    except requests.exceptions.RequestException as exc:
        return _err(f"Request failed: {exc}")

    return _parse(resp)


# ---------------------------------------------------------------------------
# Add items
# ---------------------------------------------------------------------------

def add_magnet(api_key: str, magnet_link: str) -> dict:
    """
    Submit a magnet link to TorBox.

    magnet_link: full magnet:?xt=... string
    """
    return _request(
        "POST",
        ENDPOINT_ADD_TORRENT,
        api_key,
        data={"magnet": magnet_link},
    )


def add_torrent_file(api_key: str, file_path: str) -> dict:
    """
    Upload a .torrent file to TorBox.

    file_path: absolute path to a .torrent file on disk.
    Reads the file here so worker threads don't have to manage file handles.
    """
    if not os.path.isfile(file_path):
        return _err(f"Torrent file not found: {file_path}")

    try:
        with open(file_path, "rb") as fh:
            file_bytes = fh.read()
    except OSError as exc:
        return _err(f"Could not read torrent file: {exc}")

    filename = os.path.basename(file_path)
    return _request(
        "POST",
        ENDPOINT_ADD_TORRENT,
        api_key,
        files={"file": (filename, file_bytes, "application/x-bittorrent")},
    )


def add_hoster_link(api_key: str, url: str) -> dict:
    """
    Submit a hoster URL (1fichier, Mega, etc.) for TorBox to cache.

    url: the raw hoster link pasted by the user.
    """
    return _request(
        "POST",
        ENDPOINT_ADD_WEBDL,
        api_key,
        data={"link": url},
    )


def add_nzb_file(api_key: str, file_path: str) -> dict:
    """
    Upload an .nzb file to TorBox.

    file_path: absolute path to an .nzb file on disk.
    """
    if not os.path.isfile(file_path):
        return _err(f"NZB file not found: {file_path}")

    try:
        with open(file_path, "rb") as fh:
            file_bytes = fh.read()
    except OSError as exc:
        return _err(f"Could not read NZB file: {exc}")

    filename = os.path.basename(file_path)
    return _request(
        "POST",
        ENDPOINT_ADD_USENET,
        api_key,
        files={"file": (filename, file_bytes, "application/x-nzb")},
    )


# ---------------------------------------------------------------------------
# List queue items
# ---------------------------------------------------------------------------

def list_torrents(api_key: str) -> dict:
    """Fetch all torrent/magnet queue items for this account.

    bypass_cache=true is required — without it TorBox returns a server-side
    cached snapshot that may be stale and only contain the most recent item.
    """
    return _request("GET", ENDPOINT_LIST_TORRENTS, api_key,
                    params={"bypass_cache": "true"})


def list_webdl(api_key: str) -> dict:
    """Fetch all web/hoster download queue items for this account."""
    return _request("GET", ENDPOINT_LIST_WEBDL, api_key,
                    params={"bypass_cache": "true"})


def list_usenet(api_key: str) -> dict:
    """Fetch all usenet/NZB queue items for this account."""
    return _request("GET", ENDPOINT_LIST_USENET, api_key,
                    params={"bypass_cache": "true"})


def list_all(api_key: str) -> dict:
    """
    Fetch all three queues and return a unified list.

    Each item in the returned list is tagged with a "source_type" key
    ("torrent", "magnet", "webdl", "usenet") so the UI can show the right icon.

    On partial failure (e.g. one endpoint is down), the successful results
    are still returned — the detail string will mention what failed.
    """
    results   = []
    errors    = []

    # Torrents and magnets both come from the same endpoint.
    # TorBox distinguishes them via a "magnet" boolean in each item.
    torrents = list_torrents(api_key)
    if torrents["success"] and isinstance(torrents["data"], list):
        for item in torrents["data"]:
            # magnet field is a string (the magnet URI) for magnet adds,
            # or null for .torrent file uploads. Confirmed from live API 2026-05-15.
            item["source_type"] = "magnet" if item.get("magnet") else "torrent"
            results.append(item)
    elif not torrents["success"]:
        errors.append(f"Torrents: {torrents['detail']}")

    webdl = list_webdl(api_key)
    if webdl["success"] and isinstance(webdl["data"], list):
        for item in webdl["data"]:
            item["source_type"] = "webdl"
            results.append(item)
    elif not webdl["success"]:
        errors.append(f"Web DL: {webdl['detail']}")

    usenet = list_usenet(api_key)
    if usenet["success"] and isinstance(usenet["data"], list):
        for item in usenet["data"]:
            item["source_type"] = "usenet"
            results.append(item)
    elif not usenet["success"]:
        errors.append(f"Usenet: {usenet['detail']}")

    if errors:
        detail = "Partial refresh — " + "; ".join(errors)
    else:
        detail = f"Queue refreshed — {len(results)} item(s)"

    return {
        "success": len(errors) < 3,   # total failure only if all three failed
        "detail":  detail,
        "data":    results,
    }


# ---------------------------------------------------------------------------
# Request download links
# ---------------------------------------------------------------------------

def request_download_link_torrent(api_key: str, torrent_id: int, file_id: int) -> dict:
    """
    Ask TorBox for a time-limited direct download URL for a completed torrent.

    torrent_id: the item's id from list_torrents()
    file_id:    the specific file within the torrent (use the first file if single)
    """
    return _request(
        "GET",
        ENDPOINT_DL_TORRENT,
        api_key,
        params={"token": api_key, "torrent_id": torrent_id, "file_id": file_id},
    )


def request_download_link_webdl(api_key: str, webdl_id: int) -> dict:
    """Ask TorBox for a direct download URL for a completed web/hoster download."""
    return _request(
        "GET",
        ENDPOINT_DL_WEBDL,
        api_key,
        params={"token": api_key, "webdl_id": webdl_id},
    )


def request_download_link_usenet(api_key: str, usenet_id: int) -> dict:
    """Ask TorBox for a direct download URL for a completed usenet download."""
    return _request(
        "GET",
        ENDPOINT_DL_USENET,
        api_key,
        params={"token": api_key, "usenet_id": usenet_id},
    )


# ---------------------------------------------------------------------------
# Delete items
# ---------------------------------------------------------------------------

def delete_torrent(api_key: str, torrent_id: int) -> dict:
    """Remove a torrent/magnet from the TorBox queue."""
    return _request(
        "POST",
        ENDPOINT_DEL_TORRENT,
        api_key,
        json={"torrent_id": torrent_id, "operation": "delete"},
    )


def delete_webdl(api_key: str, webdl_id: int) -> dict:
    """Remove a web/hoster download from the TorBox queue."""
    return _request(
        "POST",
        ENDPOINT_DEL_WEBDL,
        api_key,
        json={"webdl_id": webdl_id, "operation": "delete"},
    )


def delete_usenet(api_key: str, usenet_id: int) -> dict:
    """Remove a usenet item from the TorBox queue."""
    return _request(
        "POST",
        ENDPOINT_DEL_USENET,
        api_key,
        json={"usenet_id": usenet_id, "operation": "delete"},
    )

# ---------------------------------------------------------------------------
# Debug helper — first-run field name verification
# ---------------------------------------------------------------------------

def debug_raw_list(api_key: str) -> None:
    """
    Print the raw JSON response from all three list endpoints to stdout.

    Call this ONCE on first run to verify the actual field names TorBox
    returns before trusting the queue table display. Run from a quick
    scratch script in the project folder:

        import api
        api.debug_raw_list("your_api_key_here")

    Fields to confirm:
        - Status/state field name       (assumed: "download_state")
        - Progress field name           (assumed: "progress")
        - Size field name               (assumed: "size")
        - Files list field (torrents)   (assumed: "files")
        - File id within files list     (assumed: "id")
        - Magnet boolean field          (assumed: "magnet")

    Remove or comment out calls to this function after verification.
    """
    import json

    for label, endpoint in [
        ("TORRENTS", ENDPOINT_LIST_TORRENTS),
        ("WEB DL",   ENDPOINT_LIST_WEBDL),
        ("USENET",   ENDPOINT_LIST_USENET),
    ]:
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        result = _request("GET", endpoint, api_key)
        if result["success"] and isinstance(result["data"], list):
            items = result["data"]
            print(f"  {len(items)} item(s) returned")
            if items:
                print(f"\n  First item keys:\n  {list(items[0].keys())}")
                print(f"\n  First item full:\n")
                print(json.dumps(items[0], indent=4, default=str))
        else:
            print(f"  Error: {result['detail']}")
