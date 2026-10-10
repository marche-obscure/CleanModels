import json
import unittest

from cleanmodels.constants import DEFAULT_JUNK_PATTERNS
from cleanmodels.settings import load_settings, save_settings, settings_dir
from tests.helpers import TempHomeMixin


class SettingsTest(TempHomeMixin, unittest.TestCase):
    def test_defaults_when_missing(self):
        self.assertEqual(
            load_settings(),
            ({"config_version": 2, "comfyui_path": "", "junk_patterns": list(DEFAULT_JUNK_PATTERNS),
              "extra_workflow_dirs": [], "language": "fr", "theme": "light",
              "gpu": "", "vram_manual": 0}, None),
        )

    def test_roundtrip_keeps_unknown_keys(self):
        data = {"config_version": 2, "comfyui_path": "D:/ComfyUI", "junk_patterns": ["*.tmp"],
                "extra_workflow_dirs": ["E:/wf"], "language": "de", "theme": "dark",
                "gpu": "Carte A", "vram_manual": 0, "future_key": 42}
        save_settings(data)
        self.assertEqual(load_settings(), (data, None))

    def test_missing_key_gets_default(self):
        (self.tmp / "settings.json").write_text(json.dumps({"config_version": 1}), encoding="utf-8")
        data, warning = load_settings()
        self.assertEqual(data["junk_patterns"], list(DEFAULT_JUNK_PATTERNS))
        self.assertIsNone(warning)

    def test_corrupt_file_is_backed_up(self):
        (self.tmp / "settings.json").write_text("{pas du json", encoding="utf-8")
        data, warning = load_settings()
        self.assertEqual(data["junk_patterns"], list(DEFAULT_JUNK_PATTERNS))
        self.assertIsNotNone(warning)
        self.assertEqual((self.tmp / "settings.json.bak").read_text(encoding="utf-8"), "{pas du json")

    def test_settings_dir_uses_env(self):
        self.assertEqual(settings_dir(), self.tmp)


if __name__ == "__main__":
    unittest.main()
