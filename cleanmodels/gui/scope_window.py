"""Fenêtre « Périmètre du contrôle » : dossiers à cocher, gestion des workflows ajoutés, Analyser."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from ..scope import MODEL_GROUP, MODEL_PREFIX, WORKFLOW_PREFIX, describe_scope, scope_rows
from .checktree import CheckTree

DANGER = "#b00020"


class ScopeWindow(tk.Toplevel):
    """Affiche le périmètre ; à chaque ouverture, tous les dossiers disponibles sont cochés."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Périmètre du contrôle")
        self.transient(app)
        self.geometry("1250x620")
        self.minsize(800, 400)

        ttk.Label(
            self,
            text="Décochez les dossiers à ne pas analyser. Les dossiers introuvables sont affichés sans case.",
        ).pack(anchor="w", padx=10, pady=(10, 4))
        self.table = CheckTree(self, "Dossier", [("detail", "Origine", 560)],
                               on_selection_change=self._on_selection)
        self.table.pack(fill="both", expand=True, padx=10)
        self.warning = tk.Label(self, text="", fg=DANGER, justify="left", anchor="w", wraplength=1150)
        self.warning.pack(fill="x", padx=10, pady=(4, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=10)
        self.add_button = ttk.Button(bar, text="Ajouter un dossier de workflows…", command=self._browse)
        self.add_button.pack(side="left")
        self.remove_button = ttk.Button(bar, text="Retirer le dossier sélectionné", command=self._remove)
        self.remove_button.pack(side="left", padx=6)
        self.analyze_button = ttk.Button(bar, text="Analyser", command=self.analyze)
        self.analyze_button.pack(side="right")
        ttk.Button(bar, text="Fermer", command=self.close).pack(side="right", padx=6)

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _e: self.close())
        self._rows: dict = {}
        self.refresh()

    # ----- contenu --------------------------------------------------------

    def refresh(self) -> None:
        """Recalcule le périmètre ; conserve les décochages des dossiers toujours présents."""
        previous = set(self.table.keys()) - set(self.table.checked_keys())
        rows = scope_rows(describe_scope(self.app.comfy_path(), self.app.extra_workflow_dirs()))
        self._rows = {r.key: r for r in rows}
        self.table.set_rows(
            [(r.key, r.group, r.name, (r.detail,), 0) for r in rows],
            disabled={r.key for r in rows if not r.available},
        )
        self.table.check_all()
        for key in previous & set(self._rows):
            if key in self.table.checked_keys():
                self.table.toggle(key)

    def excluded_dirs(self) -> set:
        """dir_key des dossiers disponibles mais décochés."""
        checked = set(self.table.checked_keys())
        return {
            key.split(":", 1)[1]
            for key, row in self._rows.items()
            if row.available and key not in checked
        }

    def _on_selection(self) -> None:
        checked = set(self.table.checked_keys())
        models_checked = any(k.startswith(MODEL_PREFIX) and k in checked for k in self._rows)
        self.analyze_button.configure(state="normal" if models_checked else "disabled")
        unchecked_workflows = [
            row.name for key, row in self._rows.items()
            if key.startswith(WORKFLOW_PREFIX) and row.available and key not in checked
        ]
        if unchecked_workflows:
            self.warning.configure(text=(
                "Attention : les modèles utilisés par les workflows décochés apparaîtront « non utilisés ». "
                "Leur suppression sera toutefois refusée, car tous les dossiers de workflows sont relus "
                "juste avant chaque suppression."
            ))
        elif not models_checked:
            self.warning.configure(text=f"Cochez au moins un dossier dans « {MODEL_GROUP} » pour analyser.")
        else:
            self.warning.configure(text="")

    # ----- actions --------------------------------------------------------

    def _browse(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="Dossier de workflows supplémentaire")
        if folder:
            self.app.add_workflow_dir(folder)

    def _remove(self) -> None:
        added = {str(Path(p)).casefold(): p for p in self.app.extra_workflow_dirs()}
        selected = [self._rows[k].name for k in self.table.tree.selection() if k in self._rows]
        to_remove = [added[name.casefold()] for name in selected if name.casefold() in added]
        if to_remove:
            self.app.remove_workflow_dirs(to_remove)

    def analyze(self) -> None:
        if str(self.analyze_button["state"]) == "disabled":
            return
        excluded = self.excluded_dirs()
        self.close()
        self.app.start_analysis(excluded)

    def close(self) -> None:
        self.app.scope_window_closed(self)
        self.destroy()
