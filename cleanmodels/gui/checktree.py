"""Tableaux hiérarchiques triables (groupe → fichiers), avec ou sans cases à cocher.

La colonne d'arbre (#0) affiche le groupe puis le nom du fichier ; les autres colonnes sont
décrites par (id, titre, largeur). Un id finissant par « _n » est trié numériquement ;
« size_n » est trié sur la taille en octets. Le tri s'applique à l'intérieur de chaque groupe ;
les groupes gardent l'ordre de leur première apparition.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .format import format_size

GROUP_PREFIX = "group::"
CHECKBOX_SIZE = 18

UNCHECKED, CHECKED, PARTIAL = "unchecked", "checked", "partial"


def _checkbox_image(master, state: str, size: int = CHECKBOX_SIZE) -> tk.PhotoImage:
    """Case à cocher dessinée pixel par pixel (indépendante de la police)."""
    image = tk.PhotoImage(master=master, width=size, height=size)
    border, fill, mark = "#5f6368", "#ffffff", "#ffffff"
    if state == CHECKED:
        border = fill = "#1a73e8"
    image.put(fill, to=(0, 0, size, size))
    for x in range(size):  # bordure de 2 pixels
        for y in (0, 1, size - 2, size - 1):
            image.put(border, (x, y))
            image.put(border, (y, x))
    if state == CHECKED:
        # Coche : segment descendant puis montant, épaisseur 2 pixels.
        points = [(4 + i, 9 + i) for i in range(4)] + [(7 + i, 12 - i) for i in range(7)]
        for x, y in points:
            for dx, dy in ((0, 0), (0, 1), (1, 0)):
                image.put(mark, (x + dx, y + dy))
    elif state == PARTIAL:
        image.put("#1a73e8", to=(5, 5, size - 5, size - 5))
    return image


class SortableTree(ttk.Frame):
    def __init__(self, master, tree_title: str, columns: list):
        super().__init__(master)
        self._columns = list(columns)
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns], show="tree headings",
                                 selectmode="extended")
        self.tree.heading("#0", text=tree_title, command=lambda: self.sort_by("#0"))
        self.tree.column("#0", width=320, stretch=True)
        for col_id, title, width in self._columns:
            numeric = col_id.endswith("_n")
            self.tree.column(col_id, width=width, anchor="e" if numeric else "w", stretch=not numeric)
            self.tree.heading(col_id, text=title, command=lambda c=col_id: self.sort_by(c))
        self.tree.tag_configure("group", font="TkHeadingFont")
        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._sizes: dict = {}
        self._names: dict = {}
        self._group_of: dict = {}
        self._sort_state: tuple = (None, False)

    # ----- construction ---------------------------------------------------

    @staticmethod
    def _group_iid(group: str) -> str:
        return GROUP_PREFIX + group

    def _leaf_image(self, key: str):
        return ""

    def _group_image(self, group: str):
        return ""

    def set_rows(self, rows: list) -> None:
        """rows : liste de (clé, groupe, nom, valeurs des colonnes, taille en octets)."""
        self.tree.delete(*self.tree.get_children())
        self._sizes, self._names, self._group_of = {}, {}, {}
        for key, group, name, values, size in rows:
            parent = self._group_iid(group)
            if not self.tree.exists(parent):
                self.tree.insert("", "end", iid=parent, open=True, tags=("group",))
            self._sizes[key], self._names[key], self._group_of[key] = size, name, group
            self.tree.insert(parent, "end", iid=key, text=f" {name}", values=tuple(values),
                             image=self._leaf_image(key))
        for group in self.groups():
            self._refresh_group(group)
        self._sort_state = (None, False)

    def _refresh_group(self, group: str) -> None:
        children = self.tree.get_children(self._group_iid(group))
        total = sum(self._sizes.get(k, 0) for k in children)
        count = len(children)
        label = f" {group}   ({count} fichier{'s' if count > 1 else ''} – {format_size(total)})"
        self.tree.item(self._group_iid(group), text=label, image=self._group_image(group))

    # ----- lecture --------------------------------------------------------

    def groups(self) -> list:
        return [iid[len(GROUP_PREFIX):] for iid in self.tree.get_children("")]

    def group_label(self, group: str) -> str:
        return self.tree.item(self._group_iid(group), "text")

    def group_of(self, key: str) -> str:
        return self._group_of[key]

    def keys(self) -> list:
        return [k for iid in self.tree.get_children("") for k in self.tree.get_children(iid)]

    def is_group(self, iid: str) -> bool:
        return iid.startswith(GROUP_PREFIX)

    # ----- modification ---------------------------------------------------

    def remove_keys(self, keys: list) -> None:
        touched = set()
        for key in keys:
            if self.tree.exists(key) and not self.is_group(key):
                touched.add(self._group_of[key])
                self.tree.delete(key)
            self._sizes.pop(key, None)
            self._names.pop(key, None)
            self._group_of.pop(key, None)
        for group in touched:
            if self.tree.get_children(self._group_iid(group)):
                self._refresh_group(group)
            else:
                self.tree.delete(self._group_iid(group))

    def _sort_key(self, column: str, key: str):
        if column == "#0":
            return self._names.get(key, "").casefold()
        if column == "size_n":
            return self._sizes.get(key, 0)
        value = self.tree.set(key, column)
        if column.endswith("_n"):
            try:
                return float(str(value).replace(",", "."))
            except ValueError:
                return 0.0
        return str(value).casefold()

    def sort_by(self, column: str, descending: bool | None = None) -> None:
        """Trie dans chaque groupe ; sans « descending », alterne croissant / décroissant."""
        last, reverse = self._sort_state
        if descending is None:
            reverse = not reverse if last == column else False
        else:
            reverse = descending
        for parent in self.tree.get_children(""):
            children = sorted(self.tree.get_children(parent), key=lambda k: self._sort_key(column, k),
                              reverse=reverse)
            for index, key in enumerate(children):
                self.tree.move(key, parent, index)
        self._sort_state = (column, reverse)

    def bind_double_click(self, callback: Callable[[str], None]) -> None:
        def handler(event):
            key = self.tree.identify_row(event.y)
            if key and not self.is_group(key):
                callback(key)

        self.tree.bind("<Double-1>", handler)


class CheckTree(SortableTree):
    def __init__(self, master, tree_title: str, columns: list, on_selection_change: Callable[[], None]):
        self._checked: set = set()
        super().__init__(master, tree_title, columns)
        self._images = {state: _checkbox_image(self, state) for state in (UNCHECKED, CHECKED, PARTIAL)}
        self._on_change = on_selection_change
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<space>", self._on_space)

    def checkbox_size(self) -> int:
        return self._images[UNCHECKED].width()

    def _leaf_image(self, key: str):
        return self._images[CHECKED if key in self._checked else UNCHECKED]

    def _group_image(self, group: str):
        return self._images[self.group_state(group)]

    def group_state(self, group: str) -> str:
        children = self.tree.get_children(self._group_iid(group))
        checked = sum(1 for k in children if k in self._checked)
        if checked == 0:
            return UNCHECKED
        return CHECKED if checked == len(children) else PARTIAL

    def _set_checked(self, key: str, checked: bool) -> None:
        if checked:
            self._checked.add(key)
        else:
            self._checked.discard(key)
        self.tree.item(key, image=self._leaf_image(key))

    def _changed(self, groups) -> None:
        for group in set(groups):
            self._refresh_group(group)
        self._on_change()

    def _on_click(self, event):
        if self.tree.identify_element(event.x, event.y) != "image":
            return None
        iid = self.tree.identify_row(event.y)
        if not iid:
            return None
        if self.is_group(iid):
            self.toggle_group(iid[len(GROUP_PREFIX):])
        else:
            self.toggle(iid)
        return "break"

    def _on_space(self, _event):
        leaves = []
        for iid in self.tree.selection():
            leaves.extend(self.tree.get_children(iid) if self.is_group(iid) else [iid])
        if leaves:
            target = not all(k in self._checked for k in leaves)
            for key in leaves:
                self._set_checked(key, target)
            self._changed(self._group_of[k] for k in leaves)
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
        self._changed([self._group_of[key]])

    def toggle_group(self, group: str) -> None:
        children = self.tree.get_children(self._group_iid(group))
        target = self.group_state(group) != CHECKED
        for key in children:
            self._set_checked(key, target)
        self._changed([group])

    def check_all(self) -> None:
        for key in self.keys():
            self._set_checked(key, True)
        self._changed(self.groups())

    def uncheck_all(self) -> None:
        for key in self.keys():
            self._set_checked(key, False)
        self._changed(self.groups())

    def checked_keys(self) -> list:
        return [k for k in self.keys() if k in self._checked]

    def checked_size(self) -> int:
        return sum(self._sizes.get(k, 0) for k in self.checked_keys())
