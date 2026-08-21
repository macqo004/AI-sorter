"""Main PySide6 application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QMainWindow, QStatusBar, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    """Minimal foundation window used by the first implementation milestone."""

    def __init__(self, project_path: Path, database_path: Path) -> None:
        super().__init__()
        self.setWindowTitle("AI-Sorter")
        self.resize(900, 600)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("AI-Sorter", central))
        layout.addWidget(QLabel(f"Project: {project_path}", central))
        layout.addWidget(QLabel(f"Database: {database_path}", central))
        self.setCentralWidget(central)

        status = QStatusBar(self)
        status.showMessage("Application started. No module is running.")
        self.setStatusBar(status)
