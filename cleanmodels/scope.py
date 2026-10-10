"""Périmètre du contrôle : dossiers de workflows de référence et dossiers de modèles analysés."""

import os
from dataclasses import dataclass
from pathlib import Path

from .roots import RootsResult, collect_model_dirs, link_target, workflows_dir

STANDARD = "standard"
ADDED = "ajouté"


@dataclass(frozen=True)
class WorkflowSource:
    path: Path
    origin: str  # STANDARD ou ADDED
    exists: bool


@dataclass
class Scope:
    workflows: list
    roots: RootsResult


def workflow_sources(comfy: Path, extra: list) -> list:
    """Dossier standard puis dossiers ajoutés, sans doublon (comparaison sur le chemin réel)."""
    sources, seen = [], set()
    candidates = [(workflows_dir(Path(comfy)), STANDARD)] + [(Path(p), ADDED) for p in extra]
    for path, origin in candidates:
        key = os.path.normcase(os.path.realpath(path))
        if key in seen:
            continue
        seen.add(key)
        sources.append(WorkflowSource(path, origin, path.is_dir()))
    return sources


def describe_scope(comfy: Path, extra: list) -> Scope:
    return Scope(workflow_sources(comfy, extra), collect_model_dirs(Path(comfy)))


def _origin_label(origin: str) -> str:
    if origin.startswith("yaml:"):
        return f"extra_model_paths.yaml — section « {origin[5:]} »"
    return origin


def scope_lines(scope: Scope) -> list:
    lines = ["Workflows de référence (lus pour savoir quels modèles sont utilisés)"]
    for source in scope.workflows:
        if source.exists:
            lines.append(f"  ✔ {source.path}  ({source.origin})")
        else:
            lines.append(f"  ✖ {source.path}  ({source.origin} — introuvable)")

    lines += ["", "Dossiers de modèles analysés (cibles du contrôle)"]
    for model_dir in scope.roots.dirs:
        line = f"  ✔ [{model_dir.category}] {model_dir.path}  ({_origin_label(model_dir.origin)})"
        target = link_target(model_dir.path)
        if target is not None:
            line += f"  →  {target}  (lien symbolique / jonction)"
        lines.append(line)
    for model_dir in scope.roots.missing:
        lines.append(f"  ✖ [{model_dir.category}] {model_dir.path}  ({_origin_label(model_dir.origin)} — introuvable)")
    if not scope.roots.dirs and not scope.roots.missing:
        lines.append("  (aucun dossier de catégorie trouvé)")
    for warning in scope.roots.warnings:
        lines.append(f"  ⚠ {warning}")
    return lines
