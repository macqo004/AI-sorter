"""Main-window extension adding read-only SimImages cache inspection."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from ..core.simimages_data_analyzer import SimImagesDataAnalyzer
from ..core.simimages_filesystem_probe import SimImagesFilesystemProbe
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

        anchor = getattr(self, "alldup_button", None)
        anchor_index = layout.indexOf(anchor) if anchor is not None else -1
        if anchor_index >= 0:
            layout.insertWidget(anchor_index + 1, self.simimages_button)
        else:
            layout.addWidget(self.simimages_button)

    def _set_module_controls_enabled(self, enabled: bool) -> None:
        super()._set_module_controls_enabled(enabled)
        if hasattr(self, "simimages_button"):
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
            database_path = Path(path)
            inspection = SimImagesDatabaseInspector().inspect(
                database_path,
                count_rows=False,
                sample_rows=3,
            )
            blob_analysis, time_analysis = SimImagesDataAnalyzer().analyze(
                database_path,
                sample_size=1000,
                max_preview_bytes=64,
                sample_display_count=10,
            )
            filesystem_analysis = SimImagesFilesystemProbe().analyze(
                database_path,
                sample_size=1000,
                max_rows_to_probe=5000,
                blob_sample_size=20,
            )

            report = inspection.format_text()
            extra_sections = [
                result.format_text()
                for result in (blob_analysis, time_analysis, filesystem_analysis)
                if result is not None
            ]
            if extra_sections:
                report += "\n\n" + "\n\n".join(extra_sections)

            dialog = QMessageBox(self)
            dialog.setWindowTitle("SimImages database inspection")
            dialog.setText(
                "Baza została odczytana w trybie tylko do odczytu.\n"
                "Sprawdzono także próbkę istniejących plików na dysku."
            )
            dialog.setDetailedText(report)
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "SimImages database inspection", str(exc))
