# test_shortcuts.py — Delete / Ctrl+A / F5 keyboard shortcuts, scoped to the
# Queue tab (must no-op on the History tab).

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QMessageBox  # noqa: E402

from _helpers import make_window, make_torrent_item, always_yes  # noqa: E402


class TestShortcuts(unittest.TestCase):

    def setUp(self):
        self.win = make_window()
        QMessageBox.question = staticmethod(always_yes)

    def test_select_all_selects_every_queue_row(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)
        self.win._tabs.setCurrentIndex(0)
        self.win._on_select_all_shortcut()
        selected = {idx.row() for idx in self.win._table.selectionModel().selectedRows()}
        self.assertEqual(selected, {0, 1})

    def test_delete_shortcut_bulk_deletes_selection(self):
        items = [make_torrent_item(1, "One"), make_torrent_item(2, "Two")]
        self.win._update_queue_table(items)
        self.win._tabs.setCurrentIndex(0)
        self.win._on_select_all_shortcut()
        self.win._on_delete_shortcut()
        self.assertEqual(self.win._table.rowCount(), 0)

    def test_shortcuts_noop_on_history_tab(self):
        items = [make_torrent_item(3, "Three"), make_torrent_item(4, "Four")]
        self.win._update_queue_table(items)
        self.win._tabs.setCurrentIndex(1)
        self.win._on_select_all_shortcut()
        selected = {idx.row() for idx in self.win._table.selectionModel().selectedRows()}
        self.assertEqual(selected, set())
        self.win._on_delete_shortcut()
        self.assertEqual(self.win._table.rowCount(), 2)


if __name__ == "__main__":
    unittest.main()
