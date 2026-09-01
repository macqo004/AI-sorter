"""Qt worker for running Image Dimensions without blocking the GUI."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..modules.image_dimensions import DimensionProgress, DimensionSummary, ImageDimensions


class ImageDimensionsWorker(QObject):
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, module: ImageDimensions) -> None:
        super().__init__()
        self.module = module

    @Slot()
    def run(self) -> None:
        try:
            summary = self.module.run(self._on_progress)
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.module.cancel()

    def _on_progress(self, progress: DimensionProgress) -> None:
        self.progress.emit(progress)
