"""Main PySide6 application window."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
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
from ..core.scanner_store import ScannerStore
from ..modules.color_analysis import ColorAnalysis, ColorProgress, ColorSummary
from ..modules.image_dimensions import DimensionProgress, DimensionSummary, ImageDimensions
from ..modules.scanner import Scanner, ScanProgress, ScanSummary
from .color_analysis_worker import ColorAnalysisWorker
from .image_dimensions_worker import ImageDimensionsWorker
from .results_browser import ResultsBrowser
from .scanner_worker import ScannerWorker


class MainWindow(QMainWindow):
    """Main application window with Scanner, Color Analysis, Image Dimensions and maintenance tools."""

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
        self.scanner_thread = None
        self.scanner_worker = None
        self.color_thread = None
        self.color_worker = None
        self.dimension_thread = None
        self.dimension_worker = None
        self.scan_started_at = None
        self.color_started_at = None
        self.dimension_started_at = None
        self._last_scan_progress = None
        self._last_color_progress = None
        self._last_dimension_progress = None

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._refresh_live_elapsed)

        self.setWindowTitle("AI-Sorter")
        self.resize(920, 1100)

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

        self.dimension_button = QPushButton("Read Image Dimensions", central)
        self.dimension_button.clicked.connect(self.start_image_dimensions)
        layout.addWidget(self.dimension_button)
        self.dimension_cancel_button = QPushButton("Cancel Image Dimensions", central)
        self.dimension_cancel_button.setEnabled(False)
        self.dimension_cancel_button.clicked.connect(self.cancel_image_dimensions)
        layout.addWidget(self.dimension_cancel_button)

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
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)
        self.scan_details = QLabel("Scanner is idle. Color Analysis is idle. Image Dimensions is idle.", central)
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
        for button in (
            self.scan_button,
            self.color_button,
            self.dimension_button,
            self.check_locations_button,
            self.cleanup_inactive_button,
            self.results_button,
            self.alldup_button,
        ):
            button.setEnabled(enabled)

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

    def start_image_dimensions(self) -> None:
        self.dimension_started_at = time.perf_counter()
        self._last_dimension_progress = None
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(True)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_details.setText("Image Dimensions is preparing…")
        self.statusBar().showMessage("Image Dimensions is preparing…")
        self.elapsed_timer.start()

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
        self._set_module_controls_enabled(False)
        self.scan_details.setText("Checking all active file locations…")
        self.statusBar().showMessage("Checking all file locations…")
        try:
            checked, missing = ScannerStore(self.database).check_all_locations()
            self._refresh_database_status()
            self.scan_details.setText(f"Location check finished.\n\nChecked: {checked}\nMarked missing: {missing}")
            QMessageBox.information(self, "File location check", f"Sprawdzono lokalizacje: {checked}\nOznaczono jako MISSING: {missing}")
        except Exception as exc:
            QMessageBox.critical(self, "File location check", str(exc))
        finally:
            self._set_module_controls_enabled(True)

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
        self._set_module_controls_enabled(False)
        self.scan_details.setText("Cleaning inactive Scanner data…")
        self.statusBar().showMessage("Cleaning inactive Scanner data…")
        try:
            removed_locations, removed_records = ScannerStore(self.database).cleanup_inactive()
            self._refresh_database_status()
            self.scan_details.setText(f"Inactive data cleanup finished.\n\nRemoved locations: {removed_locations}\nRemoved orphan file records: {removed_records}")
            QMessageBox.information(self, "Inactive Scanner data", f"Usunięte lokalizacje: {removed_locations}\nUsunięte osierocone rekordy plików: {removed_records}")
        except Exception as exc:
            QMessageBox.critical(self, "Inactive Scanner data", str(exc))
        finally:
            self._set_module_controls_enabled(True)

    def start_scan(self, root: Path) -> None:
        self.scan_started_at = time.perf_counter()
        self._last_scan_progress = None
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(True)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
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

    def start_color_analysis(self, root: Path) -> None:
        self.color_started_at = time.perf_counter()
        self._last_color_progress = None
        self._set_module_controls_enabled(False)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(True)
        self.dimension_cancel_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.scan_details.setText(f"Color Analysis is running…\nFolder: {root}\nElapsed: 00:00:00")
        self.statusBar().showMessage(f"Color Analysis is running for {root}…")
        self.elapsed_timer.start()
        analyzer = ColorAnalysis(self.database, scope_root=root)
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
        elif self.dimension_started_at and self._last_dimension_progress:
            self._render_dimension_progress(self._last_dimension_progress)

    def on_scan_progress(self, progress: ScanProgress) -> None:
        self._last_scan_progress = progress
        self._render_scan_progress(progress)

    def _render_scan_progress(self, progress: ScanProgress) -> None:
        elapsed = time.perf_counter() - self.scan_started_at if self.scan_started_at else 0.0
        scanned_rate = progress.scanned / elapsed if elapsed > 0 else 0.0
        skipped_rate = progress.skipped / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Scanner\nDiscovered: {progress.discovered}\nProcessed: {progress.processed}\n"
            f"Scanned: {progress.scanned} | Skipped: {progress.skipped} | Errors: {progress.failed}\n"
            f"Scanned rate: {scanned_rate:.1f} files/s | Skipped rate: {skipped_rate:.1f} files/s\n"
            f"Elapsed: {self._format_duration(elapsed)}\nDiscovery: {progress.current_discovery_path or '—'}\n"
            f"Last completed: {progress.last_completed_path or '—'}"
        )

    def on_color_progress(self, progress: ColorProgress) -> None:
        self._last_color_progress = progress
        self._render_color_progress(progress)

    def _render_color_progress(self, progress: ColorProgress) -> None:
        elapsed = time.perf_counter() - self.color_started_at if self.color_started_at else 0.0
        rate = progress.processed / elapsed if elapsed > 0 else 0.0
        self.scan_details.setText(
            f"Color Analysis\nConsidered: {progress.considered}\nProcessed: {progress.processed}\n"
            f"Errors: {progress.failed}\nRate: {rate:.1f} files/s\nElapsed: {self._format_duration(elapsed)}\n"
            f"Current: {progress.current_path or '—'}"
        )

    def on_dimension_progress(self, progress: DimensionProgress) -> None:
        self._last_dimension_progress = progress
        self._render_dimension_progress(progress)

    def _render_dimension_progress(self, progress: DimensionProgress) -> None:
        elapsed = time.perf_counter() - self.dimension_started_at if self.dimension_started_at else 0.0
        rate = progress.processed / elapsed if elapsed > 0 else 0.0
        self.progress.setRange(0, max(1, progress.total))
        self.progress.setValue(min(progress.processed, progress.total))
        percent = progress.processed / progress.total * 100 if progress.total else 100.0
        self.scan_details.setText(
            f"Image Dimensions\nProcessed: {progress.processed:,} / {progress.total:,} ({percent:.2f}%)\n"
            f"Updated: {progress.updated:,} | Errors: {progress.failed:,}\n"
            f"Rate: {rate:.1f} files/s | Elapsed: {self._format_duration(elapsed)}\n"
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
            f"{title}\n\nDiscovered: {summary.discovered}\nProcessed: {summary.processed}\n"
            f"Scanned: {summary.scanned}\nSaved: {summary.saved}\nSkipped: {summary.skipped}\n"
            f"Errors: {summary.failed}\nMissing: {summary.missing}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Discovery: {self._format_duration(summary.discovery_seconds)}\n"
            f"Hashing (worker time): {self._format_duration(summary.hash_seconds)}\n"
            f"Database: {self._format_duration(summary.database_seconds)}\n\n"
            f"Scanned rate: {scanned_rate:.1f} files/s\nSkipped rate: {skipped_rate:.1f} files/s\n"
            f"Processed rate: {processed_rate:.1f} files/s"
        )

    def on_scan_finished(self, summary: ScanSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.scan_started_at = None
        self._last_scan_progress = None
        self.scan_details.setText(self._format_scan_summary(summary, "Scanner finished." if not summary.cancelled else "Scanner cancelled safely."))

    def on_scan_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_started_at = None
        self._last_scan_progress = None
        self.scan_details.setText(f"Scanner could not finish. Reason: {message}")

    def on_color_finished(self, summary: ColorSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.color_started_at = None
        self._last_color_progress = None
        self.scan_details.setText(
            f"Color Analysis finished.\n\nConsidered: {summary.considered}\nProcessed: {summary.processed}\n"
            f"Skipped: {summary.skipped}\nErrors: {summary.failed}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}"
        )

    def on_color_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._set_module_controls_enabled(True)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
        self.color_started_at = None
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_details.setText(f"Color Analysis could not finish. Reason: {message}")

    def on_dimension_finished(self, summary: DimensionSummary) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.cancel_button.setEnabled(False)
        self.color_cancel_button.setEnabled(False)
        self.dimension_cancel_button.setEnabled(False)
        self.progress.setRange(0, max(1, summary.considered))
        self.progress.setValue(min(summary.processed, max(1, summary.considered)))
        self.dimension_started_at = None
        self._last_dimension_progress = None
        title = "Image Dimensions finished." if not summary.cancelled else "Image Dimensions cancelled safely."
        rate = summary.processed / summary.elapsed_seconds if summary.elapsed_seconds > 0 else 0.0
        self.statusBar().showMessage(title)
        self.scan_details.setText(
            f"{title}\n\nConsidered: {summary.considered}\nProcessed: {summary.processed}\n"
            f"Updated: {summary.updated}\nErrors: {summary.failed}\n\n"
            f"Total time: {self._format_duration(summary.elapsed_seconds)}\n"
            f"Processed rate: {rate:.1f} files/s"
        )

    def on_dimension_failed(self, message: str) -> None:
        self.elapsed_timer.stop()
        self._refresh_database_status()
        self._set_module_controls_enabled(True)
        self.dimension_cancel_button.setEnabled(False)
        self.dimension_started_at = None
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_details.setText(f"Image Dimensions could not finish. Reason: {message}")

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

    def _cleanup_dimension_thread(self) -> None:
        if self.dimension_thread:
            self.dimension_thread.deleteLater()
        if self.dimension_worker:
            self.dimension_worker.deleteLater()
        self.dimension_thread = None
        self.dimension_worker = None
