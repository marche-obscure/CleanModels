"""Mise en forme des valeurs affichées."""

from .. import i18n

# Unités et séparateur décimal par langue.
_UNITS = {
    "fr": (("o", "Ko", "Mo", "Go", "To"), ","),
    "en": (("B", "KB", "MB", "GB", "TB"), "."),
    "de": (("B", "KB", "MB", "GB", "TB"), ","),
}


def format_size(n: int) -> str:
    """Taille lisible en base 1024, une décimale, dans la langue courante."""
    units, decimal = _UNITS.get(i18n.get_language(), _UNITS["fr"])
    if n < 1024:
        return f"{n} {units[0]}"
    value = float(n)
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024
        unit += 1
    return f"{value:.1f}".replace(".", decimal) + f" {units[unit]}"
