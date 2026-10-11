"""Qt worker for Dimension Grouping without blocking the GUI."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..modules.dimension_grouper import (
    DimensionGrouper,
    DimensionGroupingPlan,
    DimensionGroupingSummary,
    GroupingProgress,
)


class DimensionGrouperWorker(QObject):
    progress = Signal(object)
    planned = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, module: DimensionGrouper) -> None:
        super().__init__()
        self.module = module
        self.plan_result: DimensionGroupingPlan | None = None

    @Slot()
    def plan(self) -> None:
        try:
            self.plan_result = self.module.plan(self._on_progress)
            self.planned.emit(self.plan_result)
        except Exception as exc:
            self.failed.emit(str(exc))

    @Slot()
    def execute(self) -> None:
        try:
            summary: DimensionGroupingSummary = self.module.execute(
                self.plan_result,
                self._on_progress,
            )
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    def cancel(self) -> None:
        self.module.cancel()

    def _on_progress(self, progress: GroupingProgress) -> None:
        self.progress.emit(progress)
