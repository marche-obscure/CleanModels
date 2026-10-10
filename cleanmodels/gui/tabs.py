"""Les quatre onglets : Utilisés, Non utilisés, Doublons, Fichiers parasites."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ..constants import DEFAULT_JUNK_PATTERNS
from ..deletion import DeletionItem, duplicates_checker, fully_selected_groups, junk_checker, unused_checker
from ..duplicates import Cancelled, find_duplicates
from ..inventory import file_key
from ..junk import find_junk
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
            return f"{rel}  [{source.origin} : {source.path}]"
    return str(path)


def _category_order(rows: list) -> list:
    """Lignes (clé, groupe, nom, valeurs, taille) triées par catégorie puis par nom."""
    return sorted(rows, key=lambda r: (r[1].casefold(), r[2].casefold()))


class UsedTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.table = SortableTree(self, "Catégorie / Nom", [
            ("root", "Dossier racine", 380),
            ("size_n", "Taille", 90),
            ("calls_n", "Appels", 70),
            ("workflows_n", "Workflows", 80),
        ])
        ttk.Label(self, text="Double-cliquez sur un modèle pour voir les workflows qui l'utilisent.").pack(
            anchor="w", padx=6, pady=4
        )
        self.table.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.table.bind_double_click(self._details)
        self._usages: dict = {}
        self._sources: list = []

    def show(self, result) -> None:
        self._sources = list(result.workflow_sources)
        self._usages = {file_key(u.file.path): u for u in result.usage.used}
        self.table.set_rows(_category_order([
            (key, u.file.category, u.file.rel_path,
             (str(u.file.root), format_size(u.file.size), u.calls, len(u.workflows)), u.file.size)
            for key, u in self._usages.items()
        ]))
        self.table.sort_by("calls_n", descending=True)

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
            lines.append(f"{_describe_workflow(ref.workflow, self._sources)} — nœud {ref.node_id} ({ref.node_type})")
        show_details(self, f"Utilisation de {usage.file.path.name}", lines)


class _DeletableTab(ttk.Frame):
    """Onglet avec cases à cocher, compteur et bouton Supprimer."""

    def __init__(self, master, tree_title: str, columns: list, on_delete: DeleteCallback):
        super().__init__(master)
        self.on_delete = on_delete
        self.enabled = True
        self.top = ttk.Frame(self)
        self.top.pack(fill="x", padx=6, pady=4)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Button(bar, text="Tout sélectionner", command=lambda: self.table.check_all()).pack(side="left")
        ttk.Button(bar, text="Tout désélectionner", command=lambda: self.table.uncheck_all()).pack(
            side="left", padx=6
        )
        self.counter = ttk.Label(bar, text="")
        self.counter.pack(side="left", padx=12)
        self.delete_button = ttk.Button(bar, text="Supprimer", command=self._delete, state="disabled")
        self.delete_button.pack(side="right")
        self.table = CheckTree(self, tree_title, columns, on_selection_change=self._refresh)
        self.table.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._refresh()

    def _refresh(self) -> None:
        count = len(self.table.checked_keys())
        self.counter.configure(
            text=f"{count} fichier{'s' if count > 1 else ''} sélectionné{'s' if count > 1 else ''}"
                 f" – {format_size(self.table.checked_size())}"
        )
        self.delete_button.configure(state="normal" if count and self.enabled else "disabled")

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._refresh()

    def forget(self, keys: list) -> None:
        self.table.remove_keys(keys)

    def _delete(self) -> None:
        raise NotImplementedError


class UnusedTab(_DeletableTab):
    def __init__(self, master, on_delete: DeleteCallback, workflow_folders: Callable[[], list]):
        super().__init__(master, "Catégorie / Nom", [
            ("root", "Dossier racine", 340),
            ("size_n", "Taille", 90),
            ("path", "Chemin complet", 420),
        ], on_delete)
        self._files: dict = {}
        self._result = None
        self._workflow_folders = workflow_folders

    def show(self, result) -> None:
        self._result = result
        self._files = {file_key(f.path): f for f in result.usage.unused}
        self.table.set_rows(_category_order([
            (key, f.category, f.rel_path, (str(f.root), format_size(f.size), str(f.path)), f.size)
            for key, f in self._files.items()
        ]))
        self.table.sort_by("size_n", descending=True)

    def _delete(self) -> None:
        files = [self._files[k] for k in self.table.checked_keys()]
        items = [DeletionItem(f.path, f.size, "unused") for f in files]
        # Dossiers de l'analyse + dossiers actuellement configurés : on contrôle large.
        folders = [src.path for src in self._result.workflow_sources] + list(self._workflow_folders())
        inventory = self._result.inventory
        files, aliases = list(inventory.files), list(inventory.aliases)
        notes = []
        if self._result.workflows.skipped:
            notes.append(
                f"{len(self._result.workflows.skipped)} workflow(s) illisible(s) : la suppression sera refusée "
                "tant qu'ils ne sont pas corrigés ou retirés (voir « Détails… »)."
            )
        self.on_delete(items, lambda: unused_checker(folders, files, aliases), notes)


class DuplicatesTab(_DeletableTab):
    def __init__(self, master, on_delete: DeleteCallback, run_background: Callable, set_busy: Callable):
        super().__init__(master, "Groupe / Nom", [
            ("path", "Chemin", 520),
            ("size_n", "Taille", 90),
            ("referenced", "Référencé", 90),
        ], on_delete)
        self._run_background = run_background
        self._set_busy = set_busy
        self.search_button = ttk.Button(self.top, text="Rechercher les doublons", command=self._search,
                                        state="disabled")
        self.search_button.pack(side="left")
        self.cancel_button = ttk.Button(self.top, text="Annuler", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=6)
        self.progress = ttk.Progressbar(self.top, mode="determinate", maximum=100, length=240)
        self.progress.pack(side="left", padx=6)
        self.status = ttk.Label(self.top, text="La recherche lit le contenu des fichiers : elle peut être longue.")
        self.status.pack(side="left", padx=6)
        self._result = None
        self._groups: list = []
        self._entries: dict = {}
        self._used_keys: set = set()
        self._cancel_event = None

    def show(self, result) -> None:
        self._result = result
        self._used_keys = {file_key(u.file.path) for u in result.usage.used}
        self._groups, self._entries = [], {}
        self.table.set_rows([])
        self.progress.configure(value=0)
        self.status.configure(text="Cliquez sur « Rechercher les doublons ».")
        self.search_button.configure(state="normal" if self.enabled else "disabled")

    def set_enabled(self, enabled: bool) -> None:
        super().set_enabled(enabled)
        self.search_button.configure(state="normal" if enabled and self._result else "disabled")

    def _search(self) -> None:
        self._cancel_event = threading.Event()
        cancel, files = self._cancel_event, list(self._result.inventory.files)
        self._set_busy(True)
        self.cancel_button.configure(state="normal")
        self.status.configure(text="Recherche en cours…")

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
                self.status.configure(text="Recherche annulée.")
                self.progress.configure(value=0)
                return True
            return False

        self._run_background(work, on_progress, on_done, on_error)

    def _cancel(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()

    def _show_groups(self, groups: list) -> None:
        self._groups, self._entries, rows = groups, {}, []
        for number, group in enumerate(groups, start=1):
            for f in group.files:
                key = file_key(f.path)
                self._entries[key] = (group, f)
                referenced = "oui" if key in self._used_keys else ""
                label = f"Groupe {number} — {group.files[0].path.name}"
                rows.append((key, label, f.path.name, (str(f.path), format_size(f.size), referenced), f.size))
        self.table.set_rows(rows)
        self.progress.configure(value=100)
        wasted = sum(g.size * (len(g.files) - 1) for g in groups)
        self.status.configure(
            text=f"{len(groups)} groupe{'s' if len(groups) > 1 else ''} – {format_size(wasted)} récupérables"
        )

    def forget(self, keys: list) -> None:
        super().forget(keys)
        for key in keys:
            self._entries.pop(key, None)

    def _delete(self) -> None:
        selected = set(self.table.checked_keys())
        if fully_selected_groups(self._groups, selected):
            messagebox.showwarning(
                "Doublons",
                "Toutes les copies d'au moins un groupe sont cochées.\n"
                "Gardez au moins une copie de chaque groupe.",
                parent=self,
            )
            return
        files = [self._entries[k][1] for k in self.table.checked_keys()]
        items = [DeletionItem(f.path, f.size, "duplicates") for f in files]
        referenced = [str(f.path) for f in files if file_key(f.path) in self._used_keys]
        notes = []
        if referenced:
            notes.append(
                "Attention : ces copies sont citées par un workflow, qui devra pointer vers une autre copie :\n"
                + "\n".join(referenced)
            )
        groups = self._groups
        self.on_delete(items, lambda: duplicates_checker(groups, selected), notes)


class JunkTab(_DeletableTab):
    def __init__(self, master, on_delete: DeleteCallback, on_patterns_change: Callable[[list], None]):
        super().__init__(master, "Catégorie / Nom", [
            ("root", "Dossier racine", 340),
            ("size_n", "Taille", 90),
            ("pattern", "Motif", 110),
            ("path", "Chemin complet", 420),
        ], on_delete)
        self._on_patterns_change = on_patterns_change
        ttk.Label(self.top, text="Motifs (séparés par « ; ») :").pack(side="left")
        self.patterns_var = tk.StringVar()
        ttk.Entry(self.top, textvariable=self.patterns_var, width=50).pack(side="left", padx=6)
        ttk.Button(self.top, text="Appliquer", command=self._apply).pack(side="left")
        ttk.Button(self.top, text="Rétablir les motifs par défaut", command=self._reset).pack(side="left", padx=6)
        self._result = None
        self._files: dict = {}
        self.patterns: list = list(DEFAULT_JUNK_PATTERNS)

    def set_patterns(self, patterns: list) -> None:
        self.patterns = list(patterns)
        self.patterns_var.set(" ; ".join(self.patterns))

    def show(self, result, junk: list | None = None) -> None:
        self._result = result
        junk = result.junk if junk is None else junk
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
