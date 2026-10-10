"""Enchaînement complet de l'analyse d'une installation ComfyUI."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .inventory import InventoryResult, scan_models
from .junk import find_junk
from .matching import UsageReport, match_usage
from .roots import RootsResult, collect_model_dirs
from .scope import workflow_sources
from .workflows import WorkflowScan, scan_workflow_dirs


@dataclass
class AnalysisResult:
    comfy: Path
    roots: RootsResult
    inventory: InventoryResult
    workflows: WorkflowScan
    usage: UsageReport
    junk: list
    workflow_sources: list = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.inventory.files)


def run_analysis(
    comfy: Path,
    junk_patterns: list,
    progress: Callable[[str], None] | None = None,
    extra_workflow_dirs: list = (),
) -> AnalysisResult:
    def step(label: str) -> None:
        if progress is not None:
            progress(label)

    comfy = Path(comfy)
    step("Lecture des dossiers…")
    roots = collect_model_dirs(comfy)
    step("Inventaire des modèles…")
    inventory = scan_models(roots.dirs)
    step("Lecture des workflows…")
    sources = workflow_sources(comfy, list(extra_workflow_dirs))
    workflows = scan_workflow_dirs([s.path for s in sources])
    step("Correspondance…")
    usage = match_usage(
        inventory.files, workflows.references + workflows.name_references, inventory.aliases
    )
    step("Fichiers parasites…")
    junk = find_junk(roots.dirs, junk_patterns)
    return AnalysisResult(comfy, roots, inventory, workflows, usage, junk, sources)
