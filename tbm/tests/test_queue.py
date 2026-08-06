# test_queue.py — poll diffing, table sorting/row-index self-healing,
# stale-row cleanup, Clear All/Clear Done, magnet dedupe, poll overlap guard.

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QMessageBox  # noqa: E402

from _helpers import make_window, make_torrent_item, always_yes  # noqa: E402
from ui import COL_NAME, _classify_download_state  # noqa: E402


class TestStatusClassification(unittest.TestCase):

    def test_buckets(self):
        self.assertEqual(_classify_download_state("downloading torrent"), "downloading")
        self.assertEqual(_classify_download_state("error occurred"), "error")
        self.assertEqual(_classify_download_state("something else"), "queued")


class TestPollDiffing(unittest.TestCase):

    def setUp(self):
        self.win = make_window()

    def test_populate_and_reissue_same_items(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)
        self.assertEqual(self.win._table.rowCount(), 2)
        # Re-polling with identical data must not duplicate rows.
        self.win._update_queue_table(items)
        self.assertEqual(self.win._table.rowCount(), 2)

    def test_stale_row_dropped_after_three_missed_polls(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)
        subset = items[:1]
        for _ in range(3):
            self.win._update_queue_table(subset)
        self.assertEqual(self.win._table.rowCount(), 1)

    def test_stale_row_not_dropped_on_single_miss(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)
        self.win._update_queue_table(items[:1])  # one miss for item 2
        self.assertEqual(self.win._table.rowCount(), 2)

    def test_poll_overlap_guard(self):
        self.win._poll_in_flight = True
        # Should return immediately without dispatching another PollWorker
        # (no exception, no crash — the guard is purely a no-op skip).
        self.win._submit_poll()
        self.win._poll_in_flight = False


class TestFindRowSelfHeals(unittest.TestCase):
    """Regression test: enabling sortable columns means a user click can
    reorder rows outside of poll updates. _find_row must resolve the correct
    physical row even when the cached _row_index is stale, and downstream
    actions (Delete) must use it rather than the raw cache."""

    def setUp(self):
        self.win = make_window()
        items = [
            make_torrent_item(1, "Bravo"),
            make_torrent_item(2, "Alpha"),
            make_torrent_item(3, "Charlie"),
        ]
        self.win._update_queue_table(items)

    def test_find_row_correct_immediately_after_manual_sort(self):
        self.win._table.horizontalHeader().setSortIndicator(COL_NAME, Qt.SortOrder.AscendingOrder)
        names_in_order = [self.win._table.item(r, COL_NAME).text()
                           for r in range(self.win._table.rowCount())]
        self.assertEqual(names_in_order, sorted(names_in_order))

        for key, expected in [("torrent:1", "Bravo"), ("torrent:2", "Alpha"), ("torrent:3", "Charlie")]:
            row = self.win._find_row(key)
            self.assertEqual(self.win._table.item(row, COL_NAME).text(), expected)

    def test_delete_after_manual_sort_hits_correct_row(self):
        QMessageBox.question = staticmethod(always_yes)
        self.win._table.horizontalHeader().setSortIndicator(COL_NAME, Qt.SortOrder.AscendingOrder)
        self.win._on_delete_clicked("torrent:2")  # "Alpha"
        remaining = {self.win._table.item(r, COL_NAME).text()
                     for r in range(self.win._table.rowCount())}
        self.assertEqual(remaining, {"Bravo", "Charlie"})


class TestClearActions(unittest.TestCase):

    def setUp(self):
        self.win = make_window()
        QMessageBox.question = staticmethod(always_yes)

    def test_clear_all_preserves_active_download_row(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)
        self.win._downloading["torrent:2"] = 1
        self.win._active_downloads["torrent:2"] = []
        self.win._on_clear_all()
        self.assertEqual(self.win._table.rowCount(), 1)
        self.assertIn("torrent:2", self.win._row_items)

    def test_clear_all_preserves_paused_download_row(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)
        self.win._paused_downloads["torrent:2"] = {
            "part_path": r"C:\dl\x.part", "bytes_done": 1, "download_dir": r"C:\dl",
            "file_id": 1, "file_name": None,
        }
        self.win._on_clear_all()
        self.assertEqual(self.win._table.rowCount(), 1)

    def test_clear_done_spares_paused_row_even_though_ready(self):
        items = [make_torrent_item(1, "One", cached=True)]
        self.win._update_queue_table(items)
        self.win._paused_downloads["torrent:1"] = {
            "part_path": r"C:\dl\x.part", "bytes_done": 1, "download_dir": r"C:\dl",
            "file_id": 1, "file_name": None,
        }
        self.win._on_clear_done()
        self.assertEqual(self.win._table.rowCount(), 1)


class TestMagnetDedupe(unittest.TestCase):

    def test_duplicate_detection(self):
        win = make_window()
        item = make_torrent_item(1, "One")
        item["magnet"] = "magnet:?xt=urn:btih:ABC"
        win._update_queue_table([item])
        self.assertTrue(win._is_duplicate_magnet("magnet:?xt=urn:btih:ABC"))
        self.assertFalse(win._is_duplicate_magnet("magnet:?xt=urn:btih:NOPE"))


if __name__ == "__main__":
    unittest.main()
