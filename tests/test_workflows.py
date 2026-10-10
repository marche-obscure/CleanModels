import json
import unittest
from pathlib import Path

from cleanmodels.workflows import Reference, references_from_json, scan_workflows
from tests.helpers import TempHomeMixin

WF = Path("wf.json")


class ReferencesFromJsonTest(unittest.TestCase):
    def test_ui_format(self):
        data = {"nodes": [{"id": 4, "type": "CheckpointLoaderSimple", "widgets_values": ["sd\\a.safetensors"]}]}
        self.assertEqual(
            references_from_json(data, WF),
            [Reference("sd\\a.safetensors", WF, "4", "CheckpointLoaderSimple")],
        )

    def test_nested_widget_values_dict(self):
        data = {"nodes": [{"id": 1, "type": "T", "widgets_values": {"model": "x.gguf", "n": 3}}]}
        self.assertEqual([r.value for r in references_from_json(data, WF)], ["x.gguf"])

    def test_subgraph_nodes(self):
        data = {
            "nodes": [],
            "definitions": {"subgraphs": [{"nodes": [{"id": 7, "type": "VAELoader", "widgets_values": ["v.pt"]}]}]},
        }
        self.assertEqual(references_from_json(data, WF), [Reference("v.pt", WF, "7", "VAELoader")])

    def test_api_format(self):
        data = {"3": {"class_type": "UNETLoader", "inputs": {"unet_name": "f.sft", "w": "default"}}}
        self.assertEqual(references_from_json(data, WF), [Reference("f.sft", WF, "3", "UNETLoader")])

    def test_properties_models_ignored(self):
        data = {"nodes": [{"id": 1, "type": "T", "widgets_values": [],
                           "properties": {"models": [{"name": "z.safetensors"}]}}]}
        self.assertEqual(references_from_json(data, WF), [])

    def test_same_value_twice_in_node_counts_once(self):
        data = {"nodes": [{"id": 1, "type": "T", "widgets_values": ["a.pt", "a.pt"]}]}
        self.assertEqual(len(references_from_json(data, WF)), 1)

    def test_extension_case_insensitive(self):
        data = {"nodes": [{"id": 1, "type": "T", "widgets_values": ["A.SafeTensors", "photo.png"]}]}
        self.assertEqual([r.value for r in references_from_json(data, WF)], ["A.SafeTensors"])

    def test_unknown_structure_raises(self):
        with self.assertRaises(ValueError):
            references_from_json([1, 2], WF)


class ScanWorkflowsTest(TempHomeMixin, unittest.TestCase):
    def _ok(self):
        return json.dumps({"nodes": [{"id": 1, "type": "T", "widgets_values": ["a.pt"]}]})

    def test_scan_skips_invalid_json(self):
        (self.tmp / "bad.json").write_text("{oups", encoding="utf-8")
        (self.tmp / "sub").mkdir()
        (self.tmp / "sub" / "ok.json").write_text(self._ok(), encoding="utf-8")
        scan = scan_workflows(self.tmp)
        self.assertEqual(scan.workflow_count, 1)
        self.assertEqual(len(scan.skipped), 1)
        self.assertEqual(scan.skipped[0][0].name, "bad.json")
        self.assertEqual([r.workflow.name for r in scan.references], ["ok.json"])

    def test_scan_reads_utf8_bom(self):
        (self.tmp / "bom.json").write_text(self._ok(), encoding="utf-8-sig")
        scan = scan_workflows(self.tmp)
        self.assertEqual(scan.skipped, [])
        self.assertEqual(len(scan.references), 1)

    def test_unknown_structure_skipped(self):
        (self.tmp / "list.json").write_text("[1, 2]", encoding="utf-8")
        scan = scan_workflows(self.tmp)
        self.assertEqual(scan.workflow_count, 0)
        self.assertEqual(len(scan.skipped), 1)


if __name__ == "__main__":
    unittest.main()
