# test_speed_display.py — aggregate download speed / remaining-size status
# bar display.

import os
import sys
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _helpers import make_window  # noqa: E402


class TestSpeedDisplay(unittest.TestCase):

    def setUp(self):
        self.win = make_window()

    def test_hidden_when_idle(self):
        self.win._update_speed_display()
        self.assertTrue(self.win._speed_label.isHidden())

    def test_shows_count_speed_and_remaining_while_active(self):
        self.win._downloading["torrent:1"] = 1
        self.win._on_download_progress("torrent:1", 1_000_000, 10_000_000)
        self.win._update_speed_display()
        time.sleep(0.2)
        self.win._on_download_progress("torrent:1", 3_000_000, 10_000_000)
        self.win._update_speed_display()

        text = self.win._speed_label.text()
        self.assertIn("downloading", text)
        self.assertIn("/s", text)
        self.assertIn("left", text)
        self.assertFalse(self.win._speed_label.isHidden())

    def test_hides_again_once_downloads_finish(self):
        self.win._downloading["torrent:1"] = 1
        self.win._on_download_progress("torrent:1", 1_000_000, 10_000_000)
        self.win._update_speed_display()

        self.win._downloading.pop("torrent:1", None)
        self.win._progress_bytes.pop("torrent:1", None)
        self.win._progress_totals.pop("torrent:1", None)
        self.win._update_speed_display()
        self.assertTrue(self.win._speed_label.isHidden())


if __name__ == "__main__":
    unittest.main()
