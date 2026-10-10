import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from cleanmodels import shortcut
from tests.helpers import TempHomeMixin


class ShortcutTest(TempHomeMixin, unittest.TestCase):
    def test_paths(self):
        self.assertEqual(shortcut.shortcut_path(self.tmp), self.tmp / "CleanModels.lnk")
        self.assertFalse(shortcut.exists(self.tmp))
        (self.tmp / "CleanModels.lnk").write_bytes(b"x")
        self.assertTrue(shortcut.exists(self.tmp))

    def test_create_passes_paths_through_environment(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs["env"]))
            Path(kwargs["env"]["CM_LNK"]).write_bytes(b"lnk")
            return subprocess.CompletedProcess(args, 0, "", "")

        with mock.patch("cleanmodels.shortcut.subprocess.run", side_effect=fake_run):
            path = shortcut.create(self.tmp)
        self.assertEqual(path, self.tmp / "CleanModels.lnk")
        args, env = calls[0]
        self.assertEqual(args[0], "powershell")
        self.assertEqual(env["CM_ARGS"], "-m cleanmodels")
        self.assertEqual(Path(env["CM_WORKDIR"]), shortcut.PROJECT_DIR)
        self.assertTrue(env["CM_TARGET"].lower().endswith(("pythonw.exe", "python.exe")))
        self.assertEqual(Path(env["CM_ICON"]), shortcut.ICON_PATH)

    def test_failure_raises_oserror(self):
        failed = subprocess.CompletedProcess([], 1, "", "Accès refusé")
        with mock.patch("cleanmodels.shortcut.subprocess.run", return_value=failed):
            with self.assertRaises(OSError) as ctx:
                shortcut.create(self.tmp)
        self.assertIn("Accès refusé", str(ctx.exception))

    def test_missing_desktop_raises(self):
        with self.assertRaises(OSError):
            shortcut.create(self.tmp / "absent")

    def test_icon_file_exists(self):
        self.assertTrue(shortcut.ICON_PATH.is_file())

    @unittest.skipUnless(sys.platform == "win32" and shutil.which("powershell"), "Windows uniquement")
    def test_real_shortcut_in_temp_folder(self):
        path = shortcut.create(self.tmp)
        self.assertTrue(path.is_file())
        script = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:CM_LNK); "
                  "$s.TargetPath; $s.Arguments; $s.WorkingDirectory; $s.IconLocation")
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             env={**os.environ, "CM_LNK": str(path)}, capture_output=True, text=True)
        target, arguments, workdir, icon = out.stdout.strip().splitlines()
        self.assertTrue(target.lower().endswith("pythonw.exe"))
        self.assertEqual(arguments, "-m cleanmodels")
        self.assertEqual(Path(workdir), shortcut.PROJECT_DIR)
        self.assertTrue(icon.lower().startswith(str(shortcut.ICON_PATH).lower()))


if __name__ == "__main__":
    unittest.main()
