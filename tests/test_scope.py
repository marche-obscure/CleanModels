import json
import os
import unittest

from cleanmodels.analysis import run_analysis
from cleanmodels.deletion import DeletionItem, unused_checker
from cleanmodels.inventory import ModelFile
from cleanmodels.roots import dir_key, link_target
from cleanmodels.scope import MODEL_GROUP, WORKFLOW_GROUP, describe_scope, scope_rows, workflow_sources
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

    def test_scope_rows(self):
        stock = self.tmp / "stock" / "vae"
        stock.mkdir(parents=True)
        ext = self.tmp / "ext"
        (ext / "unet").mkdir(parents=True)
        comfy = make_comfy(self.tmp, {
            "models/checkpoints/a.safetensors": b"a",
            "extra_model_paths.yaml": f"perso:\n  base_path: {ext.as_posix()}\n  unet: unet\n  LLM: llm\n",
        })
        _junction(stock, comfy / "models" / "vae")
        rows = scope_rows(describe_scope(comfy, [str(self.tmp / "absent")]))
        by_name = {r.name: r for r in rows}
        standard = by_name[str(comfy / "user" / "default" / "workflows")]
        self.assertEqual((standard.group, standard.detail, standard.available),
                         (WORKFLOW_GROUP, "standard", True))
        self.assertEqual(standard.key, "wf:" + dir_key(comfy / "user" / "default" / "workflows"))
        absent = by_name[str(self.tmp / "absent")]
        self.assertEqual((absent.detail, absent.available), ("ajouté — introuvable", False))
        ckpt = by_name[f"[checkpoints] {comfy / 'models' / 'checkpoints'}"]
        self.assertEqual((ckpt.group, ckpt.detail, ckpt.available), (MODEL_GROUP, "models", True))
        self.assertEqual(ckpt.key, "md:" + dir_key(comfy / "models" / "checkpoints"))
        unet = by_name[f"[unet] {ext / 'unet'}"]
        self.assertEqual(unet.detail, "extra_model_paths.yaml — section « perso »")
        llm = by_name[f"[LLM] {ext / 'llm'}"]
        self.assertEqual((llm.detail, llm.available),
                         ("extra_model_paths.yaml — section « perso » — introuvable", False))
        vae = by_name[f"[vae] {comfy / 'models' / 'vae'}"]
        self.assertIn("→", vae.detail)
        self.assertIn("lien symbolique / jonction", vae.detail)


class ExclusionTest(TempHomeMixin, unittest.TestCase):
    def _comfy(self):
        return make_comfy(self.tmp, {
            "models/checkpoints/a.safetensors": b"a",
            "models/vae/v.pt": b"v",
            "models/vae/x.part": b"p",
        })

    def test_excluded_model_dir_not_analyzed(self):
        comfy = self._comfy()
        result = run_analysis(comfy, ["*.part"], excluded_dirs={dir_key(comfy / "models" / "vae")})
        self.assertEqual([f.path.name for f in result.inventory.files], ["a.safetensors"])
        self.assertEqual(result.junk, [])
        self.assertEqual([d.category for d in result.excluded_model_dirs], ["vae"])

    def test_excluded_workflow_dir_not_read_but_kept_in_sources(self):
        comfy = self._comfy()
        extra = self.tmp / "ailleurs"
        extra.mkdir()
        (extra / "w.json").write_text(workflow("v.pt"), encoding="utf-8")
        result = run_analysis(comfy, [], extra_workflow_dirs=[str(extra)], excluded_dirs={dir_key(extra)})
        self.assertIn("v.pt", [f.path.name for f in result.usage.unused])
        self.assertEqual([s.origin for s in result.workflow_sources], ["standard", "ajouté"])
        self.assertEqual([s.path for s in result.excluded_workflow_sources], [extra])


if __name__ == "__main__":
    unittest.main()
