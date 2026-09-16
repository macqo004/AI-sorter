"""GUI extension for the Image Format / Extension Check module."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from ..modules.image_format_check import FormatProgress, FormatSummary, ImageFormatCheck
from .image_format_check_worker import ImageFormatCheckWorker
from .main_window_dimensions import MainWindow as BaseMainWindow


class MainWindow(BaseMainWindow):
    """Application window with Image Dimensions, AllDup import and format checking."""

    def __init__(self, project_path: Path, database, database_status, compute_backend) -> None:
        self.format_thread: QThread | None = None
        self.format_worker: ImageFormatCheckWorker | None = None
        self.format_started_at: float | None = None
        self._last_format_progress: FormatProgress | None = None
        self._stop_requested = False
        super().__init__(project_path, database, database_status, compute_backend)
        self.scan_details.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        # Keep the legacy per-module cancel controls out of the UI. The actual
        # cancellation remains available through the single global STOP button.
        self.cancel_button.hide()
        self.color_cancel_button.hide()

        layout = self.centralWidget().layout()
        if layout is None:
            raise RuntimeError("Main window layout is not available.")

        self.format_button = QPushButton("Check Image Format / Extension…", self.centralWidget())
        self.format_button.clicked.connect(self.start_format_check)
        anchor = getattr(self, "dimension_button", None)
        anchor_index = layout.indexOf(anchor) if anchor is not None else -1
        if anchor_index >= 0:
            layout.insertWidget(anchor_index + 1, self.format_button)
        else:
            layout.addWidget(self.format_button)

        progress_index = layout.indexOf(self.progress)
        self.stop_button = QPushButton("STOP", self.centralWidget())
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_current_operation)
        if progress_index >= 0:
            layout.insertWidget(progress_index, self.stop_button)
        else:
            layout.addWidget(self.stop_button)

        self.stop_state_timer = QTimer(self)
        self.stop_state_timer.setInterval(100)
        self.stop_state_timer.timeout.connect(self._refresh_stop_button_state)
        self.stop_state_timer.start()

    def _set_module_controls_enabled(self, enabled: bool) -> None:
        super()._set_module_controls_enabled(enabled)
        if hasattr(self, "format_button"):
            self.format_button.setEnabled(enabled)
        self._refresh_stop_button_state()

    def _active_cancellable_worker(self):
        for attribute in (
            "scanner_worker",
            "color_worker",
            "dimension_worker",
            "format_worker",
            "renamer_worker",
        ):
            worker = getattr(self, attribute, None)
            if worker is not None and callable(getattr(worker, "cancel", None)):
                return worker
        return None

    def _refresh_stop_button_state(self) -> None:
        if not hasattr(self, "stop_button"):
            return
        active_workers = any(
            getattr(self, attribute, None) is not None
            for attribute in (
                "scanner_worker",
                "color_worker",
                "dimension_worker",
                "format_worker",
                "renamer_worker",
                "import_worker",
                "maintenance_worker",
            )
        )
        if not active_workers:
            self._stop_requested = False
            self.stop_button.setEnabled(False)
            return
        self.stop_button.setEnabled(not self._stop_requested and self._active_cancellable_worker() is not None)

    def stop_current_operation(self) -> None:
        worker = self._active_cancellable_worker()
        if worker is None:
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("The current operation cannot be interrupted safely.")
            return
        self._stop_requested = True
        self.stop_button.setEnabled(False)
        worker.cancel()
        self.statusBar().showMessage("Stopping current operation…")

    def start_format_check(self) -> None:
        root = QFileDialog.getExistingDirectory(
            self,
            "Choose folder for Image Format / Extension Check",
            str(self.project_path),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if not root:
            return
        selected_root = Path(root)

        self._stop_requested = False
        self.format_started_at = time.perf_counter()
        self._last_format_progress = None
        self._set_module_controls_enabled(False)
        self._set_progress(0, 1, "Image Format / Extension Check")
        self.progress.setFormat("Preparing…")
        self.scan_details.setText(
            f"Image Format / Extension Check\nFolder: {selected_root}\nPreparing…\nElapsed: 00:00:00"
        )
        self.statusBar().showMessage(f"Image Format / Extension Check is preparing: {selected_root}")

        module = ImageFormatCheck(self.database, root=selected_root)
        self.format_thread = QThread(self)
        self.format_worker = ImageFormatCheckWorker(module)
        self.format_worker.moveToThread(self.format_thread)
        self.format_thread.started.connect(self.format_worker.run)
        self.format_worker.progress.connect(self.on_format_progress)
        self.format_worker.finished.connect(self.on_format_finished)
        self.format_worker.failed.connect(self.on_format_failed)
        self.format_worker.finished.connect(self.format_thread.quit)
        self.format_worker.failed.connect(self.format_thread.quit)
        self.format_thread.finished.connect(self._cleanup_format_thread)
        self.format_thread.start()

    def on_format_progress(self, progress: FormatProgress) -> None:
        self._last_format_progress = progress
        self._set_progress(progress.processed, max(1, progress.total), "Image Format / Extension Check")
        elapsed = time.perf_counter() - self.format_started_at if self.format_started_at else 0.0
        rate = progress.processed / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            "Image Format / Extension Check\n"
            f"To check: {progress.total:,}\n"
            f"Already checked: {progress.skipped:,}\n"
            f"Processed: {progress.processed:,}\n"
            f"Matches: {progress.matches:,} | Mismatches: {progress.mismatches:,} | Errors: {progress.failed:,}\n"
            f"Rate: {rate:.1f} files/s | Elapsed: {self._format_duration(elapsed)}\n"
            f"Current: {progress.current_path or '—'}"
        )

    def on_format_finished(self, summary: FormatSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.format_started_at = None
        self._last_format_progress = None
        self._stop_requested = False
        self._set_progress(summary.processed, max(1, summary.considered), "Image Format / Extension Check")
        rate = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        title = (
            "Image Format / Extension Check cancelled."
            if summary.cancelled
            else "Image Format / Extension Check finished."
        )
        self.scan_details.setText(
            f"{title}\n\n"
            f"To check: {summary.considered:,}\n"
            f"Already checked: {summary.skipped:,}\n"
            f"Processed: {summary.processed:,}\n"
            f"Matches: {summary.matches:,}\n"
            f"Mismatches: {summary.mismatches:,}\n"
            f"Errors: {summary.failed:,}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Processed rate: {rate:.1f} files/s"
        )
        self.statusBar().showMessage(title)
        QMessageBox.information(self, "Image Format / Extension Check", self.scan_details.text())
        self._set_idle_progress()

    def on_format_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.format_started_at = None
        self._last_format_progress = None
        self._stop_requested = False
        self._set_idle_progress()
        self.scan_details.setText(f"Image Format / Extension Check could not finish.\nReason: {message}")
        QMessageBox.critical(self, "Image Format / Extension Check", message)

    def _cleanup_format_thread(self) -> None:
        if self.format_thread:
            self.format_thread.deleteLater()
        if self.format_worker:
            self.format_worker.deleteLater()
        self.format_thread = None
        self.format_worker = None
        self._refresh_stop_button_state()
