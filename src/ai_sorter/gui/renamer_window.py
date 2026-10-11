"""Main-window extension integrating the filesystem Renamer."""

from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QMessageBox, QPushButton

from ..modules.scanner import SUPPORTED_EXTENSIONS
from ..modules.dimension_grouper import (
    DimensionGrouper,
    DimensionGroupingPlan,
    DimensionGroupingSummary,
    GroupingProgress,
)
from .dimension_grouper_worker import DimensionGrouperWorker
from .main_window_format_check import MainWindow as BaseMainWindow
from .path_memory import choose_directory
from .renamer_confirm_dialog import RenamerConfirmDialog
from .renamer_worker_fixed import RenamerWorker


class MainWindow(BaseMainWindow):
    """Application window with the Renamer available as a safe plan-then-apply action."""

    renamer_apply_requested = Signal()
    dimension_group_apply_requested = Signal()

    def __init__(self, project_path: Path, database, database_status, compute_backend) -> None:
        self.renamer_thread: QThread | None = None
        self.renamer_worker: RenamerWorker | None = None
        self.renamer_started_at: float | None = None
        self._renamer_busy_frame = 0
        self.dimension_group_thread: QThread | None = None
        self.dimension_group_worker: DimensionGrouperWorker | None = None
        super().__init__(project_path, database, database_status, compute_backend)

        self._renamer_busy_timer = QTimer(self)
        self._renamer_busy_timer.setInterval(400)
        self._renamer_busy_timer.timeout.connect(self._refresh_renamer_busy_indicator)

        layout = self.centralWidget().layout()
        if layout is None:
            raise RuntimeError("Main window layout is not available.")

        self.renamer_button = QPushButton("Rename files…", self.centralWidget())
        self.renamer_button.clicked.connect(self.select_renamer_root)

        self.dimension_group_button = QPushButton("Group images by dimensions…", self.centralWidget())
        self.dimension_group_button.clicked.connect(self.start_dimension_grouping)

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
        layout.insertWidget(layout.indexOf(self.renamer_button) + 1, self.dimension_group_button)

    def _set_module_controls_enabled(self, enabled: bool) -> None:
        super()._set_module_controls_enabled(enabled)
        if hasattr(self, "renamer_button"):
            self.renamer_button.setEnabled(enabled)
        if hasattr(self, "dimension_group_button"):
            self.dimension_group_button.setEnabled(enabled)
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

    def start_dimension_grouping(self) -> None:
        root = choose_directory(
            self,
            "Choose folder for dimension grouping",
            self.project_path,
        )
        if root is None:
            return

        self._stop_requested = False
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        if hasattr(self, "dimension_cancel_button"):
            self.dimension_cancel_button.setEnabled(False)

        self._set_progress(0, 1, "Dimension Grouping")
        self.progress.setRange(0, 0)
        self.progress.setFormat("Planning…")
        self.scan_details.setText(
            f"Dimension Grouping\nFolder: {root}\nInspecting image dimensions without moving files…"
        )
        self.statusBar().showMessage("Dimension Grouping is preparing a safe move plan…")

        module = DimensionGrouper(self.database, root)
        self.dimension_group_thread = QThread(self)
        self.dimension_group_worker = DimensionGrouperWorker(module)
        self.dimension_group_worker.moveToThread(self.dimension_group_thread)
        self.dimension_group_thread.started.connect(self.dimension_group_worker.plan)
        self.dimension_group_worker.progress.connect(self.on_dimension_group_progress)
        self.dimension_group_worker.planned.connect(self.on_dimension_group_planned)
        self.dimension_group_worker.finished.connect(self.on_dimension_group_finished)
        self.dimension_group_worker.failed.connect(self.on_dimension_group_failed)
        self.dimension_group_worker.finished.connect(self.dimension_group_worker.deleteLater)
        self.dimension_group_worker.failed.connect(self.dimension_group_worker.deleteLater)
        self.dimension_group_worker.finished.connect(self.dimension_group_thread.quit)
        self.dimension_group_worker.failed.connect(self.dimension_group_thread.quit)
        self.dimension_group_thread.finished.connect(self._cleanup_dimension_group_thread)
        self.dimension_group_apply_requested.connect(self.dimension_group_worker.execute)
        self.dimension_group_thread.start()

    def on_dimension_group_progress(self, progress: GroupingProgress) -> None:
        if progress.phase == "planning" or progress.total <= 0:
            self.progress.setRange(0, 0)
            self.progress.setFormat("Inspecting dimensions…")
        else:
            self._set_progress(progress.processed, progress.total, "Dimension Grouping")
        self.scan_details.setText(
            f"Dimension Grouping — {progress.phase}\n"
            f"Processed: {progress.processed:,}"
            + (f" / {progress.total:,}" if progress.total > 0 else "")
            + f"\nMoved: {progress.moved:,} | Skipped: {progress.skipped:,} | Errors: {progress.failed:,}"
            + f"\nCurrent: {progress.current_path or '—'}"
        )

    def on_dimension_group_planned(self, plan: DimensionGroupingPlan) -> None:
        if plan.cancelled:
            self.scan_details.setText("Dimension Grouping cancelled during planning. No files were moved.")
            self.statusBar().showMessage("Dimension Grouping cancelled.")
            self._set_module_controls_enabled(True)
            if self.dimension_group_worker is not None:
                self.dimension_group_worker.deleteLater()
            if self.dimension_group_thread is not None:
                self.dimension_group_thread.quit()
            return

        if plan.planned_moves == 0:
            details = (
                "No safe moves found.\n\n"
                f"Images inspected: {plan.considered:,}\n"
                f"Unreadable images: {plan.unreadable:,}\n"
                f"Destination name conflicts: {plan.destination_conflicts:,}"
            )
            self.scan_details.setText(f"Dimension Grouping\n\n{details}")
            self.statusBar().showMessage("Dimension Grouping — no moves required.")
            QMessageBox.information(self, "Dimension Grouping", details)
            self._set_module_controls_enabled(True)
            if self.dimension_group_worker is not None:
                self.dimension_group_worker.deleteLater()
            if self.dimension_group_thread is not None:
                self.dimension_group_thread.quit()
            return

        dimension_lines = [
            f"{name}: {count:,}"
            for name, count in sorted(plan.by_dimension.items(), key=lambda item: (-item[1], item[0]))[:20]
        ]
        more = len(plan.by_dimension) - len(dimension_lines)
        details = (
            f"Folder: {plan.root}\n\n"
            f"Supported images inspected: {plan.considered:,}\n"
            f"Proposed moves: {plan.planned_moves:,}\n"
            f"Unreadable images: {plan.unreadable:,}\n"
            f"Destination name conflicts: {plan.destination_conflicts:,}\n\n"
            "Files will be moved into root-level folders named WIDTHxHEIGHT. "
            "Existing files will not be overwritten.\n\n"
            "Images per dimension (top groups):\n"
            + ("\n".join(dimension_lines) if dimension_lines else "—")
            + (f"\n… and {more:,} more dimension groups" if more > 0 else "")
        )
        answer = QMessageBox.question(
            self,
            "Confirm Dimension Grouping",
            details + "\n\nMove the files now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            self.scan_details.setText("Dimension Grouping cancelled before moving any files.")
            self.statusBar().showMessage("Dimension Grouping cancelled.")
            self._set_module_controls_enabled(True)
            if self.dimension_group_worker is not None:
                self.dimension_group_worker.deleteLater()
            if self.dimension_group_thread is not None:
                self.dimension_group_thread.quit()
            return

        self._set_progress(0, max(1, plan.considered), "Dimension Grouping")
        self.progress.setFormat("Moving files…")
        self.scan_details.setText(
            f"Dimension Grouping\nMoving up to {plan.planned_moves:,} files into dimension folders…"
        )
        self.statusBar().showMessage("Dimension Grouping — moving files and synchronizing the database.")
        self.dimension_group_apply_requested.emit()

    def on_dimension_group_finished(self, summary: DimensionGroupingSummary) -> None:
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self._stop_requested = False
        self._set_idle_progress()
        title = "Dimension Grouping cancelled." if summary.cancelled else "Dimension Grouping finished."
        details = (
            f"{title}\n\n"
            f"Images inspected: {summary.considered:,}\n"
            f"Files moved: {summary.moved:,}\n"
            f"Database locations updated: {summary.database_updated:,}\n"
            f"Database conflicts reconciled: {summary.database_conflicts_reconciled:,}\n"
            f"Skipped (existing destination): {summary.skipped_existing:,}\n"
            f"Unreadable images: {summary.unreadable:,}\n"
            f"Other errors: {summary.failed:,}\n"
            f"Elapsed: {self._format_duration(summary.elapsed_seconds)}"
        )
        self.scan_details.setText(details)
        self.statusBar().showMessage(title)
        QMessageBox.information(self, "Dimension Grouping", details)

    def on_dimension_group_failed(self, message: str) -> None:
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self._stop_requested = False
        self._set_idle_progress()
        self.scan_details.setText(f"Dimension Grouping could not finish.\nReason: {message}")
        self.statusBar().showMessage("Dimension Grouping failed.")
        QMessageBox.critical(self, "Dimension Grouping", message)

    def _cleanup_dimension_group_thread(self) -> None:
        thread = self.dimension_group_thread
        self.dimension_group_thread = None
        self.dimension_group_worker = None
        try:
            self.dimension_group_apply_requested.disconnect()
        except (RuntimeError, TypeError):
            pass
        if thread is not None:
            thread.deleteLater()

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
        root = choose_directory(self, "Choose folder to rename", self.project_path)
        if root is not None:
            self.start_renamer(root)

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

