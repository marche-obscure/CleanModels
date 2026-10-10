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
    # (chemin relatif de l'alias, fichier conservé) : autres chemins du même fichier physique
    aliases: list = field(default_factory=list)


def file_key(path: Path) -> str:
    """Identifiant d'un fichier physique (chemin réel, casse normalisée)."""
    return os.path.normcase(os.path.realpath(path))


def scan_models(dirs: list) -> InventoryResult:
    result = InventoryResult()
    kept_by_key: dict = {}
    kept_by_inode: dict = {}

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
                inode = (stat.st_dev, stat.st_ino) if stat.st_ino else None
                rel_path = os.path.relpath(path, root)
                kept = kept_by_key.get(key) or (kept_by_inode.get(inode) if inode else None)
                if kept is not None:
                    if os.path.normcase(rel_path) != os.path.normcase(kept.rel_path):
                        result.aliases.append((rel_path, kept))
                    continue
                model = ModelFile(
                    path=path,
                    real_path=Path(os.path.realpath(path)),
                    category=model_dir.category,
                    rel_path=rel_path,
                    size=stat.st_size,
                    root=root,
                )
                kept_by_key[key] = model
                if inode:
                    kept_by_inode[inode] = model
                result.files.append(model)
    return result
