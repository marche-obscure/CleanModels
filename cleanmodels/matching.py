"""Correspondance entre références des workflows et fichiers modèles, avec comptage."""

import ntpath
import unicodedata
from dataclasses import dataclass, field

from .constants import MODEL_EXTENSIONS
from .inventory import file_key

# Catégorie dont les modèles sont souvent désignés par le nom de leur dossier.
FOLDER_CATEGORY = "LLM"


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip().replace("/", "\\")).casefold()


@dataclass
class Usage:
    file: object
    calls: int = 0
    workflows: list = field(default_factory=list)
    references: list = field(default_factory=list)


@dataclass
class UsageReport:
    used: list = field(default_factory=list)
    unused: list = field(default_factory=list)


class FileIndex:
    """Recherche d'un fichier par chemin relatif exact, sinon par nom de fichier.

    Une référence sans extension de modèle désigne un dossier : elle correspond aux
    fichiers LLM situés sous un dossier de même chemin relatif ou de même nom.
    Les alias (autres chemins d'un même fichier physique) sont indexés comme le fichier.
    """

    def __init__(self, files: list, aliases: list = ()):
        self._by_rel: dict = {}
        self._by_name: dict = {}
        self._by_dir: dict = {}
        self._by_dir_name: dict = {}
        entries = [(f.rel_path, f) for f in files] + list(aliases)
        for rel_path, f in entries:
            rel = normalize(rel_path)
            self._add(self._by_rel, rel, f)
            self._add(self._by_name, ntpath.basename(rel), f)
            if f.category == FOLDER_CATEGORY:
                parts = rel.split("\\")[:-1]
                for depth in range(1, len(parts) + 1):
                    self._add(self._by_dir, "\\".join(parts[:depth]), f)
                    self._add(self._by_dir_name, parts[depth - 1], f)

    @staticmethod
    def _add(table: dict, key: str, f) -> None:
        bucket = table.setdefault(key, [])
        if f not in bucket:
            bucket.append(f)

    def lookup(self, value: str) -> list:
        key = normalize(value)
        if key.endswith(MODEL_EXTENSIONS):
            if key in self._by_rel:
                return list(self._by_rel[key])
            return list(self._by_name.get(ntpath.basename(key), []))
        if key in self._by_dir:
            return list(self._by_dir[key])
        return list(self._by_dir_name.get(ntpath.basename(key), []))


def match_usage(files: list, references: list, aliases: list = ()) -> UsageReport:
    index = FileIndex(files, aliases)
    usages: dict = {}
    for ref in references:
        for f in index.lookup(ref.value):
            usage = usages.setdefault(file_key(f.path), Usage(f))
            usage.calls += 1
            usage.references.append(ref)
            if ref.workflow not in usage.workflows:
                usage.workflows.append(ref.workflow)

    report = UsageReport()
    for f in files:
        usage = usages.get(file_key(f.path))
        if usage is None:
            report.unused.append(f)
        else:
            usage.workflows.sort(key=lambda p: str(p).casefold())
            report.used.append(usage)
    return report
