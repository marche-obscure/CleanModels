"""Enchaînement complet de l'analyse d'une installation ComfyUI."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .inventory import InventoryResult, scan_models
from .junk import find_junk
from .matching import UsageReport, match_usage
from .roots import RootsResult, collect_model_dirs, workflows_dir
from .workflows import WorkflowScan, scan_workflows


@dataclass
class AnalysisResult:
    comfy: Path
    roots: RootsResult
    inventory: InventoryResult
    workflows: WorkflowScan
    usage: UsageReport
    junk: list

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.inventory.files)


def run_analysis(
    comfy: Path,
    junk_patterns: list,
    progress: Callable[[str], None] | None = None,
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
    workflows = scan_workflows(workflows_dir(comfy))
    step("Correspondance…")
    usage = match_usage(inventory.files, workflows.references)
    step("Fichiers parasites…")
    junk = find_junk(roots.dirs, junk_patterns)
    return AnalysisResult(comfy, roots, inventory, workflows, usage, junk)
