"""Raccourci « CleanModels » sur le bureau Windows (bibliothèque standard + PowerShell)."""

import ctypes
import os
import subprocess
import sys
from pathlib import Path

from .i18n import Message

SHORTCUT_NAME = "CleanModels.lnk"
PROJECT_DIR = Path(__file__).resolve().parent.parent
ICON_PATH = PROJECT_DIR / "assets" / "cleanmodels.ico"
CSIDL_DESKTOPDIRECTORY = 0x10

# Les chemins passent par des variables d'environnement : pas de souci de guillemets ni d'accents.
_CREATE_SCRIPT = (
    "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:CM_LNK); "
    "$s.TargetPath = $env:CM_TARGET; "
    "$s.Arguments = $env:CM_ARGS; "
    "$s.WorkingDirectory = $env:CM_WORKDIR; "
    "if ($env:CM_ICON) { $s.IconLocation = $env:CM_ICON + ',0' }; "
    "$s.Description = 'CleanModels : nettoyage des modèles ComfyUI'; "
    "$s.Save()"
)


def desktop_dir() -> Path:
    """Vrai dossier Bureau de l'utilisateur (y compris redirigé vers OneDrive)."""
    if sys.platform == "win32":
        buffer = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buffer) == 0:
            return Path(buffer.value)
    return Path.home() / "Desktop"


def shortcut_path(desktop: Path | None = None) -> Path:
    return Path(desktop or desktop_dir()) / SHORTCUT_NAME


def exists(desktop: Path | None = None) -> bool:
    return shortcut_path(desktop).exists()


def _pythonw() -> Path:
    """pythonw.exe (pas de console) à côté de l'interpréteur courant, sinon l'interpréteur lui-même."""
    executable = Path(sys.executable)
    pythonw = executable.with_name("pythonw.exe")
    return pythonw if pythonw.exists() else executable


def create(desktop: Path | None = None) -> Path:
    """Crée le raccourci ; lève OSError en cas d'échec."""
    path = shortcut_path(desktop)
    if not path.parent.is_dir():
        raise OSError(Message("err_desktop_missing", path=path.parent))
    env = {
        **os.environ,
        "CM_LNK": str(path),
        "CM_TARGET": str(_pythonw()),
        "CM_ARGS": "-m cleanmodels",
        "CM_WORKDIR": str(PROJECT_DIR),
        "CM_ICON": str(ICON_PATH) if ICON_PATH.is_file() else "",
    }
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _CREATE_SCRIPT],
        env=env, capture_output=True, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0 or not path.exists():
        raise OSError(result.stderr.strip() or Message("err_shortcut_failed"))
    return path
