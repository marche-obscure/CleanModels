"""Fenêtre principale de CleanModels."""

import os
import queue
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable

from .. import __version__, i18n
from ..analysis import run_analysis
from ..deletion import delete_files
from ..gpu import detect_gpus
from ..i18n import LANGUAGES, localized, t
from ..inventory import file_key
from ..roots import validate_comfyui
from ..scope import origin_label
from ..settings import load_settings, save_settings, settings_dir
from ..shortcut import ICON_PATH, PROJECT_DIR
from ..shortcut import create as create_shortcut
from ..shortcut import exists as shortcut_exists
from .dialogs import ask_choice, confirm_deletion, show_details, show_report
from .format import format_size
from .scope_window import ScopeWindow
from .style import apply_style, palette
from .tabs import DuplicatesTab, JunkTab, UnusedTab, UsedTab

LOG_FILE = "cleanmodels.log"
POLL_MS = 100
THEME_KEYS = ("light", "dark")
MANUAL_GPU = "__manual__"

# Variables Tk des interfaces remplacées : gardées en vie pour qu'elles ne soient jamais libérées
# par le ramasse-miettes depuis un fil d'arrière-plan (appel Tk hors du fil principal).
_RETIRED: list = []

LOGO_PATH = PROJECT_DIR / "assets" / "cleanmodels_logo.png"
BANNER_BACKGROUND = "#1c1b20"  # bannière sombre, identique en thème Clair et Sombre (comme Deziporama)
BANNER_FOREGROUND = "#f0f0f0"
# Logo gardé en cache pour la durée du programme (même raison que _RETIRED).
_LOGO_CACHE: dict = {}


def _logo_image(root):
    """Logo PNG (transparent) lu par Tk sans dépendance ; None si le fichier est absent ou illisible."""
    key = str(root.tk)
    if key not in _LOGO_CACHE:
        try:
            _LOGO_CACHE[key] = tk.PhotoImage(master=root, file=str(LOGO_PATH))
        except tk.TclError:
            _LOGO_CACHE[key] = None
    return _LOGO_CACHE[key]


def window_layout(screen_width: int, screen_height: int) -> tuple:
    """Géométries (principale, périmètre) : principale à gauche (60 %), périmètre collé à droite."""
    height = max(screen_height - 110, 400)
    main_width = int(screen_width * 0.6)
    scope_x = main_width + 16  # largeur des bordures de fenêtre Windows
    scope_width = max(screen_width - scope_x - 16, 400)
    return f"{main_width}x{height}+0+0", f"{scope_width}x{height}+{scope_x}+0"


class CleanModelsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings, settings_warning = load_settings()
        i18n.set_language(self.settings.get("language", i18n.DEFAULT_LANGUAGE))
        apply_style(self, self._theme())
        self.title(f"CleanModels {__version__}")
        if ICON_PATH.is_file():
            try:
                self.iconbitmap(default=str(ICON_PATH))
            except tk.TclError:
                pass
        self.minsize(700, 500)
        main_geometry, self._scope_geometry = window_layout(self.winfo_screenwidth(), self.winfo_screenheight())
        self.geometry(main_geometry)
        self.result = None
        self.busy = False
        self.scope_window = None
        self.gpus = detect_gpus()
        # Présence du raccourci vérifiée une seule fois, au lancement (aucune surveillance ensuite).
        try:
            self.shortcut_present = shortcut_exists()
        except OSError:
            self.shortcut_present = False
        self._build()
        self.path_var.set(self.settings.get("comfyui_path", ""))
        self.junk_tab.set_patterns(self.settings.get("junk_patterns", []))
        self.open_scope_window()
        if not self.settings.get("desktop_shortcut_asked") and not self.shortcut_present:
            self.after_idle(self._offer_shortcut)
        if settings_warning:
            self.after(200, lambda: messagebox.showwarning(t("settings_title"), localized(settings_warning),
                                                           parent=self))

    def _theme(self) -> str:
        theme = self.settings.get("theme", "light")
        return theme if theme in THEME_KEYS else "light"

    # ----- construction -------------------------------------------------

    def _build(self) -> None:
        """Construit tout le contenu dans self.body (détruit et reconstruit au changement de langue/thème)."""
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True)

        # Bannière (même couleur dans les deux thèmes) : logo à gauche, thème et langue à droite.
        self.banner = tk.Frame(self.body, background=BANNER_BACKGROUND)
        self.banner.pack(fill="x")
        logo = _logo_image(self)
        self.logo_label = tk.Label(self.banner, image=logo if logo is not None else "",
                                   background=BANNER_BACKGROUND, borderwidth=0)
        self.logo_label.pack(side="left", padx=12, pady=6)
        prefs = tk.Frame(self.banner, background=BANNER_BACKGROUND)
        prefs.pack(side="right", anchor="n", padx=12, pady=10)
        self.language_var = tk.StringVar(value=LANGUAGES[i18n.get_language()])
        self.language_box = ttk.Combobox(prefs, textvariable=self.language_var, state="readonly", width=10,
                                         values=list(LANGUAGES.values()))
        self.language_box.pack(side="right")
        tk.Label(prefs, text=t("language"), background=BANNER_BACKGROUND, foreground=BANNER_FOREGROUND).pack(
            side="right", padx=(16, 4))
        self.theme_var = tk.StringVar(value=t(f"theme_{self._theme()}"))
        self.theme_box = ttk.Combobox(prefs, textvariable=self.theme_var, state="readonly", width=10,
                                      values=[t(f"theme_{key}") for key in THEME_KEYS])
        self.theme_box.pack(side="right")
        tk.Label(prefs, text=t("theme"), background=BANNER_BACKGROUND, foreground=BANNER_FOREGROUND).pack(
            side="right", padx=(0, 4))
        self.language_box.bind("<<ComboboxSelected>>", lambda _e: self._on_language_selected())
        self.theme_box.bind("<<ComboboxSelected>>", lambda _e: self._on_theme_selected())

        right = self.body  # tout le reste sous la bannière, sur toute la largeur
        top = ttk.Frame(right)
        top.pack(fill="x", padx=10, pady=(6, 0))
        self.path_label = ttk.Label(top, text=t("install_folder"))
        self.path_label.pack(side="left")
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(top, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.browse_button = ttk.Button(top, text=t("browse"), command=self._browse)
        self.browse_button.pack(side="left")
        self.scope_button = ttk.Button(top, text=t("scope_button"), command=self.open_scope_window)
        self.scope_button.pack(side="left", padx=(6, 0))

        self.validation = tk.Label(right, text="", fg=palette()["warn"], anchor="w")
        self.validation.pack(fill="x", padx=10)

        gpu_row = ttk.Frame(right)
        gpu_row.pack(fill="x", padx=10, pady=(2, 0))
        ttk.Label(gpu_row, text=t("gpu_label")).pack(side="left")
        self.gpu_var = tk.StringVar()
        self.gpu_box = ttk.Combobox(gpu_row, textvariable=self.gpu_var, state="readonly", width=48)
        self.gpu_box.pack(side="left", padx=6)
        self.gpu_box.bind("<<ComboboxSelected>>", lambda _e: self._on_gpu_selected())
        self.gpu_manual_button = ttk.Button(gpu_row, text=t("gpu_manual_button"), command=self._ask_manual_vram)
        self.gpu_manual_button.pack(side="left")
        tk.Label(right, text=t("vram_hint"), fg=palette()["vram"], anchor="w", justify="left",
                 wraplength=1100).pack(fill="x", padx=10)

        shortcut_row = ttk.Frame(self.body)
        shortcut_row.pack(fill="x", padx=10, pady=(4, 0))
        self.shortcut_button = ttk.Button(shortcut_row, text=t("create_shortcut"),
                                          command=self.create_desktop_shortcut,
                                          state="disabled" if self.shortcut_present else "normal")
        self.shortcut_button.pack(side="left")

        status = ttk.Frame(self.body)
        status.pack(fill="x", padx=10, pady=4)
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=200)
        self.progress.pack(side="left")
        self.step_label = ttk.Label(status, text="")
        self.step_label.pack(side="left", padx=8)

        summary = ttk.Frame(self.body)
        summary.pack(fill="x", padx=10, pady=(0, 6))
        self.summary_label = ttk.Label(summary, text=t("summary_start"), justify="left")
        self.summary_label.pack(side="left")
        self.details_button = ttk.Button(summary, text=t("details"), command=self._details, state="disabled")
        self.details_button.pack(side="right")

        self.notebook = ttk.Notebook(self.body)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.used_tab = UsedTab(self.notebook)
        self.unused_tab = UnusedTab(self.notebook, self._delete, self.extra_workflow_dirs)
        self.duplicates_tab = DuplicatesTab(self.notebook, self._delete, self.run_background, self.set_busy)
        self.junk_tab = JunkTab(self.notebook, self._delete, self._save_patterns)
        self.tabs = [self.used_tab, self.unused_tab, self.duplicates_tab, self.junk_tab]
        for tab, key in zip(self.tabs, ["tab_used", "tab_unused", "tab_duplicates", "tab_junk"]):
            self.notebook.add(tab, text=t(key))

        self.path_var.trace_add("write", lambda *_: self._on_path_change())
        self._refresh_gpu_choices()

    # ----- raccourci sur le bureau ----------------------------------------

    def _offer_shortcut(self) -> None:
        """Premier lancement : propose le raccourci, une seule fois quelle que soit la réponse."""
        self.settings["desktop_shortcut_asked"] = True
        save_settings(self.settings)
        if ask_choice(self, t("shortcut_title"), t("offer_shortcut"), t("offer_yes"), t("offer_no")):
            self.create_desktop_shortcut()

    def create_desktop_shortcut(self) -> None:
        try:
            path = create_shortcut()
        except OSError as exc:
            message = exc.args[0] if exc.args else exc
            messagebox.showerror(t("shortcut_title"), t("shortcut_failed", error=message), parent=self)
            return
        self.shortcut_present = True
        self.shortcut_button.configure(state="disabled")
        messagebox.showinfo(t("shortcut_title"), t("shortcut_created", path=path), parent=self)

    # ----- carte vidéo --------------------------------------------------

    def _gpu_choices(self) -> list:
        """(identifiant, libellé) des cartes détectées, plus la saisie manuelle si elle existe."""
        choices = [(g.name, t("gpu_entry", name=g.name, size=format_size(g.memory))) for g in self.gpus]
        manual = int(self.settings.get("vram_manual") or 0)
        if manual > 0:
            choices.append((MANUAL_GPU, t("gpu_manual_entry", size=format_size(manual))))
        return choices

    def _selected_gpu(self) -> str | None:
        ids = [gpu_id for gpu_id, _ in self._gpu_choices()]
        wanted = self.settings.get("gpu", "")
        if wanted in ids:
            return wanted
        return ids[0] if ids else None

    def vram(self) -> int | None:
        """Mémoire vidéo de référence en octets, ou None si inconnue."""
        selected = self._selected_gpu()
        if selected == MANUAL_GPU:
            return int(self.settings.get("vram_manual") or 0) or None
        for g in self.gpus:
            if g.name == selected:
                return g.memory
        return None

    def _refresh_gpu_choices(self) -> None:
        choices = self._gpu_choices()
        self.gpu_box.configure(values=[label for _, label in choices])
        selected = self._selected_gpu()
        labels = dict(choices)
        self.gpu_var.set(labels.get(selected, t("gpu_none")))
        for tab in self.tabs:
            tab.set_vram(self.vram())

    def _on_gpu_selected(self) -> None:
        by_label = {label: gpu_id for gpu_id, label in self._gpu_choices()}
        if self.gpu_var.get() in by_label:
            self.select_gpu(by_label[self.gpu_var.get()])

    def select_gpu(self, gpu_id: str) -> None:
        self.settings["gpu"] = gpu_id
        save_settings(self.settings)
        self._refresh_gpu_choices()

    def set_manual_vram(self, size: int) -> None:
        self.settings["vram_manual"] = int(size)
        self.settings["gpu"] = MANUAL_GPU
        save_settings(self.settings)
        self._refresh_gpu_choices()

    def _ask_manual_vram(self) -> None:
        value = simpledialog.askfloat(t("gpu_manual_title"), t("gpu_manual_prompt"), parent=self,
                                      minvalue=0.1, maxvalue=4096)
        if value:
            self.set_manual_vram(int(value * 1024 ** 3))

    # ----- langue et thème ----------------------------------------------

    def _on_language_selected(self) -> None:
        code = next(c for c, name in LANGUAGES.items() if name == self.language_var.get())
        self.set_language(code)

    def _on_theme_selected(self) -> None:
        labels = {t(f"theme_{key}"): key for key in THEME_KEYS}
        self.set_theme(labels.get(self.theme_var.get(), "light"))

    def set_language(self, code: str) -> None:
        if self.busy:
            return
        i18n.set_language(code)
        self.settings["language"] = i18n.get_language()
        save_settings(self.settings)
        self.rebuild()

    def set_theme(self, theme: str) -> None:
        if self.busy:
            return
        self.settings["theme"] = theme if theme in THEME_KEYS else "light"
        save_settings(self.settings)
        self.rebuild()

    def rebuild(self) -> None:
        """Reconstruit l'interface (langue ou thème) en réaffichant les résultats ; les coches sont remises à zéro."""
        path = self.path_var.get()
        tab_index = self.notebook.index("current") if self.notebook.tabs() else 0
        duplicate_groups = self.duplicates_tab.groups
        junk = list(self.junk_tab.junk)
        reopen_scope = self.scope_window is not None
        if reopen_scope:
            self.scope_window.close()
        self._retire_variables()
        self.body.destroy()

        apply_style(self, self._theme())
        self._build()
        self.path_var.set(path)
        self.junk_tab.set_patterns(self.settings.get("junk_patterns", []))
        if self.result is not None:
            for tab in self.tabs:
                tab.show(self.result)
            self.junk_tab.show(self.result, junk)
            if duplicate_groups is not None:
                self.duplicates_tab.show(self.result, duplicate_groups)
            self._show_summary(self.result)
        self.notebook.select(tab_index)
        if reopen_scope:
            self.open_scope_window()

    def _retire_variables(self) -> None:
        """Conserve les variables Tk de l'interface courante avant sa destruction."""
        _RETIRED.extend(value for value in vars(self).values() if isinstance(value, tk.Variable))
        for tab in getattr(self, "tabs", []):
            _RETIRED.extend(value for value in vars(tab).values() if isinstance(value, tk.Variable))

    def destroy(self) -> None:
        self._retire_variables()
        super().destroy()

    # ----- état ---------------------------------------------------------

    def _validate(self) -> bool:
        path = self.path_var.get().strip()
        message = t("path_missing") if not path else validate_comfyui(Path(path))
        self.validation.configure(text=localized(message) if message else "")
        state = "disabled" if self.busy else "normal"
        self.scope_button.configure(state=state)
        self.language_box.configure(state="disabled" if self.busy else "readonly")
        self.theme_box.configure(state="disabled" if self.busy else "readonly")
        return message is None

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.browse_button.configure(state=state)
        self.path_entry.configure(state=state)
        if self.scope_window is not None:
            self.scope_window.set_busy(busy)
        for tab in self.tabs:
            tab.set_enabled(not busy)
        self._validate()

    # ----- dossiers de workflows et périmètre ------------------------------

    def comfy_path(self) -> Path:
        return Path(self.path_var.get().strip())

    def extra_workflow_dirs(self) -> list:
        return [str(p) for p in self.settings.get("extra_workflow_dirs", [])]

    def _on_path_change(self) -> None:
        self._validate()
        self._refresh_scope_window()

    def _refresh_scope_window(self) -> None:
        if self.scope_window is not None:
            self.scope_window.refresh()

    def add_workflow_dir(self, folder: str) -> None:
        folder = str(Path(folder))
        current = self.extra_workflow_dirs()
        if os.path.normcase(folder) not in {os.path.normcase(f) for f in current}:
            self.settings["extra_workflow_dirs"] = current + [folder]
            save_settings(self.settings)
        self._refresh_scope_window()

    def remove_workflow_dirs(self, folders: list) -> None:
        removed = {os.path.normcase(str(f)) for f in folders}
        self.settings["extra_workflow_dirs"] = [
            f for f in self.extra_workflow_dirs() if os.path.normcase(f) not in removed
        ]
        save_settings(self.settings)
        self._refresh_scope_window()

    def open_scope_window(self):
        """Ouvre (ou ramène au premier plan) la fenêtre du périmètre, à droite de la fenêtre principale."""
        if self.scope_window is None:
            self.scope_window = ScopeWindow(self, self._scope_geometry)
            self.scope_window.set_busy(self.busy)
        else:
            self.scope_window.lift()
        return self.scope_window

    def scope_window_closed(self, window) -> None:
        if self.scope_window is window:
            try:
                self._scope_geometry = window.geometry()
            except tk.TclError:
                pass
            self.scope_window = None

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
        messagebox.showerror(t("error_title"), t("error_unexpected", error=exc), parent=self)

    # ----- actions ------------------------------------------------------

    def _browse(self) -> None:
        folder = filedialog.askdirectory(parent=self, title=t("browse_title"),
                                         initialdir=self.path_var.get() or None)
        if folder:
            self.path_var.set(str(Path(folder)))

    def _save_patterns(self, patterns: list) -> None:
        self.settings["junk_patterns"] = list(patterns)
        save_settings(self.settings)

    def _analyze(self, excluded_dirs: set = frozenset()) -> None:
        self.start_analysis(excluded_dirs)

    def start_analysis(self, excluded_dirs: set = frozenset()) -> None:
        if self.busy or not self._validate():
            return
        comfy = Path(self.path_var.get().strip())
        self.settings["comfyui_path"] = str(comfy)
        save_settings(self.settings)
        patterns = list(self.junk_tab.patterns)
        extra_dirs = self.extra_workflow_dirs()
        excluded = set(excluded_dirs)
        self.set_busy(True)
        self.progress.start(12)

        def on_done(result):
            self.progress.stop()
            self.step_label.configure(text=t("analysis_done"))
            self.result = result
            for tab in self.tabs:
                tab.show(result)
            self._show_summary(result)
            self.set_busy(False)

        self.run_background(
            lambda report: run_analysis(comfy, patterns, progress=report, extra_workflow_dirs=extra_dirs,
                                        excluded_dirs=excluded),
            lambda label: self.step_label.configure(text=localized(label)),
            on_done,
        )

    def _show_summary(self, result) -> None:
        wf, roots, usage = result.workflows, result.roots, result.usage
        unused_bytes = sum(f.size for f in usage.unused)
        lines = [
            t("summary_line1", read=wf.workflow_count, skipped=len(wf.skipped), dirs=len(roots.dirs),
              missing=len(roots.missing)),
            t("summary_line2", count=len(result.inventory.files), size=format_size(result.total_bytes),
              used=len(usage.used), unused=len(usage.unused), unused_size=format_size(unused_bytes)),
        ]
        excluded = len(result.excluded_model_dirs) + len(result.excluded_workflow_sources)
        if excluded:
            lines.append(t("summary_excluded", count=excluded))
        if roots.warnings or result.inventory.errors:
            lines.append(t("summary_warnings"))
        self.summary_label.configure(text="\n".join(lines))
        self.details_button.configure(state="normal")

    def _details(self) -> None:
        if self.result is None:
            return
        r = self.result

        def describe(d) -> str:
            return f"  [{d.category}] {d.path}  ({localized(origin_label(d.origin))})"

        lines = [t("details_workflows")]
        lines += [
            f"  {src.path}  ({localized(origin_label(src.origin))}"
            f"{'' if src.exists else t('suffix_missing')}"
            f"{t('suffix_unchecked') if src in r.excluded_workflow_sources else ''})"
            for src in r.workflow_sources
        ]
        lines += ["", t("details_dirs")] + [describe(d) for d in r.roots.dirs]
        if r.excluded_model_dirs:
            lines += ["", t("details_excluded")] + [describe(d) for d in r.excluded_model_dirs]
        if r.roots.missing:
            lines += ["", t("details_missing")] + [describe(d) for d in r.roots.missing]
        if r.workflows.skipped:
            lines += ["", t("details_skipped")]
            lines += [f"  {path} — {localized(reason)}" for path, reason in r.workflows.skipped]
        if r.roots.warnings:
            lines += ["", t("details_warnings")] + [f"  {localized(w)}" for w in r.roots.warnings]
        if r.inventory.errors:
            lines += ["", t("details_errors")] + [f"  {e}" for e in r.inventory.errors]
        show_details(self, t("details_title"), lines)

    def _delete(self, items: list, checker_factory: Callable, notes: list) -> None:
        if self.busy or not items:
            return
        total = sum(item.size for item in items)
        if not confirm_deletion(self, [item.path for item in items], total, notes):
            return
        keys = {item: file_key(item.path) for item in items}
        log_path = settings_dir() / LOG_FILE
        self.set_busy(True)
        self.step_label.configure(text=t("deleting"))

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
