"""Fenêtre principale de CleanModels."""

import queue
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .. import __version__
from ..analysis import run_analysis
from ..deletion import delete_files
from ..inventory import file_key
from ..roots import validate_comfyui
from ..settings import load_settings, save_settings, settings_dir
from .dialogs import confirm_deletion, show_details, show_report
from .format import format_size
from .tabs import DuplicatesTab, JunkTab, UnusedTab, UsedTab

LOG_FILE = "cleanmodels.log"
POLL_MS = 100


class CleanModelsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"CleanModels {__version__}")
        self.geometry("1150x720")
        self.minsize(900, 500)
        self.settings, settings_warning = load_settings()
        self.result = None
        self.busy = False
        self._build()
        self.path_var.set(self.settings.get("comfyui_path", ""))
        self.junk_tab.set_patterns(self.settings.get("junk_patterns", []))
        if settings_warning:
            self.after(200, lambda: messagebox.showwarning("Réglages", settings_warning, parent=self))

    # ----- construction -------------------------------------------------

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(top, text="Dossier ComfyUI :").pack(side="left")
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(top, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.browse_button = ttk.Button(top, text="Parcourir…", command=self._browse)
        self.browse_button.pack(side="left")
        self.analyze_button = ttk.Button(top, text="Analyser", command=self._analyze)
        self.analyze_button.pack(side="left", padx=(6, 0))

        self.validation = tk.Label(self, text="", fg="#b00020", anchor="w")
        self.validation.pack(fill="x", padx=10)

        status = ttk.Frame(self)
        status.pack(fill="x", padx=10, pady=4)
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=200)
        self.progress.pack(side="left")
        self.step_label = ttk.Label(status, text="")
        self.step_label.pack(side="left", padx=8)

        summary = ttk.Frame(self)
        summary.pack(fill="x", padx=10, pady=(0, 6))
        self.summary_label = ttk.Label(summary, text="Choisissez le dossier ComfyUI puis cliquez sur « Analyser ».",
                                       justify="left")
        self.summary_label.pack(side="left")
        self.details_button = ttk.Button(summary, text="Détails…", command=self._details, state="disabled")
        self.details_button.pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.used_tab = UsedTab(self.notebook)
        self.unused_tab = UnusedTab(self.notebook, self._delete)
        self.duplicates_tab = DuplicatesTab(self.notebook, self._delete, self.run_background, self.set_busy)
        self.junk_tab = JunkTab(self.notebook, self._delete, self._save_patterns)
        self.tabs = [self.used_tab, self.unused_tab, self.duplicates_tab, self.junk_tab]
        for tab, title in zip(self.tabs, ["Utilisés", "Non utilisés", "Doublons", "Fichiers parasites"]):
            self.notebook.add(tab, text=title)

        self.path_var.trace_add("write", lambda *_: self._validate())

    # ----- état ---------------------------------------------------------

    def _validate(self) -> bool:
        path = self.path_var.get().strip()
        message = "Choisissez le dossier d'installation de ComfyUI." if not path else validate_comfyui(Path(path))
        self.validation.configure(text=message or "")
        self.analyze_button.configure(state="disabled" if message or self.busy else "normal")
        return message is None

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.browse_button.configure(state=state)
        self.path_entry.configure(state=state)
        for tab in self.tabs:
            tab.set_enabled(not busy)
        self._validate()

    def run_background(self, work: Callable, on_progress: Callable, on_done: Callable,
                       on_error: Callable | None = None) -> None:
        """Exécute work(report) dans un fil séparé ; les rappels s'exécutent dans le fil de l'interface.

        on_error(exc, trace) renvoie True si l'erreur est gérée ; sinon elle est affichée et journalisée.
        """
        messages: queue.Queue = queue.Queue()

        def target():
            try:
                messages.put(("done", work(lambda value: messages.put(("progress", value)))))
            except BaseException as exc:  # noqa: BLE001 — remontée vers l'interface
                messages.put(("error", exc, traceback.format_exc()))

        def poll():
            try:
                while True:
                    message = messages.get_nowait()
                    if message[0] == "progress":
                        on_progress(message[1])
                    elif message[0] == "done":
                        on_done(message[1])
                        return
                    else:
                        _, exc, trace = message
                        if not (on_error and on_error(exc, trace)):
                            self.report_error(exc, trace)
                        return
            except queue.Empty:
                self.after(POLL_MS, poll)

        threading.Thread(target=target, daemon=True).start()
        self.after(POLL_MS, poll)

    def report_error(self, exc: BaseException, trace: str) -> None:
        self.set_busy(False)
        self.progress.stop()
        self.step_label.configure(text="")
        try:
            with open(settings_dir() / LOG_FILE, "a", encoding="utf-8") as handle:
                handle.write(f"{datetime.now().isoformat(timespec='seconds')}\tERREUR INTERNE\n{trace}\n")
        except OSError:
            pass
        messagebox.showerror("Erreur", f"Une erreur inattendue s'est produite :\n{exc}", parent=self)

    # ----- actions ------------------------------------------------------

    def _browse(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="Dossier d'installation de ComfyUI",
                                         initialdir=self.path_var.get() or None)
        if folder:
            self.path_var.set(str(Path(folder)))

    def _save_patterns(self, patterns: list) -> None:
        self.settings["junk_patterns"] = list(patterns)
        save_settings(self.settings)

    def _analyze(self) -> None:
        if self.busy or not self._validate():
            return
        comfy = Path(self.path_var.get().strip())
        self.settings["comfyui_path"] = str(comfy)
        save_settings(self.settings)
        patterns = list(self.junk_tab.patterns)
        self.set_busy(True)
        self.progress.start(12)

        def on_done(result):
            self.progress.stop()
            self.step_label.configure(text="Analyse terminée.")
            self.result = result
            for tab in self.tabs:
                tab.show(result)
            self._show_summary(result)
            self.set_busy(False)

        self.run_background(
            lambda report: run_analysis(comfy, patterns, progress=report),
            lambda label: self.step_label.configure(text=label),
            on_done,
        )

    def _show_summary(self, result) -> None:
        wf, roots, usage = result.workflows, result.roots, result.usage
        unused_bytes = sum(f.size for f in usage.unused)
        lines = [
            f"Workflows lus : {wf.workflow_count}   ignorés : {len(wf.skipped)}   —   "
            f"Dossiers analysés : {len(roots.dirs)}   introuvables : {len(roots.missing)}",
            f"Modèles : {len(result.inventory.files)} ({format_size(result.total_bytes)})   —   "
            f"utilisés : {len(usage.used)}   non utilisés : {len(usage.unused)} ({format_size(unused_bytes)})",
        ]
        if roots.warnings or result.inventory.errors:
            lines.append("⚠ Des avertissements sont disponibles dans « Détails… ».")
        self.summary_label.configure(text="\n".join(lines))
        self.details_button.configure(state="normal")

    def _details(self) -> None:
        if self.result is None:
            return
        r = self.result
        lines = ["Dossiers analysés :"]
        lines += [f"  [{d.category}] {d.path}  ({d.origin})" for d in r.roots.dirs]
        if r.roots.missing:
            lines += ["", "Dossiers déclarés introuvables :"]
            lines += [f"  [{d.category}] {d.path}  ({d.origin})" for d in r.roots.missing]
        if r.workflows.skipped:
            lines += ["", "Workflows ignorés :"]
            lines += [f"  {path} — {reason}" for path, reason in r.workflows.skipped]
        if r.roots.warnings:
            lines += ["", "Avertissements :"] + [f"  {w}" for w in r.roots.warnings]
        if r.inventory.errors:
            lines += ["", "Fichiers inaccessibles :"] + [f"  {e}" for e in r.inventory.errors]
        show_details(self, "Détails de l'analyse", lines)

    def _delete(self, items: list, checker_factory: Callable, notes: list) -> None:
        if self.busy or not items:
            return
        total = sum(item.size for item in items)
        if not confirm_deletion(self, [item.path for item in items], total, notes):
            return
        keys = {item: file_key(item.path) for item in items}
        log_path = settings_dir() / LOG_FILE
        self.set_busy(True)
        self.step_label.configure(text="Suppression en cours…")

        def on_done(result):
            self.set_busy(False)
            self.step_label.configure(text="")
            deleted = [keys[item] for item in result.deleted]
            for tab in self.tabs:
                tab.forget(deleted)
            show_report(self, result)

        self.run_background(lambda _report: delete_files(items, checker_factory(), log_path),
                            lambda _value: None, on_done)


def main() -> None:
    app = CleanModelsApp()
    app.mainloop()
