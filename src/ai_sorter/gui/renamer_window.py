"""Main-window extension integrating the filesystem Renamer."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QPushButton

from .main_window_simimages import MainWindow as BaseMainWindow
from .renamer_confirm_dialog import RenamerConfirmDialog
from .renamer_worker_fixed import RenamerWorker


class MainWindow(BaseMainWindow):
    """Application window with the Renamer available as a safe plan-then-apply action."""

    renamer_apply_requested = Signal()

    def __init__(self, project_path: Path, database, database_status, compute_backend) -> None:
        self.renamer_thread: QThread | None = None
        self.renamer_worker: RenamerWorker | None = None
        self.renamer_started_at: float | None = None
        super().__init__(project_path, database, database_status, compute_backend)

        layout = self.centralWidget().layout()
        if layout is None:
            raise RuntimeError("Main window layout is not available.")

        self.renamer_button = QPushButton("Rename files…", self.centralWidget())
        self.renamer_button.clicked.connect(self.select_renamer_root)

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

    def select_renamer_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose folder to rename")
        if root:
            self.start_renamer(Path(root))

    def start_renamer(self, root: Path) -> None:
        self.renamer_started_at = time.perf_counter()
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        if hasattr(self, "dimension_cancel_button"):
            self.dimension_cancel_button.setEnabled(False)

        self._set_progress(0, 1, "Renamer")
        self.progress.setFormat("Planning…")
        self.scan_details.setText(
            f"Renamer\nPlanning filename changes for:\n{root}\n\n"
            "Rules: remove numeric duplicate suffixes; remove leading non-alphanumeric characters."
        )
        self.statusBar().showMessage("Renamer is preparing a rename plan…")

        self.renamer_thread = QThread(self)
        self.renamer_worker = RenamerWorker(self.database, root)
        self.renamer_worker.moveToThread(self.renamer_thread)
        self.renamer_thread.started.connect(self.renamer_worker.plan)
        self.renamer_worker.planned.connect(self.on_renamer_planned)
        self.renamer_worker.finished.connect(self.on_renamer_finished)
        self.renamer_worker.failed.connect(self.on_renamer_failed)
        self.renamer_worker.finished.connect(self.renamer_thread.quit)
        self.renamer_worker.failed.connect(self.renamer_thread.quit)
        self.renamer_thread.finished.connect(self._cleanup_renamer_thread)
        self.renamer_apply_requested.connect(self.renamer_worker.execute)
        self.renamer_thread.start()

    def on_renamer_planned(self, result: object) -> None:
        data = dict(result)
        scanned = int(data["scanned"])
        changed = int(data["changed"])
        unchanged = int(data["unchanged"])
        preview = list(data["preview"])

        elapsed = time.perf_counter() - self.renamer_started_at if self.renamer_started_at else 0.0
        summary = (
            "Plan Renamera gotowy.\n\n"
            f"Folder: {data['root']}\n"
            f"Przeskanowano: {scanned:,}\n"
            f"Do zmiany: {changed:,}\n"
            f"Bez zmian: {unchanged:,}\n\n"
            f"Czas przygotowania: {self._format_duration(elapsed)}\n\n"
            "Zmiany nie zostały jeszcze wykonane."
        )

        if changed == 0:
            self.elapsed_timer.stop()
            self._set_module_controls_enabled(True)
            self._set_idle_progress()
            self.scan_details.setText(summary)
            self.statusBar().showMessage("Renamer: no changes required.")
            QMessageBox.information(self, "Renamer", summary)
            if self.renamer_thread:
                self.renamer_thread.quit()
            return

        preview_limit = 100
        preview_lines = [
            f"{Path(source).name}  →  {Path(destination).name}"
            for source, destination, _reason in preview[:preview_limit]
        ]
        if len(preview) > preview_limit:
            preview_lines.append(f"… i {len(preview) - preview_limit:,} kolejnych zmian")

        dialog = RenamerConfirmDialog(summary, preview_lines, self)
        if dialog.exec() == QDialog.Accepted:
            self._set_progress(0, changed, "Renamer")
            self.progress.setFormat(f"Renaming 0 / {changed:,}")
            self.scan_details.setText(
                f"Renamer\nRenaming {changed:,} files…\n"
                f"Folder: {data['root']}"
            )
            self.statusBar().showMessage(f"Renamer is renaming {changed:,} files…")
            self.renamer_apply_requested.emit()
        else:
            self.elapsed_timer.stop()
            self._set_module_controls_enabled(True)
            self._set_idle_progress()
            self.scan_details.setText(summary + "\n\nOperacja anulowana przez użytkownika.")
            self.statusBar().showMessage("Renamer cancelled before applying changes.")
            if self.renamer_thread:
                self.renamer_thread.quit()

    def on_renamer_finished(self, result: object) -> None:
        data = dict(result)
        elapsed = float(data["elapsed_seconds"])
        planned = int(data["planned"])
        renamed = int(data["renamed"])
        database_updated = int(data["database_updated"])

        self.elapsed_timer.stop()
        self.renamer_started_at = None
        self._set_module_controls_enabled(True)
        self._set_idle_progress()
        self._refresh_database_status()
        self.scan_details.setText(
            "Renamer finished.\n\n"
            f"Zaplanowano: {planned:,}\n"
            f"Zmieniono: {renamed:,}\n"
            f"Zaktualizowano ścieżki w DB: {database_updated:,}\n"
            f"Błędy: 0\n\n"
            f"Czas: {self._format_duration(elapsed)}"
        )
        self.statusBar().showMessage("Renamer finished successfully.")
        QMessageBox.information(self, "Renamer", self.scan_details.text())

    def on_renamer_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self.renamer_started_at = None
        self._set_module_controls_enabled(True)
        self._set_idle_progress()
        self._refresh_database_status()
        self.scan_details.setText(f"Renamer could not finish.\n\nReason: {message}")
        self.statusBar().showMessage("Renamer failed.")
        QMessageBox.critical(self, "Renamer", message)

    def _cleanup_renamer_thread(self) -> None:
        if self.renamer_thread:
            self.renamer_thread.deleteLater()
        if self.renamer_worker:
            self.renamer_worker.deleteLater()
        self.renamer_thread = None
        self.renamer_worker = None
