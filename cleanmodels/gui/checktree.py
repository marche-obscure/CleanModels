"""Tableaux triables, avec ou sans cases à cocher, basés sur ttk.Treeview.

Les colonnes sont décrites par (id, titre, largeur). Un id finissant par « _n » est trié
numériquement ; la colonne « size_n » est triée sur la taille en octets de la ligne.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

UNCHECKED = "☐"
CHECKED = "☑"


class SortableTree(ttk.Frame):
    def __init__(self, master, columns: list, leading: tuple = ()):
        super().__init__(master)
        self._columns = list(leading) + list(columns)
        ids = [c[0] for c in self._columns]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", selectmode="extended")
        for col_id, title, width in self._columns:
            numeric = col_id.endswith("_n")
            self.tree.column(col_id, width=width, anchor="e" if numeric else "w", stretch=not numeric)
            if col_id != "check":
                self.tree.heading(col_id, text=title, command=lambda c=col_id: self.sort_by(c))
            else:
                self.tree.heading(col_id, text=title)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._sizes: dict = {}
        self._sort_state: tuple = (None, False)

    def _row_values(self, key: str, values: tuple) -> tuple:
        return tuple(values)

    def set_rows(self, rows: list) -> None:
        """rows : liste de (clé, valeurs affichées, taille en octets)."""
        self.tree.delete(*self.tree.get_children())
        self._sizes = {}
        for key, values, size in rows:
            self._sizes[key] = size
            self.tree.insert("", "end", iid=key, values=self._row_values(key, values))
        self._sort_state = (None, False)

    def keys(self) -> list:
        return list(self.tree.get_children())

    def remove_keys(self, keys: list) -> None:
        for key in keys:
            if self.tree.exists(key):
                self.tree.delete(key)
            self._sizes.pop(key, None)

    def _sort_key(self, column: str, key: str):
        if column == "size_n":
            return self._sizes.get(key, 0)
        value = self.tree.set(key, column)
        if column.endswith("_n"):
            try:
                return float(str(value).replace(",", "."))
            except ValueError:
                return 0.0
        return str(value).casefold()

    def sort_by(self, column: str) -> None:
        last, reverse = self._sort_state
        reverse = not reverse if last == column else False
        ordered = sorted(self.keys(), key=lambda k: self._sort_key(column, k), reverse=reverse)
        for index, key in enumerate(ordered):
            self.tree.move(key, "", index)
        self._sort_state = (column, reverse)

    def bind_double_click(self, callback: Callable[[str], None]) -> None:
        def handler(event):
            key = self.tree.identify_row(event.y)
            if key:
                callback(key)

        self.tree.bind("<Double-1>", handler)


class CheckTree(SortableTree):
    def __init__(self, master, columns: list, on_selection_change: Callable[[], None]):
        super().__init__(master, columns, leading=(("check", UNCHECKED, 30),))
        self.tree.column("check", anchor="center", stretch=False)
        self._checked: set = set()
        self._on_change = on_selection_change
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<space>", self._on_space)

    def _row_values(self, key: str, values: tuple) -> tuple:
        return (UNCHECKED,) + tuple(values)

    def _set_checked(self, key: str, checked: bool) -> None:
        if checked:
            self._checked.add(key)
        else:
            self._checked.discard(key)
        self.tree.set(key, "check", CHECKED if checked else UNCHECKED)

    def _on_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#1":
            key = self.tree.identify_row(event.y)
            if key:
                self.toggle(key)
                return "break"
        return None

    def _on_space(self, _event):
        selection = self.tree.selection()
        if selection:
            target = not all(k in self._checked for k in selection)
            for key in selection:
                self._set_checked(key, target)
            self._on_change()
        return "break"

    def set_rows(self, rows: list) -> None:
        self._checked = set()
        super().set_rows(rows)
        self._on_change()

    def remove_keys(self, keys: list) -> None:
        self._checked.difference_update(keys)
        super().remove_keys(keys)
        self._on_change()

    def toggle(self, key: str) -> None:
        self._set_checked(key, key not in self._checked)
        self._on_change()

    def check_all(self) -> None:
        for key in self.keys():
            self._set_checked(key, True)
        self._on_change()

    def uncheck_all(self) -> None:
        for key in self.keys():
            self._set_checked(key, False)
        self._on_change()

    def checked_keys(self) -> list:
        return [k for k in self.keys() if k in self._checked]

    def checked_size(self) -> int:
        return sum(self._sizes.get(k, 0) for k in self.checked_keys())
