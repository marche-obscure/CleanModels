"""Fenêtre « Périmètre du contrôle » : dossiers à cocher, gestion des workflows ajoutés, Analyser.

Elle s'ouvre avec l'application, à droite de la fenêtre principale, et reste ouverte
pendant et après l'analyse.
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from ..i18n import localized, t
from ..roots import validate_comfyui
from ..scope import MODEL_GROUP, MODEL_PREFIX, WORKFLOW_PREFIX, describe_scope, scope_rows
from .checktree import CheckTree
from .style import palette


class ScopeWindow(tk.Toplevel):
    """À chaque ouverture, tous les dossiers disponibles sont cochés."""

    def __init__(self, app, geometry: str | None = None):
        super().__init__(app)
        self.app = app
        self.title(t("scope_title"))
        self.transient(app)
        if geometry:
            self.geometry(geometry)
        self.minsize(600, 400)
        self.busy = False

        ttk.Label(self, text=t("scope_hint"), wraplength=700, justify="left").pack(
            anchor="w", padx=10, pady=(10, 4))
        self.table = CheckTree(self, t("col_folder"), [("detail", t("col_origin"), 420)],
                               on_selection_change=self._on_selection)
        self.table.pack(fill="both", expand=True, padx=10)
        self.warning = tk.Label(self, text="", fg=palette()["warn"], justify="left", anchor="w",
                                wraplength=700)
        self.warning.pack(fill="x", padx=10, pady=(4, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(6, 0))
        self.add_button = ttk.Button(bar, text=t("add_workflow_dir"), command=self._browse)
        self.add_button.pack(side="left")
        self.remove_button = ttk.Button(bar, text=t("remove_workflow_dir"), command=self._remove)
        self.remove_button.pack(side="left", padx=6)

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=10)
        self.analyze_button = ttk.Button(actions, text=t("analyze"), command=self.analyze, style="Accent.TButton")
        self.analyze_button.pack(side="right")
        ttk.Button(actions, text=t("close"), command=self.close).pack(side="right", padx=6)

        self.protocol("WM_DELETE_WINDOW", self.close)
        self._rows: dict = {}
        self.refresh()

    # ----- contenu --------------------------------------------------------

    def _path_valid(self) -> bool:
        path = str(self.app.comfy_path())
        return bool(self.app.path_var.get().strip()) and validate_comfyui(Path(path)) is None

    def refresh(self) -> None:
        """Recalcule le périmètre ; conserve les décochages des dossiers toujours présents."""
        previous = set(self.table.keys()) - set(self.table.checked_keys())
        if self._path_valid():
            rows = scope_rows(describe_scope(self.app.comfy_path(), self.app.extra_workflow_dirs()))
        else:
            rows = []
        self._rows = {r.key: r for r in rows}
        self.table.set_rows(
            [(r.key, localized(r.group), r.name, (localized(r.detail),), 0) for r in rows],
            disabled={r.key for r in rows if not r.available},
        )
        self.table.check_all()
        for key in previous & set(self._rows):
            if key in self.table.checked_keys():
                self.table.toggle(key)
        self._on_selection()

    def excluded_dirs(self) -> set:
        """dir_key des dossiers disponibles mais décochés."""
        checked = set(self.table.checked_keys())
        return {
            key.split(":", 1)[1]
            for key, row in self._rows.items()
            if row.available and key not in checked
        }

    def _models_checked(self) -> bool:
        checked = set(self.table.checked_keys())
        return any(k.startswith(MODEL_PREFIX) and k in checked for k in self._rows)

    def _on_selection(self) -> None:
        if not hasattr(self, "analyze_button"):
            return
        checked = set(self.table.checked_keys())
        models_checked = self._models_checked()
        state = "normal" if models_checked and not self.busy else "disabled"
        self.analyze_button.configure(state=state)
        unchecked_workflows = [
            key for key, row in self._rows.items()
            if key.startswith(WORKFLOW_PREFIX) and row.available and key not in checked
        ]
        if not self._path_valid():
            text = t("scope_need_path")
        elif unchecked_workflows:
            text = t("warn_unchecked_workflows")
        elif not models_checked:
            text = t("warn_no_model_dir", group=localized(MODEL_GROUP))
        else:
            text = ""
        self.warning.configure(text=text)

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.add_button.configure(state=state)
        self.remove_button.configure(state=state)
        self._on_selection()

    # ----- actions --------------------------------------------------------

    def _browse(self) -> None:
        folder = filedialog.askdirectory(parent=self, title=t("workflow_dir_title"))
        if folder:
            self.app.add_workflow_dir(folder)

    def _remove(self) -> None:
        added = {str(Path(p)).casefold(): p for p in self.app.extra_workflow_dirs()}
        selected = [self._rows[k].name for k in self.table.tree.selection() if k in self._rows]
        to_remove = [added[name.casefold()] for name in selected if name.casefold() in added]
        if to_remove:
            self.app.remove_workflow_dirs(to_remove)

    def analyze(self) -> None:
        """Lance l'analyse sur les dossiers cochés ; la fenêtre reste ouverte."""
        if str(self.analyze_button["state"]) == "disabled":
            return
        self.app.start_analysis(self.excluded_dirs())

    def close(self) -> None:
        self.app.scope_window_closed(self)
        self.destroy()
