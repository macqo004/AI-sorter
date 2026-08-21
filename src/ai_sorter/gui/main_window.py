"""Main PySide6 application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFormLayout, QLabel, QMainWindow, QStatusBar, QVBoxLayout, QWidget

from ..core.compute import ComputeBackend
from ..core.models import DatabaseStatus


class MainWindow(QMainWindow):
    """Minimal foundation window used by the first implementation milestone."""

    def __init__(
        self,
        project_path: Path,
        database_status: DatabaseStatus,
        compute_backend: ComputeBackend,
    ) -> None:
        super().__init__()
        self.setWindowTitle("AI-Sorter")
        self.resize(900, 600)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("AI-Sorter", central))

        form = QFormLayout()
        form.addRow("Project", QLabel(str(project_path), central))
        form.addRow("Database", QLabel(database_status.path, central))
        form.addRow(
            "Database status",
            QLabel("● Connected" if database_status.connected else "● Disconnected", central),
        )
        form.addRow("Schema", QLabel(str(database_status.schema_version), central))
        form.addRow("Files", QLabel(str(database_status.file_count), central))
        form.addRow("Locations", QLabel(str(database_status.location_count), central))
        form.addRow("Modules", QLabel(str(database_status.module_count), central))
        form.addRow("Executions", QLabel(str(database_status.execution_count), central))
        form.addRow("Compute backend", QLabel(compute_backend.display_name, central))
        layout.addLayout(form)

        self.setCentralWidget(central)

        status = QStatusBar(self)
        status.showMessage("Application started. No module is running.")
        self.setStatusBar(status)
