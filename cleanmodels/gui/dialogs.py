"""Fenêtres modales : confirmation de suppression, détails, bilan."""

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .format import format_size

WARNING_TEXT = "Cette suppression est définitive et ne peut pas être annulée."
CANCEL_TEXT = "Annuler"
CONFIRM_TEXT = "Supprimer définitivement"
DANGER = "#b00020"


def _modal(parent, title: str) -> tk.Toplevel:
    window = tk.Toplevel(parent)
    window.title(title)
    window.transient(parent)
    window.minsize(560, 300)
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
    text.insert("1.0", "\n".join(lines))
    text.configure(state="disabled")
    text.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    xscroll.grid(row=1, column=0, sticky="ew")
    window.rowconfigure(row, weight=1)


def confirm_deletion(parent, paths: list, total_bytes: int, notes: list) -> bool:
    """Demande une confirmation explicite ; « Annuler » est le choix par défaut."""
    window = _modal(parent, "Confirmer la suppression")
    answer = {"value": False}

    count = len(paths)
    ttk.Label(
        window,
        text=f"{count} fichier{'s' if count > 1 else ''} – {format_size(total_bytes)}",
        font=("TkDefaultFont", 11, "bold"),
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
    tk.Label(window, text=WARNING_TEXT, fg=DANGER, font=("TkDefaultFont", 10, "bold")).grid(
        row=1, column=0, sticky="w", padx=12
    )
    row = 2
    for note in notes:
        tk.Label(window, text=note, fg=DANGER, justify="left", wraplength=640).grid(
            row=row, column=0, sticky="w", padx=12
        )
        row += 1
    _scrolled_text(window, [str(Path(p)) for p in paths], row)

    def close(value: bool) -> None:
        answer["value"] = value
        window.destroy()

    buttons = ttk.Frame(window)
    buttons.grid(row=row + 1, column=0, sticky="e", padx=12, pady=12)
    cancel = ttk.Button(buttons, text=CANCEL_TEXT, command=lambda: close(False), default="active")
    confirm = ttk.Button(buttons, text=CONFIRM_TEXT, command=lambda: close(True))
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
    ttk.Button(window, text="Fermer", command=window.destroy).grid(row=1, column=0, sticky="e", padx=12, pady=12)
    window.bind("<Escape>", lambda _e: window.destroy())


def show_report(parent, result) -> None:
    lines = [
        f"Supprimés : {len(result.deleted)}",
        f"Refusés : {len(result.refused)}",
        f"Erreurs : {len(result.errors)}",
        f"Espace libéré : {format_size(result.freed_bytes)}",
    ]
    if result.refused:
        lines += ["", "Refusés :"] + [f"  {item.path} — {reason}" for item, reason in result.refused]
    if result.errors:
        lines += ["", "Erreurs :"] + [f"  {item.path} — {message}" for item, message in result.errors]
    show_details(parent, "Bilan de la suppression", lines)
