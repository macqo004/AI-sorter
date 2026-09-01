"""Qt worker for importing AllDup directly into the canonical Scanner database."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..alldup_full_import import AllDupFullImporter


class AllDupFullImportWorker(QObject):
    progress = Signal(int, int, int, int)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, importer: AllDupFullImporter, apply: bool = True) -> None:
        super().__init__()
        self.importer = importer
        self.apply = apply

    @Slot()
    def run(self) -> None:
        try:
            summary = self.importer.run(apply=self.apply, progress_callback=self._on_progress)
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _on_progress(self, current: int, total: int, imported: int, conflicts: int) -> None:
        self.progress.emit(current, total, imported, conflicts)
