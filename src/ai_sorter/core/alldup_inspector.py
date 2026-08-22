"""Read-only inspector for AllDup SQLite databases."""

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
            raise RuntimeError(
                "Nie udało się odczytać bazy AllDup w trybie tylko do odczytu. "
                "Baza nie została zmieniona."
            ) from exc

        return AllDupInspection(
            path=database_path,
            file_size_bytes=database_path.stat().st_size,
            sqlite_version=sqlite_version,
            tables=tuple(tables),
            hash_candidates=tuple(hash_candidates),
            path_candidates=tuple(path_candidates),
            size_candidates=tuple(size_candidates),
            modified_candidates=tuple(modified_candidates),
        )

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
