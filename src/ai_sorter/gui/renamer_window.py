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
        self._renamer_busy_timer = QTimer(self)
        self._renamer_busy_timer.setInterval(400)
        self._renamer_busy_timer.timeout.connect(self._refresh_renamer_busy_indicator)
        super().__init__(project_path, database, database_status, compute_backend)

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
        self.statusBar().showMessage(f"Renamer — processing{dots}")

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
