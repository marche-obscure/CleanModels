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

    def test_invalid_path_disables_scope_button(self):
        self.app.path_var.set(str(self.tmp / "absent"))
        self.assertEqual(str(self.app.scope_button["state"]), "disabled")
        self.assertEqual(self.app.scope_button["text"], "Périmètre et analyse…")
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

    def test_tabs_grouped_by_category(self):
        self._analyze()
        self.assertEqual(self.app.used_tab.table.groups(), ["checkpoints"])
        self.assertEqual(self.app.unused_tab.table.groups(), ["checkpoints", "vae"])
        self.assertEqual(self.app.junk_tab.table.groups(), ["vae"])
        used = self.app.used_tab.table
        key = used.keys()[0]
        self.assertEqual(used.tree.item(key, "text").strip(), "used.safetensors")
        self.assertEqual(used.tree.set(key, "root"), str(self.comfy / "models" / "checkpoints"))
        self.assertEqual(used.tree.set(key, "calls_n"), "1")
        self.assertEqual(used.tree.set(key, "workflows_n"), "1")

    def test_duplicates_grouped_by_group(self):
        self._analyze()
        tab = self.app.duplicates_tab
        tab._search()
        self._wait_idle()
        self.assertEqual(len(tab.table.groups()), 1)
        self.assertTrue(tab.table.groups()[0].startswith("Groupe 1"))

    def test_category_checkbox_selects_whole_category(self):
        self._analyze()
        tab = self.app.unused_tab
        tab.table.toggle_group("vae")
        self.assertEqual(len(tab.table.checked_keys()), 1)
        self.assertEqual(str(tab.delete_button["state"]), "normal")

    def test_font_is_12_points(self):
        import tkinter.font as tkfont
        self.assertEqual(tkfont.nametofont("TkDefaultFont", root=self.app).cget("size"), 12)

    def test_install_label_text(self):
        self.assertEqual(self.app.path_label["text"], "Dossier d'installation de Votre ComfyUI :")

    def _settings(self):
        return json.loads((self.tmp / "settings.json").read_text(encoding="utf-8"))

    def _open_scope(self):
        from cleanmodels.scope import MODEL_GROUP, WORKFLOW_GROUP

        self.app.path_var.set(str(self.comfy))
        window = self.app.open_scope_window()
        self.app.update()
        return window, MODEL_GROUP, WORKFLOW_GROUP

    def _row_key(self, window, text):
        return next(k for k in window.table.keys() if text in window.table.tree.item(k, "text"))

    def test_scope_window_all_checked_by_default(self):
        self.app.add_workflow_dir(str(self.tmp / "absent"))
        window, model_group, workflow_group = self._open_scope()
        table = window.table
        self.assertEqual(table.groups(), [workflow_group, model_group])
        available = [k for k in table.keys() if table.tree.item(k, "image")]
        self.assertEqual(sorted(table.checked_keys()), sorted(available))
        absent = self._row_key(window, str(self.tmp / "absent"))
        self.assertNotIn(absent, table.checked_keys())
        self.assertIn("introuvable", table.tree.set(absent, "detail"))
        texts = " ".join(table.tree.item(k, "text") for k in table.keys())
        self.assertIn(str(self.comfy / "user" / "default" / "workflows"), texts)
        self.assertIn(str(self.comfy / "models" / "checkpoints"), texts)
        self.assertEqual(str(window.analyze_button["state"]), "normal")

    def test_scope_window_reopens_all_checked(self):
        window, _, _ = self._open_scope()
        window.table.uncheck_all()
        window.close()
        window, _, _ = self._open_scope()
        self.assertEqual(len(window.table.checked_keys()), len(window.table.keys()))

    def test_add_and_remove_workflow_folder_persisted(self):
        extra = self.tmp / "mes_workflows"
        extra.mkdir()
        window, _, _ = self._open_scope()
        self.app.add_workflow_dir(str(extra))
        self.assertEqual(self._settings()["extra_workflow_dirs"], [str(extra)])
        key = self._row_key(window, str(extra))
        self.assertIn(key, window.table.checked_keys())
        self.app.remove_workflow_dirs([str(extra)])
        self.assertEqual(self._settings()["extra_workflow_dirs"], [])
        self.assertFalse(any(str(extra) in window.table.tree.item(k, "text") for k in window.table.keys()))

    def test_remove_button_in_scope_window(self):
        extra = self.tmp / "mes_workflows"
        extra.mkdir()
        self.app.add_workflow_dir(str(extra))
        window, _, _ = self._open_scope()
        window.table.tree.selection_set(self._row_key(window, str(extra)))
        window._remove()
        self.assertEqual(self._settings()["extra_workflow_dirs"], [])

    def test_analyze_disabled_without_model_folder(self):
        window, model_group, _ = self._open_scope()
        window.table.toggle_group(model_group)
        self.assertEqual(str(window.analyze_button["state"]), "disabled")

    def test_unchecked_model_folder_is_excluded(self):
        window, _, _ = self._open_scope()
        window.table.toggle(self._row_key(window, f"[vae] {self.comfy / 'models' / 'vae'}"))
        window.analyze()
        self._wait_idle()
        self.assertEqual(self.app.unused_tab.table.groups(), ["checkpoints"])
        self.assertEqual(self.app.junk_tab.table.keys(), [])
        self.assertFalse(window.winfo_exists())

    def test_unchecked_workflow_folder_still_protects_at_delete_time(self):
        extra = self.tmp / "ailleurs"
        extra.mkdir()
        (extra / "w2.json").write_text(workflow("unused.pt"), encoding="utf-8")
        self.app.add_workflow_dir(str(extra))
        window, _, _ = self._open_scope()
        window.table.toggle(self._row_key(window, str(extra)))
        window.analyze()
        self._wait_idle()
        tab = self.app.unused_tab
        target = self.comfy / "models" / "vae" / "unused.pt"
        self.assertIn(file_key(target), tab.table.keys())
        tab.table.toggle(file_key(target))
        with mock.patch("cleanmodels.gui.app.confirm_deletion", return_value=True) as confirm,                 mock.patch("cleanmodels.gui.app.show_report") as report:
            tab._delete()
            self._wait_idle()
        self.assertTrue(target.exists())
        self.assertEqual(len(report.call_args[0][1].refused), 1)
        notes = " ".join(confirm.call_args[0][3])
        self.assertIn(str(extra), notes)

    def test_extra_folder_workflow_protects_model(self):
        extra = self.tmp / "ailleurs"
        extra.mkdir()
        (extra / "w2.json").write_text(workflow("unused.pt"), encoding="utf-8")
        self.app.path_var.set(str(self.comfy))
        self.app.add_workflow_dir(str(extra))
        self._analyze()
        names = [self.app.unused_tab.table.tree.item(k, "text").strip() for k in self.app.unused_tab.table.keys()]
        self.assertEqual(names, ["copy.safetensors"])

    def test_unused_checker_reads_extra_folder_at_delete_time(self):
        extra = self.tmp / "ailleurs"
        extra.mkdir()
        self.app.path_var.set(str(self.comfy))
        self.app.add_workflow_dir(str(extra))
        self._analyze()
        (extra / "late.json").write_text(workflow("unused.pt"), encoding="utf-8")
        tab = self.app.unused_tab
        target = self.comfy / "models" / "vae" / "unused.pt"
        tab.table.toggle(file_key(target))
        with mock.patch("cleanmodels.gui.app.confirm_deletion", return_value=True), \
                mock.patch("cleanmodels.gui.app.show_report") as report:
            tab._delete()
            self._wait_idle()
        self.assertTrue(target.exists())
        self.assertEqual(len(report.call_args[0][1].refused), 1)

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
