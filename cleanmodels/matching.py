"""Correspondance entre références des workflows et fichiers modèles, avec comptage."""

import ntpath
from dataclasses import dataclass, field

from .inventory import file_key


def normalize(value: str) -> str:
    return value.strip().replace("/", "\\").casefold()


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
    """Recherche d'un fichier par chemin relatif exact, sinon par nom de fichier."""

    def __init__(self, files: list):
        self._by_rel: dict = {}
        self._by_name: dict = {}
        for f in files:
            rel = normalize(f.rel_path)
            self._by_rel.setdefault(rel, []).append(f)
            self._by_name.setdefault(ntpath.basename(rel), []).append(f)

    def lookup(self, value: str) -> list:
        key = normalize(value)
        if key in self._by_rel:
            return list(self._by_rel[key])
        return list(self._by_name.get(ntpath.basename(key), []))


def match_usage(files: list, references: list) -> UsageReport:
    index = FileIndex(files)
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
