"""Détection des cartes vidéo et de leur mémoire, sans dépendance externe.

1. nvidia-smi (installé avec les pilotes NVIDIA) : nom et mémoire exacts.
2. Registre Windows (HardwareInformation.qwMemorySize) : toutes marques, valeur exacte
   au-delà de 4 Go (contrairement à WMI AdapterRAM, plafonné à 4 Go).
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

DISPLAY_CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"


@dataclass(frozen=True)
class Gpu:
    name: str
    memory: int  # octets


def exceeds_vram(size: int, vram: int | None) -> bool:
    """Vrai si la taille est supérieure ou égale à la mémoire vidéo connue."""
    return bool(vram) and size >= vram


def parse_nvidia_smi(output: str) -> list:
    """Lignes « nom, mémoire en Mio » de nvidia-smi --format=csv,noheader,nounits."""
    gpus = []
    for line in output.splitlines():
        name, sep, memory = line.rpartition(",")
        if not sep:
            continue
        try:
            mib = int(memory.strip())
        except ValueError:
            continue
        if name.strip() and mib > 0:
            gpus.append(Gpu(name.strip(), mib * 1024 * 1024))
    return gpus


def nvidia_gpus() -> list:
    executable = shutil.which("nvidia-smi")
    if executable is None and os.name == "nt":
        candidate = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvidia-smi.exe")
        executable = candidate if os.path.isfile(candidate) else None
    if executable is None:
        return []
    try:
        completed = subprocess.run(
            [executable, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_nvidia_smi(completed.stdout) if completed.returncode == 0 else []


def _as_int(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(bytes(value), "little")
    return 0


def gpus_from_registry_values(entries: list) -> list:
    """Cartes à partir des valeurs de registre de chaque adaptateur d'affichage."""
    gpus = []
    for values in entries:
        name = str(values.get("DriverDesc", "")).strip()
        memory = _as_int(values.get("HardwareInformation.qwMemorySize")) or \
            _as_int(values.get("HardwareInformation.MemorySize"))
        if name and memory > 0:
            gpus.append(Gpu(name, memory))
    return gpus


def _registry_entries() -> list:
    if sys.platform != "win32":
        return []
    import winreg

    entries = []
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, DISPLAY_CLASS_KEY)
    except OSError:
        return []
    with root:
        index = 0
        while True:
            try:
                sub = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            values = {}
            try:
                with winreg.OpenKey(root, sub) as key:
                    for name in ("DriverDesc", "HardwareInformation.qwMemorySize",
                                 "HardwareInformation.MemorySize"):
                        try:
                            values[name] = winreg.QueryValueEx(key, name)[0]
                        except OSError:
                            pass
            except OSError:
                continue
            entries.append(values)
    return entries


def registry_gpus() -> list:
    return gpus_from_registry_values(_registry_entries())


def detect_gpus() -> list:
    """Cartes NVIDIA (nvidia-smi) puis autres cartes du registre, triées par mémoire décroissante."""
    gpus = list(nvidia_gpus())
    known = {g.name.casefold() for g in gpus}
    gpus += [g for g in registry_gpus() if g.name.casefold() not in known]
    return sorted(gpus, key=lambda g: -g.memory)
