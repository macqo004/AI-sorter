"""Qt worker for Image Format / Extension Check."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..modules.image_format_check import FormatProgress, ImageFormatCheck


class ImageFormatCheckWorker(QObject):
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, module: ImageFormatCheck) -> None:
        super().__init__()
        self.module = module

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self.module.run(self.progress.emit))
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.module.cancel()
