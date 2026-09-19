"""Main-window extension integrating the filesystem Renamer."""

from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QMessageBox, QPushButton

from ..modules.scanner import SUPPORTED_EXTENSIONS
from .main_window_format_check import MainWindow as BaseMainWindow
from .renamer_confirm_dialog import RenamerConfirmDialog
from .renamer_worker_fixed import RenamerWorker


class MainWindow(BaseMainWindow):
    """Application window with the Renamer available as a safe plan-then-apply action."""

    renamer_apply_requested = Signal()

    def __init__(self, project_path: Path, database, database_status, compute_backend) -> None:
        self.renamer_thread: QThread | None = None
        self.renamer_worker: RenamerWorker | None = None
        self.renamer_started_at: float | None = None
        self._renamer_busy_frame = 0
        super().__init__(project_path, database, database_status, compute_backend)

        self._renamer_busy_timer = QTimer(self)
        self._renamer_busy_timer.setInterval(400)
        self._renamer_busy_timer.timeout.connect(self._refresh_renamer_busy_indicator)

        layout = self.centralWidget().layout()
        if layout is None:
            raise RuntimeError("Main window layout is not available.")

        self.renamer_button = QPushButton("Rename files…", self.centralWidget())
        self.renamer_button.clicked.connect(self.select_renamer_root)

        self.renamer_activity_label = QLabel("Renamer — processing.", self.centralWidget())
        self.renamer_activity_label.setVisible(False)
        progress_index = layout.indexOf(self.progress)
        if progress_index >= 0:
            layout.insertWidget(progress_index, self.renamer_activity_label)
        else:
            layout.addWidget(self.renamer_activity_label)

        anchor = getattr(self, "scan_button", None)
        anchor_index = layout.indexOf(anchor) if anchor is not None else -1
        if anchor_index >= 0:
            layout.insertWidget(anchor_index + 1, self.renamer_button)
        else:
            layout.addWidget(self.renamer_button)

    def _set_module_controls_enabled(self, enabled: bool) -> None:
        super()._set_module_controls_enabled(enabled)
        if hasattr(self, "renamer_button"):
            self.renamer_button.setEnabled(enabled)
        if enabled:
            self.renamer_started_at = None
            if hasattr(self, "_renamer_busy_timer"):
                self._renamer_busy_timer.stop()
            if hasattr(self, "renamer_activity_label"):
                self.renamer_activity_label.setVisible(False)
        elif self.renamer_started_at is not None:
            self._start_renamer_busy_indicator()

    def _count_supported_files(self, root: Path) -> int:
        """Count scanner-supported files for the GUI progress bar."""
        supported = {extension.lower() for extension in SUPPORTED_EXTENSIONS}
        total = 0
        for _dirpath, _dirnames, filenames in os.walk(root):
            total += sum(1 for name in filenames if Path(name).suffix.lower() in supported)
        return total

    def _refresh_renamer_busy_indicator(self) -> None:
        """Keep a visible activity indicator while the Renamer worker is alive."""
        if self.renamer_started_at is None:
            self._renamer_busy_timer.stop()
            if hasattr(self, "renamer_activity_label"):
                self.renamer_activity_label.setVisible(False)
            return
        self._renamer_busy_frame = (self._renamer_busy_frame + 1) % 4
        dots = "." * (self._renamer_busy_frame + 1)
        message = f"Renamer — processing{dots}"
        if hasattr(self, "renamer_activity_label"):
            self.renamer_activity_label.setText(message)
            self.renamer_activity_label.setVisible(True)
        self.statusBar().showMessage(message)

    def _start_renamer_busy_indicator(self) -> None:
        self._renamer_busy_frame = 0
        self._renamer_busy_timer.start()
        self._refresh_renamer_busy_indicator()

    def select_renamer_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose folder to rename")
        if root:
            self.start_renamer(Path(root))

    def start_renamer(self, root: Path) -> None:
        self.renamer_started_at = time.perf_counter()
        self._start_renamer_busy_indicator()
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        if hasattr(self, "dimension_cancel_button"):
            self.dimension_cancel_button.setEnabled(False)

        self._set_progress(0, 1, "Renamer")
        self.progress.setFormat("Planning…")
        self.scan_details.setText(
            f"Renamer\nPlanning filename changes for:\n{root}\n\n"
            "Rules: deterministic filename cleanup and conflict resolution."
        )
        self.statusBar().showMessage("Renamer is preparing a rename plan…")

        self.renamer_thread = QThread(self)
        self.renamer_worker = RenamerWorker(self.database, root)
        self.renamer_worker.moveToThread(self.renamer_thread)

        self.renamer_thread.started.connect(self.renamer_worker.plan)
        self.renamer_worker.progress.connect(self.on_renamer_progress)
        self.renamer_worker.planned.connect(self.on_renamer_planned)
        self.renamer_worker.finished.connect(self.on_renamer_finished)
        self.renamer_worker.failed.connect(self.on_renamer_failed)

        self.renamer_worker.finished.connect(self.renamer_worker.deleteLater)
        self.renamer_worker.failed.connect(self.renamer_worker.deleteLater)
        self.renamer_worker.finished.connect(self.renamer_thread.quit)
        self.renamer_worker.failed.connect(self.renamer_thread.quit)
        self.renamer_thread.finished.connect(self._cleanup_renamer_thread)

        self.renamer_apply_requested.connect(self.renamer_worker.execute)

        self.renamer_thread.start()

    def on_renamer_progress(self, current: int, total: int, message: str) -> None:
        elapsed = time.perf_counter() - self.renamer_started_at if self.renamer_started_at else 0.0
        if total > 0:
            self._set_progress(current, total, "Renamer")
            self.progress.setFormat(message)
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.progress.setFormat(message)
        self.scan_details.setText(
            f"Renamer\n{message}\nElapsed: {self._format_duration(elapsed)}"
        )

    def on_renamer_planned(self, summary: object) -> None:
        if self.renamer_worker is None:
            return

        data = summary if isinstance(summary, dict) else {}
        proposals = list(self.renamer_worker.proposals)

        scanned = int(data.get("scanned", len(proposals)))
        changed = int(data.get("changed", len(proposals)))
        unchanged = int(data.get("unchanged", max(0, scanned - changed)))
        skipped_missing = int(data.get("skipped_missing", 0))

        if not proposals:
            self.scan_details.setText(
                "Renamer — plan complete.\n\n"
                f"Scanned: {scanned:,}\n"
                f"Changes: 0\n"
                f"Unchanged: {unchanged:,}\n"
                f"Missing/skipped: {skipped_missing:,}"
            )
            self.statusBar().showMessage("Renamer — no changes required.")
            self._set_module_controls_enabled(True)
            self.renamer_thread.quit()
            return

        preview_lines = [
            f"{proposal.source}  →  {proposal.destination}\n    {proposal.reason}"
            for proposal in proposals
        ]
        summary_text = (
            f"Scanned: {scanned:,}\n"
            f"Changes: {changed:,}\n"
            f"Unchanged: {unchanged:,}\n"
            f"Missing/skipped: {skipped_missing:,}"
        )

        dialog = RenamerConfirmDialog(summary_text, preview_lines, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.scan_details.setText(
                "Renamer\n\nOperation cancelled before any file was changed."
            )
            self.statusBar().showMessage("Renamer cancelled before execution.")
            self._set_module_controls_enabled(True)
            if self.renamer_worker is not None:
                self.renamer_worker.deleteLater()
            self.renamer_thread.quit()
            return

        self.progress.setRange(0, max(1, changed))
        self.progress.setValue(0)
        self.progress.setFormat("Applying rename changes…")
        self.scan_details.setText(
            f"Renamer\nApplying {changed:,} rename changes…"
        )
        self.statusBar().showMessage(
            "Renamer — applying changes. Existing files will never be overwritten."
        )
        self.renamer_apply_requested.emit()

    def on_renamer_finished(self, result: object) -> None:
        data = result if isinstance(result, dict) else {}
        self._refresh_database_status()
        self._set_module_controls_enabled(True)

        renamed = int(data.get("renamed", 0))
        planned = int(data.get("planned", 0))
        database_updated = int(data.get("database_updated", 0))
        reconciled = int(data.get("database_reconciled_conflicts", 0))
        elapsed = float(data.get("elapsed_seconds", 0.0))

        details = (
            "Renamer finished.\n\n"
            f"Planned: {planned:,}\n"
            f"Renamed: {renamed:,}\n"
            f"Database updated: {database_updated:,}\n"
            f"Database conflicts reconciled: {reconciled:,}\n"
            f"Elapsed: {self._format_duration(elapsed)}"
        )
        self.scan_details.setText(details)
        self.statusBar().showMessage("Renamer finished.")
        self._set_idle_progress()
        QMessageBox.information(self, "Renamer", details)

    def on_renamer_failed(self, message: str) -> None:
        self._set_module_controls_enabled(True)
        self.scan_details.setText(f"Renamer could not finish.\nReason: {message}")
        self.statusBar().showMessage("Renamer failed.")
        self._set_idle_progress()
        QMessageBox.critical(self, "Renamer", message)

    def _cleanup_renamer_thread(self) -> None:
        thread = self.renamer_thread
        self.renamer_thread = None
        self.renamer_worker = None
        self.renamer_started_at = None
        if hasattr(self, "_renamer_busy_timer"):
            self._renamer_busy_timer.stop()
        if hasattr(self, "renamer_activity_label"):
            self.renamer_activity_label.setVisible(False)
        if thread is not None:
            thread.deleteLater()

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

