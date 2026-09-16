"""Safely correct image filename extensions using Image Format Check results."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .core.database import Database, DatabaseError

MODULE_ID = "image_format_check"
RESULT_KEY_PREFIX = "image_format_check:"
CANONICAL_EXTENSIONS = frozenset({".jpg", ".png", ".webp", ".gif", ".bmp"})
VALID_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF", "BMP"})

@dataclass(frozen=True, slots=True)
class ExtensionChangeProposal:
    source: Path
    destination: Path
    sha512: str
    detected_format: str
    reason: str

class ImageExtensionFixer:
    """Plan and execute extension-only corrections without overwriting files."""
    module_version = "0.1.1"
    TEMP_PREFIX = ".asrtmp-ext-"
    TEMP_SUFFIX = ".tmp"

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
             AND ar.result_key LIKE ?
            WHERE fl.location_status = 'ACTIVE' {root_sql}
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
                raise DatabaseError(f"Nie można odczytać wyniku kontroli rozszerzenia dla: {row['absolute_path']}") from exc
            canonical = payload.get("canonical_extension")
            detected = payload.get("detected_format")
            if not isinstance(canonical, str) or canonical.lower() not in CANONICAL_EXTENSIONS:
                continue
            if not isinstance(detected, str) or detected not in VALID_FORMATS:
                continue
            source = Path(str(row["absolute_path"])).absolute()
            destination = source.with_suffix(canonical.lower())
            source_key = self._path_key(source)
            destination_key = self._path_key(destination)
            if destination_key == source_key:
                continue
            if destination_key in destinations:
                raise FileExistsError(f"Zmiana rozszerzenia odrzucona: wiele plików wskazuje ten sam cel: {destination}")
            if not source.is_file():
                continue
            if destination.exists():
                raise FileExistsError(f"Zmiana rozszerzenia odrzucona, ponieważ plik docelowy już istnieje: {destination}")
            destinations.add(destination_key)
            matches = payload.get("matches")
            reason = (
                f"Image Format Check mismatch: {source.suffix.lower()} -> {canonical.lower()}"
                if matches is False
                else f"Image Format Check canonicalization: {source.suffix.lower()} -> {canonical.lower()}"
            )
            proposals.append(ExtensionChangeProposal(source, destination, str(row["sha512"]).lower(), detected, reason))
        self._validate(proposals)
        return proposals

    def execute(self, proposals: list[ExtensionChangeProposal]) -> int:
        if self._cancelled:
            return 0
        self._validate(proposals)
        if self._cancelled:
            return 0
        temporary: list[tuple[Path, Path, ExtensionChangeProposal]] = []
        completed: list[tuple[Path, Path, ExtensionChangeProposal]] = []
        try:
            for index, proposal in enumerate(proposals):
                if self._cancelled:
                    raise RuntimeError("Extension correction cancelled before filesystem changes completed.")
                if not proposal.source.is_file():
                    raise FileNotFoundError(f"Source file disappeared: {proposal.source}")
                if proposal.destination.exists():
                    raise FileExistsError(f"Destination appeared during extension correction: {proposal.destination}")
                temporary_path = proposal.source.with_name(f"{self.TEMP_PREFIX}{index:06d}{self.TEMP_SUFFIX}")
                if temporary_path.exists():
                    raise FileExistsError(f"Temporary path already exists: {temporary_path}")
                proposal.source.rename(temporary_path)
                temporary.append((temporary_path, proposal.destination, proposal))
            for temporary_path, destination, proposal in temporary:
                if destination.exists():
                    raise FileExistsError(f"Destination appeared before final rename: {destination}")
                temporary_path.rename(destination)
                completed.append((temporary_path, destination, proposal))
            self._update_database(completed)
            return len(completed)
        except Exception:
            for _temporary_path, destination, proposal in reversed(completed):
                try:
                    if destination.exists() and not proposal.source.exists():
                        destination.rename(proposal.source)
                except OSError:
                    pass
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
                raise FileExistsError(f"Refusing extension change because destination already exists: {proposal.destination}")

    def _update_database(self, completed: list[tuple[Path, Path, ExtensionChangeProposal]]) -> None:
        connection = self.database.connection
        if connection is None:
            raise DatabaseError("Baza danych projektu nie jest obecnie połączona.")
        try:
            with self.database.transaction() as connection:
                for _temporary_path, destination, proposal in completed:
                    source_text = str(proposal.source.resolve())
                    destination_text = str(destination.resolve())
                    row = connection.execute("SELECT sha512 FROM file_location WHERE absolute_path = ?", (source_text,)).fetchone()
                    if row is None:
                        raise DatabaseError(f"Nie znaleziono źródłowej lokalizacji w bazie danych: {source_text}")
                    if str(row["sha512"]).lower() != proposal.sha512:
                        raise DatabaseError(f"SHA-512 źródła zmieniło się przed aktualizacją bazy: {source_text}")
                    if connection.execute("SELECT 1 FROM file_location WHERE absolute_path = ?", (destination_text,)).fetchone() is not None:
                        raise DatabaseError(f"Docelowa lokalizacja pojawiła się w bazie danych: {destination_text}")
                    cursor = connection.execute(
                        "UPDATE file_location SET absolute_path = ?, location_status = 'ACTIVE' WHERE absolute_path = ? AND sha512 = ?",
                        (destination_text, source_text, proposal.sha512),
                    )
                    if cursor.rowcount != 1:
                        raise DatabaseError(f"Nie udało się zaktualizować lokalizacji po zmianie rozszerzenia: {destination_text}")
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError("Nie udało się zaktualizować bazy danych po zmianie rozszerzenia.") from exc
