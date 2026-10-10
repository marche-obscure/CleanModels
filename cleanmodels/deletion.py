"""Suppression définitive, avec revalidation juste avant chaque fichier et journal."""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .i18n import Message
from .inventory import file_key
from .junk import match_pattern
from .matching import FileIndex
from .workflows import scan_workflow_dirs


@dataclass(frozen=True)
class DeletionItem:
    path: Path
    size: int
    source: str  # "unused", "duplicates" ou "junk"


@dataclass
class DeletionResult:
    deleted: list = field(default_factory=list)
    refused: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    log_errors: list = field(default_factory=list)

    @property
    def freed_bytes(self) -> int:
        return sum(item.size for item in self.deleted)


Checker = Callable[[DeletionItem], "str | None"]


def unused_checker(workflow_folders: list, files: list, aliases: list = ()) -> Checker:
    """Refuse un fichier qu'un workflow cite au moment de la suppression.

    Seuls les fichiers encore présents sont indexés : une référence dont la cible
    exacte a disparu retombe sur les copies de même nom. Si un workflow est illisible,
    toute suppression est refusée, car ses références sont inconnues.
    """
    present = [f for f in files if os.path.isfile(f.path)]
    present_aliases = [(rel, f) for rel, f in aliases if os.path.isfile(f.path)]
    index = FileIndex(present, present_aliases)
    scan = scan_workflow_dirs(list(workflow_folders))
    referenced = {
        file_key(f.path)
        for ref in scan.references + scan.name_references
        for f in index.lookup(ref.value)
    }
    unreadable = len(scan.skipped)

    def check(item: DeletionItem) -> str | None:
        if unreadable:
            return Message("reason_unreadable", count=unreadable)
        return Message("reason_referenced") if file_key(item.path) in referenced else None

    return check


def fully_selected_groups(groups: list, selected: set) -> list:
    return [g for g in groups if all(file_key(f.path) in selected for f in g.files)]


def duplicates_checker(groups: list, selected: set) -> Checker:
    """Accepte une copie seulement si une autre copie non sélectionnée existe encore."""
    group_of = {file_key(f.path): g for g in groups for f in g.files}

    def check(item: DeletionItem) -> str | None:
        key = file_key(item.path)
        group = group_of.get(key)
        if group is None:
            return Message("reason_no_group")
        kept = [
            f for f in group.files
            if file_key(f.path) != key and file_key(f.path) not in selected and os.path.isfile(f.path)
        ]
        return None if kept else Message("reason_no_copy")

    return check


def junk_checker(patterns: list) -> Checker:
    def check(item: DeletionItem) -> str | None:
        return None if match_pattern(item.path.name, patterns) else Message("reason_pattern")

    return check


def _log(log_path: Path, item: DeletionItem, status: str, result: "DeletionResult") -> None:
    """Écrit une ligne de journal ; un échec d'écriture est noté sans interrompre la suppression."""
    stamp = datetime.now().isoformat(timespec="seconds")
    line = "\t".join([stamp, item.source, status, str(item.size), str(item.path)])
    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError as exc:
        result.log_errors.append(Message("log_not_written", path=item.path, status=status, error=exc))


def _precheck(item: DeletionItem) -> str | None:
    if not os.path.lexists(item.path):
        return Message("reason_missing")
    if not os.path.isfile(item.path):
        return Message("reason_not_file")
    if os.path.getsize(item.path) != item.size:
        return Message("reason_size")
    return None


def delete_files(items: list, checker: Checker, log_path: Path) -> DeletionResult:
    result = DeletionResult()
    for item in items:
        try:
            reason = _precheck(item) or checker(item)
        except OSError as exc:
            reason = Message("reason_check_failed", error=exc)
        if reason:
            result.refused.append((item, reason))
            _log(log_path, item, f"REFUSÉ: {reason}", result)
            continue
        try:
            os.remove(item.path)
        except OSError as exc:
            result.errors.append((item, str(exc)))
            _log(log_path, item, f"ERREUR: {exc}", result)
            continue
        result.deleted.append(item)
        _log(log_path, item, "SUPPRIMÉ", result)
    return result
