"""Main PySide6 application window."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFormLayout,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core.compute import ComputeBackend
from ..core.database import Database
from ..core.models import DatabaseStatus
from ..modules.scanner import Scanner, ScanProgress, ScanSummary
from .scanner_worker import ScannerWorker


class MainWindow(QMainWindow):
    """Foundation GUI with the first usable Scanner workflow."""

    def __init__(
        self,
        project_path: Path,
        database: Database,
        database_status: DatabaseStatus,
        compute_backend: ComputeBackend,
    ) -> None:
        super().__init__()
        self.database = database
        self.project_path = project_path
        self.compute_backend = compute_backend
        self.scanner_thread: QThread | None = None
        self.scanner_worker: ScannerWorker | None = None
        self.scan_started_at: float | None = None
        self.close_after_scan = False

        self.setWindowTitle("AI-Sorter")
        self.resize(920, 650)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("AI-Sorter", central))

        form = QFormLayout()
        self.database_status_label = QLabel(central)
        self.schema_label = QLabel(central)
        self.files_label = QLabel(central)
        self.locations_label = QLabel(central)
        self.modules_label = QLabel(central)
        self.executions_label = QLabel(central)
        form.addRow("Project", QLabel(str(project_path), central))
        form.addRow("Database", QLabel(database_status.path, central))
        form.addRow("Database status", self.database_status_label)
        form.addRow("Schema", self.schema_label)
        form.addRow("Files", self.files_label)
        form.addRow("Locations", self.locations_label)
        form.addRow("Modules", self.modules_label)
        form.addRow("Executions", self.executions_label)
        form.addRow("Compute backend", QLabel(compute_backend.display_name, central))
        layout.addLayout(form)

        self.scan_button = QPushButton("Scan folder…", central)
        self.scan_button.clicked.connect(self.select_scan_root)
        layout.addWidget(self.scan_button)

        self.cancel_button = QPushButton("Cancel scan", central)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        layout.addWidget(self.cancel_button)

        self.progress = QProgressBar(central)
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        self.scan_details = QLabel("Scanner is idle.", central)
        self.scan_details.setWordWrap(True)
        layout.addWidget(self.scan_details)

        self.setCentralWidget(central)
        status = QStatusBar(self)
        status.showMessage("Application started. Scanner is idle.")
        self.setStatusBar(status)
        self._apply_database_status(database_status)

    def _apply_database_status(self, status: DatabaseStatus) -> None:
        self.database_status_label.setText("● Connected" if status.connected else "● Disconnected")
        self.schema_label.setText(str(status.schema_version))
        self.files_label.setText(str(status.file_count))
        self.locations_label.setText(str(status.location_count))
        self.modules_label.setText(str(status.module_count))
        self.executions_label.setText(str(status.execution_count))

    def _refresh_database_status(self) -> None:
        self._apply_database_status(self.database.status())

    def select_scan_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose folder to scan")
        if root:
            self.start_scan(Path(root))

    def start_scan(self, root: Path) -> None:
        self.close_after_scan = False
        self.scan_started_at = time.perf_counter()
        self.scan_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, 0)
        self.scan_details.setText(f"Scanning: {root}\nElapsed: 0s")
        self.statusBar().showMessage("Scanner is running…")

        scanner = Scanner(self.database)
        self.scanner_thread = QThread(self)
        self.scanner_worker = ScannerWorker(scanner, root)
        self.scanner_worker.moveToThread(self.scanner_thread)
        self.scanner_thread.started.connect(self.scanner_worker.run)
        self.scanner_worker.progress.connect(self.on_scan_progress)
        self.scanner_worker.finished.connect(self.on_scan_finished)
        self.scanner_worker.failed.connect(self.on_scan_failed)
        self.scanner_worker.finished.connect(self.scanner_thread.quit)
        self.scanner_worker.failed.connect(self.scanner_thread.quit)
        self.scanner_thread.finished.connect(self._cleanup_scanner_thread)
        self.scanner_thread.start()

    def cancel_scan(self) -> None:
        if self.scanner_worker:
            self.scanner_worker.cancel()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancelling scanner…")

    def on_scan_progress(self, progress: ScanProgress) -> None:
        elapsed = int(time.perf_counter() - self.scan_started_at) if self.scan_started_at else 0
        rate = progress.processed / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Discovered: {progress.discovered}\n"
            f"Processed: {progress.processed}\n"
            f"Saved: {progress.saved} | Skipped: {progress.skipped} | Errors: {progress.failed}\n"
            f"Elapsed: {elapsed}s | Rate: {rate:.1f} files/s\n"
            f"Current: {progress.current_path or '—'}"
        )

    def _format_scan_summary(self, summary: ScanSummary, title: str) -> str:
        average = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        return (
            f"{title}\n\n"
            f"Discovered: {summary.discovered}\n"
            f"Processed: {summary.processed}\n"
            f"Saved: {summary.saved}\n"
            f"Skipped: {summary.skipped}\n"
            f"Errors: {summary.failed}\n"
            f"Missing: {summary.missing}\n\n"
            f"Total time: {summary.elapsed_seconds:.1f}s\n"
            f"Discovery: {summary.discovery_seconds:.1f}s\n"
            f"Hashing (worker time): {summary.hash_seconds:.1f}s\n"
            f"Database: {summary.database_seconds:.1f}s\n"
            f"Average: {average:.1f} files/s"
        )

    def on_scan_finished(self, summary: ScanSummary) -> None:
        self._refresh_database_status()
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.scan_started_at = None
        self.statusBar().showMessage("Scanner finished." if not summary.cancelled else "Scanner cancelled safely.")
        title = "Scanner finished." if not summary.cancelled else "Scanner cancelled safely."
        self.scan_details.setText(self._format_scan_summary(summary, title))
        if self.close_after_scan:
            self.close_after_scan = False
            QMessageBox.information(self, "Scanner summary", self._format_scan_summary(summary, title))

    def on_scan_failed(self, message: str) -> None:
        self._refresh_database_status()
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_started_at = None
        self.statusBar().showMessage("Scanner stopped because of an error.")
        self.scan_details.setText(f"Scanner could not finish. Reason: {message}")

    def _cleanup_scanner_thread(self) -> None:
        if self.scanner_thread:
            self.scanner_thread.deleteLater()
        if self.scanner_worker:
            self.scanner_worker.deleteLater()
        self.scanner_thread = None
        self.scanner_worker = None

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.scanner_worker and self.scanner_thread and self.scanner_thread.isRunning():
            answer = QMessageBox.question(
                self,
                "Scanner is running",
                "Skanowanie jest nadal w toku. Czy chcesz je bezpiecznie przerwać i zobaczyć podsumowanie?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.No:
                event.ignore()
                return
            self.close_after_scan = True
            self.scanner_worker.cancel()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancelling scanner… Please wait for the final summary.")
            event.ignore()
            return
        event.accept()
