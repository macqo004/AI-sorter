"""GUI extension for the Image Format / Extension Check module."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QPushButton

from ..image_extension_fixer import ImageExtensionFixer
from ..modules.image_format_check import FormatProgress, FormatSummary, ImageFormatCheck
from .image_extension_confirm_dialog import ImageExtensionConfirmDialog
from .image_extension_fixer_worker import ImageExtensionFixerWorker
from .image_format_check_worker import ImageFormatCheckWorker
from .path_memory import choose_directory
from .main_window_dimensions import MainWindow as BaseMainWindow


class MainWindow(BaseMainWindow):
    """Application window with Image Dimensions, AllDup import and format checking."""

    extension_apply_requested = Signal()

    def __init__(self, project_path: Path, database, database_status, compute_backend) -> None:
        self.format_thread: QThread | None = None
        self.format_worker: ImageFormatCheckWorker | None = None
        self.format_started_at: float | None = None
        self._last_format_progress: FormatProgress | None = None
        self.extension_thread: QThread | None = None
        self.extension_worker: ImageExtensionFixerWorker | None = None
        self.extension_started_at: float | None = None
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

        self.extension_button = QPushButton("Correct Image Extensions…", self.centralWidget())
        self.extension_button.clicked.connect(self.start_extension_correction)
        format_index = layout.indexOf(self.format_button)
        if format_index >= 0:
            layout.insertWidget(format_index + 1, self.extension_button)
        else:
            layout.addWidget(self.extension_button)

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
        if hasattr(self, "extension_button"):
            self.extension_button.setEnabled(enabled)
        self._refresh_stop_button_state()

    def _active_cancellable_worker(self):
        for attribute in (
            "scanner_worker",
            "color_worker",
            "dimension_worker",
            "format_worker",
            "extension_worker",
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
                "extension_worker",
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
        selected_root = choose_directory(
            self,
            "Choose folder for Image Format / Extension Check",
            self.project_path,
        )
        if selected_root is None:
            return

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
        details = (
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
        if summary.errors:
            details += "\n\nError details:\n" + "\n\n".join(summary.errors)
        self.scan_details.setText(details)
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

    def start_extension_correction(self) -> None:
        selected_root = choose_directory(
            self,
            "Choose folder for Image Extension Correction",
            self.project_path,
        )
        if selected_root is None:
            return

        self._stop_requested = False
        self.extension_started_at = time.perf_counter()
        self._set_module_controls_enabled(False)
        self._set_progress(0, 1, "Image Extension Correction")
        self.progress.setFormat("Planning…")
        self.scan_details.setText(
            f"Image Extension Correction\nFolder: {selected_root}\nPlanning safe extension changes…"
        )
        self.statusBar().showMessage(f"Preparing safe extension correction: {selected_root}")

        fixer = ImageExtensionFixer(self.database, root=selected_root)
        self.extension_thread = QThread(self)
        self.extension_worker = ImageExtensionFixerWorker(fixer)
        self.extension_worker.moveToThread(self.extension_thread)
        self.extension_thread.started.connect(self.extension_worker.plan)
        self.extension_worker.planned.connect(self.on_extension_planned)
        self.extension_worker.finished.connect(self.on_extension_finished)
        self.extension_worker.failed.connect(self.on_extension_failed)
        self.extension_worker.finished.connect(self.extension_thread.quit)
        self.extension_worker.failed.connect(self.extension_thread.quit)
        self.extension_thread.finished.connect(self._cleanup_extension_thread)
        self.extension_apply_requested.connect(self.extension_worker.execute)
        self.extension_thread.start()

    def on_extension_planned(self, proposals) -> None:
        if self._stop_requested:
            self.extension_thread.quit()
            return
        if not proposals:
            diagnostics = (
                self.extension_worker.fixer.last_plan_diagnostics
                if self.extension_worker is not None
                else None
            )
            report_path = None
            if diagnostics is not None and diagnostics.skipped_details:
                report_path = diagnostics.write_skipped_report(
                    self.project_path / "image_extension_correction_skipped.txt"
                )
            details = "Image Extension Correction\n\nNo safe extension changes were found."
            if diagnostics is not None:
                details += f"\n\nPlanning diagnostics:\n{diagnostics.format_text()}"
                if report_path is not None:
                    details += f"\n\nSkipped file details written to:\n{report_path}"
            self._set_module_controls_enabled(True)
            self._stop_requested = False
            self.scan_details.setText(details)
            self.statusBar().showMessage("No extension changes required.")
            self._set_idle_progress()
            self.extension_thread.quit()
            return

        dialog = ImageExtensionConfirmDialog(list(proposals), self)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if not accepted:
            self._set_module_controls_enabled(True)
            self._stop_requested = False
            self.scan_details.setText("Image Extension Correction\n\nOperation cancelled before any file was changed.")
            self.statusBar().showMessage("Extension correction cancelled before execution.")
            self._set_idle_progress()
            self.extension_thread.quit()
            return

        self.progress.setFormat("Applying…")
        self.scan_details.setText(
            f"Image Extension Correction\nApplying {len(proposals):,} safe extension changes…"
        )
        self.statusBar().showMessage("Applying extension changes — existing files will never be overwritten.")
        self.extension_apply_requested.emit()

    def on_extension_finished(self, changed: int) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.extension_started_at = None
        self._stop_requested = False
        self.scan_details.setText(
            "Image Extension Correction finished.\n\n"
            f"Files renamed: {changed:,}\n"
            "Image contents were not modified."
        )
        self.statusBar().showMessage(f"Extension correction finished: {changed:,} files renamed.")
        QMessageBox.information(self, "Image Extension Correction", self.scan_details.text())
        self._set_idle_progress()

    def on_extension_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.extension_started_at = None
        self._stop_requested = False
        self._set_idle_progress()
        self.scan_details.setText(
            "Image Extension Correction could not finish.\n\n"
            f"Reason: {message}"
        )
        QMessageBox.critical(self, "Image Extension Correction", message)

    def _cleanup_extension_thread(self) -> None:
        if self.extension_thread:
            self.extension_thread.deleteLater()
        if self.extension_worker:
            self.extension_worker.deleteLater()
        try:
            self.extension_apply_requested.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.extension_thread = None
        self.extension_worker = None
        self._refresh_stop_button_state()
