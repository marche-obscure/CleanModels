"""Extraction des références de modèles depuis les workflows ComfyUI (.json)."""

import json
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
    workflow_count: int = 0
    skipped: list = field(default_factory=list)


def _model_strings(value) -> list:
    """Chaînes ressemblant à un fichier modèle, sans doublon, dans l'ordre de rencontre."""
    found = []
    pending = [value]
    while pending:
        item = pending.pop(0)
        if isinstance(item, str):
            if item.strip().lower().endswith(MODEL_EXTENSIONS) and item not in found:
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


def references_from_json(data: object, workflow: Path) -> list:
    """Références d'un workflow déjà décodé. ValueError si la structure est inconnue."""
    refs = []
    if isinstance(data, dict) and isinstance(data.get("nodes"), list):
        for node in _ui_nodes(data):
            node_id, node_type = str(node.get("id", "")), str(node.get("type", ""))
            for value in _model_strings(node.get("widgets_values")):
                refs.append(Reference(value, workflow, node_id, node_type))
    elif isinstance(data, dict) and _is_api_format(data):
        for node_id, node in data.items():
            for value in _model_strings(node.get("inputs")):
                refs.append(Reference(value, workflow, str(node_id), str(node.get("class_type", ""))))
    else:
        raise ValueError("structure de workflow inconnue")
    return refs


def scan_workflows(folder: Path) -> WorkflowScan:
    scan = WorkflowScan()
    for path in sorted(Path(folder).rglob("*.json")):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            refs = references_from_json(data, path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            scan.skipped.append((path, str(exc)))
            continue
        scan.workflow_count += 1
        scan.references.extend(refs)
    return scan
