"""Main-window extension adding read-only SimImages cache inspection."""

from __future__ import annotations

import os
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

    def _count_supported_files(self, root: Path) -> int:
        count = 0
        try:
            for current, directories, files in os.walk(root):
                directories[:] = sorted(directories, key=str.casefold)
                count += sum(1 for name in files if Path(name).suffix.lower() in self._scanner_supported_extensions())
        except OSError:
            return count
        return count

    @staticmethod
    def _scanner_supported_extensions() -> frozenset[str]:
        return frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".pns"})

    def _count_color_targets(self, root: Path) -> int:
        connection = self.database.connection
        if connection is None:
            return 0
        root_text = str(root.resolve()).rstrip("\\/")
        pattern = root_text + "\\%"
        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM file_record AS f
            JOIN file_location AS fl ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
            WHERE f.status = 'ACTIVE'
              AND NOT EXISTS (
                    SELECT 1 FROM analysis_result AS ar
                    WHERE ar.sha512 = f.sha512
                      AND ar.module_id = 'color_analysis'
                      AND ar.result_key = 'color_analysis'
              )
              AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)
            """,
            (root_text, pattern),
        ).fetchone()
        return int(row["count"]) if row else 0

    def on_color_finished(self, summary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self._set_progress(summary.processed, max(getattr(self, "_color_total", 0), summary.processed, 1), "Color Analysis")
        self.color_started_at = None
        self._last_color_progress = None
        self.scan_details.setText(
            f"Color Analysis finished.\n\nConsidered: {summary.considered}\nProcessed: {summary.processed}\n"
            f"Skipped: {summary.skipped}\nErrors: {summary.failed}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}"
        )

    def on_color_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._set_module_controls_enabled(True)
        self.color_cancel_button.setEnabled(False)
        self.color_started_at = None
        self._last_color_progress = None
        self._set_idle_progress()
        self.scan_details.setText(f"Color Analysis could not finish. Reason: {message}")

    def _cleanup_maintenance_thread(self) -> None:
        if self.maintenance_thread:
            self.maintenance_thread.deleteLater()
        if self.maintenance_worker:
            self.maintenance_worker.deleteLater()
        self.maintenance_thread = None
        self.maintenance_worker = None

    def _cleanup_scanner_thread(self) -> None:
        if self.scanner_thread:
            self.scanner_thread.deleteLater()
        if self.scanner_worker:
            self.scanner_worker.deleteLater()
        self.scanner_thread = None
        self.scanner_worker = None

    def _cleanup_color_thread(self) -> None:
        if self.color_thread:
            self.color_thread.deleteLater()
        if self.color_worker:
            self.color_worker.deleteLater()
        self.color_thread = None
        self.color_worker = None

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
