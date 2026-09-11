"""Qt worker for planning and executing filename renames without blocking the GUI."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..core.scanner_store import ScannerStore
from ..core.database import DatabaseError
from ..renamer import RenameProposal, RenamerEngine, iter_files


class RenamerWorker(QObject):
    """Run Renamer planning/execution on a worker thread."""

    planned = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, database, root: Path, recursive: bool = True) -> None:
        super().__init__()
        self.database = database
        self.root = root
        self.recursive = recursive
        self.engine = RenamerEngine()
        self.proposals: list[RenameProposal] = []

    @Slot()
    def plan(self) -> None:
        try:
            files = iter_files(self.root, recursive=self.recursive)
            self.proposals = self.engine.plan(files)
            self.planned.emit(
                {
                    "root": str(self.root),
                    "scanned": len(files),
                    "changed": len(self.proposals),
                    "unchanged": len(files) - len(self.proposals),
                    "preview": [
                        (str(p.source), str(p.destination), p.reason)
                        for p in self.proposals
                    ],
                }
            )
        except Exception as exc:
            self.failed.emit(f"Nie udało się przygotować planu Renamera: {exc}")

    def _reconcile_database_after_rename(
        self, paths: list[tuple[Path, Path]]
    ) -> tuple[int, int]:
        """Synchronize DB paths after the filesystem rename.

        A successful filesystem rename is authoritative here. If the destination
        already has stale DB rows for another SHA-512, those rows are removed so
        the renamed file can take ownership of the destination path. If the
        destination already belongs to the same SHA-512, the source location is
        merged into the existing destination location instead of failing.
        """
        if not paths:
            return 0, 0
        database = self.database
        if database.connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")

        reconciled_conflicts = 0
        updated = 0
        with database.transaction() as connection:
            for source, destination in paths:
                source_text = str(source.resolve())
                destination_text = str(destination.resolve())
                source_rows = connection.execute(
                    "SELECT DISTINCT sha512 FROM file_location WHERE absolute_path = ?",
                    (source_text,),
                ).fetchall()
                destination_rows = connection.execute(
                    "SELECT sha512 FROM file_location WHERE absolute_path = ?",
                    (destination_text,),
                ).fetchall()

                if source_rows:
                    source_shas = {str(row["sha512"]).lower() for row in source_rows}
                    if len(source_shas) != 1:
                        raise DatabaseError(
                            "Nie można jednoznacznie ustalić SHA-512 dla źródłowej lokalizacji: "
                            f"{source_text}"
                        )
                    source_sha = next(iter(source_shas))
                elif destination_rows:
                    # The DB may already have been reconciled by a previous retry.
                    # Do not create another location row in that case.
                    destination_shas = {str(row["sha512"]).lower() for row in destination_rows}
                    if len(destination_shas) == 1:
                        updated += 1
                        continue
                    raise DatabaseError(
                        "Nie można jednoznacznie ustalić SHA-512 dla docelowej lokalizacji: "
                        f"{destination_text}"
                    )
                else:
                    continue

                same_sha_destination = any(
                    str(row["sha512"]).lower() == source_sha for row in destination_rows
                )
                stale_destination_rows = [
                    row
                    for row in destination_rows
                    if str(row["sha512"]).lower() != source_sha
                ]

                if stale_destination_rows:
                    connection.execute(
                        "DELETE FROM file_location WHERE absolute_path = ? AND sha512 <> ?",
                        (destination_text, source_sha),
                    )
                    reconciled_conflicts += len(stale_destination_rows)

                if same_sha_destination:
                    connection.execute(
                        "DELETE FROM file_location WHERE absolute_path = ?",
                        (source_text,),
                    )
                    connection.execute(
                        "UPDATE file_location SET location_status = 'ACTIVE' WHERE absolute_path = ? AND sha512 = ?",
                        (destination_text, source_sha),
                    )
                else:
                    connection.execute(
                        "UPDATE file_location SET absolute_path = ?, location_status = 'ACTIVE' WHERE absolute_path = ? AND sha512 = ?",
                        (destination_text, source_text, source_sha),
                    )
                updated += 1

        return updated, reconciled_conflicts

    @Slot()
    def execute(self) -> None:
        try:
            started_at = time.perf_counter()
            executed = self.engine.execute(self.proposals)
            db_updated, db_reconciled_conflicts = self._reconcile_database_after_rename(
                [(proposal.source, proposal.destination) for proposal in executed]
            )
            self.finished.emit(
                {
                    "root": str(self.root),
                    "planned": len(self.proposals),
                    "renamed": len(executed),
                    "database_updated": db_updated,
                    "database_reconciled_conflicts": db_reconciled_conflicts,
                    "elapsed_seconds": time.perf_counter() - started_at,
                }
            )
        except Exception as exc:
            self.failed.emit(f"Renamer nie zakończył operacji: {exc}")
