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


class StyleTest(unittest.TestCase):
    def test_fonts_are_12_points_and_rows_fit(self):
        import tkinter.font as tkfont
        from tkinter import ttk

        from cleanmodels.gui.style import apply_style

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"pas d'affichage disponible : {exc}")
        try:
            root.withdraw()
            apply_style(root)
            for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkFixedFont"):
                self.assertEqual(tkfont.nametofont(name, root=root).cget("size"), 12)
            linespace = tkfont.nametofont("TkDefaultFont", root=root).metrics("linespace")
            self.assertGreater(int(ttk.Style(root).lookup("Treeview", "rowheight")), linespace)
        finally:
            root.destroy()


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
