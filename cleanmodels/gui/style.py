"""Style global : polices de 12 points, thème « clam », palettes Clair et Sombre.

Le thème « clam » est nécessaire pour que les couleurs des boutons (Analyser en vert,
Supprimer en rouge) soient réellement affichées sous Windows.
"""

import tkinter.font as tkfont
from tkinter import ttk

FONT_SIZE = 12
_NAMED_FONTS = ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkFixedFont",
                "TkCaptionFont", "TkSmallCaptionFont", "TkTooltipFont", "TkIconFont")

LIGHT = {
    "bg": "#f3f3f3", "fg": "#1f1f1f", "field": "#ffffff", "heading": "#e4e4e4",
    "border": "#c4c4c4", "select": "#cce4ff", "select_fg": "#000000", "muted": "#5f6368",
    "accent": "#2e7d32", "accent_active": "#388e3c",
    "danger": "#d32f2f", "danger_active": "#e53935",
    "disabled_bg": "#d6d6d6", "disabled_fg": "#8a8a8a",
    "warn": "#b00020", "check": "#1a73e8", "vram": "#b35c00",
}
DARK = {
    "bg": "#1e1f22", "fg": "#e6e6e6", "field": "#2b2d31", "heading": "#34363b",
    "border": "#4a4d52", "select": "#2f4f7f", "select_fg": "#ffffff", "muted": "#a0a4aa",
    "accent": "#2e7d32", "accent_active": "#43a047",
    "danger": "#d32f2f", "danger_active": "#ef5350",
    "disabled_bg": "#3a3c40", "disabled_fg": "#7a7d82",
    "warn": "#ff6b6b", "check": "#4c8bf5", "vram": "#ffa94d",
}
THEMES = {"light": LIGHT, "dark": DARK}

_current = LIGHT


def palette() -> dict:
    return _current


def apply_style(root, theme: str = "light") -> None:
    """Applique polices et couleurs ; les widgets créés ensuite héritent des options tk."""
    global _current
    _current = THEMES.get(theme, LIGHT)
    p = _current

    for name in _NAMED_FONTS:
        try:
            tkfont.nametofont(name, root=root).configure(size=FONT_SIZE)
        except Exception:  # police nommée absente sur cette plateforme
            continue
    linespace = tkfont.nametofont("TkDefaultFont", root=root).metrics("linespace")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"],
                    bordercolor=p["border"], lightcolor=p["bg"], darkcolor=p["bg"],
                    troughcolor=p["heading"], selectbackground=p["select"], selectforeground=p["select_fg"],
                    insertcolor=p["fg"])
    style.map(".", foreground=[("disabled", p["disabled_fg"])])
    style.configure("TButton", background=p["heading"], padding=(10, 4))
    style.map("TButton", background=[("disabled", p["disabled_bg"]), ("active", p["border"])])
    style.configure("Accent.TButton", background=p["accent"], foreground="#ffffff",
                    font=("TkDefaultFont", FONT_SIZE, "bold"), padding=(16, 6))
    style.map("Accent.TButton",
              background=[("disabled", p["disabled_bg"]), ("active", p["accent_active"]), ("!disabled", p["accent"])],
              foreground=[("disabled", p["disabled_fg"]), ("!disabled", "#ffffff")])
    style.configure("Danger.TButton", font=("TkDefaultFont", FONT_SIZE, "bold"), padding=(14, 4))
    style.map("Danger.TButton",
              background=[("disabled", p["disabled_bg"]), ("active", p["danger_active"]), ("!disabled", p["danger"])],
              foreground=[("disabled", p["disabled_fg"]), ("!disabled", "#ffffff")])
    style.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"])
    style.configure("TCombobox", fieldbackground=p["field"], foreground=p["fg"], background=p["heading"],
                    arrowcolor=p["fg"])
    style.map("TCombobox", fieldbackground=[("readonly", p["field"])], foreground=[("readonly", p["fg"])])
    style.configure("Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"],
                    rowheight=max(linespace + 10, 26))
    style.map("Treeview", background=[("selected", p["select"])], foreground=[("selected", p["select_fg"])])
    style.configure("Treeview.Heading", background=p["heading"], foreground=p["fg"], padding=(4, 4))
    style.map("Treeview.Heading", background=[("active", p["border"])])
    style.configure("TNotebook", background=p["bg"])
    style.configure("TNotebook.Tab", background=p["heading"], foreground=p["fg"], padding=(12, 4))
    style.map("TNotebook.Tab", background=[("selected", p["bg"])])
    style.configure("TLabelframe", background=p["bg"])
    style.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"])
    style.configure("TProgressbar", background=p["check"], troughcolor=p["heading"])
    style.configure("TScrollbar", background=p["heading"], troughcolor=p["bg"], arrowcolor=p["fg"])

    # Widgets tk classiques (créés après cet appel).
    root.configure(background=p["bg"])
    for pattern, value in (
        ("*Toplevel.background", p["bg"]),
        ("*Label.background", p["bg"]),
        ("*Label.foreground", p["fg"]),
        ("*Text.background", p["field"]),
        ("*Text.foreground", p["fg"]),
        ("*Text.insertBackground", p["fg"]),
        ("*Listbox.background", p["field"]),
        ("*Listbox.foreground", p["fg"]),
        ("*TCombobox*Listbox.background", p["field"]),
        ("*TCombobox*Listbox.foreground", p["fg"]),
        ("*TCombobox*Listbox.selectBackground", p["select"]),
        ("*TCombobox*Listbox.selectForeground", p["select_fg"]),
    ):
        root.option_add(pattern, value)
