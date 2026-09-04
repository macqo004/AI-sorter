"""Read-only SimImages cache reverse-engineering probe."""

from __future__ import annotations

import ctypes
import hashlib
import math
import os
import re
import sqlite3
import struct
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

_HEX_SERIAL_RE = re.compile(r"^[0-9a-fA-F]+$")


@dataclass(frozen=True, slots=True)
class ByteFieldStats:
    offset: int
    correlation_width: float | None
    correlation_height: float | None
    correlation_area: float | None
    int16le_range: tuple[int, int] | None
    int16be_range: tuple[int, int] | None
    int32le_range: tuple[int, int] | None
    int32be_range: tuple[int, int] | None
    float32le_range: tuple[float, float] | None
    float32be_range: tuple[float, float] | None


@dataclass(frozen=True, slots=True)
class ReverseEngineeringRow:
    row_id: int
    path: str
    width: int
    height: int
    area: int
    cache_size: int | None
    format: str | None
    payload_hex: str
    sha512: str | None


@dataclass(frozen=True, slots=True)
class ReverseEngineeringResult:
    requested_files: int
    cache_rows_inspected: int
    existing_files: int
    readable_images: int
    errors: int
    cache_total_rows: int | None
    unique_dimensions: int
    unique_sizes: int
    byte_stats: tuple[ByteFieldStats, ...]
    scalar_hits: tuple[str, ...]
    rows: tuple[ReverseEngineeringRow, ...]
    sha_enabled: bool

    def format_text(self) -> str:
        lines = [
            "SimImages cache reverse-engineering spy",
            f"Requested files: {self.requested_files:,}",
            f"Cache rows inspected: {self.cache_rows_inspected:,}",
            f"Cache total rows: {self.cache_total_rows:,}" if self.cache_total_rows is not None else "Cache total rows: —",
            f"Existing files: {self.existing_files:,}",
            f"Readable images: {self.readable_images:,}",
            f"Errors: {self.errors:,}",
            f"Unique dimensions: {self.unique_dimensions:,}",
            f"Unique cache sizes: {self.unique_sizes:,}",
            f"SHA-512: {'enabled' if self.sha_enabled else 'disabled'}",
            "",
            "Exact scalar correlations inside m.data:",
        ]
        if self.scalar_hits:
            lines.extend(f"  {item}" for item in self.scalar_hits[:100])
        else:
            lines.append("  None found.")

        lines.append("")
        lines.append("Strongest per-byte correlations:")
        interesting = [
            item for item in self.byte_stats
            if item.correlation_width is not None
            and item.correlation_height is not None
        ]
        interesting.sort(
            key=lambda item: max(abs(item.correlation_width or 0.0), abs(item.correlation_height or 0.0)),
            reverse=True,
        )
        if not interesting:
            lines.append("  No usable numeric correlations.")
        else:
            for item in interesting[:20]:
                lines.append(
                    f"  offset={item.offset:02d} | "
                    f"r(width)={_fmt_corr(item.correlation_width)} | "
                    f"r(height)={_fmt_corr(item.correlation_height)} | "
                    f"r(area)={_fmt_corr(item.correlation_area)}"
                )

        lines.append("")
        lines.append("84-byte payload fields (most useful offsets):")
        for offset in range(0, 84, 4):
            item = next((x for x in self.byte_stats if x.offset == offset), None)
            if item is None:
                continue
            lines.append(
                f"  {offset:02d}-{offset + 3:02d} | "
                f"i16LE={_range_text(item.int16le_range)} | i16BE={_range_text(item.int16be_range)} | "
                f"i32LE={_range_text(item.int32le_range)} | i32BE={_range_text(item.int32be_range)} | "
                f"f32LE={_float_range_text(item.float32le_range)} | f32BE={_float_range_text(item.float32be_range)}"
            )

        lines.append("")
        lines.append("Samples:")
        for row in self.rows:
            lines.append(
                f"  id={row.row_id} | {row.width}x{row.height} | area={row.area} | "
                f"format={row.format or '—'} | size={row.cache_size if row.cache_size is not None else '—'} | "
                f"sha512={row.sha512 or '—'} | path={row.path}"
            )
            lines.append(f"    data[84 B]={row.payload_hex}")

        lines.append("")
        lines.append(
            "Safety: SQLite is opened read-only. Files are only opened by Pillow for metadata; "
            "no image or cache row is modified. SHA-512 is calculated only when explicitly requested."
        )
        return "\n".join(lines)


def _fmt_corr(value: float | None) -> str:
    return "—" if value is None else f"{value:+.4f}"


def _range_text(value: tuple[int, int] | None) -> str:
    if value is None:
        return "—"
    return f"{value[0]}..{value[1]}"


def _float_range_text(value: tuple[float, float] | None) -> str:
    if value is None:
        return "—"
    return f"{value[0]:.6g}..{value[1]:.6g}"


class SimImagesDimensionSpy:
    """Sample the whole SimImages cache and inspect the 84-byte payload."""

    def analyze(
        self,
        database_path: Path,
        *,
        requested_files: int = 200,
        max_cache_rows: int = 50_000,
        sample_display_count: int = 15,
        compute_sha512: bool = False,
    ) -> ReverseEngineeringResult:
        database_path = database_path.resolve()
        if not database_path.is_file():
            raise ValueError(f"Plik bazy SimImages nie istnieje: {database_path}")
        requested_files = max(1, min(1000, int(requested_files)))
        max_cache_rows = max(requested_files, min(1_000_000, int(max_cache_rows)))
        sample_display_count = max(0, min(requested_files, int(sample_display_count)))

        connection = self._open_read_only(database_path)
        try:
            connection.row_factory = sqlite3.Row
            connection.text_factory = bytes
            total_rows = self._count_m_rows(connection)
            candidates = self._sample_cache_rows(connection, total_rows, max_cache_rows)
        finally:
            connection.close()

        drive_map = self._build_drive_map()
        cache_inspected = 0
        existing = 0
        readable = 0
        errors = 0
        results: list[ReverseEngineeringRow] = []
        seen_dimensions: set[tuple[int, int]] = set()
        seen_sizes: set[int] = set()
        all_records: list[tuple[int, int, int, bytes, int | None]] = []
        deferred: list[ReverseEngineeringRow] = []
        seen_ids: set[int] = set()

        def process_row(row: sqlite3.Row) -> ReverseEngineeringRow | None:
            nonlocal existing, readable, errors
            drive = self._decode_text(row["drive_record"])
            folder = self._decode_text(row["folder"])
            name = self._decode_text(row["file_name"])
            if not drive or folder is None or not name:
                return None
            root = self._resolve_drive_root(drive, drive_map)
            if root is None:
                return None
            path = self._combine_path(root, folder, name)
            try:
                if not Path(path).is_file():
                    return None
            except OSError:
                return None
            existing += 1
            payload = row["data"]
            if not isinstance(payload, (bytes, bytearray, memoryview)):
                return None
            blob = bytes(payload)
            try:
                with Image.open(path) as image:
                    width, height = image.size
                    image_format = image.format
                    image.verify()
            except Exception:
                errors += 1
                return None
            readable += 1
            sha = self._sha512(path) if compute_sha512 else None
            return ReverseEngineeringRow(
                row_id=int(row["mid"]),
                path=path,
                width=int(width),
                height=int(height),
                area=int(width) * int(height),
                cache_size=self._as_int(row["cache_size"]),
                format=str(image_format) if image_format else None,
                payload_hex=blob.hex(),
                sha512=sha,
            )

        for row in candidates:
            cache_inspected += 1
            result = process_row(row)
            if result is None:
                continue
            seen_ids.add(result.row_id)
            record = (result.row_id, result.width, result.height, bytes.fromhex(result.payload_hex), result.cache_size)
            all_records.append(record)
            diverse = (result.width, result.height) not in seen_dimensions or result.cache_size not in seen_sizes
            if diverse and len(results) < requested_files:
                results.append(result)
                seen_dimensions.add((result.width, result.height))
                if result.cache_size is not None:
                    seen_sizes.add(result.cache_size)
            else:
                deferred.append(result)
            if len(results) >= requested_files:
                # We already have a diverse set, but continue collecting sampled
                # records for the statistical byte analysis.
                continue

        if len(results) < requested_files:
            for result in deferred:
                if len(results) >= requested_files:
                    break
                if result.row_id not in seen_ids:
                    results.append(result)
                    seen_ids.add(result.row_id)

        # Build the statistical population from every readable sampled record,
        # not merely the printed diverse subset.
        byte_stats = self._build_byte_stats(all_records)
        scalar_hits = self._find_scalar_hits(all_records)

        return ReverseEngineeringResult(
            requested_files=requested_files,
            cache_rows_inspected=cache_inspected,
            existing_files=existing,
            readable_images=readable,
            errors=errors,
            cache_total_rows=total_rows,
            unique_dimensions=len({(r[1], r[2]) for r in all_records}),
            unique_sizes=len({r[4] for r in all_records if r[4] is not None}),
            byte_stats=byte_stats,
            scalar_hits=scalar_hits,
            rows=tuple(results[:sample_display_count]),
            sha_enabled=compute_sha512,
        )

    @staticmethod
    def _sample_cache_rows(
        connection: sqlite3.Connection,
        total_rows: int | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        columns = """
            m.id AS mid, d.drive AS drive_record, f.folder AS folder,
            m.file AS file_name, m.size AS cache_size, m.time AS cache_time,
            m.data AS data
        """
        if not total_rows or total_rows <= limit:
            return connection.execute(
                f"""SELECT {columns} FROM m JOIN f ON f.id=m.fid JOIN d ON d.id=f.did ORDER BY m.id"""
            ).fetchall()

        # Deterministic stratified sampling across the complete id range. This
        # avoids bias toward the newest DuplicateReview records while still
        # keeping SQL bounded and reproducible.
        min_id, max_id = connection.execute("SELECT MIN(id), MAX(id) FROM m").fetchone()
        if min_id is None or max_id is None:
            return []
        step = (int(max_id) - int(min_id)) / float(limit)
        ids: list[int] = []
        for index in range(limit):
            ids.append(int(round(int(min_id) + index * step)))
        unique_ids = sorted(set(ids))
        placeholders = ",".join("?" for _ in unique_ids)
        return connection.execute(
            f"""SELECT {columns} FROM m JOIN f ON f.id=m.fid JOIN d ON d.id=f.did
                WHERE m.id IN ({placeholders}) ORDER BY m.id""",
            tuple(unique_ids),
        ).fetchall()

    @staticmethod
    def _count_m_rows(connection: sqlite3.Connection) -> int | None:
        try:
            row = connection.execute("SELECT COUNT(*) FROM m").fetchone()
            return int(row[0]) if row else None
        except sqlite3.Error:
            return None

    @staticmethod
    def _pearson(values_x: list[float], values_y: list[float]) -> float | None:
        n = len(values_x)
        if n < 3 or n != len(values_y):
            return None
        mean_x = sum(values_x) / n
        mean_y = sum(values_y) / n
        dx = [x - mean_x for x in values_x]
        dy = [y - mean_y for y in values_y]
        denom_x = math.sqrt(sum(x * x for x in dx))
        denom_y = math.sqrt(sum(y * y for y in dy))
        if denom_x == 0.0 or denom_y == 0.0:
            return None
        return sum(a * b for a, b in zip(dx, dy)) / (denom_x * denom_y)

    @classmethod
    def _build_byte_stats(cls, records: list[tuple[int, int, int, bytes, int | None]]) -> tuple[ByteFieldStats, ...]:
        if not records:
            return ()
        result: list[ByteFieldStats] = []
        widths = [float(r[1]) for r in records]
        heights = [float(r[2]) for r in records]
        areas = [float(r[1] * r[2]) for r in records]
        for offset in range(84):
            byte_values = [float(r[3][offset]) for r in records if len(r[3]) > offset]
            if len(byte_values) != len(records):
                continue
            i16le = [struct.unpack_from("<H", r[3], offset)[0] for r in records if offset + 2 <= len(r[3])]
            i16be = [struct.unpack_from(">H", r[3], offset)[0] for r in records if offset + 2 <= len(r[3])]
            if offset % 4 == 0 and offset + 4 <= 84:
                i32le = [struct.unpack_from("<I", r[3], offset)[0] for r in records]
                i32be = [struct.unpack_from(">I", r[3], offset)[0] for r in records]
                f32le = [struct.unpack_from("<f", r[3], offset)[0] for r in records]
                f32be = [struct.unpack_from(">f", r[3], offset)[0] for r in records]
            else:
                i32le = []
                i32be = []
                f32le = []
                f32be = []
            result.append(
                ByteFieldStats(
                    offset=offset,
                    correlation_width=cls._pearson(byte_values, widths),
                    correlation_height=cls._pearson(byte_values, heights),
                    correlation_area=cls._pearson(byte_values, areas),
                    int16le_range=(min(i16le), max(i16le)) if i16le else None,
                    int16be_range=(min(i16be), max(i16be)) if i16be else None,
                    int32le_range=(min(i32le), max(i32le)) if i32le else None,
                    int32be_range=(min(i32be), max(i32be)) if i32be else None,
                    float32le_range=_finite_range(f32le),
                    float32be_range=_finite_range(f32be),
                )
            )
        return tuple(result)

    @classmethod
    def _find_scalar_hits(cls, records: list[tuple[int, int, int, bytes, int | None]]) -> tuple[str, ...]:
        if not records:
            return ()
        derived = {
            "width": lambda w, h: w,
            "height": lambda w, h: h,
            "area": lambda w, h: w * h,
            "width/2": lambda w, h: w / 2,
            "height/2": lambda w, h: h / 2,
            "width-1": lambda w, h: w - 1,
            "height-1": lambda w, h: h - 1,
        }
        hits: list[str] = []
        for name, function in derived.items():
            target = [function(r[1], r[2]) for r in records]
            for offset in range(84):
                for bits, endian in ((16, "le"), (16, "be"), (32, "le"), (32, "be"), (64, "le"), (64, "be")):
                    size = bits // 8
                    if offset + size > 84:
                        continue
                    observed: list[float] = []
                    valid = True
                    for r in records:
                        blob = r[3]
                        if bits == 16:
                            value = int.from_bytes(blob[offset : offset + size], endian)
                        elif bits == 32:
                            value = int.from_bytes(blob[offset : offset + size], endian)
                        else:
                            value = int.from_bytes(blob[offset : offset + size], endian)
                        observed.append(float(value))
                    if observed == target:
                        hits.append(f"{name} = uint{bits}_{endian} at offset {offset}")
        # Float exact equality is useful for deliberately stored dimensions/scalars,
        # but only test numerically sensible derived values.
        for name, function in derived.items():
            target = [function(r[1], r[2]) for r in records]
            for offset in range(0, 81, 4):
                for endian in ("<", ">"):
                    observed = [struct.unpack_from(f"{endian}f", r[3], offset)[0] for r in records]
                    if all(math.isfinite(x) for x in observed) and all(abs(a - b) < 1e-6 for a, b in zip(observed, target)):
                        hits.append(f"{name} = float32_{'le' if endian == '<' else 'be'} at offset {offset}")
        return tuple(hits)

    @staticmethod
    def _open_read_only(path: Path) -> sqlite3.Connection:
        uri = f"file:{path.as_posix()}?mode=ro"
        try:
            return sqlite3.connect(uri, uri=True, timeout=10)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Nie udało się otworzyć Cache.db tylko do odczytu: {exc}") from exc

    @staticmethod
    def _decode_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            raw = bytes(value)
            for encoding in ("utf-8", "cp1252"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    pass
            return None
        return str(value)

    @staticmethod
    def _build_drive_map() -> dict[str, str]:
        mapping: dict[str, str] = {}
        for root in SimImagesDimensionSpy._logical_drive_roots():
            serial = SimImagesDimensionSpy._volume_serial(root)
            if serial is not None:
                mapping[format(serial, "x").casefold()] = root
                mapping[str(serial).casefold()] = root
        return mapping

    @staticmethod
    def _logical_drive_roots() -> list[str]:
        if os.name != "nt":
            return ["/"]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        func = kernel32.GetLogicalDriveStringsW
        func.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
        func.restype = ctypes.c_uint32
        required = func(0, None)
        if required <= 0:
            return []
        buffer = ctypes.create_unicode_buffer(required + 1)
        written = func(required + 1, buffer)
        return [root for root in buffer[:written].split("\x00") if root]

    @staticmethod
    def _volume_serial(root: str) -> int | None:
        if os.name != "nt":
            return None
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        func = kernel32.GetVolumeInformationW
        func.argtypes = [
            ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32), ctypes.c_wchar_p, ctypes.c_uint32,
        ]
        func.restype = ctypes.c_int
        serial = ctypes.c_uint32()
        max_component = ctypes.c_uint32()
        flags = ctypes.c_uint32()
        filesystem_name = ctypes.create_unicode_buffer(261)
        volume_name = ctypes.create_unicode_buffer(261)
        if not func(root, volume_name, len(volume_name), ctypes.byref(serial), ctypes.byref(max_component), ctypes.byref(flags), filesystem_name, len(filesystem_name)):
            return None
        return int(serial.value)

    @staticmethod
    def _resolve_drive_root(drive_record: str, drive_map: dict[str, str]) -> str | None:
        first = drive_record.split("|", 1)[0].strip()
        if len(first) >= 2 and first[1] == ":":
            return first[:2] + "\\"
        if first.casefold() in drive_map:
            return drive_map[first.casefold()]
        if _HEX_SERIAL_RE.fullmatch(first):
            try:
                return drive_map.get(format(int(first, 16), "x").casefold())
            except ValueError:
                return None
        return None

    @staticmethod
    def _combine_path(root: str, folder: str, file_name: str) -> str:
        return str(Path(root) / folder.replace("/", "\\").lstrip("\\/") / file_name.replace("/", "\\").lstrip("\\/"))

    @staticmethod
    def _as_int(value: Any) -> int | None:
        try:
            return None if value is None else int(value)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _sha512(path: str) -> str:
        digest = hashlib.sha512()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


def _finite_range(values: list[float]) -> tuple[float, float] | None:
    finite = [x for x in values if math.isfinite(x)]
    return (min(finite), max(finite)) if finite else None
