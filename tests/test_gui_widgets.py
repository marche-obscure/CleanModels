import tkinter as tk
import unittest

from cleanmodels.gui.format import format_size


class FormatSizeTest(unittest.TestCase):
    def test_values(self):
        self.assertEqual(format_size(0), "0 o")
        self.assertEqual(format_size(1536), "1,5 Ko")
        self.assertEqual(format_size(5 * 1024 ** 3), "5,0 Go")


class CheckTreeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"pas d'affichage disponible : {exc}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        from cleanmodels.gui.checktree import CheckTree

        self.changes = []
        self.tree = CheckTree(
            self.root, "Nom", [("size_n", "Taille", 80)],
            on_selection_change=lambda: self.changes.append(1),
        )
        # (clé, groupe, nom, valeurs des colonnes, taille)
        self.tree.set_rows([
            ("a", "checkpoints", "a.pt", ("1 o",), 1),
            ("b", "checkpoints", "b.pt", ("2 o",), 2),
            ("c", "vae", "c.pt", ("4 o",), 4),
        ])

    def tearDown(self):
        self.tree.destroy()

    def test_rows_grouped_under_category(self):
        self.assertEqual(self.tree.groups(), ["checkpoints", "vae"])
        self.assertEqual(self.tree.keys(), ["a", "b", "c"])
        self.assertEqual(self.tree.group_of("c"), "vae")
        self.assertIn("2 fichiers – 3 o", self.tree.group_label("checkpoints"))
        self.assertIn("1 fichier – 4 o", self.tree.group_label("vae"))

    def test_toggle(self):
        self.tree.toggle("b")
        self.assertEqual(self.tree.checked_keys(), ["b"])
        self.assertEqual(self.tree.checked_size(), 2)
        self.assertTrue(self.changes)

    def test_group_toggle_checks_children_only(self):
        self.tree.toggle_group("checkpoints")
        self.assertEqual(self.tree.checked_keys(), ["a", "b"])
        self.assertEqual(self.tree.group_state("checkpoints"), "checked")
        self.assertEqual(self.tree.group_state("vae"), "unchecked")
        self.tree.toggle_group("checkpoints")
        self.assertEqual(self.tree.checked_keys(), [])

    def test_partial_group_state(self):
        self.tree.toggle("a")
        self.assertEqual(self.tree.group_state("checkpoints"), "partial")
        self.tree.toggle_group("checkpoints")
        self.assertEqual(self.tree.checked_keys(), ["a", "b"])

    def test_check_all_and_uncheck_all(self):
        self.tree.check_all()
        self.assertEqual(self.tree.checked_keys(), ["a", "b", "c"])
        self.assertEqual(self.tree.checked_size(), 7)
        self.tree.uncheck_all()
        self.assertEqual(self.tree.checked_keys(), [])

    def test_set_rows_clears_checks(self):
        self.tree.toggle("a")
        self.tree.set_rows([("a", "checkpoints", "a.pt", ("1 o",), 1)])
        self.assertEqual(self.tree.checked_keys(), [])

    def test_remove_keys_updates_and_drops_empty_groups(self):
        self.tree.toggle("a")
        self.tree.remove_keys(["a", "c"])
        self.assertEqual(self.tree.keys(), ["b"])
        self.assertEqual(self.tree.groups(), ["checkpoints"])
        self.assertIn("1 fichier – 2 o", self.tree.group_label("checkpoints"))
        self.assertEqual(self.tree.checked_keys(), [])

    def test_sort_within_groups(self):
        self.tree.sort_by("size_n", descending=True)
        self.assertEqual(self.tree.keys(), ["b", "a", "c"])
        self.assertEqual(self.tree.groups(), ["checkpoints", "vae"])
        self.tree.sort_by("#0")
        self.assertEqual(self.tree.keys(), ["a", "b", "c"])

    def test_disabled_rows_cannot_be_checked(self):
        self.tree.set_rows([
            ("a", "g", "a", ("1 o",), 1),
            ("b", "g", "b", ("2 o",), 2),
        ], disabled={"b"})
        self.tree.toggle("b")
        self.assertEqual(self.tree.checked_keys(), [])
        self.tree.check_all()
        self.assertEqual(self.tree.checked_keys(), ["a"])
        self.assertEqual(self.tree.group_state("g"), "checked")
        self.assertEqual(self.tree.tree.item("b", "image"), "")
        self.tree.toggle_group("g")
        self.assertEqual(self.tree.checked_keys(), [])

    def test_checkbox_images_are_large(self):
        self.assertGreaterEqual(self.tree.checkbox_size(), 18)


class CheckboxImageLifetimeTest(unittest.TestCase):
    def test_discarded_tree_images_never_freed_from_worker_thread(self):
        import gc
        import sys
        import threading

        from cleanmodels.gui.checktree import CheckTree

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"pas d'affichage disponible : {exc}")
        root.withdraw()
        errors = []
        previous_hook = sys.unraisablehook
        sys.unraisablehook = lambda info: errors.append(info.exc_value)
        try:
            tree = CheckTree(root, "Nom", [], on_selection_change=lambda: None)
            tree.destroy()
            del tree
            worker = threading.Thread(target=gc.collect)
            worker.start()
            worker.join(10)
        finally:
            sys.unraisablehook = previous_hook
            root.destroy()
        self.assertEqual([e for e in errors if isinstance(e, RuntimeError)], [])


class MarkedRowsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"pas d'affichage disponible : {exc}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_set_marked(self):
        from cleanmodels.gui.checktree import SortableTree

        tree = SortableTree(self.root, "Nom", [("size_n", "Taille", 80), ("vram", "≥ VRAM", 60)])
        tree.set_rows([
            ("a", "checkpoints", "a.pt", ("1 o", ""), 1),
            ("b", "checkpoints", "b.pt", ("2 o", ""), 2),
        ])
        tree.set_marked({"a"})
        self.assertEqual(tree.tree.set("a", "vram"), "⚠")
        self.assertEqual(tree.tree.set("b", "vram"), "")
        self.assertIn("over_vram", tree.tree.item("a", "tags"))
        self.assertNotIn("over_vram", tree.tree.item("b", "tags"))
        self.assertIn("1 ≥ VRAM", tree.group_label("checkpoints"))
        tree.remove_keys(["b"])
        self.assertIn("1 ≥ VRAM", tree.group_label("checkpoints"))
        tree.set_marked(set())
        self.assertEqual(tree.tree.set("a", "vram"), "")
        self.assertNotIn("VRAM", tree.group_label("checkpoints"))
        tree.destroy()


class StyleTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"pas d'affichage disponible : {exc}")
        self.root.withdraw()

    def tearDown(self):
        from cleanmodels.gui.style import apply_style

        apply_style(self.root, "light")
        self.root.destroy()

    def test_fonts_are_12_points_and_rows_fit(self):
        import tkinter.font as tkfont
        from tkinter import ttk

        from cleanmodels.gui.style import apply_style

        apply_style(self.root, "light")
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkFixedFont"):
            self.assertEqual(tkfont.nametofont(name, root=self.root).cget("size"), 12)
        linespace = tkfont.nametofont("TkDefaultFont", root=self.root).metrics("linespace")
        self.assertGreater(int(ttk.Style(self.root).lookup("Treeview", "rowheight")), linespace)

    def test_dark_and_light_palettes(self):
        from tkinter import ttk

        from cleanmodels.gui.style import DARK, LIGHT, apply_style, palette

        style = ttk.Style(self.root)
        apply_style(self.root, "dark")
        self.assertEqual(palette(), DARK)
        self.assertEqual(style.lookup("Treeview", "fieldbackground"), DARK["field"])
        self.assertEqual(str(self.root.cget("background")), DARK["bg"])
        apply_style(self.root, "light")
        self.assertEqual(palette(), LIGHT)
        self.assertEqual(style.lookup("Treeview", "fieldbackground"), LIGHT["field"])

    def test_accent_and_danger_buttons(self):
        from tkinter import ttk

        from cleanmodels.gui.style import LIGHT, apply_style

        apply_style(self.root, "light")
        style = ttk.Style(self.root)
        self.assertEqual(style.lookup("Accent.TButton", "background"), LIGHT["accent"])
        self.assertEqual(style.lookup("Danger.TButton", "background", ["!disabled"]), LIGHT["danger"])
        self.assertEqual(style.lookup("Danger.TButton", "background", ["disabled"]), LIGHT["disabled_bg"])
        self.assertEqual(style.lookup("Danger.TButton", "foreground", ["!disabled"]), "#ffffff")


class ConfirmDeletionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"pas d'affichage disponible : {exc}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def _run(self, button_text):
        from cleanmodels.gui import dialogs

        seen = {}

        def press():
            window = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            widgets, texts = list(window.winfo_children()), []
            while widgets:
                w = widgets.pop()
                widgets.extend(w.winfo_children())
                try:
                    texts.append(w.cget("text"))
                except tk.TclError:
                    continue
                if w.cget("text") == button_text:
                    target = w
            seen["texts"] = texts
            target.invoke()

        self.root.after(100, press)
        answer = dialogs.confirm_deletion(self.root, ["C:/m/a.pt"], 1536, ["note rouge"])
        return answer, seen["texts"]

    def test_cancel_returns_false_and_shows_warning(self):
        answer, texts = self._run("Annuler")
        self.assertFalse(answer)
        self.assertIn("Cette suppression est définitive et ne peut pas être annulée.", texts)
        self.assertIn("note rouge", texts)
        self.assertIn("1 fichier – 1,5 Ko", texts)

    def test_confirm_returns_true(self):
        answer, _ = self._run("Supprimer définitivement")
        self.assertTrue(answer)


if __name__ == "__main__":
    unittest.main()
