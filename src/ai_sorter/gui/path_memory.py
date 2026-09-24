"""Persistent filesystem path selection helpers for the GUI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog

_LAST_DIRECTORY_KEY = "ui/last_directory"
_SETTINGS_ORGANIZATION = "AI-Sorter"
_SETTINGS_APPLICATION = "AI-Sorter"


def _settings() -> QSettings:
    return QSettings(_SETTINGS_ORGANIZATION, _SETTINGS_APPLICATION)


def last_directory(fallback: Path) -> Path:
    """Return the last selected directory, falling back to a usable path."""
    settings = _settings()
    stored = str(settings.value(_LAST_DIRECTORY_KEY, "") or "").strip()
    if stored:
        stored_path = Path(stored)
        if stored_path.is_dir():
            return stored_path

    fallback = Path(fallback)
    if fallback.is_dir():
        return fallback
    return fallback.parent if fallback.parent.is_dir() else Path.home()


def choose_directory(parent, title: str, fallback: Path) -> Path | None:
    """Show a directory picker and persist the selected directory globally."""
    selected = QFileDialog.getExistingDirectory(
        parent,
        title,
        str(last_directory(fallback)),
        QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
    )
    if not selected:
        return None

    path = Path(selected)
    settings = _settings()
    settings.setValue(_LAST_DIRECTORY_KEY, str(path))
    settings.sync()
    return path
