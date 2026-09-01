"""Reusable GUI helpers for Image Dimensions integration.

This module is intentionally separate so the existing MainWindow can adopt the
module without changing its existing lifecycle behavior.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QMessageBox

from ..core.database import Database
from ..modules.image_dimensions import ImageDimensions


def run_image_dimensions_dialog(parent: QMainWindow, database: Database) -> None:
    """Run Image Dimensions from a simple modal action.

    The dedicated module itself is worker-safe and resumable. The main window can
    call this helper when integrating the button into an existing UI.
    """
    reply = QMessageBox.question(
        parent,
        "Image Dimensions",
        "Uzupełnić brakujące wymiary obrazów (width × height) w bazie?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return
    try:
        summary = ImageDimensions(database).run()
        QMessageBox.information(
            parent,
            "Image Dimensions",
            f"Przetworzono: {summary.processed}\n"
            f"Uzupełniono: {summary.updated}\n"
            f"Błędy: {summary.failed}",
        )
    except Exception as exc:
        QMessageBox.critical(parent, "Image Dimensions", str(exc))
