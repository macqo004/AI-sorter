"""Read-only inspector and correlation utilities for AllDup SQLite databases."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AllDupColumn:
    name: str
    declared_type: str
    not_null: bool
    primary_key_position: int


@dataclass(frozen=True, slots=True)
class AllDupTable:
    name: str
    columns: tuple[AllDupColumn, ...]
    indexes: tuple[str, ...]
    row_count: int | None


@dataclass(frozen=True, slots=True)
class AllDupInspection:
    path: Path
    file_size_bytes: int
    sqlite_version: str
    wal_present: bool
    shm_present: bool
    tables: tuple[AllDupTable, ...]
    hash_candidates: tuple[tuple[str, str, str], ...]
    path_candidates: tuple[tuple[str, str, str], ...]
    size_candidates: tuple[tuple[str, str, str], ...]
    modified_candidates: tuple[tuple[str, str, str], ...]

    def format_text(self) -> str:
        lines = [
            "AllDup database inspection",
            f"Path: {self.path}",
            f"Database size: {self.file_size_bytes:,} bytes",
            f"SQLite: {self.sqlite_version}",
            f"WAL sidecar: {'present' if self.wal_present else 'not found'}",
            f"SHM sidecar: {'present' if self.shm_present else 'not found'}",
            f"Tables: {len(self.tables)}",
            "",
        ]
        for table in self.tables:
            count = "not counted" if table.row_count is None else f"{table.row_count:,}"
            lines.append(f"TABLE {table.name} — rows: {count}")
            for column in table.columns:
                flags = []
                if column.primary_key_position:
                    flags.append(f"PK#{column.primary_key_position}")
                if column.not_null:
                    flags.append("NOT NULL")
                suffix = f" [{', '.join(flags)}]" if flags else ""
                lines.append(f"  {column.name}: {column.declared_type or 'UNDECLARED'}{suffix}")
            if table.indexes:
                lines.append(f"  Indexes: {', '.join(table.indexes)}")
            lines.append("")

        def section(title: str, rows: tuple[tuple[str, str, str], ...]) -> None:
            lines.append(title)
            if not rows:
                lines.append("  none")
            else:
                for table, column, score in rows:
                    lines.append(f"  {table}.{column} ({score})")
            lines.append("")

        section("Hash candidates", self.hash_candidates)
        section("Path candidates", self.path_candidates)
        section("Size candidates", self.size_candidates)
        section("Modified-time candidates", self.modified_candidates)
        lines.append("Safety: database opened read-only; no schema or data writes are performed.")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class AllDupCorrelationRow:
    path: str
    our_sha512: str
    alldup_match: bool
    matching_algo_values: tuple[int, ...]
    all_algo_values: tuple[int, ...]
    matched_checksum_hex: str | None


@dataclass(frozen=True, slots=True)
class AllDupCorrelation:
    sample_size: int
    matched_paths: int
    checksum_matches: int
    checksum_mismatches: int
    no_hash_match: int
    rows: tuple[AllDupCorrelationRow, ...]

    def format_text(self) -> str:
        lines = [
            "AllDup ↔ AI-Sorter SHA512 correlation",
            "",
            f"Sample: {self.sample_size}",
            f"Paths found in AllDup: {self.matched_paths}",
            f"SHA512 matches: {self.checksum_matches}",
            f"SHA512 mismatches: {self.checksum_mismatches}",
            f"Files with no hasha row: {self.no_hash_match}",
            "",
            "Details:",
        ]
        for row in self.rows:
            if not row.alldup_match:
                state = "NO HASH ROW"
            elif row.matched_checksum_hex:
                state = "SHA512 MATCH"
            else:
                state = "HASH MISMATCH"
            matching = ",".join(str(v) for v in row.matching_algo_values) or "—"
            all_algos = ",".join(str(v) for v in row.all_algo_values) or "—"
            lines.append(
                f"  {state} | matching algo={matching} | all algo={all_algos} | {row.path}"
            )
        lines.append("")
        lines.append("Safety: both databases were opened read-only; no writes or checksum recalculation were performed.")
        return "\n".join(lines)


class AllDupDatabaseInspector:
    """Inspect an AllDup database without modifying it."""

    _HASH_NAMES = ("hash", "checksum", "sha", "digest", "md5", "sha1", "sha256", "sha512")
    _PATH_NAMES = ("path", "filename", "file_name", "filepath", "file_path", "fullpath", "full_path", "location")
    _SIZE_NAMES = ("size", "filesize", "file_size", "length", "bytes")
    _TIME_NAMES = ("mtime", "modified", "modified_at", "modify", "last_write", "lastmodified", "timestamp")

    def inspect(self, database_path: Path, count_rows: bool = False) -> AllDupInspection:
        database_path = database_path.resolve()
        if not database_path.is_file():
            raise ValueError(f"Plik bazy AllDup nie istnieje: {database_path}")
        if not self._looks_like_sqlite(database_path):
            raise ValueError(f"Plik nie wygląda na poprawną bazę SQLite: {database_path}")

        wal_present = database_path.with_name(database_path.name + "-wal").exists()
        shm_present = database_path.with_name(database_path.name + "-shm").exists()
        uri = f"file:{database_path.as_posix()}?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True, timeout=10)
            connection.row_factory = sqlite3.Row
            try:
                tables: list[AllDupTable] = []
                hash_candidates: list[tuple[str, str, str]] = []
                path_candidates: list[tuple[str, str, str]] = []
                size_candidates: list[tuple[str, str, str]] = []
                modified_candidates: list[tuple[str, str, str]] = []

                table_rows = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
                for table_row in table_rows:
                    table_name = str(table_row["name"])
                    columns = tuple(self._read_columns(connection, table_name))
                    indexes = tuple(self._read_indexes(connection, table_name))
                    row_count = self._count_rows(connection, table_name) if count_rows else None
                    tables.append(AllDupTable(table_name, columns, indexes, row_count))
                    for column in columns:
                        lowered = column.name.casefold()
                        declared = column.declared_type.casefold()
                        combined = f"{lowered} {declared}"
                        for score in self._score_column(combined, self._HASH_NAMES):
                            hash_candidates.append((table_name, column.name, score))
                        for score in self._score_column(combined, self._PATH_NAMES):
                            path_candidates.append((table_name, column.name, score))
                        for score in self._score_column(combined, self._SIZE_NAMES):
                            size_candidates.append((table_name, column.name, score))
                        for score in self._score_column(combined, self._TIME_NAMES):
                            modified_candidates.append((table_name, column.name, score))

                sqlite_version = str(connection.execute("SELECT sqlite_version() AS version").fetchone()["version"])
            finally:
                connection.close()
        except sqlite3.Error as exc:
            sidecars = []
            if wal_present:
                sidecars.append("-wal")
            if shm_present:
                sidecars.append("-shm")
            sidecar_text = ", ".join(sidecars) if sidecars else "none"
            raise RuntimeError(
                "Nie udało się odczytać bazy AllDup w trybie tylko do odczytu. "
                f"SQLite zgłosił: {exc}. Wykryte pliki towarzyszące: {sidecar_text}. "
                "Zamknij całkowicie AllDup i spróbuj ponownie. Baza nie została zmieniona."
            ) from exc

        return AllDupInspection(
            path=database_path,
            file_size_bytes=database_path.stat().st_size,
            sqlite_version=sqlite_version,
            wal_present=wal_present,
            shm_present=shm_present,
            tables=tuple(tables),
            hash_candidates=tuple(hash_candidates),
            path_candidates=tuple(path_candidates),
            size_candidates=tuple(size_candidates),
            modified_candidates=tuple(modified_candidates),
        )

    def correlate_project_db(self, alldup_database_path: Path, project_database_path: Path, sample_size: int = 50) -> AllDupCorrelation:
        """Compare a small sample of project SHA512 values against AllDup hasha rows."""
        alldup_database_path = alldup_database_path.resolve()
        project_database_path = project_database_path.resolve()
        sample_size = max(1, min(500, int(sample_size)))
        if not alldup_database_path.is_file():
            raise ValueError(f"Plik bazy AllDup nie istnieje: {alldup_database_path}")
        if not project_database_path.is_file():
            raise ValueError(f"Baza projektu nie istnieje: {project_database_path}")

        project_uri = f"file:{project_database_path.as_posix()}?mode=ro"
        alldup_uri = f"file:{alldup_database_path.as_posix()}?mode=ro"
        try:
            project = sqlite3.connect(project_uri, uri=True, timeout=10)
            alldup = sqlite3.connect(alldup_uri, uri=True, timeout=10)
            project.row_factory = sqlite3.Row
            alldup.row_factory = sqlite3.Row
            try:
                samples = project.execute(
                    """
                    SELECT fl.absolute_path, fl.sha512
                    FROM file_location fl
                    JOIN file_record fr ON fr.sha512 = fl.sha512
                    WHERE fl.location_status = 'ACTIVE'
                      AND fr.status = 'ACTIVE'
                    ORDER BY RANDOM()
                    LIMIT ?
                    """,
                    (sample_size,),
                ).fetchall()

                rows: list[AllDupCorrelationRow] = []
                matched_paths = checksum_matches = checksum_mismatches = no_hash_match = 0

                for sample in samples:
                    path = str(sample["absolute_path"])
                    our_sha = str(sample["sha512"]).lower()
                    candidates = alldup.execute(
                        """
                        SELECT h.algo, h.checksum
                        FROM files f
                        JOIN hasha h ON h.fileid = f.id
                        WHERE lower(f.file) = lower(?)
                        """,
                        (path,),
                    ).fetchall()
                    if not candidates:
                        no_hash_match += 1
                        rows.append(AllDupCorrelationRow(path, our_sha, False, (), (), None))
                        continue

                    matched_paths += 1
                    matching_algos: set[int] = set()
                    all_algos: set[int] = set()
                    matched_checksum: str | None = None
                    for candidate in candidates:
                        algo = int(candidate["algo"])
                        all_algos.add(algo)
                        blob = candidate["checksum"]
                        if blob is None:
                            continue
                        hex_value = blob.hex() if isinstance(blob, bytes) else bytes(blob).hex()
                        if hex_value.casefold() == our_sha.casefold():
                            matching_algos.add(algo)
                            matched_checksum = hex_value

                    if matching_algos:
                        checksum_matches += 1
                    else:
                        checksum_mismatches += 1

                    rows.append(
                        AllDupCorrelationRow(
                            path=path,
                            our_sha512=our_sha,
                            alldup_match=True,
                            matching_algo_values=tuple(sorted(matching_algos)),
                            all_algo_values=tuple(sorted(all_algos)),
                            matched_checksum_hex=matched_checksum,
                        )
                    )

                return AllDupCorrelation(
                    sample_size=len(samples),
                    matched_paths=matched_paths,
                    checksum_matches=checksum_matches,
                    checksum_mismatches=checksum_mismatches,
                    no_hash_match=no_hash_match,
                    rows=tuple(rows),
                )
            finally:
                project.close()
                alldup.close()
        except sqlite3.Error as exc:
            raise RuntimeError(
                "Nie udało się porównać bazy AllDup z bazą projektu w trybie tylko do odczytu. "
                f"SQLite zgłosił: {exc}. Żadna z baz nie została zmieniona."
            ) from exc

    @staticmethod
    def _looks_like_sqlite(path: Path) -> bool:
        with path.open("rb") as stream:
            header = stream.read(16)
        return header == b"SQLite format 3\x00"

    @staticmethod
    def _read_columns(connection: sqlite3.Connection, table_name: str) -> list[AllDupColumn]:
        escaped = table_name.replace('"', '""')
        rows = connection.execute(f'PRAGMA table_info("{escaped}")').fetchall()
        return [
            AllDupColumn(
                name=str(row["name"]),
                declared_type=str(row["type"] or ""),
                not_null=bool(row["notnull"]),
                primary_key_position=int(row["pk"]),
            )
            for row in rows
        ]

    @staticmethod
    def _read_indexes(connection: sqlite3.Connection, table_name: str) -> list[str]:
        escaped = table_name.replace('"', '""')
        rows = connection.execute(f'PRAGMA index_list("{escaped}")').fetchall()
        return [str(row["name"]) for row in rows]

    @staticmethod
    def _count_rows(connection: sqlite3.Connection, table_name: str) -> int | None:
        escaped = table_name.replace('"', '""')
        try:
            row = connection.execute(f'SELECT COUNT(*) AS count FROM "{escaped}"').fetchone()
            return int(row["count"])
        except sqlite3.Error:
            return None

    @staticmethod
    def _score_column(value: str, needles: tuple[str, ...]) -> list[str]:
        scores: list[str] = []
        tokens = set(value.replace("_", " ").split())
        for needle in needles:
            if needle in value:
                scores.append("strong" if needle in tokens else "possible")
                break
        return scores
