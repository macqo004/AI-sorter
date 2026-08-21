"""Portable application path handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Resolved paths belonging to one portable AI-Sorter installation."""

    root: Path

    @property
    def app(self) -> Path:
        return self.root / "app"

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def modules(self) -> Path:
        return self.root / "modules"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def temp(self) -> Path:
        return self.root / "temp"

    @property
    def database(self) -> Path:
        return self.data / "project.db"

    def ensure_runtime_directories(self) -> None:
        """Create all durable/runtime directories required by the baseline."""
        for path in (
            self.app,
            self.config,
            self.data,
            self.logs,
            self.cache,
            self.models,
            self.modules,
            self.backups,
            self.temp,
        ):
            path.mkdir(parents=True, exist_ok=True)


def detect_app_root() -> Path:
    """Return the directory containing the current source/executable."""
    return Path(__file__).resolve().parents[3]
