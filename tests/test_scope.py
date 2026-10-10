import json
import os
import unittest

from cleanmodels.analysis import run_analysis
from cleanmodels.deletion import DeletionItem, unused_checker
from cleanmodels.inventory import ModelFile
from cleanmodels.roots import link_target
from cleanmodels.scope import describe_scope, scope_lines, workflow_sources
from cleanmodels.settings import load_settings
from cleanmodels.workflows import scan_workflow_dirs
from tests.helpers import TempHomeMixin, make_comfy


def workflow(*values):
    return json.dumps({"nodes": [{"id": i, "type": "Loader", "widgets_values": [v]} for i, v in enumerate(values)]})


def _junction(target, link):
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))


class SettingsV2Test(TempHomeMixin, unittest.TestCase):
    def test_v1_file_is_upgraded(self):
        (self.tmp / "settings.json").write_text(
            json.dumps({"config_version": 1, "comfyui_path": "D:/C", "junk_patterns": ["*.tmp"]}), encoding="utf-8"
        )
        data, warning = load_settings()
        self.assertIsNone(warning)
        self.assertEqual(data["config_version"], 2)
        self.assertEqual(data["extra_workflow_dirs"], [])
        self.assertEqual(data["comfyui_path"], "D:/C")

    def test_newer_version_kept(self):
        (self.tmp / "settings.json").write_text(json.dumps({"config_version": 3}), encoding="utf-8")
        self.assertEqual(load_settings()[0]["config_version"], 3)


class WorkflowDirsTest(TempHomeMixin, unittest.TestCase):
    def test_scan_several_dirs_skips_missing_and_duplicates(self):
        a, b = self.tmp / "a", self.tmp / "b"
        (a / "sub").mkdir(parents=True)
        b.mkdir()
        (a / "sub" / "w1.json").write_text(workflow("x.pt"), encoding="utf-8")
        (b / "w2.json").write_text(workflow("y.pt"), encoding="utf-8")
        scan = scan_workflow_dirs([a, b, self.tmp / "absent", a / "sub"])
        self.assertEqual(scan.workflow_count, 2)
        self.assertEqual(sorted(r.value for r in scan.references), ["x.pt", "y.pt"])

    def test_workflow_sources(self):
        comfy = make_comfy(self.tmp, {})
        extra = self.tmp / "mes_workflows"
        extra.mkdir()
        standard = comfy / "user" / "default" / "workflows"
        sources = workflow_sources(comfy, [str(extra), str(self.tmp / "absent"), str(extra), str(standard)])
        self.assertEqual([(s.path, s.origin, s.exists) for s in sources], [
            (standard, "standard", True),
            (extra, "ajouté", True),
            (self.tmp / "absent", "ajouté", False),
        ])

    def test_unused_checker_reads_extra_dirs(self):
        comfy = make_comfy(self.tmp, {"models/vae/v.pt": b"v"})
        extra = self.tmp / "ailleurs"
        extra.mkdir()
        (extra / "w.json").write_text(workflow("v.pt"), encoding="utf-8")
        root = comfy / "models" / "vae"
        f = ModelFile(root / "v.pt", root / "v.pt", "vae", "v.pt", 1, root)
        folders = [comfy / "user" / "default" / "workflows", extra]
        reason = unused_checker(folders, [f])(DeletionItem(f.path, 1, "unused"))
        self.assertEqual(reason, "cité par un workflow")

    def test_analysis_uses_extra_dirs(self):
        comfy = make_comfy(self.tmp, {"models/vae/v.pt": b"v"})
        extra = self.tmp / "ailleurs"
        extra.mkdir()
        (extra / "w.json").write_text(workflow("v.pt"), encoding="utf-8")
        result = run_analysis(comfy, [], extra_workflow_dirs=[str(extra)])
        self.assertEqual(result.usage.unused, [])
        self.assertEqual([s.origin for s in result.workflow_sources], ["standard", "ajouté"])


class ScopeTest(TempHomeMixin, unittest.TestCase):
    def test_link_target(self):
        real = self.tmp / "stock" / "vae"
        real.mkdir(parents=True)
        link = self.tmp / "vae_link"
        _junction(real, link)
        self.assertEqual(os.path.normcase(link_target(link)), os.path.normcase(os.path.realpath(real)))
        self.assertIsNone(link_target(real))

    def test_scope_lines(self):
        stock = self.tmp / "stock" / "vae"
        stock.mkdir(parents=True)
        ext = self.tmp / "ext"
        (ext / "unet").mkdir(parents=True)
        comfy = make_comfy(self.tmp, {
            "models/checkpoints/a.safetensors": b"a",
            "extra_model_paths.yaml": f"perso:\n  base_path: {ext.as_posix()}\n  unet: unet\n  LLM: llm\n",
        })
        _junction(stock, comfy / "models" / "vae")
        lines = scope_lines(describe_scope(comfy, [str(self.tmp / "absent")]))
        text = "\n".join(lines)
        self.assertIn("Workflows de référence", text)
        self.assertIn(f"✔ {comfy / 'user' / 'default' / 'workflows'}  (standard)", text)
        self.assertIn(f"✖ {self.tmp / 'absent'}  (ajouté — introuvable)", text)
        self.assertIn("Dossiers de modèles analysés", text)
        self.assertIn(f"✔ [checkpoints] {comfy / 'models' / 'checkpoints'}  (models)", text)
        self.assertIn(f"✔ [unet] {ext / 'unet'}  (extra_model_paths.yaml — section « perso »)", text)
        self.assertIn(f"✖ [LLM] {ext / 'llm'}  (extra_model_paths.yaml — section « perso » — introuvable)", text)
        vae_line = next(line for line in lines if "[vae]" in line)
        self.assertIn("→", vae_line)
        self.assertIn("lien symbolique / jonction", vae_line)


if __name__ == "__main__":
    unittest.main()
