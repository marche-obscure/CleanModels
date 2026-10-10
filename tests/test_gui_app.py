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
        from cleanmodels.gpu import Gpu
        from cleanmodels.gui.app import CleanModelsApp

        # Cartes simulées : 3 octets (unused.pt fait 3 octets) et 1 octet.
        self.gpus = [Gpu("Carte A", 3), Gpu("Carte B", 1)]
        self._gpu_patch = mock.patch("cleanmodels.gui.app.detect_gpus", return_value=self.gpus)
        self._gpu_patch.start()
        self.addCleanup(self._gpu_patch.stop)
        # Par défaut : raccourci déjà présent (aucune question au lancement pendant les tests).
        self._shortcut_patch = mock.patch("cleanmodels.gui.app.shortcut_exists", return_value=True)
        self._shortcut_patch.start()
        self.addCleanup(self._shortcut_patch.stop)
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
        from cleanmodels import i18n
        from cleanmodels.gui.style import apply_style

        try:
            apply_style(self.app, "light")
            self.app.destroy()
        except tk.TclError:
            pass
        i18n.set_language("fr")
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

    def test_invalid_path_keeps_scope_window_usable(self):
        self.app.path_var.set(str(self.tmp / "absent"))
        self.assertEqual(self.app.scope_button["text"], "Périmètre et analyse…")
        self.assertEqual(str(self.app.scope_button["state"]), "normal")
        self.assertTrue(self.app.validation["text"])
        window = self.app.scope_window
        self.assertIsNotNone(window)
        self.assertEqual(str(window.analyze_button["state"]), "disabled")
        self.assertIn("Indiquez le dossier", window.warning["text"])

    def test_scope_window_opens_at_startup_on_the_right(self):
        from cleanmodels.gui.app import window_layout

        self.assertIsNotNone(self.app.scope_window)
        main, scope = window_layout(1920, 1080)
        main_w, rest = main.split("x")
        main_x = int(rest.split("+")[1])
        scope_w, scope_rest = scope.split("x")
        scope_x = int(scope_rest.split("+")[1])
        self.assertEqual(main_x, 0)
        self.assertGreaterEqual(scope_x, int(main_w))
        self.assertLessEqual(scope_x + int(scope_w), 1920)
        self.assertGreater(int(scope_w), 500)

    def test_button_styles(self):
        self.assertEqual(str(self.app.scope_window.analyze_button["style"]), "Accent.TButton")
        for tab in (self.app.unused_tab, self.app.duplicates_tab, self.app.junk_tab):
            self.assertEqual(str(tab.delete_button["style"]), "Danger.TButton")

    def test_switch_language_rebuilds_and_keeps_results(self):
        self._analyze()
        self.app.set_language("en")
        self.assertEqual(self.app.path_label["text"], "Your ComfyUI installation folder:")
        self.assertEqual(self.app.notebook.tab(1, "text"), "Unused")
        self.assertEqual(len(self.app.unused_tab.table.keys()), 2)
        self.assertEqual(self.app.unused_tab.table.checked_keys(), [])
        self.assertEqual(self.app.scope_window.title(), "Check scope")
        self.assertEqual(self.app.path_var.get(), str(self.comfy))
        self.assertEqual(self._settings()["language"], "en")
        self.app.set_language("de")
        self.assertEqual(self.app.scope_window.analyze_button["text"], "Analysieren")

    def test_switch_theme_rebuilds_and_keeps_results(self):
        from tkinter import ttk

        from cleanmodels.gui.style import DARK

        self._analyze()
        self.app.set_theme("dark")
        self.assertEqual(ttk.Style(self.app).lookup("Treeview", "fieldbackground"), DARK["field"])
        self.assertEqual(len(self.app.unused_tab.table.keys()), 2)
        self.assertEqual(self._settings()["theme"], "dark")

    def test_language_and_theme_restored_at_startup(self):
        from cleanmodels.gui.app import CleanModelsApp
        from cleanmodels.settings import load_settings, save_settings

        data, _ = load_settings()
        data["language"], data["theme"] = "de", "dark"
        save_settings(data)
        self.app.destroy()
        self.app = CleanModelsApp()
        self.app.withdraw()
        self.assertEqual(self.app.path_label["text"], "Installationsordner Ihres ComfyUI:")
        self.assertEqual(self.app.theme_var.get(), "Dunkel")

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

    def _vram_marks(self, tab):
        table = tab.table
        return {table.tree.item(k, "text").strip(): table.tree.set(k, "vram") for k in table.keys()}

    def test_largest_gpu_selected_by_default(self):
        self.assertEqual(self.app.vram(), 3)
        self.assertIn("Carte A", self.app.gpu_var.get())

    def test_files_at_or_above_vram_are_marked(self):
        self._analyze()
        self.assertEqual(self._vram_marks(self.app.unused_tab),
                         {"copy.safetensors": "", "unused.pt": "⚠"})
        self.assertEqual(self._vram_marks(self.app.used_tab), {"used.safetensors": ""})
        self.assertIn("1 ≥ VRAM", self.app.unused_tab.table.group_label("vae"))

    def test_changing_gpu_updates_marks_and_is_saved(self):
        self._analyze()
        self.app.select_gpu("Carte B")
        self.assertEqual(self.app.vram(), 1)
        self.assertEqual(set(self._vram_marks(self.app.unused_tab).values()), {"⚠"})
        self.assertEqual(self._settings()["gpu"], "Carte B")

    def test_manual_vram(self):
        self._analyze()
        self.app.set_manual_vram(2)
        self.assertEqual(self.app.vram(), 2)
        self.assertEqual(self._vram_marks(self.app.unused_tab),
                         {"copy.safetensors": "⚠", "unused.pt": "⚠"})
        self.assertEqual(self._settings()["vram_manual"], 2)
        self.assertEqual(self._settings()["gpu"], "__manual__")

    def test_duplicates_marked_too(self):
        self.app.select_gpu("Carte B")
        self._analyze()
        tab = self.app.duplicates_tab
        tab._search()
        self._wait_idle()
        self.assertEqual(set(self._vram_marks(tab).values()), {"⚠"})

    def test_no_gpu_detected(self):
        from cleanmodels.gui.app import CleanModelsApp

        self.app.destroy()
        with mock.patch("cleanmodels.gui.app.detect_gpus", return_value=[]):
            self.app = CleanModelsApp()
        self.app.withdraw()
        self.assertIsNone(self.app.vram())
        self.assertIn("Aucune carte", self.app.gpu_var.get())
        self._analyze()
        self.assertEqual(set(self._vram_marks(self.app.unused_tab).values()), {""})

    def test_rebuild_leaves_nothing_freed_from_worker_thread(self):
        import gc
        import sys
        import threading

        errors = []
        previous_hook = sys.unraisablehook
        sys.unraisablehook = lambda info: errors.append(info.exc_value)
        try:
            self.app.set_theme("dark")
            self.app.set_language("en")
            worker = threading.Thread(target=gc.collect)
            worker.start()
            worker.join(10)
        finally:
            sys.unraisablehook = previous_hook
        self.assertEqual([e for e in errors if isinstance(e, RuntimeError)], [])

    def _restart(self, asked: bool, present: bool, choice: bool = False, create=None):
        """Relance l'application avec un état de raccourci donné ; renvoie les simulacres."""
        from cleanmodels.gui.app import CleanModelsApp
        from cleanmodels.settings import load_settings, save_settings

        data, _ = load_settings()
        data["desktop_shortcut_asked"] = asked
        save_settings(data)
        self.app.destroy()
        ask = mock.patch("cleanmodels.gui.app.ask_choice", return_value=choice).start()
        created = mock.patch("cleanmodels.gui.app.create_shortcut",
                             side_effect=create or (lambda: self.tmp / "CleanModels.lnk")).start()
        info = mock.patch("cleanmodels.gui.app.messagebox.showinfo").start()
        error = mock.patch("cleanmodels.gui.app.messagebox.showerror").start()
        self.addCleanup(mock.patch.stopall)
        with mock.patch("cleanmodels.gui.app.shortcut_exists", return_value=present):
            self.app = CleanModelsApp()
            self.app.withdraw()
            self.app.update()
        return ask, created, info, error

    def test_logo_shown_in_main_window(self):
        self.assertTrue(str(self.app.logo_label["image"]))

    def test_shortcut_button_disabled_when_shortcut_exists(self):
        self.assertEqual(str(self.app.shortcut_button["state"]), "disabled")

    def test_first_launch_offers_shortcut_once_and_creates_it(self):
        ask, created, info, _ = self._restart(asked=False, present=False, choice=True)
        ask.assert_called_once()
        created.assert_called_once()
        info.assert_called_once()
        self.assertTrue(self._settings()["desktop_shortcut_asked"])
        self.assertEqual(str(self.app.shortcut_button["state"]), "disabled")

    def test_offer_declined_is_not_asked_again(self):
        ask, created, _, _ = self._restart(asked=False, present=False, choice=False)
        ask.assert_called_once()
        created.assert_not_called()
        self.assertTrue(self._settings()["desktop_shortcut_asked"])
        self.assertEqual(str(self.app.shortcut_button["state"]), "normal")
        ask, _, _, _ = self._restart(asked=True, present=False)
        ask.assert_not_called()

    def test_no_offer_when_shortcut_already_exists(self):
        ask, _, _, _ = self._restart(asked=False, present=True)
        ask.assert_not_called()

    def test_shortcut_button_creates_later_and_reports_errors(self):
        def fail():
            raise OSError("Accès refusé")

        _, created, _, error = self._restart(asked=True, present=False, create=fail)
        self.assertEqual(str(self.app.shortcut_button["state"]), "normal")
        self.app.shortcut_button.invoke()
        created.assert_called_once()
        error.assert_called_once()
        self.assertEqual(str(self.app.shortcut_button["state"]), "normal")

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
        self.assertTrue(window.winfo_exists())
        self.assertIs(self.app.scope_window, window)

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
