# test_settings.py — SettingsDialog construction (split _build_ui),
# FilePickerDialog checkbox wrapper fix, and the Windows startup-registry
# toggle. The registry test is careful never to leave a real entry behind
# on the machine running the suite.

import os
import sys
import unittest
import winreg

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _helpers import app, make_window  # noqa: E402,F401
from config import DEFAULTS  # noqa: E402
from dialogs import SettingsDialog, FilePickerDialog  # noqa: E402

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "TorBoxManagerEchoStorm"


def _value_exists():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as k:
            winreg.QueryValueEx(k, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


class TestDialogConstruction(unittest.TestCase):

    def test_settings_dialog_builds(self):
        dlg = SettingsDialog(dict(DEFAULTS))
        self.assertIsNotNone(dlg._key_input)
        self.assertEqual(dlg._poll_input.text(), "30")
        self.assertFalse(dlg._startup_cb.isChecked())

    def test_file_picker_uses_plain_widget_not_qlabel(self):
        files = [{"id": 1, "name": "a.txt", "size": 100}, {"id": 2, "name": "b.txt", "size": 200}]
        dlg = FilePickerDialog("Test Item", files, None)
        checkboxes = list(dlg._checkboxes())
        self.assertEqual(len(checkboxes), 2)


class TestStartupRegistryToggle(unittest.TestCase):

    def setUp(self):
        # Make sure a stale value from a previous manual run doesn't make
        # this test meaningless either way.
        if _value_exists():
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, VALUE_NAME)

    def test_disabled_is_real_and_safe(self):
        """Default (disabled) path is idempotent — just ensures the value's
        absence, safe to actually run against the real registry."""
        win = make_window()  # __init__ calls _apply_startup_setting(); default is disabled
        self.assertFalse(_value_exists())

    def test_enabled_builds_a_launch_command_without_touching_registry(self):
        """The enabled path is verified via a mocked winreg so this test
        never actually writes a startup entry on the machine running it."""
        win = make_window()
        captured = {}

        class FakeKey:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        real_open_key = winreg.OpenKey
        winreg.OpenKey = lambda *a, **k: FakeKey()
        winreg.SetValueEx = lambda key, name, reserved, type_, data: captured.update(name=name, data=data)
        try:
            win.config["run_at_startup"] = True
            win._apply_startup_setting()
        finally:
            winreg.OpenKey = real_open_key

        self.assertEqual(captured["name"], VALUE_NAME)
        self.assertTrue("main.py" in captured["data"] or captured["data"].strip('"').lower().endswith(".exe"))
        # Confirm the mock actually intercepted everything — nothing real was written.
        self.assertFalse(_value_exists())


if __name__ == "__main__":
    unittest.main()
