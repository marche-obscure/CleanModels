"""Outils communs aux tests : fausse installation ComfyUI et dossier de réglages isolé."""

import os
import shutil
import tempfile
from pathlib import Path


def make_comfy(root: Path, files: dict) -> Path:
    """Crée root/ComfyUI avec models/ et user/default/workflows/, puis les fichiers donnés."""
    comfy = Path(root) / "ComfyUI"
    (comfy / "models").mkdir(parents=True, exist_ok=True)
    (comfy / "user" / "default" / "workflows").mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = comfy / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return comfy


class TempHomeMixin:
    """Dossier temporaire self.tmp, utilisé aussi comme CLEANMODELS_HOME."""

    def setUp(self):
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="cleanmodels-"))
        self._old_home = os.environ.get("CLEANMODELS_HOME")
        os.environ["CLEANMODELS_HOME"] = str(self.tmp)

    def tearDown(self):
        if self._old_home is None:
            os.environ.pop("CLEANMODELS_HOME", None)
        else:
            os.environ["CLEANMODELS_HOME"] = self._old_home
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()
