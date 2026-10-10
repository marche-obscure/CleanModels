"""Enchaînement complet de l'analyse d'une installation ComfyUI."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .i18n import Message
from .inventory import InventoryResult, scan_models
from .junk import find_junk
from .matching import UsageReport, match_usage
from .roots import RootsResult, collect_model_dirs, dir_key
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
    workflow_sources: list = field(default_factory=list)       # tous, même décochés
    excluded_workflow_sources: list = field(default_factory=list)
    excluded_model_dirs: list = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.inventory.files)


def run_analysis(
    comfy: Path,
    junk_patterns: list,
    progress: Callable[[str], None] | None = None,
    extra_workflow_dirs: list = (),
    excluded_dirs: set = frozenset(),
) -> AnalysisResult:
    """excluded_dirs : dir_key des dossiers (workflows ou modèles) décochés par l'utilisateur."""
    def step(key: str) -> None:
        if progress is not None:
            progress(Message(key))

    comfy = Path(comfy)
    step("step_dirs")
    all_roots = collect_model_dirs(comfy)
    roots = RootsResult(
        dirs=[d for d in all_roots.dirs if dir_key(d.path) not in excluded_dirs],
        missing=all_roots.missing,
        warnings=all_roots.warnings,
    )
    excluded_models = [d for d in all_roots.dirs if dir_key(d.path) in excluded_dirs]
    step("step_inventory")
    inventory = scan_models(roots.dirs)
    step("step_workflows")
    sources = workflow_sources(comfy, list(extra_workflow_dirs))
    excluded_sources = [s for s in sources if dir_key(s.path) in excluded_dirs]
    workflows = scan_workflow_dirs([s.path for s in sources if s not in excluded_sources])
    step("step_matching")
    usage = match_usage(
        inventory.files, workflows.references + workflows.name_references, inventory.aliases
    )
    step("step_junk")
    junk = find_junk(roots.dirs, junk_patterns)
    return AnalysisResult(comfy, roots, inventory, workflows, usage, junk, sources,
                          excluded_sources, excluded_models)
