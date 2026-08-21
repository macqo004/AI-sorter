"""Qt worker for running Scanner without blocking the GUI thread."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..modules.scanner import ScanProgress, ScanSummary, Scanner


class ScannerWorker(QObject):
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, scanner: Scanner, root: Path) -> None:
        super().__init__()
        self.scanner = scanner
        self.root = root

    @Slot()
    def run(self) -> None:
        try:
            summary = self.scanner.scan(self.root, self._on_progress)
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.scanner.cancel()

    def _on_progress(self, progress: ScanProgress) -> None:
        self.progress.emit(progress)
