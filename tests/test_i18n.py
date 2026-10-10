import re
import string
import unittest
from pathlib import Path

from cleanmodels import i18n
from cleanmodels.i18n import LANGUAGES, TEXTS, Message, localized, set_language, t

SOURCE = Path(__file__).resolve().parent.parent / "cleanmodels"


def _fields(text: str) -> set:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class I18nTest(unittest.TestCase):
    def tearDown(self):
        set_language("fr")

    def test_languages(self):
        self.assertEqual(LANGUAGES, {"fr": "Français", "en": "English", "de": "Deutsch"})
        self.assertEqual(i18n.DEFAULT_LANGUAGE, "fr")

    def test_same_keys_in_every_language(self):
        for code in LANGUAGES:
            self.assertEqual(set(TEXTS[code]), set(TEXTS["fr"]), code)

    def test_same_placeholders_in_every_language(self):
        for key, text in TEXTS["fr"].items():
            for code in LANGUAGES:
                self.assertEqual(_fields(TEXTS[code][key]), _fields(text), f"{code}:{key}")

    def test_every_key_used_in_code_exists(self):
        pattern = re.compile(r"""\b(?:t|tn|Message)\(\s*["']([a-z0-9_]+)["']""")
        used = set()
        for path in SOURCE.rglob("*.py"):
            used |= set(pattern.findall(path.read_text(encoding="utf-8")))
        self.assertTrue(used)
        self.assertEqual(sorted(k for k in used if k not in TEXTS["fr"]
                                and k + "_one" not in TEXTS["fr"]), [])

    def test_translation_switches(self):
        self.assertEqual(t("browse"), "Parcourir…")
        set_language("en")
        self.assertEqual(t("browse"), "Browse…")
        set_language("de")
        self.assertEqual(t("browse"), "Durchsuchen…")

    def test_unknown_language_falls_back_to_french(self):
        set_language("xx")
        self.assertEqual(i18n.get_language(), "fr")

    def test_plural(self):
        self.assertEqual(i18n.tn("files_count", 1, size="1 o"), "1 fichier – 1 o")
        self.assertEqual(i18n.tn("files_count", 2, size="2 o"), "2 fichiers – 2 o")

    def test_message_is_french_text_but_localizes(self):
        message = Message("reason_missing")
        self.assertEqual(message, "fichier introuvable")
        set_language("en")
        self.assertEqual(message, "fichier introuvable")
        self.assertEqual(localized(message), "file not found")
        self.assertEqual(localized("texte simple"), "texte simple")

    def test_nested_message_localizes(self):
        message = Message("detail_missing", origin=Message("origin_added"))
        self.assertEqual(message, "ajouté — introuvable")
        set_language("en")
        self.assertEqual(localized(message), "added — not found")

    def test_format_size_follows_language(self):
        from cleanmodels.gui.format import format_size

        self.assertEqual(format_size(1536), "1,5 Ko")
        set_language("en")
        self.assertEqual(format_size(1536), "1.5 KB")
        self.assertEqual(format_size(10), "10 B")
        set_language("de")
        self.assertEqual(format_size(1536), "1,5 KB")


if __name__ == "__main__":
    unittest.main()
