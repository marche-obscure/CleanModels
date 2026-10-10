import json
import os
import unittest
from unittest import mock

from cleanmodels.deletion import (
    DeletionItem,
    delete_files,
    duplicates_checker,
    fully_selected_groups,
    junk_checker,
    unused_checker,
)
from cleanmodels.duplicates import DuplicateGroup
from cleanmodels.inventory import ModelFile, file_key
from tests.helpers import TempHomeMixin, make_comfy


def accept(item):
    return None


class DeletionTest(TempHomeMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.log = self.tmp / "cleanmodels.log"

    def _make(self, name: str, content: bytes = b"data") -> DeletionItem:
        path = self.tmp / name
        path.write_bytes(content)
        return DeletionItem(path, len(content), "unused")

    def _log_lines(self):
        return self.log.read_text(encoding="utf-8").splitlines()

    def test_deletes_and_logs(self):
        a, b = self._make("a.pt"), self._make("b.pt", b"bb")
        result = delete_files([a, b], accept, self.log)
        self.assertEqual(result.deleted, [a, b])
        self.assertEqual(result.freed_bytes, 6)
        self.assertFalse(a.path.exists() or b.path.exists())
        lines = self._log_lines()
        self.assertEqual(len(lines), 2)
        fields = lines[0].split("\t")
        self.assertEqual(fields[1:], ["unused", "SUPPRIMÉ", "4", str(a.path)])
        self.assertRegex(fields[0], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")

    def test_missing_or_changed_file_refused(self):
        gone, changed = self._make("gone.pt"), self._make("changed.pt")
        os.remove(gone.path)
        changed.path.write_bytes(b"bigger content")
        result = delete_files([gone, changed], accept, self.log)
        self.assertEqual(result.deleted, [])
        self.assertEqual([reason for _, reason in result.refused], ["fichier introuvable", "taille modifiée"])
        self.assertTrue(changed.path.exists())
        self.assertIn("REFUSÉ: taille modifiée", self._log_lines()[1])

    def test_permission_error_continues(self):
        a, b = self._make("a.pt"), self._make("b.pt")
        real_remove = os.remove

        def flaky_remove(path, *args, **kwargs):
            if os.path.basename(path) == "a.pt":
                raise PermissionError(13, "Accès refusé", str(path))
            return real_remove(path, *args, **kwargs)

        with mock.patch("os.remove", side_effect=flaky_remove):
            result = delete_files([a, b], accept, self.log)
        self.assertEqual([item for item, _ in result.errors], [a])
        self.assertEqual(result.deleted, [b])
        self.assertTrue(a.path.exists())
        self.assertIn("ERREUR: ", self._log_lines()[0])

    def test_unused_checker_refuses_newly_referenced(self):
        comfy = make_comfy(self.tmp, {"models/vae/v.pt": b"vv"})
        root = comfy / "models" / "vae"
        path = root / "v.pt"
        model = ModelFile(path, path, "vae", "v.pt", 2, root)
        wf = comfy / "user" / "default" / "workflows"
        checker_before = unused_checker(wf, [model])
        (wf / "new.json").write_text(
            json.dumps({"nodes": [{"id": 1, "type": "VAELoader", "widgets_values": ["v.pt"]}]}), encoding="utf-8"
        )
        item = DeletionItem(path, 2, "unused")
        self.assertIsNone(checker_before(item))
        result = delete_files([item], unused_checker(wf, [model]), self.log)
        self.assertEqual([reason for _, reason in result.refused], ["cité par un workflow"])
        self.assertTrue(path.exists())
        self.assertIn("REFUSÉ: cité par un workflow", self._log_lines()[0])

    def _two_same_name(self):
        comfy = make_comfy(self.tmp, {
            "models/checkpoints/dup.safetensors": b"dd",
            "models/checkpoints/old/dup.safetensors": b"dd",
            "user/default/workflows/w.json": json.dumps(
                {"nodes": [{"id": 1, "type": "L", "widgets_values": ["dup.safetensors"]}]}),
        })
        root = comfy / "models" / "checkpoints"
        a = ModelFile(root / "dup.safetensors", root / "dup.safetensors", "checkpoints", "dup.safetensors", 2, root)
        b_path = root / "old" / "dup.safetensors"
        b = ModelFile(b_path, b_path, "checkpoints", os.path.join("old", "dup.safetensors"), 2, root)
        return comfy, a, b

    def test_unused_checker_ignores_deleted_files(self):
        comfy, a, b = self._two_same_name()
        wf = comfy / "user" / "default" / "workflows"
        os.remove(a.path)
        checker = unused_checker(wf, [a, b])
        self.assertEqual(checker(DeletionItem(b.path, 2, "unused")), "cité par un workflow")

    def test_unused_checker_refuses_when_workflow_unreadable(self):
        comfy, a, b = self._two_same_name()
        wf = comfy / "user" / "default" / "workflows"
        (wf / "broken.json").write_text("{", encoding="utf-8")
        other = self._make("other.pt")
        reason = unused_checker(wf, [a, b])(other)
        self.assertIsNotNone(reason)
        self.assertIn("illisible", reason)

    def test_unused_checker_uses_llm_folder_references(self):
        comfy = make_comfy(self.tmp, {
            "models/LLM/Qwen2.5-VL/model.safetensors": b"q",
            "user/default/workflows/w.json": json.dumps(
                {"nodes": [{"id": 1, "type": "QwenVL", "widgets_values": ["Qwen2.5-VL"]}]}),
        })
        root = comfy / "models" / "LLM"
        path = root / "Qwen2.5-VL" / "model.safetensors"
        f = ModelFile(path, path, "LLM", os.path.join("Qwen2.5-VL", "model.safetensors"), 1, root)
        reason = unused_checker(comfy / "user" / "default" / "workflows", [f])(DeletionItem(path, 1, "unused"))
        self.assertEqual(reason, "cité par un workflow")

    def test_log_failure_does_not_abort(self):
        a, b = self._make("a.pt"), self._make("b.pt")
        result = delete_files([a, b], accept, self.tmp)  # un dossier : écriture du journal impossible
        self.assertEqual(result.deleted, [a, b])
        self.assertEqual(len(result.log_errors), 2)

    def _group(self):
        a, b = self._make("a.pt", b"same"), self._make("b.pt", b"same")
        files = [ModelFile(i.path, i.path, "vae", i.path.name, 4, self.tmp) for i in (a, b)]
        items = [DeletionItem(i.path, 4, "duplicates") for i in (a, b)]
        return DuplicateGroup("digest", 4, files), items

    def test_duplicates_keeps_one_copy(self):
        group, (a, b) = self._group()
        selected = {file_key(a.path), file_key(b.path)}
        self.assertEqual(fully_selected_groups([group], selected), [group])
        result = delete_files([a, b], duplicates_checker([group], selected), self.log)
        self.assertEqual(result.deleted, [])
        self.assertEqual([r for _, r in result.refused], ["aucune autre copie conservée"] * 2)
        self.assertTrue(a.path.exists() and b.path.exists())

    def test_duplicates_deletes_selected_copy(self):
        group, (a, b) = self._group()
        selected = {file_key(a.path)}
        self.assertEqual(fully_selected_groups([group], selected), [])
        result = delete_files([a], duplicates_checker([group], selected), self.log)
        self.assertEqual(result.deleted, [a])
        self.assertTrue(b.path.exists())

    def test_junk_checker(self):
        item = DeletionItem(self._make("x.part").path, 4, "junk")
        self.assertIsNone(junk_checker(["*.part"])(item))
        self.assertEqual(junk_checker(["*.tmp"])(item), "ne correspond plus à un motif")

    def test_accented_path_logged(self):
        item = self._make("modèle_été.safetensors")
        delete_files([item], accept, self.log)
        self.assertIn("modèle_été.safetensors", self._log_lines()[0])


if __name__ == "__main__":
    unittest.main()
