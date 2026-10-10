import os
import unittest

from cleanmodels.roots import ModelDir, collect_model_dirs, validate_comfyui, workflows_dir
from tests.helpers import TempHomeMixin, make_comfy


def _real(path):
    return os.path.normcase(os.path.realpath(path))


class RootsTest(TempHomeMixin, unittest.TestCase):
    def _dirs(self, result):
        return {(d.category, _real(d.path), d.origin) for d in result.dirs}

    def test_validate_ok(self):
        comfy = make_comfy(self.tmp, {})
        self.assertIsNone(validate_comfyui(comfy))
        self.assertEqual(workflows_dir(comfy), comfy / "user" / "default" / "workflows")

    def test_validate_missing_workflows(self):
        comfy = self.tmp / "ComfyUI"
        (comfy / "models").mkdir(parents=True)
        message = validate_comfyui(comfy)
        self.assertIsNotNone(message)
        self.assertIn("user/default/workflows", message)

    def test_validate_not_a_dir(self):
        self.assertIsNotNone(validate_comfyui(self.tmp / "absent"))

    def test_models_dir_filtered_to_categories(self):
        comfy = make_comfy(self.tmp, {
            "models/checkpoints/a.safetensors": b"a",
            "models/loras/b.safetensors": b"b",
            "models/VAE/c.pt": b"c",
        })
        result = collect_model_dirs(comfy)
        self.assertEqual(self._dirs(result), {
            ("checkpoints", _real(comfy / "models" / "checkpoints"), "models"),
            ("vae", _real(comfy / "models" / "VAE"), "models"),
        })

    def test_yaml_relative_to_base_path(self):
        ext = self.tmp / "ext"
        (ext / "m" / "unet").mkdir(parents=True)
        comfy = make_comfy(self.tmp, {
            "extra_model_paths.yaml": (
                f"extra:\n  base_path: {ext.as_posix()}/\n  unet: |\n    m/unet\n    n/unet\n"
                "  loras: l\n  is_default: true\n"
            ),
        })
        result = collect_model_dirs(comfy)
        self.assertIn(("unet", _real(ext / "m" / "unet"), "yaml:extra"), self._dirs(result))
        self.assertEqual([_real(d.path) for d in result.missing], [_real(ext / "n" / "unet")])
        self.assertFalse(any(d.category == "loras" for d in result.dirs + result.missing))

    def test_yaml_without_base_path_is_relative_to_comfy(self):
        comfy = make_comfy(self.tmp, {
            "other/ckpt/x.safetensors": b"x",
            "extra_model_paths.yaml": "extra:\n  checkpoints: other/ckpt\n",
        })
        result = collect_model_dirs(comfy)
        self.assertIn(("checkpoints", _real(comfy / "other" / "ckpt"), "yaml:extra"), self._dirs(result))

    def test_yaml_windows_paths_crlf(self):
        ext = self.tmp / "ext"
        (ext / "models" / "vae").mkdir(parents=True)
        base = str(ext).replace("/", "\\") + "\\"
        comfy = make_comfy(self.tmp, {})
        (comfy / "extra_model_paths.yaml").write_bytes(
            f"win:\r\n  base_path: {base}\r\n  vae: models\\vae\r\n".encode("utf-8")
        )
        result = collect_model_dirs(comfy)
        self.assertIn(("vae", _real(ext / "models" / "vae"), "yaml:win"), self._dirs(result))
        self.assertEqual(result.missing, [])

    def test_yaml_invalid_falls_back(self):
        comfy = make_comfy(self.tmp, {
            "models/vae/v.pt": b"v",
            "extra_model_paths.yaml": "s:\n  a: 1\n b: 2\n",
        })
        result = collect_model_dirs(comfy)
        self.assertEqual(self._dirs(result), {("vae", _real(comfy / "models" / "vae"), "models")})
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("extra_model_paths.yaml", result.warnings[0])

    def test_same_dir_declared_twice_listed_once(self):
        comfy = make_comfy(self.tmp, {"models/checkpoints/a.safetensors": b"a"})
        (comfy / "extra_model_paths.yaml").write_text(
            f"dup:\n  base_path: {comfy.as_posix()}\n  checkpoints: models/checkpoints\n", encoding="utf-8"
        )
        result = collect_model_dirs(comfy)
        self.assertEqual(len(result.dirs), 1)
        self.assertIsInstance(result.dirs[0], ModelDir)


if __name__ == "__main__":
    unittest.main()
