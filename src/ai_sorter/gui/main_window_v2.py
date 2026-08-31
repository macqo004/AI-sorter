"""Main PySide6 application window with determinate operation progress."""

from __future__ import annotations

import os
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
from ..modules.scanner import SUPPORTED_EXTENSIONS, ScanProgress, ScanSummary, Scanner
from .color_analysis_worker import ColorAnalysisWorker
from .maintenance_worker import MaintenanceWorker
from .results_browser import ResultsBrowser
from .scanner_worker import ScannerWorker


class MainWindow(QMainWindow):
    """Foundation GUI with real determinate progress for long-running operations."""

    def __init__(self, project_path: Path, database: Database, database_status: DatabaseStatus, compute_backend: ComputeBackend) -> None:
        super().__init__()
        self.database = database
        self.project_path = project_path
        self.compute_backend = compute_backend
        self.scanner_thread: QThread | None = None
        self.scanner_worker: ScannerWorker | None = None
        self.color_thread: QThread | None = None
        self.color_worker: ColorAnalysisWorker | None = None
        self.maintenance_thread: QThread | None = None
        self.maintenance_worker: MaintenanceWorker | None = None
        self.scan_started_at: float | None = None
        self.color_started_at: float | None = None
        self.maintenance_started_at: float | None = None
        self._last_scan_progress: ScanProgress | None = None
        self._last_color_progress: ColorProgress | None = None
        self._scan_total = 0
        self._color_total = 0
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._refresh_live_elapsed)

        self.setWindowTitle("AI-Sorter")
        self.resize(920, 1050)
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

        self.color_button = QPushButton("Run Color / BW Analysis…", central)
        self.color_button.clicked.connect(self.select_color_root)
        layout.addWidget(self.color_button)
        self.color_cancel_button = QPushButton("Cancel Color Analysis", central)
        self.color_cancel_button.setEnabled(False)
        self.color_cancel_button.clicked.connect(self.cancel_color_analysis)
        layout.addWidget(self.color_cancel_button)

        self.check_locations_button = QPushButton("Check all file locations", central)
        self.check_locations_button.clicked.connect(self.check_all_locations)
        layout.addWidget(self.check_locations_button)
        self.cleanup_inactive_button = QPushButton("Clean inactive Scanner data…", central)
        self.cleanup_inactive_button.clicked.connect(self.cleanup_inactive_data)
        layout.addWidget(self.cleanup_inactive_button)

        self.results_button = QPushButton("Browse database results…", central)
        self.results_button.clicked.connect(self.browse_results)
        layout.addWidget(self.results_button)
        self.alldup_button = QPushButton("Inspect AllDup database…", central)
        self.alldup_button.clicked.connect(self.inspect_alldup_database)
        layout.addWidget(self.alldup_button)

        self.progress = QProgressBar(central)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("Idle")
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
        self.check_locations_button.setEnabled(enabled)
        self.cleanup_inactive_button.setEnabled(enabled)
        self.results_button.setEnabled(enabled)
        self.alldup_button.setEnabled(enabled)

    def _set_progress(self, current: int, total: int, label: str) -> None:
        safe_total = max(1, int(total))
        safe_current = min(max(0, int(current)), safe_total)
        self.progress.setRange(0, safe_total)
        self.progress.setValue(safe_current)
        percent = (safe_current / safe_total) * 100.0
        self.progress.setFormat(f"{safe_current:,} / {safe_total:,} ({percent:.2f}%)")
        self.statusBar().showMessage(f"{label} — {safe_current:,} / {safe_total:,} ({percent:.2f}%)")

    def _set_idle_progress(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("Idle")

    def select_scan_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose folder to scan")
        if root:
            self.start_scan(Path(root))

    def select_color_root(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose folder for Color / BW analysis")
        if root:
            self.start_color_analysis(Path(root))

    def browse_results(self) -> None:
        ResultsBrowser(self.database, self).exec()

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

    def check_all_locations(self) -> None:
        reply = QMessageBox.question(
            self,
            "Check all file locations",
            "Sprawdzić istnienie wszystkich aktywnych lokalizacji plików w bazie?\n\n"
            "Operacja nie czyta zawartości plików i nie przelicza SHA-512.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._start_maintenance("check_locations", "Checking all file locations…")

    def cleanup_inactive_data(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clean inactive Scanner data",
            "Usunąć z bazy wszystkie nieaktywne lokalizacje oraz osierocone rekordy plików?\n\n"
            "Ta operacja NIE usuwa żadnych plików z dysku.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._start_maintenance("cleanup_inactive", "Cleaning inactive Scanner data…")

    def _start_maintenance(self, operation: str, label: str) -> None:
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.maintenance_started_at = time.perf_counter()
        self._set_progress(0, 1, label)
        self.progress.setFormat("Preparing…")
        self.scan_details.setText(f"{label}\nElapsed: 00:00:00")
        self.maintenance_thread = QThread(self)
        self.maintenance_worker = MaintenanceWorker(self.database, operation)
        self.maintenance_worker.moveToThread(self.maintenance_thread)
        self.maintenance_thread.started.connect(self.maintenance_worker.run)
        self.maintenance_worker.progress.connect(self.on_maintenance_progress)
        self.maintenance_worker.finished.connect(self.on_maintenance_finished)
        self.maintenance_worker.failed.connect(self.on_maintenance_failed)
        self.maintenance_worker.finished.connect(self.maintenance_thread.quit)
        self.maintenance_worker.failed.connect(self.maintenance_thread.quit)
        self.maintenance_thread.finished.connect(self._cleanup_maintenance_thread)
        self.maintenance_thread.start()

    def on_maintenance_progress(self, current: int, total: int, message: str) -> None:
        self._set_progress(current, total, message)
        elapsed = time.perf_counter() - self.maintenance_started_at if self.maintenance_started_at else 0.0
        self.scan_details.setText(f"{message}\nElapsed: {self._format_duration(elapsed)}")

    def on_maintenance_finished(self, result: object) -> None:
        elapsed = time.perf_counter() - self.maintenance_started_at if self.maintenance_started_at else 0.0
        self.maintenance_started_at = None
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self._set_idle_progress()
        self.scan_details.setText(f"Maintenance finished.\nElapsed: {self._format_duration(elapsed)}\n\n{result}")
        self.statusBar().showMessage("Maintenance finished.")
        QMessageBox.information(self, "Maintenance", f"Operacja zakończona.\n\n{result}")

    def on_maintenance_failed(self, message: str) -> None:
        self.maintenance_started_at = None
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self._set_idle_progress()
        self.scan_details.setText(f"Maintenance could not finish.\nReason: {message}")
        QMessageBox.critical(self, "Maintenance", message)

    def start_scan(self, root: Path) -> None:
        self.scan_started_at = time.perf_counter()
        self._last_scan_progress = None
        self._scan_total = self._count_supported_files(root)
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(True)
        self.color_cancel_button.setEnabled(False)
        self._set_progress(0, self._scan_total, "Scanner")
        self.scan_details.setText(f"Scanner\nTotal files: {self._scan_total:,}\nElapsed: 00:00:00")
        scanner = Scanner(self.database)
        self.elapsed_timer.start()
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

    def start_color_analysis(self, root: Path) -> None:
        self.color_started_at = time.perf_counter()
        self._last_color_progress = None
        self._color_total = self._count_color_targets(root)
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(True)
        self._set_progress(0, self._color_total, "Color Analysis")
        self.scan_details.setText(f"Color Analysis\nTotal targets: {self._color_total:,}\nElapsed: 00:00:00")
        analyzer = ColorAnalysis(self.database, scope_root=root)
        self.elapsed_timer.start()
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

    def on_scan_progress(self, progress: ScanProgress) -> None:
        self._last_scan_progress = progress
        current = min(progress.processed, self._scan_total)
        self._set_progress(current, self._scan_total, "Scanner")
        self._render_scan_progress(progress)

    def _render_scan_progress(self, progress: ScanProgress) -> None:
        elapsed = time.perf_counter() - self.scan_started_at if self.scan_started_at else 0.0
        scanned_rate = progress.scanned / elapsed if elapsed > 0 else 0.0
        skipped_rate = progress.skipped / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Scanner\nDiscovered: {progress.discovered:,}\nProcessed: {progress.processed:,}\n"
            f"Scanned: {progress.scanned:,} | Skipped: {progress.skipped:,} | Errors: {progress.failed:,}\n"
            f"Scanned rate: {scanned_rate:.1f} files/s | Skipped rate: {skipped_rate:.1f} files/s\n"
            f"Elapsed: {self._format_duration(elapsed)}\nDiscovery: {progress.current_discovery_path or '—'}\n"
            f"Last completed: {progress.last_completed_path or '—'}"
        )

    def on_color_progress(self, progress: ColorProgress) -> None:
        self._last_color_progress = progress
        current = min(progress.processed, self._color_total)
        self._set_progress(current, self._color_total, "Color Analysis")
        elapsed = time.perf_counter() - self.color_started_at if self.color_started_at else 0.0
        rate = progress.processed / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Color Analysis\nConsidered: {progress.considered:,}\nProcessed: {progress.processed:,}\n"
            f"Errors: {progress.failed:,}\nRate: {rate:.1f} files/s\nElapsed: {self._format_duration(elapsed)}\n"
            f"Current: {progress.current_path or '—'}"
        )

    def on_scan_finished(self, summary: ScanSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self._set_progress(summary.processed, max(self._scan_total, summary.processed, 1), "Scanner")
        self.scan_started_at = None
        title = "Scanner finished." if not summary.cancelled else "Scanner cancelled safely."
        self.statusBar().showMessage(title)
        self.scan_details.setText(self._format_scan_summary(summary, title))

    def on_scan_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.scan_started_at = None
        self.progress.setFormat("ERROR")
        self.scan_details.setText(f"Scanner could not finish. Reason: {message}")

    def on_color_finished(self, summary: ColorSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self._set_progress(summary.processed, max(self._color_total, summary.processed, 1), "Color Analysis")
        self.color_started_at = None
        title = "Color Analysis finished." if not summary.cancelled else "Color Analysis cancelled safely."
        self.statusBar().showMessage(title)
        self.scan_details.setText(self._format_color_summary(summary, title))

    def on_color_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.color_started_at = None
        self.progress.setFormat("ERROR")
        self.scan_details.setText(f"Color Analysis could not finish. Reason: {message}")

    def _count_supported_files(self, root: Path) -> int:
        total = 0
        stack = [root.resolve()]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in SUPPORTED_EXTENSIONS:
                                total += 1
                        except OSError:
                            continue
            except OSError:
                continue
        return total

    def _count_color_targets(self, root: Path) -> int:
        connection = self.database.connection
        if connection is None:
            return 0
        root_text = str(root.resolve()).rstrip("\\/")
        pattern = root_text + "\\%"
        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM (
                SELECT f.sha512
                FROM file_record AS f
                JOIN file_location AS fl
                  ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
                WHERE f.status = 'ACTIVE'
                  AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM analysis_result AS ar
                      WHERE ar.sha512 = f.sha512
                        AND ar.module_id = 'color_analysis'
                        AND ar.result_key = 'color_analysis'
                  )
                GROUP BY f.sha512
            )
            """,
            (root_text, pattern),
        ).fetchone()
        return int(row["count"] if row else 0)

    def _format_scan_summary(self, summary: ScanSummary, title: str) -> str:
        rate = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        return (
            f"{title}\n\nDiscovered: {summary.discovered:,}\nProcessed: {summary.processed:,}\n"
            f"Scanned: {summary.scanned:,}\nSaved: {summary.saved:,}\nSkipped: {summary.skipped:,}\n"
            f"Errors: {summary.failed:,}\nMissing: {summary.missing:,}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Processed rate: {rate:.1f} files/s"
        )

    def _format_color_summary(self, summary: ColorSummary, title: str) -> str:
        rate = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        return (
            f"{title}\n\nConsidered: {summary.considered:,}\nProcessed: {summary.processed:,}\n"
            f"Skipped: {summary.skipped:,}\nErrors: {summary.failed:,}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Processed rate: {rate:.1f} files/s"
        )

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _refresh_live_elapsed(self) -> None:
        if self.scan_started_at and self._last_scan_progress:
            self._render_scan_progress(self._last_scan_progress)
        elif self.color_started_at and self._last_color_progress:
            self.on_color_progress(self._last_color_progress)

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

    def _cleanup_maintenance_thread(self) -> None:
        if self.maintenance_thread:
            self.maintenance_thread.deleteLater()
        if self.maintenance_worker:
            self.maintenance_worker.deleteLater()
        self.maintenance_thread = None
        self.maintenance_worker = None
