"""Main-window extension that adds the Image Dimensions operation to v2 GUI."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox, QPushButton

from ..modules.image_dimensions import DimensionProgress, DimensionSummary, ImageDimensions
from .image_dimensions_worker import ImageDimensionsWorker
from .main_window_v2 import MainWindow as BaseMainWindow


class MainWindow(BaseMainWindow):
    """v2 foundation GUI with Image Dimensions integrated into the live window."""

    def __init__(self, project_path: Path, database, database_status, compute_backend) -> None:
        self.dimension_thread: QThread | None = None
        self.dimension_worker: ImageDimensionsWorker | None = None
        self.dimension_started_at: float | None = None
        self._last_dimension_progress: DimensionProgress | None = None
        super().__init__(project_path, database, database_status, compute_backend)

        layout = self.centralWidget().layout()
        if layout is None:
            raise RuntimeError("Main window layout is not available.")

        self.dimension_button = QPushButton("Read Image Dimensions", self.centralWidget())
        self.dimension_button.clicked.connect(self.start_image_dimensions)
        progress_index = layout.indexOf(self.progress)
        if progress_index >= 0:
            layout.insertWidget(progress_index, self.dimension_button)
            self.dimension_cancel_button = QPushButton("Cancel Image Dimensions", self.centralWidget())
            self.dimension_cancel_button.setEnabled(False)
            self.dimension_cancel_button.clicked.connect(self.cancel_image_dimensions)
            layout.insertWidget(progress_index + 1, self.dimension_cancel_button)
        else:
            layout.addWidget(self.dimension_button)
            self.dimension_cancel_button = QPushButton("Cancel Image Dimensions", self.centralWidget())
            self.dimension_cancel_button.setEnabled(False)
            self.dimension_cancel_button.clicked.connect(self.cancel_image_dimensions)
            layout.addWidget(self.dimension_cancel_button)

    def _set_module_controls_enabled(self, enabled: bool) -> None:
        super()._set_module_controls_enabled(enabled)
        self.dimension_button.setEnabled(enabled)

    def start_image_dimensions(self) -> None:
        self.dimension_started_at = time.perf_counter()
        self._last_dimension_progress = None
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(True)
        self._set_progress(0, 1, "Image Dimensions")
        self.progress.setFormat("Preparing…")
        self.scan_details.setText("Image Dimensions is preparing…\nElapsed: 00:00:00")

        module = ImageDimensions(self.database)
        self.dimension_thread = QThread(self)
        self.dimension_worker = ImageDimensionsWorker(module)
        self.dimension_worker.moveToThread(self.dimension_thread)
        self.dimension_thread.started.connect(self.dimension_worker.run)
        self.dimension_worker.progress.connect(self.on_dimension_progress)
        self.dimension_worker.finished.connect(self.on_dimension_finished)
        self.dimension_worker.failed.connect(self.on_dimension_failed)
        self.dimension_worker.finished.connect(self.dimension_thread.quit)
        self.dimension_worker.failed.connect(self.dimension_thread.quit)
        self.dimension_thread.finished.connect(self._cleanup_dimension_thread)
        self.dimension_thread.start()

    def cancel_image_dimensions(self) -> None:
        if self.dimension_worker:
            self.dimension_worker.cancel()
            self.dimension_cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancelling Image Dimensions…")

    def on_dimension_progress(self, progress: DimensionProgress) -> None:
        self._last_dimension_progress = progress
        self._set_progress(progress.processed, max(1, progress.total), "Image Dimensions")
        elapsed = time.perf_counter() - self.dimension_started_at if self.dimension_started_at else 0.0
        rate = progress.processed / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Image Dimensions\n"
            f"Processed: {progress.processed:,} / {progress.total:,}\n"
            f"Updated: {progress.updated:,} | Errors: {progress.failed:,}\n"
            f"Rate: {rate:.1f} files/s | Elapsed: {self._format_duration(elapsed)}\n"
            f"Current: {progress.current_path or '—'}"
        )

    def _refresh_live_elapsed(self) -> None:
        if self.dimension_started_at and self._last_dimension_progress:
            self.on_dimension_progress(self._last_dimension_progress)
            return
        super()._refresh_live_elapsed()

    def on_dimension_finished(self, summary: DimensionSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
        total = max(1, summary.considered)
        self._set_progress(summary.processed, total, "Image Dimensions")
        self.dimension_started_at = None
        self._last_dimension_progress = None
        title = "Image Dimensions finished." if not summary.cancelled else "Image Dimensions cancelled safely."
        rate = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        self.statusBar().showMessage(title)
        self.scan_details.setText(
            f"{title}\n\n"
            f"Considered: {summary.considered:,}\n"
            f"Processed: {summary.processed:,}\n"
            f"Updated: {summary.updated:,}\n"
            f"Errors: {summary.failed:,}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Processed rate: {rate:.1f} files/s"
        )
        QMessageBox.information(self, "Image Dimensions", self.scan_details.text())
        self._set_idle_progress()

    def on_dimension_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
        self.dimension_started_at = None
        self._last_dimension_progress = None
        self._set_idle_progress()
        self.scan_details.setText(f"Image Dimensions could not finish. Reason: {message}")
        QMessageBox.critical(self, "Image Dimensions", message)

    def _cleanup_dimension_thread(self) -> None:
        if self.dimension_thread:
            self.dimension_thread.deleteLater()
        if self.dimension_worker:
            self.dimension_worker.deleteLater()
        self.dimension_thread = None
        self.dimension_worker = None
