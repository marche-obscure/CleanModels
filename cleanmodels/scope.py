"""Périmètre du contrôle : dossiers de workflows de référence et dossiers de modèles analysés."""

import os
from dataclasses import dataclass
from pathlib import Path

from .i18n import Message
from .roots import RootsResult, collect_model_dirs, dir_key, link_target, workflows_dir

STANDARD = "standard"
ADDED = "ajouté"

WORKFLOW_GROUP = Message("group_workflows")
MODEL_GROUP = Message("group_models")
_ORIGIN_KEYS = {STANDARD: "origin_standard", ADDED: "origin_added"}
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


def origin_label(origin: str):
    """Libellé d'origine d'un dossier (Message traduisible, ou « models »)."""
    if origin.startswith("yaml:"):
        return Message("origin_yaml", section=origin[5:])
    if origin in _ORIGIN_KEYS:
        return Message(_ORIGIN_KEYS[origin])
    return origin


def scope_rows(scope: Scope) -> list:
    """Lignes du périmètre, pour l'affichage avec cases à cocher."""
    rows = []
    for source in scope.workflows:
        origin = origin_label(source.origin)
        detail = origin if source.exists else Message("detail_missing", origin=origin)
        rows.append(ScopeRow(WORKFLOW_PREFIX + dir_key(source.path), WORKFLOW_GROUP, str(source.path),
                             detail, source.exists))
    for model_dir in scope.roots.dirs:
        detail = origin_label(model_dir.origin)
        target = link_target(model_dir.path)
        if target is not None:
            detail = Message("detail_link", origin=detail, target=target)
        rows.append(ScopeRow(MODEL_PREFIX + dir_key(model_dir.path), MODEL_GROUP,
                             f"[{model_dir.category}] {model_dir.path}", detail, True))
    for model_dir in scope.roots.missing:
        rows.append(ScopeRow(MODEL_PREFIX + dir_key(model_dir.path), MODEL_GROUP,
                             f"[{model_dir.category}] {model_dir.path}",
                             Message("detail_missing", origin=origin_label(model_dir.origin)), False))
    return rows
