"""Périmètre du contrôle : dossiers de workflows de référence et dossiers de modèles analysés."""

import os
from dataclasses import dataclass
from pathlib import Path

from .roots import RootsResult, collect_model_dirs, dir_key, link_target, workflows_dir

STANDARD = "standard"
ADDED = "ajouté"

WORKFLOW_GROUP = "Workflows de référence"
MODEL_GROUP = "Dossiers de modèles analysés"
WORKFLOW_PREFIX = "wf:"
MODEL_PREFIX = "md:"


@dataclass(frozen=True)
class ScopeRow:
    key: str        # préfixe (wf: / md:) + dir_key du dossier
    group: str      # WORKFLOW_GROUP ou MODEL_GROUP
    name: str       # texte affiché
    detail: str     # origine, cible du lien, « introuvable »
    available: bool # False : dossier introuvable, non sélectionnable


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


def scope_rows(scope: Scope) -> list:
    """Lignes du périmètre, pour l'affichage avec cases à cocher."""
    rows = []
    for source in scope.workflows:
        detail = source.origin if source.exists else f"{source.origin} — introuvable"
        rows.append(ScopeRow(WORKFLOW_PREFIX + dir_key(source.path), WORKFLOW_GROUP, str(source.path),
                             detail, source.exists))
    for model_dir in scope.roots.dirs:
        detail = _origin_label(model_dir.origin)
        target = link_target(model_dir.path)
        if target is not None:
            detail += f"  →  {target}  (lien symbolique / jonction)"
        rows.append(ScopeRow(MODEL_PREFIX + dir_key(model_dir.path), MODEL_GROUP,
                             f"[{model_dir.category}] {model_dir.path}", detail, True))
    for model_dir in scope.roots.missing:
        rows.append(ScopeRow(MODEL_PREFIX + dir_key(model_dir.path), MODEL_GROUP,
                             f"[{model_dir.category}] {model_dir.path}",
                             f"{_origin_label(model_dir.origin)} — introuvable", False))
    return rows
