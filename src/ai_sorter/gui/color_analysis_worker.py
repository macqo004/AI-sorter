"""Qt worker for running Color Analysis without blocking the GUI."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..modules.color_analysis import ColorAnalysis, ColorProgress, ColorSummary


class ColorAnalysisWorker(QObject):
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, analyzer: ColorAnalysis) -> None:
        super().__init__()
        self.analyzer = analyzer

    @Slot()
    def run(self) -> None:
        try:
            summary = self.analyzer.run(self._on_progress)
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.analyzer.cancel()

    def _on_progress(self, progress: ColorProgress) -> None:
        self.progress.emit(progress)
