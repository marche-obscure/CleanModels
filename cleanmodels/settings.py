"""Réglages utilisateur, stockés en JSON versionné."""

import json
import os
from pathlib import Path

from .constants import CONFIG_VERSION, DEFAULT_JUNK_PATTERNS
from .i18n import DEFAULT_LANGUAGE, Message

SETTINGS_FILE = "settings.json"


def settings_dir() -> Path:
    """Dossier des réglages et du journal (créé si besoin)."""
    if os.environ.get("CLEANMODELS_HOME"):
        folder = Path(os.environ["CLEANMODELS_HOME"])
    elif os.environ.get("APPDATA"):
        folder = Path(os.environ["APPDATA"]) / "CleanModels"
    else:
        folder = Path.home() / ".cleanmodels"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _defaults() -> dict:
    return {
        "config_version": CONFIG_VERSION,
        "comfyui_path": "",
        "junk_patterns": list(DEFAULT_JUNK_PATTERNS),
        "extra_workflow_dirs": [],
        "language": DEFAULT_LANGUAGE,
        "theme": "light",
        "gpu": "",
        "vram_manual": 0,
        "desktop_shortcut_asked": False,
    }


def load_settings() -> tuple[dict, str | None]:
    """Renvoie (réglages, avertissement éventuel). Les clés inconnues sont conservées."""
    path = settings_dir() / SETTINGS_FILE
    data = _defaults()
    if not path.exists():
        return data, None
    try:
        stored = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(stored, dict):
            raise ValueError("le contenu n'est pas un objet JSON")
    except (OSError, ValueError) as exc:
        backup = path.with_name(SETTINGS_FILE + ".bak")
        try:
            os.replace(path, backup)
        except OSError:
            pass
        return data, Message("warn_settings_corrupt", error=exc, backup=backup.name)
    data.update(stored)
    # Mise à niveau : une version antérieure est portée à la version courante,
    # une version plus récente est conservée telle quelle.
    version = stored.get("config_version", 1)
    if not isinstance(version, int) or version < CONFIG_VERSION:
        data["config_version"] = CONFIG_VERSION
    return data, None


def save_settings(data: dict) -> None:
    """Écrit les réglages de façon atomique."""
    path = settings_dir() / SETTINGS_FILE
    tmp = path.with_name(SETTINGS_FILE + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
