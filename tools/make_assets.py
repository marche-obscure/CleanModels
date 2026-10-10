"""Génère les images de l'application à partir des sources (outil de développement).

Nécessite Pillow (`pip install pillow`), mais UNIQUEMENT pour régénérer les fichiers :
l'application elle-même lit les PNG/ICO produits avec la seule bibliothèque standard.

    py -3 tools/make_assets.py
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "source"
ASSETS = ROOT / "assets"
SENTINEL = (255, 0, 255)


def _remove_white_background(path: Path) -> Image.Image:
    """Rend transparent le blanc relié aux coins (le crème de l'image est conservé)."""
    image = Image.open(path).convert("RGB")
    filled = image.copy()
    w, h = filled.size
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if filled.getpixel(corner) != SENTINEL:
            ImageDraw.floodfill(filled, corner, SENTINEL, thresh=18)
    difference = ImageChops.difference(filled, Image.new("RGB", filled.size, SENTINEL)).convert("L")
    alpha = difference.point(lambda v: 0 if v == 0 else 255)
    # Bord adouci : évite le liseré blanc sur fond sombre.
    alpha = alpha.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(2))
    result = image.convert("RGBA")
    result.putalpha(alpha)
    return result.crop(alpha.getbbox())


def _square(image: Image.Image) -> Image.Image:
    side = max(image.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return canvas


def make_logo() -> None:
    logo = _square(_remove_white_background(SOURCE / "logo_source.webp"))
    logo.resize((120, 120), Image.LANCZOS).save(ASSETS / "cleanmodels_logo.png", optimize=True)
    logo.resize((320, 320), Image.LANCZOS).save(ASSETS / "cleanmodels_readme.png", optimize=True)


def make_icon() -> None:
    icon = _square(_remove_white_background(SOURCE / "icon_source.webp"))
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.resize((256, 256), Image.LANCZOS).save(ASSETS / "cleanmodels.ico", sizes=sizes)
    icon.resize((64, 64), Image.LANCZOS).save(ASSETS / "cleanmodels_icon64.png", optimize=True)


if __name__ == "__main__":
    make_logo()
    make_icon()
    for path in sorted(ASSETS.glob("cleanmodels*")):
        print(path.name, path.stat().st_size, "octets")
