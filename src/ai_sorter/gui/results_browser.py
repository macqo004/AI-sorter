"""Database-backed results browser for module outputs."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..core.database import Database, DatabaseError
from ..core.module_result_cleanup import ModuleResultCleanup
from ..core.scanner_store import ScannerStore


class ResultsBrowser(QDialog):
    """Browse existing database records without running any module."""

    MODULE_ID = "color_analysis"
    RESULT_KEY = "color_analysis"

    def __init__(self, database: Database, parent=None) -> None:
        super().__init__(parent)
        self.database = database
        self.rows: list[dict[str, object]] = []
        self.selected_root: Path | None = None
        self.setWindowTitle("AI-Sorter – Database Results")
        self.resize(1400, 800)

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.folder_label = QLabel("Folder: not selected")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All",
            "BW",
            "Mostly BW",
            "Monochrome",
            "Mostly Monochrome",
            "No result",
        ])
        self.filter_combo.currentIndexChanged.connect(self.refresh_view)
        controls.addWidget(self.folder_label, 1)
        controls.addWidget(QLabel("Filter:"))
        controls.addWidget(self.filter_combo)
        self.choose_button = QPushButton("Choose folder…")
        self.choose_button.clicked.connect(self.choose_folder)
        controls.addWidget(self.choose_button)
        self.open_button = QPushButton("Open selected file")
        self.open_button.clicked.connect(self.open_selected_file)
        self.open_button.setEnabled(False)
        controls.addWidget(self.open_button)
        self.export_button = QPushButton("Export CSV…")
        self.export_button.clicked.connect(self.export_csv)
        controls.addWidget(self.export_button)
        self.clear_button = QPushButton("Clear Color Analysis results…")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setEnabled(False)
        controls.addWidget(self.clear_button)
        self.clear_scanner_button = QPushButton("Clear Scanner data for folder…")
        self.clear_scanner_button.clicked.connect(self.clear_scanner_data)
        self.clear_scanner_button.setEnabled(False)
        controls.addWidget(self.clear_scanner_button)
        layout.addLayout(controls)

        self.summary = QLabel("Choose a folder to inspect database results.")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels([
            "Path", "SHA512", "Size", "BW", "Mostly BW", "Monochrome", "Mostly Mono",
        ])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._update_open_button)
        self.table.doubleClicked.connect(self.open_selected_file)
        layout.addWidget(self.table)

    def choose_folder(self) -> None:
        root = QFileDialog.getExistingDirectory(self, "Choose folder to inspect")
        if root:
            self.load_folder(Path(root))

    def load_folder(self, root: Path) -> None:
        connection = self.database.connection
        if connection is None:
            QMessageBox.critical(self, "Database results", "Baza danych projektu nie jest obecnie połączona.")
            return
        normalized = root.resolve()
        self.selected_root = normalized
        root_text = str(normalized).rstrip("\\/")
        rows = connection.execute(
            """
            SELECT f.sha512, f.size_bytes, fl.absolute_path,
                   ar.payload_json
            FROM file_record AS f
            JOIN file_location AS fl
              ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
            LEFT JOIN analysis_result AS ar
              ON ar.sha512 = f.sha512
             AND ar.module_id = ?
             AND ar.result_key = ?
            WHERE f.status = 'ACTIVE'
              AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)
            ORDER BY fl.absolute_path
            """,
            (self.MODULE_ID, self.RESULT_KEY, root_text, root_text + "\\%"),
        ).fetchall()
        self.rows = []
        for row in rows:
            payload: dict[str, object] = {}
            if row["payload_json"]:
                try:
                    payload = json.loads(row["payload_json"])
                except (TypeError, ValueError):
                    payload = {}
            self.rows.append({
                "path": str(row["absolute_path"]),
                "sha512": str(row["sha512"]),
                "size": row["size_bytes"],
                "bw": bool(payload.get("is_bw", False)),
                "mostly_bw": bool(payload.get("is_mostly_bw", False)),
                "monochrome": bool(payload.get("is_monochrome", False)),
                "mostly_monochrome": bool(payload.get("is_mostly_monochrome", False)),
                "has_result": bool(row["payload_json"]),
            })
        self.folder_label.setText(f"Folder: {root_text}")
        self.clear_button.setEnabled(True)
        self.clear_scanner_button.setEnabled(True)
        self.refresh_view()

    def _matches_filter(self, row: dict[str, object]) -> bool:
        selected = self.filter_combo.currentText()
        if selected == "All":
            return True
        if selected == "No result":
            return not bool(row["has_result"])
        return bool(row[{
            "BW": "bw",
            "Mostly BW": "mostly_bw",
            "Monochrome": "monochrome",
            "Mostly Monochrome": "mostly_monochrome",
        }[selected]])

    def refresh_view(self) -> None:
        visible = [row for row in self.rows if self._matches_filter(row)]
        counts = {
            "BW": sum(bool(row["bw"]) for row in self.rows),
            "Mostly BW": sum(bool(row["mostly_bw"]) for row in self.rows),
            "Monochrome": sum(bool(row["monochrome"]) for row in self.rows),
            "Mostly Monochrome": sum(bool(row["mostly_monochrome"]) for row in self.rows),
            "No result": sum(not bool(row["has_result"]) for row in self.rows),
        }
        self.summary.setText(
            f"Records: {len(self.rows)} | Showing: {len(visible)} | "
            f"BW: {counts['BW']} | Mostly BW: {counts['Mostly BW']} | "
            f"Monochrome: {counts['Monochrome']} | Mostly Monochrome: {counts['Mostly Monochrome']} | "
            f"No result: {counts['No result']}"
        )
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(visible))
        for r, row in enumerate(visible):
            values = [
                str(row["path"]),
                str(row["sha512"]),
                str(row["size"] if row["size"] is not None else ""),
                "YES" if row["bw"] else "",
                "YES" if row["mostly_bw"] else "",
                "YES" if row["monochrome"] else "",
                "YES" if row["mostly_monochrome"] else "",
            ]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self._update_open_button()

    def _current_visible_rows(self) -> list[dict[str, object]]:
        return [row for row in self.rows if self._matches_filter(row)]

    def _update_open_button(self) -> None:
        self.open_button.setEnabled(bool(self.table.selectedItems()))

    def open_selected_file(self) -> None:
        if not self.table.selectedItems():
            QMessageBox.information(self, "Open file", "Najpierw wybierz plik z tabeli.")
            return
        row_index = self.table.currentRow()
        visible = self._current_visible_rows()
        if row_index < 0 or row_index >= len(visible):
            return
        path = Path(str(visible[row_index]["path"]))
        if not path.exists():
            QMessageBox.warning(
                self,
                "Open file",
                f"Plik nie został znaleziony na dysku:\n{path}\n\nWynik bazy pozostawiono bez zmian.",
            )
            return
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Open file",
                f"Nie udało się otworzyć pliku w domyślnej aplikacji.\nPowód: {exc}",
            )

    def clear_results(self) -> None:
        if self.selected_root is None:
            QMessageBox.information(self, "Clear results", "Najpierw wybierz folder.")
            return
        cleanup = ModuleResultCleanup(self.database)
        count = cleanup.count_results(self.MODULE_ID, self.RESULT_KEY, self.selected_root)
        if count == 0:
            QMessageBox.information(self, "Clear results", "W wybranym folderze nie ma wyników Color Analysis do usunięcia.")
            return
        answer = QMessageBox.question(
            self,
            "Clear Color Analysis results",
            f"Usunąć {count} wyników Color Analysis z wybranego folderu?\n\n"
            "Pliki, SHA512 i lokalizacje nie zostaną zmienione.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            deleted = cleanup.clear_results(self.MODULE_ID, self.RESULT_KEY, self.selected_root)
            self.load_folder(self.selected_root)
            QMessageBox.information(
                self,
                "Clear results",
                f"Usunięto {deleted} wyników Color Analysis. Możesz teraz uruchomić analizę ponownie.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Clear results", str(exc))

    def clear_scanner_data(self) -> None:
        if self.selected_root is None:
            QMessageBox.information(self, "Clear Scanner data", "Najpierw wybierz folder.")
            return
        connection = self.database.connection
        if connection is None:
            QMessageBox.critical(self, "Clear Scanner data", "Baza danych projektu nie jest obecnie połączona.")
            return
        root_text = str(self.selected_root).rstrip("\\/")
        try:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM file_location
                WHERE location_status IN ('ACTIVE', 'MISSING')
                  AND (absolute_path = ? OR absolute_path LIKE ?)
                """,
                (root_text, root_text + "\\%"),
            ).fetchone()
            location_count = int(row["count"])
        except Exception as exc:
            QMessageBox.critical(self, "Clear Scanner data", f"Nie udało się sprawdzić danych Scanner.\nPowód: {exc}")
            return
        if location_count == 0:
            QMessageBox.information(self, "Clear Scanner data", "W wybranym folderze nie ma danych Scanner do usunięcia.")
            return
        answer = QMessageBox.question(
            self,
            "Clear Scanner data",
            f"Usunąć dane Scanner dla {location_count} lokalizacji w tym folderze i podfolderach?\n\n"
            "Zostaną usunięte tylko wpisy z bazy. Pliki na dysku nie zostaną zmienione. "
            "Rekord SHA512 zostanie zachowany, jeśli ma inną lokalizację w bazie.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            locations, orphaned = ScannerStore(self.database).clear_folder(self.selected_root)
            self.load_folder(self.selected_root)
            QMessageBox.information(
                self,
                "Clear Scanner data",
                f"Usunięto {locations} lokalizacji Scanner.\n"
                f"Usunięto {orphaned} osieroconych rekordów plików wraz z wynikami przypisanymi do tych rekordów.",
            )
        except DatabaseError as exc:
            QMessageBox.critical(self, "Clear Scanner data", str(exc))

    def export_csv(self) -> None:
        if not self.rows:
            QMessageBox.information(self, "Export CSV", "Najpierw wybierz folder z wynikami.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export results",
            "color-analysis-results.csv",
            "CSV files (*.csv)",
        )
        if not path:
            return
        visible = self._current_visible_rows()
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow([
                    "path", "sha512", "size", "is_bw", "is_mostly_bw",
                    "is_monochrome", "is_mostly_monochrome", "has_result",
                ])
                for row in visible:
                    writer.writerow([
                        row["path"], row["sha512"], row["size"], row["bw"],
                        row["mostly_bw"], row["monochrome"], row["mostly_monochrome"],
                        row["has_result"],
                    ])
            QMessageBox.information(self, "Export CSV", f"Wyniki zapisano do:\n{path}")
        except OSError as exc:
            QMessageBox.critical(self, "Export CSV", f"Nie udało się zapisać pliku CSV.\nPowód: {exc}")
