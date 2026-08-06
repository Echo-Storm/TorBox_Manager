# test_downloads.py — cancel, pause/resume, retry-all-failed, bulk
# download/delete/copy-links, disk-space guard, error-state button wiring.

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from _helpers import make_window, make_torrent_item, always_yes  # noqa: E402
import ui as ui_module  # noqa: E402
from ui import COL_DOWNLOAD  # noqa: E402


class FakeWorker:
    def __init__(self):
        self.cancel_called = False
        self.pause_called = False

    def cancel(self):
        self.cancel_called = True

    def pause(self):
        self.pause_called = True


class TestCancel(unittest.TestCase):

    def test_cancel_requests_stop_on_all_active_workers(self):
        win = make_window()
        win._update_queue_table([make_torrent_item(1, "One")])
        key = "torrent:1"
        w1, w2 = FakeWorker(), FakeWorker()
        win._active_downloads[key] = [w1, w2]
        win._downloading[key] = 2
        win._cancel_download(key)
        self.assertTrue(w1.cancel_called and w2.cancel_called)

    def test_cancelled_row_shows_retry_when_torbox_reports_error(self):
        """A 2-way Ready/not-Ready check would wrongly leave this disabled."""
        win = make_window()
        item = make_torrent_item(1, "One", cached=False, download_state="error")
        win._update_queue_table([item])
        key = "torrent:1"
        win._active_downloads[key] = [FakeWorker()]
        win._downloading[key] = 1
        win._on_download_cancelled(key)
        dl_btn = win._table.cellWidget(win._find_row(key), COL_DOWNLOAD)
        self.assertEqual(dl_btn.text(), "Retry")
        self.assertTrue(dl_btn.isEnabled())


class TestPauseResume(unittest.TestCase):

    def setUp(self):
        self.win = make_window()
        self.win._update_queue_table([make_torrent_item(1, "One")])
        self.key = "torrent:1"

    def test_pause_then_row_shows_resume(self):
        w = FakeWorker()
        self.win._active_downloads[self.key] = [w]
        self.win._downloading[self.key] = 1
        self.win._pause_download(self.key)
        self.assertTrue(w.pause_called)

        self.win._untrack_worker(self.key, w)
        self.win._on_download_paused(self.key, 400, r"C:\dl\One\a.part", r"C:\dl\One", 1, None)
        self.assertNotIn(self.key, self.win._downloading)
        self.assertIn(self.key, self.win._paused_downloads)
        dl_btn = self.win._table.cellWidget(self.win._find_row(self.key), COL_DOWNLOAD)
        self.assertEqual(dl_btn.text(), "Resume")

    def test_poll_does_not_clobber_paused_row(self):
        self.win._on_download_paused(self.key, 400, r"C:\dl\One\a.part", r"C:\dl\One", 1, None)
        self.win._update_queue_table([make_torrent_item(1, "One")])
        dl_btn = self.win._table.cellWidget(self.win._find_row(self.key), COL_DOWNLOAD)
        self.assertEqual(dl_btn.text(), "Resume")

    def test_resume_dispatches_with_correct_args(self):
        self.win._on_download_paused(self.key, 400, r"C:\dl\One\a.part", r"C:\dl\One", 1, None)

        captured = {}

        class FakeDownloadWorker:
            def __init__(self, **kwargs):
                captured.update(kwargs)
                self.signals = type("S", (), {
                    n: type("Sig", (), {"connect": lambda self, cb: None})()
                    for n in ("progress", "finished", "error", "cancelled", "paused", "status")
                })()

        ui_module.DownloadWorker = FakeDownloadWorker
        self.win._pool.start = lambda w: None

        self.win._resume_download(self.key)
        self.assertNotIn(self.key, self.win._paused_downloads)
        self.assertEqual(captured["resume_from"], 400)
        self.assertEqual(captured["resume_part_path"], r"C:\dl\One\a.part")
        self.assertEqual(captured["download_dir"], r"C:\dl\One")

    def test_discard_resets_row_and_removes_part_file_entry(self):
        self.win._on_download_paused(self.key, 400, r"C:\dl\One\a.part", r"C:\dl\One", 1, None)
        self.win._discard_paused_download(self.key)
        self.assertNotIn(self.key, self.win._paused_downloads)
        dl_btn = self.win._table.cellWidget(self.win._find_row(self.key), COL_DOWNLOAD)
        self.assertEqual(dl_btn.text(), "Download")
        self.assertTrue(dl_btn.isEnabled())  # item is still Ready on TorBox

    def test_discard_shows_retry_when_torbox_now_reports_error(self):
        item = make_torrent_item(1, "One", cached=False, download_state="error")
        self.win._update_queue_table([item])
        self.win._on_download_paused(self.key, 400, r"C:\dl\One\a.part", r"C:\dl\One", 1, None)
        self.win._discard_paused_download(self.key)
        dl_btn = self.win._table.cellWidget(self.win._find_row(self.key), COL_DOWNLOAD)
        self.assertEqual(dl_btn.text(), "Retry")
        self.assertTrue(dl_btn.isEnabled())

    def test_multi_file_torrent_pause_metadata_not_premature(self):
        """Regression: metadata must not be published until ALL workers for
        a multi-file row have reported paused, not just the first."""
        item2 = make_torrent_item(2, "Two", cached=True,
                                   files=[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
        self.win._update_queue_table([item2])
        key2 = "torrent:2"
        self.win._downloading[key2] = 2

        self.win._on_download_paused(key2, 100, r"C:\dl\Two\a.part", r"C:\dl\Two", 1, "a")
        self.assertNotIn(key2, self.win._paused_downloads)
        self.assertEqual(self.win._downloading.get(key2), 1)

        self.win._on_download_paused(key2, 200, r"C:\dl\Two\b.part", r"C:\dl\Two", 2, "b")
        self.assertIn(key2, self.win._paused_downloads)
        self.assertEqual(self.win._paused_downloads[key2]["file_id"], 2)
        self.assertNotIn(key2, self.win._downloading)


class TestRetryAllFailed(unittest.TestCase):

    def test_retries_only_tracked_error_rows(self):
        win = make_window()
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        win._update_queue_table(items)
        win._download_errors.add("torrent:1")

        started = []
        win._start_download = lambda key, item: started.append(key)
        win._on_retry_all_failed()
        self.assertEqual(started, ["torrent:1"])

    def test_no_candidates_does_not_raise(self):
        win = make_window()
        win._on_retry_all_failed()  # nothing tracked — should just log and return


class TestBulkActions(unittest.TestCase):

    def setUp(self):
        self.win = make_window()
        QMessageBox.question = staticmethod(always_yes)

    def test_bulk_delete_removes_only_targets(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two"), make_torrent_item(3, "Three")]
        self.win._update_queue_table(items)

        class FakeDeleteWorker:
            def __init__(self, delete_fn, row_key, item_name):
                self.signals = type("S", (), {
                    "finished": type("Sig", (), {"connect": lambda self, cb: None})(),
                    "status": type("Sig", (), {"connect": lambda self, cb: None})(),
                })()

        ui_module.DeleteWorker = FakeDeleteWorker
        self.win._pool.start = lambda w: None

        self.win._bulk_delete(["torrent:1", "torrent:2"])
        remaining = {self.win._table.item(r, 0).text() for r in range(self.win._table.rowCount())}
        self.assertEqual(remaining, {"Three"})

    def test_bulk_download_routes_through_disk_space_check(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)

        called = {}

        def fake_confirm(candidates):
            called["count"] = len(candidates)
            return False  # simulate declining

        self.win._confirm_disk_space = fake_confirm
        self.win._bulk_download(["torrent:1", "torrent:2"])
        self.assertEqual(called.get("count"), 2)

    def test_bulk_copy_links_joins_only_resolved(self):
        items = [make_torrent_item(1, "One", cached=True), make_torrent_item(2, "Two", cached=True)]
        self.win._update_queue_table(items)

        class FakeSig:
            def __init__(self):
                self.cb = None

            def connect(self, cb):
                self.cb = cb

        class FakeLinkWorker:
            def __init__(self, api_key, item):
                self.signals = type("S", (), {"finished": FakeSig(), "error": FakeSig()})()

        ui_module.LinkRequestWorker = FakeLinkWorker
        captured_workers = []
        self.win._pool.start = lambda w: captured_workers.append(w)

        self.win._bulk_copy_links(["torrent:1", "torrent:2"])
        self.assertEqual(len(captured_workers), 2)
        captured_workers[0].signals.finished.cb("https://example.com/file1")
        captured_workers[1].signals.error.cb("timeout")

        clip = QApplication.clipboard().text()
        self.assertEqual(clip, "https://example.com/file1")


if __name__ == "__main__":
    unittest.main()
