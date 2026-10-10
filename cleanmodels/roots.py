"""Validation du dossier ComfyUI et liste des dossiers de catégories à analyser."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from .constants import CATEGORIES
from .i18n import Message
from .yaml_lite import YamlError, parse

EXTRA_PATHS_FILE = "extra_model_paths.yaml"

_CANONICAL = {name.casefold(): name for name in CATEGORIES}


@dataclass(frozen=True)
class ModelDir:
    category: str
    path: Path
    origin: str


@dataclass
class RootsResult:
    dirs: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def workflows_dir(comfy: Path) -> Path:
    return Path(comfy) / "user" / "default" / "workflows"


def validate_comfyui(path: Path) -> str | None:
    """Message d'erreur en français, ou None si le dossier est une installation ComfyUI."""
    path = Path(path)
    if not path.is_dir():
        return Message("err_dir_missing", path=path)
    if not (path / "models").is_dir():
        return Message("err_no_models", path=path)
    if not workflows_dir(path).is_dir():
        return Message("err_no_workflows", path=path)
    return None


def dir_key(path: Path) -> str:
    """Identifiant d'un dossier (chemin réel, casse normalisée)."""
    return os.path.normcase(os.path.realpath(path))


def link_target(path: Path) -> Path | None:
    """Cible réelle si le chemin passe par un lien symbolique ou une jonction, sinon None."""
    real = os.path.realpath(path)
    if os.path.normcase(real) == os.path.normcase(os.path.abspath(path)):
        return None
    return Path(real)


def _to_path(value: str) -> Path:
    expanded = os.path.expanduser(os.path.expandvars(value.strip()))
    return Path(expanded.replace("\\", "/"))


def _yaml_dirs(comfy: Path, data: dict) -> list:
    found = []
    for section, content in data.items():
        if not isinstance(content, dict):
            continue
        base = comfy
        if isinstance(content.get("base_path"), str) and content["base_path"].strip():
            base = _to_path(content["base_path"])
            if not base.is_absolute():
                base = comfy / base
        for key, value in content.items():
            category = _CANONICAL.get(key.casefold())
            if category is None or not isinstance(value, str):
                continue
            for line in value.splitlines():
                if line.strip():
                    path = _to_path(line)
                    if not path.is_absolute():
                        path = base / path
                    found.append(ModelDir(category, path, f"yaml:{section}"))
    return found


def collect_model_dirs(comfy: Path) -> RootsResult:
    comfy = Path(comfy)
    result = RootsResult()
    candidates = []

    models = comfy / "models"
    if models.is_dir():
        for child in sorted(models.iterdir()):
            category = _CANONICAL.get(child.name.casefold())
            if category is not None and child.is_dir():
                candidates.append(ModelDir(category, child, "models"))

    yaml_file = comfy / EXTRA_PATHS_FILE
    if yaml_file.is_file():
        try:
            data = parse(yaml_file.read_text(encoding="utf-8-sig"))
            candidates.extend(_yaml_dirs(comfy, data))
        except (OSError, UnicodeDecodeError, YamlError) as exc:
            result.warnings.append(Message("warn_yaml_unreadable", file=EXTRA_PATHS_FILE, error=exc))

    seen = set()
    for model_dir in candidates:
        if not model_dir.path.is_dir():
            result.missing.append(model_dir)
            continue
        key = dir_key(model_dir.path)
        if key not in seen:
            seen.add(key)
            result.dirs.append(model_dir)
    return result
