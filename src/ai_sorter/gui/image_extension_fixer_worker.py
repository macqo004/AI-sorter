"""Qt worker for safe image filename-extension correction."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..image_extension_fixer import ExtensionChangeProposal, ImageExtensionFixer


class ImageExtensionFixerWorker(QObject):
    planned = Signal(object)
    finished = Signal(int)
    failed = Signal(str)

    def __init__(self, fixer: ImageExtensionFixer) -> None:
        super().__init__()
        self.fixer = fixer
        self.proposals: list[ExtensionChangeProposal] = []

    @Slot()
    def plan(self) -> None:
        try:
            self.proposals = self.fixer.plan()
            self.planned.emit(self.proposals)
        except Exception as exc:
            self.failed.emit(str(exc))

    @Slot()
    def execute(self) -> None:
        try:
            changed = self.fixer.execute(self.proposals)
            self.finished.emit(changed)
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.fixer.cancel()
