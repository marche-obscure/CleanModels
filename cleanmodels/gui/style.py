"""Style global de l'interface : polices de 12 points et hauteurs de lignes adaptées."""

import tkinter.font as tkfont
from tkinter import ttk

FONT_SIZE = 12
_NAMED_FONTS = ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkFixedFont",
                "TkCaptionFont", "TkSmallCaptionFont", "TkTooltipFont", "TkIconFont")


def apply_style(root) -> None:
    for name in _NAMED_FONTS:
        try:
            tkfont.nametofont(name, root=root).configure(size=FONT_SIZE)
        except Exception:  # police nommée absente sur cette plateforme
            continue
    linespace = tkfont.nametofont("TkDefaultFont", root=root).metrics("linespace")
    style = ttk.Style(root)
    # Lignes assez hautes pour le texte et les cases à cocher de 18 pixels.
    style.configure("Treeview", rowheight=max(linespace + 10, 26))
    style.configure("Treeview.Heading", padding=(4, 4))
    style.configure("TNotebook.Tab", padding=(12, 4))
