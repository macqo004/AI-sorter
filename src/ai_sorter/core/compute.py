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


def _has_nvidia_gpu() -> bool:
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


def _has_amd_gpu() -> bool:
    # ROCm/AMD-specific runtime detection is deliberately deferred until an
    # AI framework is introduced. This fallback only recognizes common tools.
    return any(_command_exists(command) for command in ("rocminfo", "rocm-smi"))


def detect_compute_backend() -> ComputeBackend:
    """Detect a safe baseline backend without requiring an AI framework."""
    if _has_nvidia_gpu():
        return ComputeBackend("cuda", "NVIDIA GPU (CUDA-ready)", True)
    if _has_amd_gpu():
        return ComputeBackend("amd", "AMD GPU (optional backend)", True)
    return ComputeBackend("cpu", "CPU", False)
