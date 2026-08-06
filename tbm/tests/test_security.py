# test_security.py — Zip Slip path-traversal guard, filename sanitizing.

import os
import sys
import tempfile
import unittest
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import worker  # noqa: E402


class TestPathTraversalGuard(unittest.TestCase):

    def test_is_within_directory(self):
        self.assertTrue(worker._is_within_directory("C:/dl", "C:/dl/sub/file.txt"))
        self.assertFalse(worker._is_within_directory("C:/dl", "C:/other/file.txt"))
        self.assertFalse(worker._is_within_directory("C:/dl", "C:/dl/../../evil.txt"))

    def test_zip_slip_blocked_end_to_end(self):
        """A zip with a '../' entry must not extract anything outside dest,
        and the whole extraction should abort rather than partially succeed."""
        tmpdir = tempfile.mkdtemp()
        evil_zip = os.path.join(tmpdir, "evil.zip")
        dest_dir = os.path.join(tmpdir, "dest")
        os.makedirs(dest_dir, exist_ok=True)

        with zipfile.ZipFile(evil_zip, "w") as zf:
            zf.writestr("normal.txt", "fine")
            zf.writestr("../../escaped.txt", "should NOT land outside dest")

        with self.assertRaises(ValueError):
            worker.ExtractWorker._extract_zip(evil_zip, dest_dir)

        self.assertFalse(os.path.exists(os.path.join(tmpdir, "escaped.txt")))

    def test_normal_zip_extracts_fine(self):
        tmpdir = tempfile.mkdtemp()
        good_zip = os.path.join(tmpdir, "good.zip")
        dest_dir = os.path.join(tmpdir, "dest")
        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(good_zip, "w") as zf:
            zf.writestr("file.txt", "hello")
        worker.ExtractWorker._extract_zip(good_zip, dest_dir)
        self.assertTrue(os.path.isfile(os.path.join(dest_dir, "file.txt")))


class FakeResponse:
    def __init__(self, headers=None):
        self.headers = headers or {}


class TestFilenameSanitizing(unittest.TestCase):

    def test_reserved_windows_name_prefixed(self):
        name = worker.DownloadWorker._extract_filename(FakeResponse(), "CON.txt")
        self.assertEqual(name, "_CON.txt")

    def test_long_name_truncated_but_extension_kept(self):
        name = worker.DownloadWorker._extract_filename(FakeResponse(), "x" * 300 + ".mkv")
        self.assertLessEqual(len(name), 154)
        self.assertTrue(name.endswith(".mkv"))

    def test_illegal_characters_replaced(self):
        name = worker.DownloadWorker._extract_filename(FakeResponse(), 'a<b>c:d"e.txt')
        self.assertNotIn("<", name)
        self.assertNotIn(":", name)
        self.assertNotIn('"', name)

    def test_content_range_total_parsed(self):
        resp = FakeResponse(headers={"Content-Range": "bytes 1000-1999/5000"})
        self.assertEqual(worker.DownloadWorker._parse_content_range_total(resp), 5000)

    def test_content_range_absent_returns_none(self):
        self.assertIsNone(worker.DownloadWorker._parse_content_range_total(FakeResponse()))


if __name__ == "__main__":
    unittest.main()
