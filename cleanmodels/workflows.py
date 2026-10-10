"""Extraction des références de modèles depuis les workflows ComfyUI (.json)."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .constants import MODEL_EXTENSIONS


@dataclass(frozen=True)
class Reference:
    value: str
    workflow: Path
    node_id: str
    node_type: str


@dataclass
class WorkflowScan:
    references: list = field(default_factory=list)
    name_references: list = field(default_factory=list)
    workflow_count: int = 0
    skipped: list = field(default_factory=list)


MAX_NAME_LENGTH = 255


def _is_model_string(text: str) -> bool:
    return text.strip().lower().endswith(MODEL_EXTENSIONS)


def _is_name_string(text: str) -> bool:
    """Chaîne courte sur une ligne, sans extension de modèle (ex. nom de dossier LLM)."""
    stripped = text.strip()
    return 0 < len(stripped) <= MAX_NAME_LENGTH and "\n" not in stripped and not _is_model_string(stripped)


def _strings(value, keep) -> list:
    """Chaînes retenues par keep, sans doublon, dans l'ordre de rencontre."""
    found = []
    pending = [value]
    while pending:
        item = pending.pop(0)
        if isinstance(item, str):
            if keep(item) and item not in found:
                found.append(item)
        elif isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return found


def _ui_nodes(graph: dict) -> list:
    nodes = [n for n in graph.get("nodes") or [] if isinstance(n, dict)]
    definitions = graph.get("definitions")
    if isinstance(definitions, dict):
        for subgraph in definitions.get("subgraphs") or []:
            if isinstance(subgraph, dict):
                nodes.extend(_ui_nodes(subgraph))
    return nodes


def _is_api_format(data: dict) -> bool:
    return bool(data) and all(isinstance(v, dict) and "class_type" in v for v in data.values())


def _node_payloads(data: object) -> list:
    """(id, type, valeurs) de chaque nœud. ValueError si la structure est inconnue."""
    if isinstance(data, dict) and isinstance(data.get("nodes"), list):
        return [(str(n.get("id", "")), str(n.get("type", "")), n.get("widgets_values")) for n in _ui_nodes(data)]
    if isinstance(data, dict) and _is_api_format(data):
        return [(str(k), str(n.get("class_type", "")), n.get("inputs")) for k, n in data.items()]
    raise ValueError("structure de workflow inconnue")


def _references(data: object, workflow: Path, keep) -> list:
    return [
        Reference(value, workflow, node_id, node_type)
        for node_id, node_type, payload in _node_payloads(data)
        for value in _strings(payload, keep)
    ]


def references_from_json(data: object, workflow: Path) -> list:
    """Références à des fichiers modèles. ValueError si la structure est inconnue."""
    return _references(data, workflow, _is_model_string)


def name_references_from_json(data: object, workflow: Path) -> list:
    """Autres chaînes courtes, susceptibles de désigner un dossier de modèle LLM."""
    return _references(data, workflow, _is_name_string)


def scan_workflows(folder: Path) -> WorkflowScan:
    return scan_workflow_dirs([folder])


def scan_workflow_dirs(folders: list) -> WorkflowScan:
    """Lit les workflows de plusieurs dossiers ; un dossier absent est ignoré,
    un même fichier atteint par deux dossiers n'est lu qu'une fois."""
    scan = WorkflowScan()
    paths, seen = [], set()
    for folder in folders:
        folder = Path(folder)
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*.json")):
            key = os.path.normcase(os.path.realpath(path))
            if key not in seen and path.is_file():
                seen.add(key)
                paths.append(path)
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            refs = references_from_json(data, path)
            names = name_references_from_json(data, path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            scan.skipped.append((path, str(exc)))
            continue
        scan.workflow_count += 1
        scan.references.extend(refs)
        scan.name_references.extend(names)
    return scan
