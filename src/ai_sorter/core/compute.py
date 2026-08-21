"""Optional compute-backend detection for AI workloads."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass(frozen=True, slots=True)
class ComputeBackend:
    """Describes the preferred currently detectable local compute backend."""

    kind: str
    display_name: str
    hardware_available: bool


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _nvidia_available() -> bool:
    if not _command_exists("nvidia-smi"):
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _windows_video_controllers() -> list[str]:
    """Return Windows-reported display-controller names without extra packages."""
    if not _command_exists("powershell.exe"):
        return []
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Select-Object -ExpandProperty Name",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _amd_available() -> bool:
    names = _windows_video_controllers()
    if any("AMD" in name.upper() or "RADEON" in name.upper() for name in names):
        return True
    return any(_command_exists(command) for command in ("rocminfo", "rocm-smi"))


def detect_compute_backend() -> ComputeBackend:
    """Detect a safe baseline backend without requiring an AI framework."""
    if _nvidia_available():
        return ComputeBackend("cuda", "NVIDIA GPU (CUDA-ready)", True)
    if _amd_available():
        return ComputeBackend("amd", "AMD GPU (optional backend)", True)
    return ComputeBackend("cpu", "CPU", False)
