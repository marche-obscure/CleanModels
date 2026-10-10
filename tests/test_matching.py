import os
import unittest
from pathlib import Path

from cleanmodels.inventory import ModelFile
from cleanmodels.matching import FileIndex, match_usage, normalize
from cleanmodels.workflows import Reference

BASE = Path(os.path.abspath("fake_models"))


def model(category: str, rel: str, size: int = 1) -> ModelFile:
    root = BASE / category
    path = root / rel
    return ModelFile(path, path, category, os.path.normpath(rel), size, root)


def ref(value: str, workflow: str = "w1.json", node: str = "1") -> Reference:
    return Reference(value, Path(workflow), node, "Loader")


class MatchingTest(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("  Flux/Model.SafeTensors "), "flux\\model.safetensors")

    def test_exact_rel_path_wins_over_name(self):
        flux = model("checkpoints", "flux/m.safetensors")
        sdxl = model("checkpoints", "sdxl/m.safetensors")
        report = match_usage([flux, sdxl], [ref("flux/M.safetensors")])
        self.assertEqual([u.file for u in report.used], [flux])
        self.assertEqual(report.unused, [sdxl])

    def test_basename_fallback_matches_all_same_name(self):
        flux = model("checkpoints", "flux/m.safetensors")
        sdxl = model("checkpoints", "sdxl/m.safetensors")
        index = FileIndex([flux, sdxl])
        self.assertEqual(index.lookup("m.safetensors"), [flux, sdxl])
        report = match_usage([flux, sdxl], [ref("m.safetensors")])
        self.assertEqual(report.unused, [])

    def test_absolute_path_reference_matches_by_name(self):
        vae = model("vae", "v.pt")
        report = match_usage([vae], [ref("D:\\AI\\models\\vae\\v.pt")])
        self.assertEqual([u.file for u in report.used], [vae])

    def test_calls_and_workflows_counts(self):
        a = model("unet", "a.gguf")
        refs = [ref("a.gguf", "w1.json", "1"), ref("a.gguf", "w1.json", "2"), ref("a.gguf", "w2.json", "1")]
        usage = match_usage([a], refs).used[0]
        self.assertEqual(usage.calls, 3)
        self.assertEqual(usage.workflows, [Path("w1.json"), Path("w2.json")])
        self.assertEqual(len(usage.references), 3)

    def test_unreferenced_goes_to_unused(self):
        a = model("vae", "a.pt")
        b = model("vae", "b.pt")
        report = match_usage([a, b], [ref("a.pt")])
        self.assertEqual(report.unused, [b])

    def test_lora_reference_ignored(self):
        a = model("vae", "a.pt")
        report = match_usage([a], [ref("my_lora.safetensors")])
        self.assertEqual(report.used, [])
        self.assertEqual(report.unused, [a])

    def test_accented_names(self):
        f = model("checkpoints", "modèle_été.safetensors")
        report = match_usage([f], [ref("MODÈLE_ÉTÉ.safetensors")])
        self.assertEqual([u.file for u in report.used], [f])


    def test_llm_folder_reference_marks_shards_used(self):
        a = model("LLM", "Qwen2.5-VL/model-00001.safetensors")
        b = model("LLM", "Qwen2.5-VL/model-00002.safetensors")
        report = match_usage([a, b], [ref("Qwen2.5-VL")])
        self.assertEqual(report.unused, [])

    def test_llm_repo_id_reference_matches_last_component(self):
        a = model("LLM", "Qwen2.5-VL-3B/model.safetensors")
        self.assertEqual(match_usage([a], [ref("Qwen/Qwen2.5-VL-3B")]).unused, [])

    def test_folder_name_ignored_outside_llm(self):
        t5 = model("text_encoders", "flux/t5.safetensors")
        self.assertEqual(match_usage([t5], [ref("flux")]).unused, [t5])

    def test_alias_reference_marks_kept_file_used(self):
        a = model("checkpoints", "a_real.safetensors")
        report = match_usage([a], [ref("b_alias.safetensors")], aliases=[("b_alias.safetensors", a)])
        self.assertEqual([u.file for u in report.used], [a])

    def test_nfd_reference_matches_nfc_file(self):
        import unicodedata
        f = model("checkpoints", unicodedata.normalize("NFC", "modèle_été.safetensors"))
        report = match_usage([f], [ref(unicodedata.normalize("NFD", "modèle_été.safetensors"))])
        self.assertEqual(report.unused, [])


if __name__ == "__main__":
    unittest.main()
