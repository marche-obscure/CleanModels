"""Les quatre onglets : Utilisés, Non utilisés, Doublons, Fichiers parasites."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ..constants import DEFAULT_JUNK_PATTERNS
from ..deletion import DeletionItem, duplicates_checker, fully_selected_groups, junk_checker, unused_checker
from ..duplicates import Cancelled, find_duplicates
from ..gpu import exceeds_vram
from ..i18n import localized, t, tn
from ..inventory import file_key
from ..junk import find_junk
from ..scope import origin_label
from .checktree import CheckTree, SortableTree
from .dialogs import show_details
from .format import format_size

# on_delete(items, fabrique du vérificateur, notes à afficher dans la confirmation)
DeleteCallback = Callable[[list, Callable, list], None]


def _describe_workflow(path, sources: list) -> str:
    """Chemin du workflow relatif à son dossier de référence, suivi de ce dossier."""
    for source in sources:
        try:
            rel = os.path.relpath(path, source.path)
        except ValueError:
            continue
        if not rel.startswith(".."):
            return f"{rel}  [{localized(origin_label(source.origin))} : {source.path}]"
    return str(path)


def _mark_vram(table, vram) -> None:
    table.set_marked({k for k in table.keys() if exceeds_vram(table.size_of(k), vram)})


def _category_order(rows: list) -> list:
    """Lignes (clé, groupe, nom, valeurs, taille) triées par catégorie puis par nom."""
    return sorted(rows, key=lambda r: (r[1].casefold(), r[2].casefold()))


class UsedTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.table = SortableTree(self, t("col_category_name"), [
            ("root", t("col_root"), 380),
            ("size_n", t("col_size"), 90),
            ("calls_n", t("col_calls"), 70),
            ("workflows_n", t("col_workflows"), 80),
            ("vram", t("col_vram"), 80),
        ])
        ttk.Label(self, text=t("used_hint")).pack(anchor="w", padx=6, pady=4)
        self.table.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.table.bind_double_click(self._details)
        self._usages: dict = {}
        self._sources: list = []
        self._vram = None

    def show(self, result) -> None:
        self._sources = list(result.workflow_sources)
        self._usages = {file_key(u.file.path): u for u in result.usage.used}
        self.table.set_rows(_category_order([
            (key, u.file.category, u.file.rel_path,
             (str(u.file.root), format_size(u.file.size), u.calls, len(u.workflows), ""), u.file.size)
            for key, u in self._usages.items()
        ]))
        self.table.sort_by("calls_n", descending=True)
        _mark_vram(self.table, self._vram)

    def set_vram(self, vram) -> None:
        self._vram = vram
        _mark_vram(self.table, vram)

    def forget(self, keys: list) -> None:
        self.table.remove_keys(keys)

    def set_enabled(self, enabled: bool) -> None:
        pass

    def _details(self, key: str) -> None:
        usage = self._usages.get(key)
        if usage is None:
            return
        lines = [str(usage.file.path), ""]
        for ref in usage.references:
            lines.append(t("workflow_node", workflow=_describe_workflow(ref.workflow, self._sources),
                           node=ref.node_id, type=ref.node_type))
        show_details(self, t("usage_title", name=usage.file.path.name), lines)


class _DeletableTab(ttk.Frame):
    """Onglet avec cases à cocher, compteur et bouton Supprimer (rouge quand il est actif)."""

    def __init__(self, master, tree_title: str, columns: list, on_delete: DeleteCallback):
        super().__init__(master)
        self.on_delete = on_delete
        self.enabled = True
        self._vram = None
        self.top = ttk.Frame(self)
        self.top.pack(fill="x", padx=6, pady=4)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Button(bar, text=t("select_all"), command=lambda: self.table.check_all()).pack(side="left")
        ttk.Button(bar, text=t("unselect_all"), command=lambda: self.table.uncheck_all()).pack(
            side="left", padx=6
        )
        self.counter = ttk.Label(bar, text="")
        self.counter.pack(side="left", padx=12)
        self.delete_button = ttk.Button(bar, text=t("delete"), command=self._delete, state="disabled",
                                        style="Danger.TButton")
        self.delete_button.pack(side="right")
        self.table = CheckTree(self, tree_title, columns, on_selection_change=self._refresh)
        self.table.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._refresh()

    def _refresh(self) -> None:
        count = len(self.table.checked_keys())
        self.counter.configure(text=tn("selected_count", count, size=format_size(self.table.checked_size())))
        self.delete_button.configure(state="normal" if count and self.enabled else "disabled")

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._refresh()

    def forget(self, keys: list) -> None:
        self.table.remove_keys(keys)

    def set_vram(self, vram) -> None:
        """Mémoire vidéo de référence ; seuls les onglets ayant une colonne « vram » marquent."""
        self._vram = vram
        if "vram" in self.table.tree["columns"]:
            _mark_vram(self.table, vram)

    def _delete(self) -> None:
        raise NotImplementedError


class UnusedTab(_DeletableTab):
    def __init__(self, master, on_delete: DeleteCallback, workflow_folders: Callable[[], list]):
        super().__init__(master, t("col_category_name"), [
            ("root", t("col_root"), 340),
            ("size_n", t("col_size"), 90),
            ("vram", t("col_vram"), 80),
            ("path", t("col_full_path"), 420),
        ], on_delete)
        self._files: dict = {}
        self._result = None
        self._workflow_folders = workflow_folders

    def show(self, result) -> None:
        self._result = result
        self._files = {file_key(f.path): f for f in result.usage.unused}
        self.table.set_rows(_category_order([
            (key, f.category, f.rel_path, (str(f.root), format_size(f.size), "", str(f.path)), f.size)
            for key, f in self._files.items()
        ]))
        self.table.sort_by("size_n", descending=True)
        self.set_vram(self._vram)

    def _delete(self) -> None:
        files = [self._files[k] for k in self.table.checked_keys()]
        items = [DeletionItem(f.path, f.size, "unused") for f in files]
        # Tous les dossiers de l'analyse (même décochés) + dossiers configurés : on contrôle large.
        folders = [src.path for src in self._result.workflow_sources] + list(self._workflow_folders())
        inventory = self._result.inventory
        files, aliases = list(inventory.files), list(inventory.aliases)
        notes = []
        if self._result.excluded_workflow_sources:
            notes.append(t("note_unchecked_workflows", folders="\n".join(
                str(src.path) for src in self._result.excluded_workflow_sources)))
        if self._result.workflows.skipped:
            notes.append(t("note_unreadable", count=len(self._result.workflows.skipped)))
        self.on_delete(items, lambda: unused_checker(folders, files, aliases), notes)


class DuplicatesTab(_DeletableTab):
    def __init__(self, master, on_delete: DeleteCallback, run_background: Callable, set_busy: Callable):
        super().__init__(master, t("col_group_name"), [
            ("path", t("col_path"), 520),
            ("size_n", t("col_size"), 90),
            ("referenced", t("col_referenced"), 110),
            ("vram", t("col_vram"), 80),
        ], on_delete)
        self._run_background = run_background
        self._set_busy = set_busy
        self.search_button = ttk.Button(self.top, text=t("search_duplicates"), command=self._search,
                                        state="disabled")
        self.search_button.pack(side="left")
        self.cancel_button = ttk.Button(self.top, text=t("cancel"), command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=6)
        self.progress = ttk.Progressbar(self.top, mode="determinate", maximum=100, length=240)
        self.progress.pack(side="left", padx=6)
        self.status = ttk.Label(self.top, text=t("dup_hint"))
        self.status.pack(side="left", padx=6)
        self._result = None
        self.groups: list | None = None  # None : recherche pas encore faite
        self._entries: dict = {}
        self._used_keys: set = set()
        self._cancel_event = None

    def show(self, result, groups: list | None = None) -> None:
        """Affiche une nouvelle analyse ; `groups` réaffiche une recherche déjà faite."""
        self._result = result
        self._used_keys = {file_key(u.file.path) for u in result.usage.used}
        self.groups, self._entries = None, {}
        self.table.set_rows([])
        self.progress.configure(value=0)
        self.status.configure(text=t("dup_click_search"))
        self.search_button.configure(state="normal" if self.enabled else "disabled")
        if groups is not None:
            self._show_groups(groups)

    def set_enabled(self, enabled: bool) -> None:
        super().set_enabled(enabled)
        self.search_button.configure(state="normal" if enabled and self._result else "disabled")

    def _search(self) -> None:
        self._cancel_event = threading.Event()
        cancel, files = self._cancel_event, list(self._result.inventory.files)
        self._set_busy(True)
        self.cancel_button.configure(state="normal")
        self.status.configure(text=t("dup_searching"))

        def work(report):
            return find_duplicates(files, progress=lambda done, total: report((done, total)), cancel=cancel)

        def on_progress(value):
            done, total = value
            self.progress.configure(value=100 * done / total if total else 100)
            self.status.configure(text=f"{format_size(done)} / {format_size(total)}")

        def finish():
            self.cancel_button.configure(state="disabled")
            self._set_busy(False)

        def on_done(groups):
            finish()
            self._show_groups(groups)

        def on_error(exc, trace):
            finish()
            if isinstance(exc, Cancelled):
                self.status.configure(text=t("dup_cancelled"))
                self.progress.configure(value=0)
                return True
            return False

        self._run_background(work, on_progress, on_done, on_error)

    def _cancel(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()

    def _show_groups(self, groups: list) -> None:
        self.groups, self._entries, rows = groups, {}, []
        for number, group in enumerate(groups, start=1):
            for f in group.files:
                key = file_key(f.path)
                self._entries[key] = (group, f)
                referenced = t("yes") if key in self._used_keys else ""
                label = t("dup_group", number=number, name=group.files[0].path.name)
                rows.append((key, label, f.path.name, (str(f.path), format_size(f.size), referenced, ""), f.size))
        self.table.set_rows(rows)
        self.set_vram(self._vram)
        self.progress.configure(value=100)
        wasted = sum(g.size * (len(g.files) - 1) for g in groups)
        self.status.configure(text=tn("dup_result", len(groups), size=format_size(wasted)))

    def forget(self, keys: list) -> None:
        super().forget(keys)
        for key in keys:
            self._entries.pop(key, None)

    def _delete(self) -> None:
        selected = set(self.table.checked_keys())
        groups = self.groups or []
        if fully_selected_groups(groups, selected):
            messagebox.showwarning(t("tab_duplicates"), t("dup_all_selected"), parent=self)
            return
        files = [self._entries[k][1] for k in self.table.checked_keys()]
        items = [DeletionItem(f.path, f.size, "duplicates") for f in files]
        referenced = [str(f.path) for f in files if file_key(f.path) in self._used_keys]
        notes = [t("note_referenced_copies", paths="\n".join(referenced))] if referenced else []
        self.on_delete(items, lambda: duplicates_checker(groups, selected), notes)


class JunkTab(_DeletableTab):
    def __init__(self, master, on_delete: DeleteCallback, on_patterns_change: Callable[[list], None]):
        super().__init__(master, t("col_category_name"), [
            ("root", t("col_root"), 340),
            ("size_n", t("col_size"), 90),
            ("pattern", t("col_pattern"), 110),
            ("path", t("col_full_path"), 420),
        ], on_delete)
        self._on_patterns_change = on_patterns_change
        ttk.Label(self.top, text=t("junk_patterns")).pack(side="left")
        self.patterns_var = tk.StringVar()
        ttk.Entry(self.top, textvariable=self.patterns_var, width=50).pack(side="left", padx=6)
        ttk.Button(self.top, text=t("apply"), command=self._apply).pack(side="left")
        ttk.Button(self.top, text=t("reset_patterns"), command=self._reset).pack(side="left", padx=6)
        self._result = None
        self._files: dict = {}
        self.junk: list = []
        self.patterns: list = list(DEFAULT_JUNK_PATTERNS)

    def set_patterns(self, patterns: list) -> None:
        self.patterns = list(patterns)
        self.patterns_var.set(" ; ".join(self.patterns))

    def show(self, result, junk: list | None = None) -> None:
        self._result = result
        junk = result.junk if junk is None else junk
        self.junk = list(junk)
        self._files = {file_key(j.path): j for j in junk}
        self.table.set_rows(_category_order([
            (key, j.category, j.path.name, (str(j.root), format_size(j.size), j.pattern, str(j.path)), j.size)
            for key, j in self._files.items()
        ]))

    def _apply(self) -> None:
        patterns = [p.strip() for p in self.patterns_var.get().split(";") if p.strip()]
        self.set_patterns(patterns)
        self._on_patterns_change(patterns)
        if self._result is not None:
            self.show(self._result, find_junk(self._result.roots.dirs, patterns))

    def _reset(self) -> None:
        self.patterns_var.set(" ; ".join(DEFAULT_JUNK_PATTERNS))
        self._apply()

    def _delete(self) -> None:
        files = [self._files[k] for k in self.table.checked_keys()]
        items = [DeletionItem(j.path, j.size, "junk") for j in files]
        patterns = list(self.patterns)
        self.on_delete(items, lambda: junk_checker(patterns), [])
