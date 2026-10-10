"""Fichiers parasites (téléchargements incomplets, temporaires…) repérés par motifs."""

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path

from .inventory import file_key


@dataclass(frozen=True)
class JunkFile:
    path: Path
    category: str
    size: int
    pattern: str
    root: Path


def match_pattern(name: str, patterns: list) -> str | None:
    """Premier motif correspondant au nom (insensible à la casse), sinon None."""
    folded = name.casefold()
    for pattern in patterns:
        if fnmatch.fnmatchcase(folded, pattern.casefold()):
            return pattern
    return None


def find_junk(dirs: list, patterns: list) -> list:
    if not patterns:
        return []
    found = {}
    for model_dir in dirs:
        for folder, _subdirs, names in os.walk(model_dir.path, followlinks=True):
            for name in names:
                pattern = match_pattern(name, patterns)
                if pattern is None:
                    continue
                path = Path(folder) / name
                key = file_key(path)
                if key in found:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                found[key] = JunkFile(path, model_dir.category, size, pattern, Path(model_dir.path))
    return sorted(found.values(), key=lambda j: str(j.path).casefold())
