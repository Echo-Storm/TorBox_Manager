# test_v12_features.py — emoji-presentation icon fixes, drag-and-drop
# .torrent/.nzb onto the main window, and the download-complete sound.

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QMimeData, QUrl  # noqa: E402

from _helpers import make_window, make_torrent_item  # noqa: E402
import ui as ui_module  # noqa: E402

_UI_PY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui.py")


class TestIconFixes(unittest.TestCase):
    """Regression test for the emoji-presentation rendering bug: PAUSE/arrow
    characters render as colorful emoji on Windows unlike the app's other
    plain monochrome glyphs. Swapped for plain-arrows-block characters with
    no emoji fallback at all."""

    def test_no_flagged_characters_remain(self):
        with open(_UI_PY_PATH, encoding="utf-8") as f:
            src = f.read()
        flagged = {
            "\u23F8": "PAUSE (U+23F8, emoji-presentation)",
            "\u2B07": "DOWNWARDS BLACK ARROW (U+2B07, emoji-presentation)",
            "\u2B06": "UPWARDS BLACK ARROW (U+2B06, emoji-presentation)",
        }
        for bad_char, name in flagged.items():
            self.assertNotIn(bad_char, src, f"{name} character should not appear in ui.py")

    def test_replacement_characters_present(self):
        with open(_UI_PY_PATH, encoding="utf-8") as f:
            src = f.read()
        replacements = {
            "\u2016": "Pause All",   # DOUBLE VERTICAL LINE
            "\u2193": "Download All",  # DOWNWARDS ARROW
            "\u2191": "Update available",  # UPWARDS ARROW
        }
        for char, label_fragment in replacements.items():
            self.assertIn(f"{char}  {label_fragment}", src)


class TestDragAndDrop(unittest.TestCase):

    def setUp(self):
        self.win = make_window()

    def _mime_with_paths(self, paths):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        return mime

    def test_extracts_only_torrent_and_nzb_files(self):
        tmpdir = tempfile.mkdtemp()
        torrent = os.path.join(tmpdir, "a.torrent")
        nzb = os.path.join(tmpdir, "b.nzb")
        other = os.path.join(tmpdir, "c.txt")
        for p in (torrent, nzb, other):
            open(p, "w").close()

        mime = self._mime_with_paths([torrent, nzb, other])
        result = self.win._dropped_torrent_nzb_paths(mime)
        # QUrl round-trips through forward-slash-normalized paths on Windows
        # (still fully valid — os.path.isfile/basename handle both styles) —
        # normalize before comparing so the test isn't sensitive to that.
        self.assertEqual({os.path.normpath(p) for p in result},
                          {os.path.normpath(torrent), os.path.normpath(nzb)})

    def test_ignores_nonexistent_paths(self):
        mime = self._mime_with_paths([r"C:\does\not\exist.torrent"])
        result = self.win._dropped_torrent_nzb_paths(mime)
        self.assertEqual(result, [])

    def test_empty_when_no_urls(self):
        mime = QMimeData()
        mime.setText("just some text, not a file drop")
        result = self.win._dropped_torrent_nzb_paths(mime)
        self.assertEqual(result, [])

    def test_submit_dropped_file_routes_torrent_and_nzb_correctly(self):
        submitted = []
        self.win._submit_add = lambda fn, label: submitted.append(label)

        tmpdir = tempfile.mkdtemp()
        torrent = os.path.join(tmpdir, "a.torrent")
        nzb = os.path.join(tmpdir, "b.nzb")
        self.win._submit_dropped_file(torrent)
        self.win._submit_dropped_file(nzb)
        self.assertEqual(submitted, ["torrent", "NZB"])

    def test_drag_leave_restores_prior_status(self):
        """Regression: dragging a file over the window then away again (no
        drop) must not leave 'Drop to add...' stuck in the status bar."""
        self.win._set_status("30 items · 28 ready")

        class FakeEvent:
            def __init__(self, mime):
                self._mime = mime
                self.accepted = False

            def mimeData(self):
                return self._mime

            def acceptProposedAction(self):
                self.accepted = True

        tmpdir = tempfile.mkdtemp()
        torrent = os.path.join(tmpdir, "a.torrent")
        open(torrent, "w").close()

        self.win.dragEnterEvent(FakeEvent(self._mime_with_paths([torrent])))
        self.assertEqual(self.win._status_label.text(), "Drop to add .torrent / .nzb file(s)")

        self.win.dragLeaveEvent(None)
        self.assertEqual(self.win._status_label.text(), "30 items · 28 ready")

    def test_dropped_file_does_not_delete_source(self):
        """Drag-and-drop must never delete the source file — unlike Watch
        Folder, this file isn't 'ours' to clean up."""
        tmpdir = tempfile.mkdtemp()
        torrent = os.path.join(tmpdir, "a.torrent")
        open(torrent, "w").close()

        self.win._submit_add = lambda fn, label: None
        self.win._submit_dropped_file(torrent)
        self.assertTrue(os.path.isfile(torrent), "dropped file should not be deleted")


class TestCompleteSound(unittest.TestCase):

    def test_play_complete_sound_never_raises(self):
        # Real winsound call on this Windows test environment — just confirm
        # it doesn't raise or block.
        from ui import MainWindow
        MainWindow._play_complete_sound()

    def test_on_download_finished_plays_sound_only_when_enabled(self):
        win = make_window()
        win._update_queue_table([make_torrent_item(1, "One", cached=True)])
        key = "torrent:1"

        # _on_download_finished also calls hist.append() unconditionally —
        # since tests run unfrozen, history._history_path() would otherwise
        # resolve to (and write real fake entries into) this actual project's
        # tbm/download_history.json. Redirect it to a throwaway temp file.
        import history as history_module
        tmp_history = os.path.join(tempfile.mkdtemp(), "download_history.json")
        history_module._history_path = lambda: tmp_history

        played = []
        win._play_complete_sound = lambda: played.append(True)

        win.config["play_sound_on_complete"] = False
        win._on_download_finished(key, r"C:\dl\One\a.bin")
        self.assertEqual(played, [])

        win.config["play_sound_on_complete"] = True
        win._on_download_finished(key, r"C:\dl\One\a.bin")
        self.assertEqual(played, [True])


if __name__ == "__main__":
    unittest.main()
