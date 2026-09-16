"""Safely correct image filename extensions using Image Format Check results."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .core.database import Database, DatabaseError
from .core.scanner_store import ScannerStore


MODULE_ID = "image_format_check"
RESULT_KEY_PREFIX = "image_format_check:"


@dataclass(frozen=True, slots=True)
class ExtensionChangeProposal:
    source: Path
    destination: Path
    sha512: str
    detected_format: str
    reason: str


class ImageExtensionFixer:
    """Plan and execute extension-only corrections without overwriting files.

    The fixer trusts only persisted Image Format Check results. It never changes
    image contents and never invents a conflict suffix. Any occupied destination
    causes the whole plan to be rejected before filesystem changes begin.
    """

    module_version = "0.1.0"

    def __init__(self, database: Database, root: Path | None = None) -> None:
        self.database = database
        self.root = root.resolve() if root is not None else None
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @staticmethod
    def _path_key(path: Path) -> str:
        return os.path.normcase(os.path.abspath(str(path)))

    def plan(self) -> list[ExtensionChangeProposal]:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")

        root_sql = ""
        root_params: tuple[str, ...] = ()
        if self.root is not None:
            root = str(self.root).rstrip("\\/")
            root_sql = " AND (fl.absolute_path = ? OR fl.absolute_path LIKE ?)"
            root_params = (root, root + "\\%")

        rows = connection.execute(
            f"""
            SELECT fl.sha512, fl.absolute_path, ar.payload_json
            FROM file_location AS fl
            JOIN analysis_result AS ar
              ON ar.sha512 = fl.sha512
             AND ar.module_id = ?
             AND ar.result_key = ?
            WHERE fl.location_status = 'ACTIVE'
              {root_sql}
            ORDER BY fl.absolute_path
            """,
            (MODULE_ID, RESULT_KEY_PREFIX + ".jpg", *root_params),
        ).fetchall()

        # A single file can have different result rows for different extensions.
        # Query all extension-specific result keys instead of assuming .jpg.
        rows = connection.execute(
            f"""
            SELECT fl.sha512, fl.absolute_path, ar.result_key, ar.payload_json
            FROM file_location AS fl
            JOIN analysis_result AS ar
              ON ar.sha512 = fl.sha512
             AND ar.module_id = ?
             AND ar.result_key LIKE ?
            WHERE fl.location_status = 'ACTIVE'
              {root_sql}
            ORDER BY fl.absolute_path
            """,
            (MODULE_ID, RESULT_KEY_PREFIX + ".%", *root_params),
        ).fetchall()

        proposals: list[ExtensionChangeProposal] = []
        destinations: set[str] = set()
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise DatabaseError(
                    f"Nie można odczytać wyniku kontroli rozszerzenia dla: {row['absolute_path']}"
                ) from exc

            if payload.get("matches") is not False:
                continue
            canonical = payload.get("canonical_extension")
            detected = payload.get("detected_format")
            if not isinstance(canonical, str) or canonical.lower() not in {".jpg", ".png", ".webp", ".gif", ".bmp"}:
                continue
            if not isinstance(detected, str) or detected not in {"JPEG", "PNG", "WEBP", "GIF", "BMP"}:
                continue

            source = Path(str(row["absolute_path"])).absolute()
            destination = source.with_suffix(canonical.lower())
            source_key = self._path_key(source)
            destination_key = self._path_key(destination)

            if destination_key == source_key:
                continue
            if destination_key in destinations:
                raise FileExistsError(
                    f"Zmiana rozszerzenia odrzucona: wiele plików wskazuje ten sam cel: {destination}"
                )
            if destination.exists():
                raise FileExistsError(
                    f"Zmiana rozszerzenia odrzucona, ponieważ plik docelowy już istnieje: {destination}"
                )
            if not source.is_file():
                continue

            destinations.add(destination_key)
            proposals.append(
                ExtensionChangeProposal(
                    source=source,
                    destination=destination,
                    sha512=str(row["sha512"]).lower(),
                    detected_format=detected,
                    reason=f"Image Format Check: {source.suffix.lower()} -> {canonical.lower()}",
                )
            )

        return proposals

    def execute(self, proposals: list[ExtensionChangeProposal]) -> int:
        if self._cancelled:
            return 0
        self._validate(proposals)
        if self._cancelled:
            return 0

        temporary: list[tuple[Path, Path, ExtensionChangeProposal]] = []
        try:
            for index, proposal in enumerate(proposals):
                if self._cancelled:
                    raise RuntimeError("Extension correction cancelled before filesystem changes completed.")
                if not proposal.source.is_file():
                    raise FileNotFoundError(f"Source file disappeared: {proposal.source}")
                if proposal.destination.exists():
                    raise FileExistsError(
                        f"Destination appeared during extension correction: {proposal.destination}"
                    )
                temporary_path = proposal.source.with_name(
                    f".asrtmp-ext-{index:06d}.tmp"
                )
                if temporary_path.exists():
                    raise FileExistsError(f"Temporary path already exists: {temporary_path}")
                proposal.source.rename(temporary_path)
                temporary.append((temporary_path, proposal.destination, proposal))

            for temporary_path, destination, proposal in temporary:
                if destination.exists():
                    raise FileExistsError(
                        f"Destination appeared before final rename: {destination}"
                    )
                temporary_path.rename(destination)

            ScannerStore(self.database).update_renamed_locations(
                [(proposal.source, proposal.destination) for proposal in proposals]
            )
            return len(proposals)
        except Exception:
            for temporary_path, _destination, proposal in reversed(temporary):
                try:
                    if temporary_path.exists() and not proposal.source.exists():
                        temporary_path.rename(proposal.source)
                except OSError:
                    pass
            raise

    def _validate(self, proposals: list[ExtensionChangeProposal]) -> None:
        destinations: set[str] = set()
        for proposal in proposals:
            source_key = self._path_key(proposal.source)
            destination_key = self._path_key(proposal.destination)
            if source_key == destination_key:
                raise ValueError(f"Source and destination are identical: {proposal.source}")
            if destination_key in destinations:
                raise FileExistsError(f"Duplicate extension destination: {proposal.destination}")
            destinations.add(destination_key)
            if not proposal.source.is_file():
                raise FileNotFoundError(f"Source file does not exist: {proposal.source}")
            if proposal.destination.exists():
                raise FileExistsError(
                    f"Refusing extension change because destination already exists: {proposal.destination}"
                )
