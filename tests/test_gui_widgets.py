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
            self.root,
            [("name", "Nom", 200), ("size_n", "Taille", 80)],
            on_selection_change=lambda: self.changes.append(1),
        )
        self.tree.set_rows([
            ("a", ("a.pt", "1 o"), 1),
            ("b", ("b.pt", "2 o"), 2),
            ("c", ("c.pt", "4 o"), 4),
        ])

    def tearDown(self):
        self.tree.destroy()

    def test_toggle(self):
        self.tree.toggle("b")
        self.assertEqual(self.tree.checked_keys(), ["b"])
        self.assertEqual(self.tree.checked_size(), 2)
        self.assertTrue(self.changes)

    def test_check_all_and_uncheck_all(self):
        self.tree.check_all()
        self.assertEqual(self.tree.checked_keys(), ["a", "b", "c"])
        self.assertEqual(self.tree.checked_size(), 7)
        self.tree.uncheck_all()
        self.assertEqual(self.tree.checked_keys(), [])

    def test_set_rows_clears_checks(self):
        self.tree.toggle("a")
        self.tree.set_rows([("a", ("a.pt", "1 o"), 1)])
        self.assertEqual(self.tree.checked_keys(), [])

    def test_remove_keys(self):
        self.tree.toggle("a")
        self.tree.remove_keys(["a", "c"])
        self.assertEqual(self.tree.keys(), ["b"])
        self.assertEqual(self.tree.checked_keys(), [])

    def test_sort_by_size_ascending_then_descending(self):
        self.tree.sort_by("size_n")
        self.assertEqual(self.tree.keys(), ["a", "b", "c"])
        self.tree.sort_by("size_n")
        self.assertEqual(self.tree.keys(), ["c", "b", "a"])


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
