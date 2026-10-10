"""Inventaire des fichiers modèles présents dans les dossiers de catégories."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from .constants import MODEL_EXTENSIONS


@dataclass(frozen=True)
class ModelFile:
    path: Path
    real_path: Path
    category: str
    rel_path: str
    size: int
    root: Path


@dataclass
class InventoryResult:
    files: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def file_key(path: Path) -> str:
    """Identifiant d'un fichier physique (chemin réel, casse normalisée)."""
    return os.path.normcase(os.path.realpath(path))


def scan_models(dirs: list) -> InventoryResult:
    result = InventoryResult()
    seen_keys = set()
    seen_inodes = set()

    def on_error(exc: OSError) -> None:
        result.errors.append(f"{exc.filename} : {exc.strerror or exc}")

    for model_dir in dirs:
        root = Path(model_dir.path)
        for folder, _subdirs, names in os.walk(root, onerror=on_error, followlinks=True):
            for name in sorted(names):
                if not name.lower().endswith(MODEL_EXTENSIONS):
                    continue
                path = Path(folder) / name
                try:
                    stat = path.stat()
                except OSError as exc:
                    on_error(exc)
                    continue
                key = file_key(path)
                inode = (stat.st_dev, stat.st_ino)
                if key in seen_keys or (stat.st_ino and inode in seen_inodes):
                    continue
                seen_keys.add(key)
                if stat.st_ino:
                    seen_inodes.add(inode)
                result.files.append(ModelFile(
                    path=path,
                    real_path=Path(os.path.realpath(path)),
                    category=model_dir.category,
                    rel_path=os.path.relpath(path, root),
                    size=stat.st_size,
                    root=root,
                ))
    return result
