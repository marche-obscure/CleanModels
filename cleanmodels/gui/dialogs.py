"""Fenêtres modales : confirmation de suppression, détails, bilan."""

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ..i18n import localized, t, tn
from .format import format_size
from .style import palette


def _modal(parent, title: str) -> tk.Toplevel:
    window = tk.Toplevel(parent)
    window.title(title)
    window.transient(parent)
    window.minsize(700, 360)
    window.columnconfigure(0, weight=1)
    return window


def _scrolled_text(window, lines: list, row: int) -> None:
    frame = ttk.Frame(window)
    frame.grid(row=row, column=0, sticky="nsew", padx=12, pady=6)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    text = tk.Text(frame, wrap="none", height=14, width=90)
    yscroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    xscroll = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
    text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
    text.insert("1.0", "\n".join(localized(line) for line in lines))
    text.configure(state="disabled")
    text.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    xscroll.grid(row=1, column=0, sticky="ew")
    window.rowconfigure(row, weight=1)


def confirm_deletion(parent, paths: list, total_bytes: int, notes: list) -> bool:
    """Demande une confirmation explicite ; « Annuler » est le choix par défaut."""
    window = _modal(parent, t("confirm_title"))
    answer = {"value": False}
    danger = palette()["warn"]

    ttk.Label(
        window,
        text=tn("files_count", len(paths), size=format_size(total_bytes)),
        font=("TkDefaultFont", 13, "bold"),
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
    tk.Label(window, text=t("delete_warning"), fg=danger, font=("TkDefaultFont", 12, "bold")).grid(
        row=1, column=0, sticky="w", padx=12
    )
    row = 2
    for note in notes:
        tk.Label(window, text=localized(note), fg=danger, justify="left", wraplength=640).grid(
            row=row, column=0, sticky="w", padx=12
        )
        row += 1
    _scrolled_text(window, [str(Path(p)) for p in paths], row)

    def close(value: bool) -> None:
        answer["value"] = value
        window.destroy()

    buttons = ttk.Frame(window)
    buttons.grid(row=row + 1, column=0, sticky="e", padx=12, pady=12)
    cancel = ttk.Button(buttons, text=t("cancel"), command=lambda: close(False), default="active")
    confirm = ttk.Button(buttons, text=t("confirm_delete"), command=lambda: close(True), style="Danger.TButton")
    confirm.grid(row=0, column=0, padx=(0, 8))
    cancel.grid(row=0, column=1)
    window.bind("<Escape>", lambda _e: close(False))
    window.bind("<Return>", lambda _e: close(False))
    window.protocol("WM_DELETE_WINDOW", lambda: close(False))
    cancel.focus_set()
    window.grab_set()
    parent.wait_window(window)
    return answer["value"]


def show_details(parent, title: str, lines: list) -> None:
    window = _modal(parent, title)
    _scrolled_text(window, lines, 0)
    ttk.Button(window, text=t("close"), command=window.destroy).grid(row=1, column=0, sticky="e", padx=12, pady=12)
    window.bind("<Escape>", lambda _e: window.destroy())


def show_report(parent, result) -> None:
    lines = [
        t("report_deleted", count=len(result.deleted)),
        t("report_refused", count=len(result.refused)),
        t("report_errors", count=len(result.errors)),
        t("report_freed", size=format_size(result.freed_bytes)),
    ]
    if result.refused:
        lines += ["", t("report_refused_list")]
        lines += [f"  {item.path} — {localized(reason)}" for item, reason in result.refused]
    if result.errors:
        lines += ["", t("report_errors_list")] + [f"  {item.path} — {message}" for item, message in result.errors]
    if result.log_errors:
        lines += ["", t("report_log_errors")] + [f"  {localized(message)}" for message in result.log_errors]
    show_details(parent, t("report_title"), lines)


def ask_choice(parent, title: str, message: str, yes_text: str, no_text: str) -> bool:
    """Question à deux boutons libellés ; « non » est le choix par défaut (Échap, fermeture)."""
    window = _modal(parent, title)
    window.minsize(420, 140)
    answer = {"value": False}
    ttk.Label(window, text=message, wraplength=520, justify="left").grid(
        row=0, column=0, sticky="w", padx=16, pady=(16, 8))

    def close(value: bool) -> None:
        answer["value"] = value
        window.destroy()

    buttons = ttk.Frame(window)
    buttons.grid(row=1, column=0, sticky="e", padx=16, pady=(4, 16))
    yes = ttk.Button(buttons, text=yes_text, command=lambda: close(True), style="Accent.TButton")
    no = ttk.Button(buttons, text=no_text, command=lambda: close(False))
    yes.grid(row=0, column=0, padx=(0, 8))
    no.grid(row=0, column=1)
    window.bind("<Escape>", lambda _e: close(False))
    window.protocol("WM_DELETE_WINDOW", lambda: close(False))
    yes.focus_set()
    window.grab_set()
    parent.wait_window(window)
    return answer["value"]
