import json
import time
import tkinter as tk
import unittest
from unittest import mock

from cleanmodels.inventory import file_key
from tests.helpers import TempHomeMixin, make_comfy


def workflow(*values):
    return json.dumps({"nodes": [{"id": i, "type": "Loader", "widgets_values": [v]} for i, v in enumerate(values)]})


class AppTest(TempHomeMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from cleanmodels.gui.app import CleanModelsApp

        try:
            self.app = CleanModelsApp()
        except tk.TclError as exc:
            self.skipTest(f"pas d'affichage disponible : {exc}")
        self.app.withdraw()
        self.comfy = make_comfy(self.tmp, {
            "models/checkpoints/used.safetensors": b"aa",
            "models/checkpoints/copy.safetensors": b"aa",
            "models/vae/unused.pt": b"bbb",
            "models/vae/x.part": b"p",
            "user/default/workflows/w.json": workflow("used.safetensors"),
        })

    def tearDown(self):
        self.app.destroy()
        super().tearDown()

    def _wait_idle(self, timeout=10.0):
        deadline = time.monotonic() + timeout
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.02)
        self.app.update()
        self.assertFalse(self.app.busy, "l'opération ne s'est pas terminée")

    def _analyze(self):
        self.app.path_var.set(str(self.comfy))
        self.app._analyze()
        self._wait_idle()

    def test_invalid_path_disables_analyze(self):
        self.app.path_var.set(str(self.tmp / "absent"))
        self.assertEqual(str(self.app.analyze_button["state"]), "disabled")
        self.assertTrue(self.app.validation["text"])

    def test_analysis_fills_tabs_and_saves_path(self):
        self._analyze()
        self.assertEqual(len(self.app.used_tab.table.keys()), 1)
        self.assertEqual(len(self.app.unused_tab.table.keys()), 2)
        self.assertEqual(len(self.app.junk_tab.table.keys()), 1)
        saved = json.loads((self.tmp / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["comfyui_path"], str(self.comfy))

    def test_delete_button_enabled_only_with_selection(self):
        self._analyze()
        tab = self.app.unused_tab
        self.assertEqual(str(tab.delete_button["state"]), "disabled")
        tab.table.toggle(tab.table.keys()[0])
        self.assertEqual(str(tab.delete_button["state"]), "normal")

    def test_unused_delete_after_confirmation(self):
        self._analyze()
        tab = self.app.unused_tab
        target = self.comfy / "models" / "vae" / "unused.pt"
        tab.table.toggle(file_key(target))
        with mock.patch("cleanmodels.gui.app.confirm_deletion", return_value=True), \
                mock.patch("cleanmodels.gui.app.show_report") as report:
            tab._delete()
            self._wait_idle()
        self.assertFalse(target.exists())
        self.assertNotIn(file_key(target), tab.table.keys())
        self.assertEqual(len(report.call_args[0][1].deleted), 1)

    def test_cancelled_confirmation_deletes_nothing(self):
        self._analyze()
        tab = self.app.unused_tab
        tab.table.check_all()
        with mock.patch("cleanmodels.gui.app.confirm_deletion", return_value=False):
            tab._delete()
            self._wait_idle()
        self.assertTrue((self.comfy / "models" / "vae" / "unused.pt").exists())
        self.assertEqual(len(tab.table.keys()), 2)

    def test_duplicates_search_and_full_group_blocked(self):
        self._analyze()
        tab = self.app.duplicates_tab
        tab._search()
        self._wait_idle()
        self.assertEqual(len(tab.table.keys()), 2)
        tab.table.check_all()
        with mock.patch("cleanmodels.gui.tabs.messagebox.showwarning") as warn, \
                mock.patch("cleanmodels.gui.app.confirm_deletion") as confirm:
            tab._delete()
        warn.assert_called_once()
        confirm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
