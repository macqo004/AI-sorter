"""Application bootstrap and lifecycle."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox

from .core.compute import detect_compute_backend
from .core.database import Database, DatabaseError
from .core.paths import AppPaths
from .gui.main_window_simimages import MainWindow


class Application:
    """Owns the top-level application lifecycle."""

    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self.database = Database(paths.database)
        self.qt_app = QApplication.instance() or QApplication([])
        self.window: MainWindow | None = None

    def start(self) -> int:
        self.paths.ensure_runtime_directories()
        try:
            self.database.open()
            compute_backend = detect_compute_backend()
            self.window = MainWindow(
                self.paths.root,
                self.database,
                self.database.status(),
                compute_backend,
            )
            self.window.show()
            return self.qt_app.exec()
        except DatabaseError as exc:
            QMessageBox.critical(None, "Baza danych projektu", str(exc))
            return 1

    def shutdown(self) -> None:
        self.database.close()
