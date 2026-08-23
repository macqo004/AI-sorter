"""Database-backed results browser for module outputs."""

from __future__ import annotations

import csv
import json
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

from ..core.database import Database


class ResultsBrowser(QDialog):
    """Browse existing database records without running any module."""

    def __init__(self, database: Database, parent=None) -> None:
        super().__init__(parent)
        self.database = database
        self.rows: list[dict[str, object]] = []
        self.setWindowTitle("AI-Sorter – Database Results")
        self.resize(1200, 700)

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
        self.export_button = QPushButton("Export CSV…")
        self.export_button.clicked.connect(self.export_csv)
        controls.addWidget(self.export_button)
        layout.addLayout(controls)

        self.summary = QLabel("Choose a folder to inspect database results.")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels([
            "Path", "SHA512", "Size", "BW", "Mostly BW", "Monochrome", "Mostly Mono",
        ])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
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
        normalized = str(root.resolve()).rstrip("\\/")
        rows = connection.execute(
            """
            SELECT f.sha512, f.size_bytes, fl.absolute_path,
                   ar.payload_json
            FROM file_record AS f
            JOIN file_location AS fl
              ON fl.sha512 = f.sha512 AND fl.location_status = 'ACTIVE'
            LEFT JOIN analysis_result AS ar
              ON ar.sha512 = f.sha512
             AND ar.module_id = 'color_analysis'
             AND ar.result_key = 'color_analysis'
            WHERE f.status = 'ACTIVE'
              AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)
            ORDER BY fl.absolute_path
            """,
            (normalized, normalized + "\\%"),
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
        self.folder_label.setText(f"Folder: {normalized}")
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

    def export_csv(self) -> None:
        if not self.rows:
            QMessageBox.information(self, "Export CSV", "Najpierw wybierz folder z wynikami.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export results", "color-analysis-results.csv", "CSV files (*.csv)")
        if not path:
            return
        visible = [row for row in self.rows if self._matches_filter(row)]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(["path", "sha512", "size", "is_bw", "is_mostly_bw", "is_monochrome", "is_mostly_monochrome", "has_result"])
                for row in visible:
                    writer.writerow([
                        row["path"], row["sha512"], row["size"], row["bw"], row["mostly_bw"],
                        row["monochrome"], row["mostly_monochrome"], row["has_result"],
                    ])
            QMessageBox.information(self, "Export CSV", f"Wyniki zapisano do:\n{path}")
        except OSError as exc:
            QMessageBox.critical(self, "Export CSV", f"Nie udało się zapisać pliku CSV.\nPowód: {exc}")
