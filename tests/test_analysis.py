import json
import unittest

from cleanmodels.analysis import run_analysis
from cleanmodels.constants import DEFAULT_JUNK_PATTERNS
from tests.helpers import TempHomeMixin, make_comfy


def workflow(*values):
    return json.dumps({"nodes": [{"id": i, "type": "Loader", "widgets_values": [v]} for i, v in enumerate(values)]})


class AnalysisTest(TempHomeMixin, unittest.TestCase):
    def test_end_to_end(self):
        ext = self.tmp / "ext"
        (ext / "unet").mkdir(parents=True)
        (ext / "unet" / "u.gguf").write_bytes(b"uuuu")
        comfy = make_comfy(self.tmp, {
            "models/checkpoints/used.safetensors": b"aa",
            "models/vae/unused.pt": b"bbb",
            "models/vae/x.part": b"p",
            "user/default/workflows/w1.json": workflow("used.safetensors"),
            "user/default/workflows/w2.json": workflow("used.safetensors", "a_lora.safetensors"),
            "user/default/workflows/broken.json": "{",
            "extra_model_paths.yaml": f"ext:\n  base_path: {ext.as_posix()}\n  unet: unet\n",
        })
        steps = []
        result = run_analysis(comfy, list(DEFAULT_JUNK_PATTERNS), progress=steps.append)
        self.assertEqual(len(result.usage.used), 1)
        self.assertEqual(result.usage.used[0].calls, 2)
        self.assertEqual(sorted(f.path.name for f in result.usage.unused), ["u.gguf", "unused.pt"])
        self.assertEqual(len(result.workflows.skipped), 1)
        self.assertEqual([j.path.name for j in result.junk], ["x.part"])
        self.assertEqual(len(steps), 5)
        self.assertEqual(result.total_bytes, 2 + 3 + 4)
        self.assertEqual(result.comfy, comfy)

    def test_llm_folder_and_hardlink_alias_count_as_used(self):
        import os

        comfy = make_comfy(self.tmp, {
            "models/LLM/Qwen2.5-VL/model.safetensors": b"q",
            "models/vae/real.pt": b"r",
            "user/default/workflows/w.json": workflow("Qwen2.5-VL", "alias.pt"),
        })
        os.link(comfy / "models" / "vae" / "real.pt", comfy / "models" / "vae" / "alias.pt")
        result = run_analysis(comfy, [])
        self.assertEqual(result.usage.unused, [])
        self.assertEqual(len(result.usage.used), 2)


if __name__ == "__main__":
    unittest.main()
