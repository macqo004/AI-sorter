"""Sample-based analysis of SimImages cache payloads, read-only."""

from __future__ import annotations

import collections
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SimImagesBlobSample:
    row_id: int
    file_name: str
    size: int | None
    time_value: int | None
    length: int
    hex_preview: str


@dataclass(frozen=True, slots=True)
class SimImagesBlobAnalysis:
    requested: int
    sampled: int
    null_count: int
    blob_count: int
    other_type_count: int
    min_length: int | None
    max_length: int | None
    common_lengths: tuple[tuple[int, int], ...]
    samples: tuple[SimImagesBlobSample, ...]

    def format_text(self) -> str:
        lines = [
            "BLOB analysis: m.data",
            f"  Requested sample: {self.requested:,}",
            f"  Rows sampled: {self.sampled:,}",
            f"  NULL: {self.null_count:,}",
            f"  BLOB: {self.blob_count:,}",
            f"  Other types: {self.other_type_count:,}",
            f"  Length range: {self.min_length if self.min_length is not None else '—'} .. "
            f"{self.max_length if self.max_length is not None else '—'} bytes",
        ]
        if self.common_lengths:
            lines.append(
                "  Most common lengths: "
                + ", ".join(f"{length}={count:,}" for length, count in self.common_lengths)
            )
        if self.samples:
            lines.append("  Samples:")
            for sample in self.samples:
                lines.append(
                    f"    id={sample.row_id} | file={sample.file_name} | size={sample.size if sample.size is not None else '—'} "
                    f"| time={sample.time_value if sample.time_value is not None else '—'} "
                    f"| length={sample.length} | data={sample.hex_preview}"
                )
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class SimImagesTimeSample:
    value: int
    converted: str
    file_name: str


@dataclass(frozen=True, slots=True)
class SimImagesTimeAnalysis:
    requested: int
    sampled: int
    numeric_count: int
    min_value: int | None
    max_value: int | None
    samples: tuple[SimImagesTimeSample, ...]

    def format_text(self) -> str:
        lines = [
            "Time analysis: m.time",
            f"  Requested sample: {self.requested:,}",
            f"  Rows sampled: {self.sampled:,}",
            f"  Numeric values: {self.numeric_count:,}",
            f"  Raw range: {self.min_value if self.min_value is not None else '—'} .. "
            f"{self.max_value if self.max_value is not None else '—'}",
        ]
        if self.samples:
            lines.append("  Examples:")
            for sample in self.samples:
                lines.append(f"    {sample.value} -> {sample.converted} | {sample.file_name}")
        return "\n".join(lines)


class SimImagesDataAnalyzer:
    """Analyze selected SimImages cache fields using bounded read-only samples."""

    def analyze(
        self,
        database_path: Path,
        *,
        sample_size: int = 1000,
        max_preview_bytes: int = 64,
        sample_display_count: int = 10,
    ) -> tuple[SimImagesBlobAnalysis | None, SimImagesTimeAnalysis | None]:
        database_path = database_path.resolve()
        if not database_path.is_file():
            raise ValueError(f"Plik bazy SimImages nie istnieje: {database_path}")
        if not self._looks_like_sqlite(database_path):
            raise ValueError(f"Plik nie wygląda na poprawną bazę SQLite: {database_path}")

        sample_size = max(0, min(5000, int(sample_size)))
        max_preview_bytes = max(1, min(256, int(max_preview_bytes)))
        sample_display_count = max(0, min(25, int(sample_display_count)))
        if sample_size == 0:
            return None, None

        uri = f"file:{database_path.as_posix()}?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True, timeout=10)
            connection.row_factory = sqlite3.Row
            try:
                tables = {
                    str(row["name"]).casefold()
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if "m" not in tables:
                    return None, None

                columns = {
                    str(row["name"]).casefold()
                    for row in connection.execute("PRAGMA table_info(\"m\")")
                }
                blob_result = self._analyze_blob(
                    connection, columns, sample_size, max_preview_bytes, sample_display_count
                )
                time_result = self._analyze_time(connection, columns, sample_size, sample_display_count)
                return blob_result, time_result
            finally:
                connection.close()
        except sqlite3.Error as exc:
            raise RuntimeError(
                "Nie udało się przeanalizować danych SimImages w trybie tylko do odczytu. "
                f"SQLite zgłosił: {exc}. Żadna zmiana w bazie nie została wykonana."
            ) from exc

    def _analyze_blob(
        self,
        connection: sqlite3.Connection,
        columns: set[str],
        sample_size: int,
        preview_bytes: int,
        display_count: int,
    ) -> SimImagesBlobAnalysis | None:
        if "data" not in columns:
            return None

        rows = connection.execute(
            "SELECT id, file, size, time, data FROM \"m\" "
            "WHERE data IS NOT NULL LIMIT ?",
            (sample_size,),
        ).fetchall()

        lengths: list[int] = []
        blob_count = 0
        other_type_count = 0
        samples: list[SimImagesBlobSample] = []
        for row in rows:
            value: Any = row["data"]
            if isinstance(value, (bytes, bytearray, memoryview)):
                blob = bytes(value)
                blob_count += 1
                lengths.append(len(blob))
                if len(samples) < display_count:
                    samples.append(
                        SimImagesBlobSample(
                            row_id=int(row["id"]),
                            file_name=str(row["file"]),
                            size=int(row["size"]) if row["size"] is not None else None,
                            time_value=int(row["time"]) if row["time"] is not None else None,
                            length=len(blob),
                            hex_preview=blob[:preview_bytes].hex(),
                        )
                    )
            else:
                other_type_count += 1

        counts = collections.Counter(lengths).most_common(10)
        return SimImagesBlobAnalysis(
            requested=sample_size,
            sampled=len(rows),
            null_count=0,
            blob_count=blob_count,
            other_type_count=other_type_count,
            min_length=min(lengths) if lengths else None,
            max_length=max(lengths) if lengths else None,
            common_lengths=tuple((int(length), int(count)) for length, count in counts),
            samples=tuple(samples),
        )

    def _analyze_time(
        self,
        connection: sqlite3.Connection,
        columns: set[str],
        sample_size: int,
        display_count: int,
    ) -> SimImagesTimeAnalysis | None:
        if "time" not in columns:
            return None

        rows = connection.execute(
            "SELECT time, file FROM \"m\" WHERE time IS NOT NULL LIMIT ?",
            (sample_size,),
        ).fetchall()

        numeric: list[int] = []
        samples: list[SimImagesTimeSample] = []
        for row in rows:
            value = row["time"]
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                number = int(value)
            elif isinstance(value, float) and value.is_integer():
                number = int(value)
            else:
                continue
            numeric.append(number)
            if len(samples) < display_count:
                samples.append(
                    SimImagesTimeSample(
                        value=number,
                        converted=self._format_time(number),
                        file_name=str(row["file"]),
                    )
                )

        return SimImagesTimeAnalysis(
            requested=sample_size,
            sampled=len(rows),
            numeric_count=len(numeric),
            min_value=min(numeric) if numeric else None,
            max_value=max(numeric) if numeric else None,
            samples=tuple(samples),
        )

    @staticmethod
    def _format_time(value: int) -> str:
        if 100_000_000_000_000_000 <= value <= 300_000_000_000_000_000:
            try:
                unix_seconds = (value - 116444736000000000) / 10_000_000
                return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat()
            except (OverflowError, OSError, ValueError):
                pass
        return "unrecognized"

    @staticmethod
    def _looks_like_sqlite(path: Path) -> bool:
        with path.open("rb") as stream:
            return stream.read(16) == b"SQLite format 3\x00"
