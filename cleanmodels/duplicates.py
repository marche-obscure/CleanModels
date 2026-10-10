"""Recherche de fichiers modèles au contenu identique (taille, puis SHA-256)."""

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Callable


class Cancelled(Exception):
    """La recherche a été annulée par l'utilisateur."""


@dataclass
class DuplicateGroup:
    digest: str
    size: int
    files: list = field(default_factory=list)


def find_duplicates(
    files: list,
    progress: Callable[[int, int], None] | None = None,
    cancel: threading.Event | None = None,
    chunk_size: int = 8 * 1024 * 1024,
) -> list:
    by_size: dict = {}
    for f in files:
        by_size.setdefault(f.size, []).append(f)
    candidates = [f for same in by_size.values() if len(same) > 1 for f in same]
    total = sum(f.size for f in candidates)
    done = 0

    by_digest: dict = {}
    for f in candidates:
        sha = hashlib.sha256()
        try:
            with open(f.path, "rb") as handle:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    block = handle.read(chunk_size)
                    if not block:
                        break
                    sha.update(block)
                    done += len(block)
                    if progress is not None:
                        progress(done, total)
        except OSError:
            continue
        by_digest.setdefault((f.size, sha.hexdigest()), []).append(f)

    groups = [
        DuplicateGroup(digest, size, sorted(same, key=lambda f: str(f.path).casefold()))
        for (size, digest), same in by_digest.items()
        if len(same) > 1
    ]
    groups.sort(key=lambda g: (-g.size, g.digest))
    return groups
