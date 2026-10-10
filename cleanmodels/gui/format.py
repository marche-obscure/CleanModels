"""Mise en forme des valeurs affichées."""

_UNITS = ("o", "Ko", "Mo", "Go", "To")


def format_size(n: int) -> str:
    """Taille lisible en base 1024, une décimale, virgule française."""
    if n < 1024:
        return f"{n} o"
    value = float(n)
    unit = 0
    while value >= 1024 and unit < len(_UNITS) - 1:
        value /= 1024
        unit += 1
    return f"{value:.1f}".replace(".", ",") + f" {_UNITS[unit]}"
