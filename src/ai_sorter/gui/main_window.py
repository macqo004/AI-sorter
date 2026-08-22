"""Main PySide6 application window."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer
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

from ..core.alldup_inspector import AllDupDatabaseInspector
from ..core.compute import ComputeBackend
from ..core.database import Database
from ..core.models import DatabaseStatus
from ..modules.color_analysis import ColorAnalysis, ColorProgress, ColorSummary
from ..modules.scanner import Scanner, ScanProgress, ScanSummary
from .color_analysis_worker import ColorAnalysisWorker
from .scanner_worker import ScannerWorker


class MainWindow(QMainWindow):
    """Foundation GUI with Scanner, Color Analysis and AllDup inspection workflows."""

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
        self.color_thread: QThread | None = None
        self.color_worker: ColorAnalysisWorker | None = None

        self.scan_started_at: float | None = None
        self.color_started_at: float | None = None
        self.close_after_scan = False
        self.close_after_color = False
        self._last_scan_progress: ScanProgress | None = None
        self._last_color_progress: ColorProgress | None = None

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._refresh_live_elapsed)

        self.setWindowTitle("AI-Sorter")
        self.resize(920, 900)

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

        self.color_button = QPushButton("Run Color / BW Analysis", central)
        self.color_button.clicked.connect(self.start_color_analysis)
        layout.addWidget(self.color_button)

        self.color_cancel_button = QPushButton("Cancel Color Analysis", central)
        self.color_cancel_button.setEnabled(False)
        self.color_cancel_button.clicked.connect(self.cancel_color_analysis)
        layout.addWidget(self.color_cancel_button)

        self.alldup_button = QPushButton("Inspect AllDup database…", central)
        self.alldup_button.clicked.connect(self.inspect_alldup_database)
        layout.addWidget(self.alldup_button)

        self.progress = QProgressBar(central)
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        self.scan_details = QLabel("Scanner is idle. Color Analysis is idle.", central)
        self.scan_details.setWordWrap(True)
        layout.addWidget(self.scan_details)

        self.setCentralWidget(central)
        status = QStatusBar(self)
        status.showMessage("Application started. No module is running.")
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

    def _set_module_controls_enabled(self, enabled: bool) -> None:
        self.scan_button.setEnabled(enabled)
        self.color_button.setEnabled(enabled)
        self.alldup_button.setEnabled(enabled)

    def select_scan_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose folder to scan")
        if root:
            self.start_scan(Path(root))

    def inspect_alldup_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose AllDup database",
            str(Path.home() / "AppData" / "Roaming" / "AllDup" / "db"),
            "SQLite database (*.adb *.db);;All files (*.*)",
        )
        if not path:
            return
        try:
            inspection = AllDupDatabaseInspector().inspect(Path(path), count_rows=False)
            dialog = QMessageBox(self)
            dialog.setWindowTitle("AllDup database inspection")
            dialog.setText("Baza została odczytana w trybie tylko do odczytu.")
            dialog.setDetailedText(inspection.format_text())
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "AllDup database inspection", str(exc))

    def start_scan(self, root: Path) -> None:
        self.close_after_scan = False
        self.scan_started_at = time.perf_counter()
        self._last_scan_progress = None
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(True)
        self.color_cancel_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.scan_details.setText(f"Scanning: {root}\nElapsed: 00:00:00")
        self.statusBar().showMessage("Scanner is running…")
        self.elapsed_timer.start()

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

    def start_color_analysis(self) -> None:
        self.close_after_color = False
        self.color_started_at = time.perf_counter()
        self._last_color_progress = None
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(True)
        self.progress.setRange(0, 0)
        self.scan_details.setText("Color Analysis is running…\nElapsed: 00:00:00")
        self.statusBar().showMessage("Color Analysis is running…")
        self.elapsed_timer.start()

        analyzer = ColorAnalysis(self.database)
        self.color_thread = QThread(self)
        self.color_worker = ColorAnalysisWorker(analyzer)
        self.color_worker.moveToThread(self.color_thread)
        self.color_thread.started.connect(self.color_worker.run)
        self.color_worker.progress.connect(self.on_color_progress)
        self.color_worker.finished.connect(self.on_color_finished)
        self.color_worker.failed.connect(self.on_color_failed)
        self.color_worker.finished.connect(self.color_thread.quit)
        self.color_worker.failed.connect(self.color_thread.quit)
        self.color_thread.finished.connect(self._cleanup_color_thread)
        self.color_thread.start()

    def cancel_color_analysis(self) -> None:
        if self.color_worker:
            self.color_worker.cancel()
            self.color_cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancelling Color Analysis…")

    def _refresh_live_elapsed(self) -> None:
        if self.scan_started_at and self._last_scan_progress:
            self._render_scan_progress(self._last_scan_progress)
        elif self.color_started_at and self._last_color_progress:
            self._render_color_progress(self._last_color_progress)

    def on_scan_progress(self, progress: ScanProgress) -> None:
        self._last_scan_progress = progress
        self._render_scan_progress(progress)

    def _render_scan_progress(self, progress: ScanProgress) -> None:
        elapsed = time.perf_counter() - self.scan_started_at if self.scan_started_at else 0.0
        scanned_rate = progress.scanned / elapsed if elapsed > 0 else 0.0
        skipped_rate = progress.skipped / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Scanner\n"
            f"Discovered: {progress.discovered}\n"
            f"Processed: {progress.processed}\n"
            f"Scanned: {progress.scanned} | Skipped: {progress.skipped} | Errors: {progress.failed}\n"
            f"Scanned rate: {scanned_rate:.1f} files/s | Skipped rate: {skipped_rate:.1f} files/s\n"
            f"Elapsed: {self._format_duration(elapsed)}\n"
            f"Discovery: {progress.current_discovery_path or '—'}\n"
            f"Last completed: {progress.last_completed_path or '—'}"
        )

    def on_color_progress(self, progress: ColorProgress) -> None:
        self._last_color_progress = progress
        self._render_color_progress(progress)

    def _render_color_progress(self, progress: ColorProgress) -> None:
        elapsed = time.perf_counter() - self.color_started_at if self.color_started_at else 0.0
        rate = progress.processed / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Color Analysis\n"
            f"Processed: {progress.processed}\n"
            f"Errors: {progress.failed}\n"
            f"Rate: {rate:.1f} files/s\n"
            f"Elapsed: {self._format_duration(elapsed)}\n"
            f"Current: {progress.current_path or '—'}"
        )

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _format_scan_summary(self, summary: ScanSummary, title: str) -> str:
        scanned_rate = summary.scanned / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        skipped_rate = summary.skipped / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        processed_rate = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        return (
            f"{title}\n\n"
            f"Discovered: {summary.discovered}\n"
            f"Processed: {summary.processed}\n"
            f"Scanned: {summary.scanned}\n"
            f"Saved: {summary.saved}\n"
            f"Skipped: {summary.skipped}\n"
            f"Errors: {summary.failed}\n"
            f"Missing: {summary.missing}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Discovery: {self._format_duration(summary.discovery_seconds)}\n"
            f"Hashing (worker time): {self._format_duration(summary.hash_seconds)}\n"
            f"Database: {self._format_duration(summary.database_seconds)}\n\n"
            f"Scanned rate: {scanned_rate:.1f} files/s\n"
            f"Skipped rate: {skipped_rate:.1f} files/s\n"
            f"Processed rate: {processed_rate:.1f} files/s"
        )

    def on_scan_finished(self, summary: ScanSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.scan_started_at = None
        self._last_scan_progress = None
        title = "Scanner finished." if not summary.cancelled else "Scanner cancelled safely."
        self.statusBar().showMessage(title)
        summary_text = self._format_scan_summary(summary, title)
        self.scan_details.setText(summary_text)
        if self.close_after_scan:
            self.close_after_scan = False
            QMessageBox.information(self, "Scanner summary", summary_text)

    def on_scan_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_started_at = None
        self._last_scan_progress = None
        self.statusBar().showMessage("Scanner stopped because of an error.")
        self.scan_details.setText(f"Scanner could not finish. Reason: {message}")

    def _format_color_summary(self, summary: ColorSummary, title: str) -> str:
        rate = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        return (
            f"{title}\n\n"
            f"Considered: {summary.considered}\n"
            f"Processed: {summary.processed}\n"
            f"Skipped: {summary.skipped}\n"
            f"Errors: {summary.failed}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Processed rate: {rate:.1f} files/s"
        )

    def on_color_finished(self, summary: ColorSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.color_started_at = None
        self._last_color_progress = None
        title = "Color Analysis finished." if not summary.cancelled else "Color Analysis cancelled safely."
        self.statusBar().showMessage(title)
        summary_text = self._format_color_summary(summary, title)
        self.scan_details.setText(summary_text)
        if self.close_after_color:
            self.close_after_color = False
            QMessageBox.information(self, "Color Analysis summary", summary_text)

    def on_color_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.color_started_at = None
        self._last_color_progress = None
        self.statusBar().showMessage("Color Analysis stopped because of an error.")
        self.scan_details.setText(f"Color Analysis could not finish. Reason: {message}")

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

        if self.color_worker and self.color_thread and self.color_thread.isRunning():
            answer = QMessageBox.question(
                self,
                "Color Analysis is running",
                "Color Analysis jest nadal w toku. Czy chcesz je bezpiecznie przerwać i zobaczyć podsumowanie?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.No:
                event.ignore()
                return
            self.close_after_color = True
            self.color_worker.cancel()
            self.color_cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancelling Color Analysis… Please wait for the final summary.")
            event.ignore()
            return

        self.elapsed_timer.stop()
        event.accept()
