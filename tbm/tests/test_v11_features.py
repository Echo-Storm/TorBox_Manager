# test_v11_features.py — multi-magnet paste, Pause All/Resume All (and the
# concurrency-limit bug it surfaced in _resume_download), tray notification
# click-to-open, type/status filtering, account bandwidth stats, and
# settings export/import.

import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox  # noqa: E402

from _helpers import make_window, make_torrent_item, always_yes  # noqa: E402
import ui as ui_module  # noqa: E402
from config import DEFAULTS  # noqa: E402
from dialogs import AddMagnetDialog, SettingsDialog  # noqa: E402


class TestMultiMagnetDialog(unittest.TestCase):

    def test_magnet_links_splits_and_strips_lines(self):
        dlg = AddMagnetDialog(None)
        dlg._input.setPlainText(
            "magnet:?xt=urn:btih:AAA\n\n  magnet:?xt=urn:btih:BBB  \nmagnet:?xt=urn:btih:CCC"
        )
        self.assertEqual(
            dlg.magnet_links(),
            ["magnet:?xt=urn:btih:AAA", "magnet:?xt=urn:btih:BBB", "magnet:?xt=urn:btih:CCC"],
        )

    def test_validation_rejects_non_magnet_line(self):
        dlg = AddMagnetDialog(None)
        dlg._input.setPlainText("magnet:?xt=urn:btih:AAA\nhttps://not-a-magnet")
        accepted = []
        dlg.accept = lambda: accepted.append(True)
        dlg._validate_and_accept()
        self.assertEqual(accepted, [])
        self.assertIn("magnet:", dlg._error_label.text())


class TestAddMagnetLoop(unittest.TestCase):

    def test_adds_each_link_and_batches_duplicate_prompt(self):
        win = make_window()
        item = make_torrent_item(1, "Existing")
        item["magnet"] = "magnet:?xt=urn:btih:DUPE"
        win._update_queue_table([item])

        class FakeDialog:
            def exec(self):
                return True

            def magnet_links(self):
                return ["magnet:?xt=urn:btih:DUPE", "magnet:?xt=urn:btih:NEW"]

        ui_module.AddMagnetDialog = lambda parent: FakeDialog()
        QMessageBox.question = staticmethod(always_yes)

        submitted = []
        win._submit_add = lambda fn, label: submitted.append(fn)

        win._on_add_magnet()
        self.assertEqual(len(submitted), 2)


class TestPauseAllResumeAll(unittest.TestCase):

    def setUp(self):
        self.win = make_window()

    def test_pause_all_pauses_every_active_worker(self):
        class FakeWorker:
            def __init__(self):
                self.paused = False

            def pause(self):
                self.paused = True

        w1, w2 = FakeWorker(), FakeWorker()
        self.win._active_downloads = {"a": [w1], "b": [w2]}
        self.win._downloading = {"a": 1, "b": 1}
        self.win._on_pause_all()
        self.assertTrue(w1.paused and w2.paused)

    def test_resume_all_respects_concurrency_limit(self):
        """The actual bug found in this round's sweep: resume used to bypass
        the concurrency limit entirely. Resume All on 3 paused rows with a
        limit of 1 must start only 1 and queue the rest."""
        self.win.config["max_concurrent_downloads"] = 1
        items = [make_torrent_item(i, f"Item{i}") for i in (1, 2, 3)]
        self.win._update_queue_table(items)
        for i in (1, 2, 3):
            self.win._paused_downloads[f"torrent:{i}"] = {
                "part_path": f"C:\\dl\\{i}.part", "bytes_done": 10,
                "download_dir": "C:\\dl", "file_id": 1, "file_name": None,
            }

        dispatched = []

        def fake_dispatch(**kw):
            key = kw["key"]
            dispatched.append(key)
            # Real _dispatch_download_worker increments this — the mock must
            # too, or the concurrency check has nothing to see.
            self.win._downloading[key] = self.win._downloading.get(key, 0) + 1

        self.win._dispatch_download_worker = fake_dispatch
        self.win._on_resume_all()

        self.assertEqual(len(dispatched), 1, "only one slot available — only one should dispatch")
        self.assertEqual(len(self.win._resume_queue), 2, "the other two should be queued, not started")

    def test_queued_resume_drains_as_slot_frees_up(self):
        self.win.config["max_concurrent_downloads"] = 1
        items = [make_torrent_item(i, f"Item{i}") for i in (1, 2)]
        self.win._update_queue_table(items)
        for i in (1, 2):
            self.win._paused_downloads[f"torrent:{i}"] = {
                "part_path": f"C:\\dl\\{i}.part", "bytes_done": 10,
                "download_dir": "C:\\dl", "file_id": 1, "file_name": None,
            }

        dispatched = []

        def fake_dispatch(**kw):
            key = kw["key"]
            dispatched.append(key)
            self.win._downloading[key] = self.win._downloading.get(key, 0) + 1

        self.win._dispatch_download_worker = fake_dispatch
        self.win._on_resume_all()
        self.assertEqual(dispatched, ["torrent:1"])
        self.assertEqual(self.win._resume_queue, ["torrent:2"])

        # Slot frees up (e.g. torrent:1 finished) -> queued resume should drain.
        self.win._downloading.pop("torrent:1", None)
        self.win._try_start_queued()
        self.assertEqual(dispatched, ["torrent:1", "torrent:2"])
        self.assertEqual(self.win._resume_queue, [])

    def test_removing_a_queued_resume_row_discards_it_cleanly(self):
        self.win.config["max_concurrent_downloads"] = 0  # force everything to queue
        items = [make_torrent_item(1, "One")]
        self.win._update_queue_table(items)
        self.win._paused_downloads["torrent:1"] = {
            "part_path": "C:\\dl\\1.part", "bytes_done": 10,
            "download_dir": "C:\\dl", "file_id": 1, "file_name": None,
        }
        self.win._resume_download("torrent:1")
        self.assertIn("torrent:1", self.win._resume_queue)

        self.win._remove_row("torrent:1")
        self.assertNotIn("torrent:1", self.win._resume_queue)
        self.assertNotIn("torrent:1", self.win._paused_downloads)


class TestTrayNotificationClick(unittest.TestCase):

    def test_click_opens_last_notification_path(self):
        win = make_window()
        win._last_notification_path = r"C:\dl\file.bin"
        opened = []
        win._open_in_explorer = staticmethod(lambda p: opened.append(p))
        win._on_tray_message_clicked()
        self.assertEqual(opened, [r"C:\dl\file.bin"])

    def test_click_with_no_path_does_nothing(self):
        win = make_window()
        win._last_notification_path = None
        opened = []
        win._open_in_explorer = staticmethod(lambda p: opened.append(p))
        win._on_tray_message_clicked()
        self.assertEqual(opened, [])


class TestFilterByTypeStatus(unittest.TestCase):

    def test_filter_matches_type_badge_text(self):
        win = make_window()
        items = [
            make_torrent_item(1, "Alpha"),
            {**make_torrent_item(2, "Beta"), "source_type": "webdl"},
        ]
        # webdl items don't carry "files"/torrent-only fields; keep it simple.
        items[1] = {"id": 2, "name": "Beta", "source_type": "webdl", "size": 500, "cached": True, "download_state": "seeding"}
        win._update_queue_table(items)
        win._apply_filter("hoster")
        hidden = [win._table.isRowHidden(r) for r in range(win._table.rowCount())]
        names = [win._table.item(r, 0).text() for r in range(win._table.rowCount())]
        visible_names = [n for n, h in zip(names, hidden) if not h]
        self.assertEqual(visible_names, ["Beta"])

    def test_filter_matches_status_text(self):
        win = make_window()
        items = [
            make_torrent_item(1, "Alpha", cached=True),
            make_torrent_item(2, "Beta", cached=False, download_state="error"),
        ]
        win._update_queue_table(items)
        win._apply_filter("error")
        names = [win._table.item(r, 0).text() for r in range(win._table.rowCount())
                  if not win._table.isRowHidden(r)]
        self.assertEqual(names, ["Beta"])


class TestAccountBandwidth(unittest.TestCase):

    def test_usage_label_set_when_present(self):
        win = make_window()
        win._on_account_info_finished({"plan": 2, "total_downloaded": 5_000_000_000})
        self.assertIn("Downloaded", win._account_usage_label.text())

    def test_usage_label_blank_when_absent(self):
        win = make_window()
        win._on_account_info_finished({"plan": 2})
        self.assertEqual(win._account_usage_label.text(), "")


class TestSettingsExportImport(unittest.TestCase):

    def test_export_writes_current_widget_state(self):
        dlg = SettingsDialog(dict(DEFAULTS))
        dlg._key_input.setText("my-test-key")
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "export.json")

        from PyQt6.QtWidgets import QFileDialog
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (path, ""))
        QMessageBox.information = staticmethod(lambda *a, **k: None)

        dlg._export_settings()
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["api_key"], "my-test-key")

    def test_import_writes_config_and_closes_dialog(self):
        dlg = SettingsDialog(dict(DEFAULTS))
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "import.json")
        payload = dict(DEFAULTS)
        payload["api_key"] = "imported-key"
        payload["poll_interval"] = 42
        with open(path, "w") as f:
            json.dump(payload, f)

        from PyQt6.QtWidgets import QFileDialog
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (path, ""))
        QMessageBox.question = staticmethod(always_yes)
        QMessageBox.information = staticmethod(lambda *a, **k: None)

        rejected = []
        dlg.reject = lambda: rejected.append(True)

        real_config_path = tempfile.mkdtemp()
        import config as config_module
        config_module._config_path = lambda: os.path.join(real_config_path, "config.json")

        dlg._import_settings()
        self.assertTrue(rejected, "dialog should close via reject() after import")
        with open(os.path.join(real_config_path, "config.json")) as f:
            written = json.load(f)
        self.assertEqual(written["api_key"], "imported-key")
        self.assertEqual(written["poll_interval"], 42)

    def test_import_rejects_non_dict_json(self):
        dlg = SettingsDialog(dict(DEFAULTS))
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            json.dump([1, 2, 3], f)

        from PyQt6.QtWidgets import QFileDialog
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (path, ""))
        warnings = []
        QMessageBox.warning = staticmethod(lambda *a, **k: warnings.append(a))

        rejected = []
        dlg.reject = lambda: rejected.append(True)

        dlg._import_settings()
        self.assertTrue(warnings)
        self.assertFalse(rejected, "should not close the dialog on a bad import")


if __name__ == "__main__":
    unittest.main()
