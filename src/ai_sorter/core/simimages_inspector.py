"""Read-only inspector for SimImages SQLite cache databases."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SimImagesColumn:
    name: str
    declared_type: str
    not_null: bool
    primary_key_position: int


@dataclass(frozen=True, slots=True)
class SimImagesTable:
    name: str
    columns: tuple[SimImagesColumn, ...]
    indexes: tuple[str, ...]
    row_count: int | None


@dataclass(frozen=True, slots=True)
class SimImagesSampleRow:
    table: str
    values: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class SimImagesInspection:
    path: Path
    file_size_bytes: int
    sqlite_version: str
    journal_mode: str | None
    wal_present: bool
    shm_present: bool
    tables: tuple[SimImagesTable, ...]
    path_candidates: tuple[tuple[str, str, str], ...]
    filename_candidates: tuple[tuple[str, str, str], ...]
    size_candidates: tuple[tuple[str, str, str], ...]
    checksum_candidates: tuple[tuple[str, str, str], ...]
    width_candidates: tuple[tuple[str, str, str], ...]
    height_candidates: tuple[tuple[str, str, str], ...]
    sample_rows: tuple[SimImagesSampleRow, ...]

    def format_text(self) -> str:
        lines = [
            "SimImages database inspection",
            f"Path: {self.path}",
            f"Database size: {self.file_size_bytes:,} bytes",
            f"SQLite: {self.sqlite_version}",
            f"Journal mode: {self.journal_mode or 'unknown'}",
            f"WAL sidecar: {'present' if self.wal_present else 'not found'}",
            f"SHM sidecar: {'present' if self.shm_present else 'not found'}",
            f"Tables: {len(self.tables)}",
            "",
        ]

        for table in self.tables:
            count = "not counted" if table.row_count is None else f"{table.row_count:,}"
            lines.append(f"TABLE {table.name} — rows: {count}")
            for column in table.columns:
                flags: list[str] = []
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

        section("Path candidates", self.path_candidates)
        section("Filename candidates", self.filename_candidates)
        section("Size candidates", self.size_candidates)
        section("Checksum candidates", self.checksum_candidates)
        section("Width candidates", self.width_candidates)
        section("Height candidates", self.height_candidates)

        if self.sample_rows:
            lines.append("Sample rows:")
            for sample in self.sample_rows:
                lines.append(f"  TABLE {sample.table}")
                for name, value in sample.values:
                    lines.append(f"    {name} = {value}")
            lines.append("")
        else:
            lines.append("Sample rows: none")
            lines.append("")

        lines.append(
            "Safety: database opened read-only; no schema or data writes are performed. "
            "Samples are limited and are never loaded wholesale."
        )
        return "\n".join(lines)


class SimImagesDatabaseInspector:
    """Inspect a SimImages SQLite cache without modifying it."""

    _PATH_NAMES = (
        "path", "filepath", "file_path", "fullpath", "full_path", "location",
        "folder", "directory", "dir",
    )
    _FILENAME_NAMES = (
        "filename", "file_name", "name", "basename", "file",
    )
    _SIZE_NAMES = ("size", "filesize", "file_size", "length", "bytes")
    _CHECKSUM_NAMES = (
        "crc", "crc32", "checksum", "hash", "digest", "md5", "sha1", "sha256", "sha512",
    )
    _WIDTH_NAMES = ("width", "width_px", "image_width", "pixel_width")
    _HEIGHT_NAMES = ("height", "height_px", "image_height", "pixel_height")

    def inspect(
        self,
        database_path: Path,
        count_rows: bool = False,
        sample_rows: int = 3,
        sample_values: int = 20,
    ) -> SimImagesInspection:
        database_path = database_path.resolve()
        if not database_path.is_file():
            raise ValueError(f"Plik bazy SimImages nie istnieje: {database_path}")
        if not self._looks_like_sqlite(database_path):
            raise ValueError(f"Plik nie wygląda na poprawną bazę SQLite: {database_path}")

        wal_path = database_path.with_name(database_path.name + "-wal")
        shm_path = database_path.with_name(database_path.name + "-shm")
        wal_present = wal_path.exists()
        shm_present = shm_path.exists()
        uri = f"file:{database_path.as_posix()}?mode=ro"

        sample_rows = max(0, min(10, int(sample_rows)))
        sample_values = max(1, min(50, int(sample_values)))

        try:
            connection = sqlite3.connect(uri, uri=True, timeout=10)
            connection.row_factory = sqlite3.Row
            try:
                sqlite_version = str(
                    connection.execute("SELECT sqlite_version() AS version").fetchone()["version"]
                )
                journal_mode = str(
                    connection.execute("PRAGMA journal_mode").fetchone()[0]
                )

                tables: list[SimImagesTable] = []
                path_candidates: list[tuple[str, str, str]] = []
                filename_candidates: list[tuple[str, str, str]] = []
                size_candidates: list[tuple[str, str, str]] = []
                checksum_candidates: list[tuple[str, str, str]] = []
                width_candidates: list[tuple[str, str, str]] = []
                height_candidates: list[tuple[str, str, str]] = []
                examples: list[SimImagesSampleRow] = []

                table_rows = connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()

                for table_row in table_rows:
                    table_name = str(table_row["name"])
                    columns = tuple(self._read_columns(connection, table_name))
                    indexes = tuple(self._read_indexes(connection, table_name))
                    row_count = self._count_rows(connection, table_name) if count_rows else None
                    tables.append(SimImagesTable(table_name, columns, indexes, row_count))

                    for column in columns:
                        lowered = column.name.casefold()
                        declared = column.declared_type.casefold()
                        combined = f"{lowered} {declared}"
                        path_candidates.extend(
                            (table_name, column.name, score)
                            for score in self._score_column(combined, self._PATH_NAMES)
                        )
                        filename_candidates.extend(
                            (table_name, column.name, score)
                            for score in self._score_column(combined, self._FILENAME_NAMES)
                        )
                        size_candidates.extend(
                            (table_name, column.name, score)
                            for score in self._score_column(combined, self._SIZE_NAMES)
                        )
                        checksum_candidates.extend(
                            (table_name, column.name, score)
                            for score in self._score_column(combined, self._CHECKSUM_NAMES)
                        )
                        width_candidates.extend(
                            (table_name, column.name, score)
                            for score in self._score_column(combined, self._WIDTH_NAMES)
                        )
                        height_candidates.extend(
                            (table_name, column.name, score)
                            for score in self._score_column(combined, self._HEIGHT_NAMES)
                        )

                    if len(examples) < sample_rows and columns:
                        examples.append(
                            self._read_sample(
                                connection,
                                table_name,
                                columns,
                                sample_values,
                            )
                        )
            finally:
                connection.close()
        except sqlite3.Error as exc:
            sidecars: list[str] = []
            if wal_present:
                sidecars.append("-wal")
            if shm_present:
                sidecars.append("-shm")
            sidecar_text = ", ".join(sidecars) if sidecars else "none"
            raise RuntimeError(
                "Nie udało się odczytać bazy SimImages w trybie tylko do odczytu. "
                f"SQLite zgłosił: {exc}. Wykryte pliki towarzyszące: {sidecar_text}. "
                "Jeżeli SimImages aktualnie skanuje, po zakończeniu zamknij program i spróbuj ponownie. "
                "Baza nie została zmieniona."
            ) from exc

        return SimImagesInspection(
            path=database_path,
            file_size_bytes=database_path.stat().st_size,
            sqlite_version=sqlite_version,
            journal_mode=journal_mode,
            wal_present=wal_present,
            shm_present=shm_present,
            tables=tuple(tables),
            path_candidates=tuple(path_candidates),
            filename_candidates=tuple(filename_candidates),
            size_candidates=tuple(size_candidates),
            checksum_candidates=tuple(checksum_candidates),
            width_candidates=tuple(width_candidates),
            height_candidates=tuple(height_candidates),
            sample_rows=tuple(examples),
        )

    @staticmethod
    def _read_columns(connection: sqlite3.Connection, table_name: str) -> list[SimImagesColumn]:
        quoted = SimImagesDatabaseInspector._quote_identifier(table_name)
        rows = connection.execute(f"PRAGMA table_info({quoted})").fetchall()
        return [
            SimImagesColumn(
                name=str(row["name"]),
                declared_type=str(row["type"] or ""),
                not_null=bool(row["notnull"]),
                primary_key_position=int(row["pk"]),
            )
            for row in rows
        ]

    @staticmethod
    def _read_indexes(connection: sqlite3.Connection, table_name: str) -> list[str]:
        quoted = SimImagesDatabaseInspector._quote_identifier(table_name)
        rows = connection.execute(f"PRAGMA index_list({quoted})").fetchall()
        return [str(row["name"]) for row in rows]

    @staticmethod
    def _count_rows(connection: sqlite3.Connection, table_name: str) -> int:
        quoted = SimImagesDatabaseInspector._quote_identifier(table_name)
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {quoted}").fetchone()
        return int(row["count"])

    @staticmethod
    def _read_sample(
        connection: sqlite3.Connection,
        table_name: str,
        columns: tuple[SimImagesColumn, ...],
        value_limit: int,
    ) -> SimImagesSampleRow:
        quoted = SimImagesDatabaseInspector._quote_identifier(table_name)
        column_sql = ", ".join(
            SimImagesDatabaseInspector._quote_identifier(column.name) for column in columns
        )
        rows = connection.execute(
            f"SELECT {column_sql} FROM {quoted} LIMIT ?",
            (value_limit,),
        ).fetchall()

        # Keep the report small: show only the first row because the schema is the main target.
        if not rows:
            return SimImagesSampleRow(table_name, (("<empty>", "<table has no rows>"),))

        row = rows[0]
        values = tuple((column.name, SimImagesDatabaseInspector._format_value(row[column.name])) for column in columns)
        return SimImagesSampleRow(table_name, values)

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            preview = value[:32].hex()
            suffix = "…" if len(value) > 32 else ""
            return f"BLOB[{len(value)} bytes] {preview}{suffix}"
        text = str(value)
        if len(text) > 300:
            text = text[:300] + "…"
        return text.replace("\r", "\\r").replace("\n", "\\n")

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _score_column(value: str, names: tuple[str, ...]) -> tuple[str, ...]:
        lowered = value.casefold()
        scores: list[str] = []
        for name in names:
            if name in lowered.split():
                scores.append("strong")
            elif name in lowered.replace("_", " "):
                scores.append("possible")
        if not scores:
            return ()
        return ("strong" if "strong" in scores else "possible",)

    @staticmethod
    def _looks_like_sqlite(path: Path) -> bool:
        with path.open("rb") as stream:
            return stream.read(16) == b"SQLite format 3\x00"
