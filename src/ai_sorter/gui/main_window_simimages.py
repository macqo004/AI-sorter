"""Main-window extension adding read-only SimImages cache inspection."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from ..core.simimages_inspector import SimImagesDatabaseInspector
from .main_window_dimensions import MainWindow as BaseMainWindow


class MainWindow(BaseMainWindow):
    """Application window with Image Dimensions, AllDup, and SimImages inspection."""

    def __init__(self, project_path: Path, database, database_status, compute_backend) -> None:
        super().__init__(project_path, database, database_status, compute_backend)

        layout = self.centralWidget().layout()
        if layout is None:
            raise RuntimeError("Main window layout is not available.")

        self.simimages_button = QPushButton("Inspect SimImages database…", self.centralWidget())
        self.simimages_button.clicked.connect(self.inspect_simimages_database)

        # Keep the diagnostic actions together near the existing AllDup controls.
        anchor = getattr(self, "alldup_button", None)
        anchor_index = layout.indexOf(anchor) if anchor is not None else -1
        if anchor_index >= 0:
            layout.insertWidget(anchor_index + 1, self.simimages_button)
        else:
            layout.addWidget(self.simimages_button)

    def _set_module_controls_enabled(self, enabled: bool) -> None:
        super()._set_module_controls_enabled(enabled)
        self.simimages_button.setEnabled(enabled)

    def inspect_simimages_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose SimImages database",
            str(Path.home() / "AppData" / "Local" / "SimilarImages"),
            "SQLite database (*.db);;All files (*.*)",
        )
        if not path:
            return

        try:
            inspection = SimImagesDatabaseInspector().inspect(
                Path(path),
                count_rows=False,
                sample_rows=3,
            )
            dialog = QMessageBox(self)
            dialog.setWindowTitle("SimImages database inspection")
            dialog.setText("Baza została odczytana w trybie tylko do odczytu.")
            dialog.setDetailedText(inspection.format_text())
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "SimImages database inspection", str(exc))
