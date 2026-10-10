import os
import unittest

from cleanmodels.inventory import file_key, scan_models
from cleanmodels.roots import ModelDir
from tests.helpers import TempHomeMixin, make_comfy


class InventoryTest(TempHomeMixin, unittest.TestCase):
    def test_lists_model_extensions_recursively(self):
        comfy = make_comfy(self.tmp, {
            "models/checkpoints/a.safetensors": b"aaa",
            "models/checkpoints/sub/b.GGUF": b"bbbbb",
            "models/checkpoints/readme.txt": b"r",
        })
        root = comfy / "models" / "checkpoints"
        result = scan_models([ModelDir("checkpoints", root, "models")])
        by_name = {f.path.name: f for f in result.files}
        self.assertEqual(set(by_name), {"a.safetensors", "b.GGUF"})
        self.assertEqual(by_name["b.GGUF"].rel_path, os.path.join("sub", "b.GGUF"))
        self.assertEqual(by_name["b.GGUF"].size, 5)
        self.assertEqual(by_name["a.safetensors"].category, "checkpoints")
        self.assertEqual(by_name["a.safetensors"].root, root)
        self.assertEqual(result.errors, [])

    def test_llm_multifile_each_listed(self):
        comfy = make_comfy(self.tmp, {
            "models/LLM/qwen/model-00001.safetensors": b"1",
            "models/LLM/qwen/model-00002.safetensors": b"2",
            "models/LLM/qwen/config.json": "{}",
        })
        result = scan_models([ModelDir("LLM", comfy / "models" / "LLM", "models")])
        self.assertEqual(len(result.files), 2)

    def test_symlinked_dir_counted_once(self):
        comfy = make_comfy(self.tmp, {"models/vae/v.pt": b"v", "models/vae/w.pt": b"w"})
        real = comfy / "models" / "vae"
        link = self.tmp / "vae_link"
        try:
            os.symlink(real, link, target_is_directory=True)
        except OSError:
            try:
                import _winapi
                _winapi.CreateJunction(str(real), str(link))
            except (ImportError, OSError):
                self.skipTest("ni lien symbolique ni jonction possible")
        result = scan_models([
            ModelDir("vae", real, "models"),
            ModelDir("vae", link, "yaml:x"),
        ])
        self.assertEqual(sorted(f.path.name for f in result.files), ["v.pt", "w.pt"])

    def test_hardlink_counted_once(self):
        comfy = make_comfy(self.tmp, {"models/vae/v.pt": b"v"})
        folder = comfy / "models" / "vae"
        os.link(folder / "v.pt", folder / "v_copy.pt")
        result = scan_models([ModelDir("vae", folder, "models")])
        self.assertEqual(len(result.files), 1)
        self.assertEqual(result.aliases, [("v_copy.pt", result.files[0])])

    def test_file_key_normalizes(self):
        comfy = make_comfy(self.tmp, {"models/vae/v.pt": b"v"})
        path = comfy / "models" / "vae" / "v.pt"
        self.assertEqual(file_key(path), os.path.normcase(os.path.realpath(path)))


if __name__ == "__main__":
    unittest.main()
