import unittest

from cleanmodels.constants import DEFAULT_JUNK_PATTERNS
from cleanmodels.junk import find_junk, match_pattern
from cleanmodels.roots import ModelDir
from tests.helpers import TempHomeMixin, make_comfy


class JunkTest(TempHomeMixin, unittest.TestCase):
    def _dirs(self, files):
        comfy = make_comfy(self.tmp, files)
        return [ModelDir("checkpoints", comfy / "models" / "checkpoints", "models")]

    def test_match_pattern(self):
        self.assertEqual(match_pattern("B.CRDOWNLOAD", list(DEFAULT_JUNK_PATTERNS)), "*.crdownload")
        self.assertIsNone(match_pattern("c.safetensors", list(DEFAULT_JUNK_PATTERNS)))

    def test_default_patterns(self):
        dirs = self._dirs({
            "models/checkpoints/a.part": b"aa",
            "models/checkpoints/sub/b.CRDOWNLOAD": b"b",
            "models/checkpoints/c.safetensors": b"c",
        })
        junk = find_junk(dirs, list(DEFAULT_JUNK_PATTERNS))
        self.assertEqual([(j.path.name, j.pattern, j.size) for j in junk],
                         [("a.part", "*.part", 2), ("b.CRDOWNLOAD", "*.crdownload", 1)])
        self.assertEqual(junk[0].category, "checkpoints")
        self.assertEqual(junk[0].root, dirs[0].path)

    def test_custom_pattern(self):
        dirs = self._dirs({"models/checkpoints/x.old": b"x", "models/checkpoints/y.part": b"y"})
        self.assertEqual([j.path.name for j in find_junk(dirs, ["*.old"])], ["x.old"])

    def test_empty_patterns_returns_nothing(self):
        dirs = self._dirs({"models/checkpoints/a.part": b"a"})
        self.assertEqual(find_junk(dirs, []), [])


if __name__ == "__main__":
    unittest.main()
