"""Génère les images de l'application à partir des sources (outil de développement).

Nécessite Pillow (`pip install pillow`), mais UNIQUEMENT pour régénérer les fichiers :
l'application elle-même lit les PNG/ICO produits avec la seule bibliothèque standard.

    py -3 tools/make_assets.py              # régénère PNG et ICO (avec la mention de droits)
    py -3 tools/make_assets.py --tag F.webp # ajoute la mention de droits à un WebP, sans réencodage
"""

import struct
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "source"
ASSETS = ROOT / "assets"
SENTINEL = (255, 0, 255)

AUTHOR = "marche-obscure"
COPYRIGHT = "© 2026 marche-obscure — All rights reserved"
EXIF_ARTIST, EXIF_COPYRIGHT = 0x013B, 0x8298
WEBP_EXIF_FLAG, WEBP_XMP_FLAG = 0x08, 0x04
XMP_PACKET = f"""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/">
   <dc:creator><rdf:Seq><rdf:li>{AUTHOR}</rdf:li></rdf:Seq></dc:creator>
   <dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{COPYRIGHT}</rdf:li></rdf:Alt></dc:rights>
   <xmpRights:Marked>True</xmpRights:Marked>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>""".encode("utf-8")


def _exif_tiff() -> bytes:
    """Bloc EXIF (TIFF petit-boutiste) avec Artist et Copyright ; texte en UTF-8."""
    entries = [(EXIF_ARTIST, AUTHOR.encode("utf-8") + b"\0"), (EXIF_COPYRIGHT, COPYRIGHT.encode("utf-8") + b"\0")]
    data_offset = 8 + 2 + 12 * len(entries) + 4
    ifd, data = struct.pack("<H", len(entries)), b""
    for tag, value in entries:
        ifd += struct.pack("<HHII", tag, 2, len(value), data_offset + len(data))
        data += value
    return b"II*\0" + struct.pack("<I", 8) + ifd + struct.pack("<I", 0) + data


def _png_info() -> PngInfo:
    info = PngInfo()
    info.add_text("Author", AUTHOR)
    info.add_itxt("Copyright", COPYRIGHT)  # iTXt : UTF-8, pour « © » et « — »
    return info


def _save_png(image: Image.Image, path: Path) -> None:
    image.save(path, optimize=True, pnginfo=_png_info())


def tag_webp(path: Path) -> None:
    """Ajoute (ou remplace) les blocs EXIF et XMP auteur/droits d'un WebP sans toucher à l'image."""
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"{path} n'est pas un WebP")
    chunks, pos = [], 12
    while pos + 8 <= len(data):
        tag, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        chunks.append([tag, data[pos + 8:pos + 8 + size]])
        pos += 8 + size + (size & 1)
    if chunks[0][0] != b"VP8X":
        # WebP simple : on ajoute l'en-tête étendu (drapeaux + dimensions du canevas moins 1, sur 24 bits).
        width, height = Image.open(path).size
        vp8x = bytes(4) + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
        chunks.insert(0, [b"VP8X", vp8x])
    chunks = [c for c in chunks if c[0] not in (b"EXIF", b"XMP ")]
    chunks += [[b"EXIF", _exif_tiff()], [b"XMP ", XMP_PACKET]]
    header = bytearray(chunks[0][1])
    header[0] |= WEBP_EXIF_FLAG | WEBP_XMP_FLAG
    chunks[0][1] = bytes(header)
    body = b"".join(tag + struct.pack("<I", len(content)) + content + (b"\x00" if len(content) & 1 else b"")
                    for tag, content in chunks)
    path.write_bytes(b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WEBP" + body)


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
    _save_png(logo.resize((120, 120), Image.LANCZOS), ASSETS / "cleanmodels_logo.png")
    _save_png(logo.resize((320, 320), Image.LANCZOS), ASSETS / "cleanmodels_readme.png")


def make_icon() -> None:
    icon = _square(_remove_white_background(SOURCE / "icon_source.webp"))
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.resize((256, 256), Image.LANCZOS).save(ASSETS / "cleanmodels.ico", sizes=sizes)
    _save_png(icon.resize((64, 64), Image.LANCZOS), ASSETS / "cleanmodels_icon64.png")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--tag":
        for name in sys.argv[2:]:
            tag_webp(Path(name))
            print("mention ajoutée :", name)
        sys.exit(0)
    for source in sorted(SOURCE.glob("*.webp")):
        tag_webp(source)
    make_logo()
    make_icon()
    for path in sorted(ASSETS.glob("cleanmodels*")):
        print(path.name, path.stat().st_size, "octets")
