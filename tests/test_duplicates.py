import hashlib
import os
import threading
import unittest

from cleanmodels.duplicates import Cancelled, find_duplicates
from cleanmodels.inventory import ModelFile
from tests.helpers import TempHomeMixin


class DuplicatesTest(TempHomeMixin, unittest.TestCase):
    def _file(self, name: str, content: bytes) -> ModelFile:
        path = self.tmp / name
        path.write_bytes(content)
        return ModelFile(path, path, "vae", name, len(content), self.tmp)

    def test_identical_content_grouped(self):
        a = self._file("a.pt", b"x" * 1000)
        b = self._file("b.pt", b"x" * 1000)
        c = self._file("c.pt", b"y" * 1000)
        d = self._file("d.pt", b"x" * 999)
        groups = find_duplicates([d, c, b, a])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].files, [a, b])
        self.assertEqual(groups[0].size, 1000)
        self.assertEqual(groups[0].digest, hashlib.sha256(b"x" * 1000).hexdigest())

    def test_unique_sizes_not_hashed(self):
        a = self._file("a.pt", b"x" * 10)
        b = self._file("b.pt", b"y" * 10)
        c = self._file("c.pt", b"z" * 5)
        totals = []
        find_duplicates([a, b, c], progress=lambda done, total: totals.append(total))
        self.assertTrue(totals)
        self.assertEqual(set(totals), {20})

    def test_cancel_raises(self):
        a = self._file("a.pt", b"x" * 100)
        b = self._file("b.pt", b"x" * 100)
        cancel = threading.Event()
        with self.assertRaises(Cancelled):
            find_duplicates([a, b], progress=lambda d, t: cancel.set(), cancel=cancel, chunk_size=10)

    def test_unreadable_file_skipped(self):
        a = self._file("a.pt", b"x" * 10)
        b = self._file("b.pt", b"x" * 10)
        c = self._file("c.pt", b"x" * 10)
        os.remove(c.path)
        groups = find_duplicates([a, b, c])
        self.assertEqual([g.files for g in groups], [[a, b]])


if __name__ == "__main__":
    unittest.main()
