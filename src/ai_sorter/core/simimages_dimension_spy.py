"""Read-only SimImages dimension/fingerprint reverse-engineering probe."""

from __future__ import annotations

import ctypes
import hashlib
import math
import os
import re
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

_HEX_SERIAL_RE = re.compile(r"^[0-9a-fA-F]+$")


@dataclass(frozen=True, slots=True)
class DimensionSpyRow:
    row_id: int
    path: str
    cache_size: int | None
    cache_time: int | None
    width: int
    height: int
    format: str | None
    blob_hex: str
    sha512: str | None


@dataclass(frozen=True, slots=True)
class FieldMatch:
    offset: int
    field: str
    encoding: str
    matches: int
    total: int
    examples: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ByteCorrelation:
    offset: int
    field: str
    correlation: float


@dataclass(frozen=True, slots=True)
class DimensionSpyResult:
    requested_files: int
    cache_rows_inspected: int
    existing_files: int
    readable_images: int
    errors: int
    rows: tuple[DimensionSpyRow, ...]
    field_matches: tuple[FieldMatch, ...]
    byte_correlations: tuple[ByteCorrelation, ...]
    sha_enabled: bool

    def format_text(self) -> str:
        lines = [
            "SimImages dimension/fingerprint reverse-engineering spy",
            f"Requested files: {self.requested_files:,}",
            f"Cache rows inspected: {self.cache_rows_inspected:,}",
            f"Existing files: {self.existing_files:,}",
            f"Readable images: {self.readable_images:,}",
            f"Errors: {self.errors:,}",
            f"SHA-512: {'enabled' if self.sha_enabled else 'disabled'}",
            "",
            "Exact scalar correlations inside m.data:",
        ]
        if not self.field_matches:
            lines.append("  No repeated exact width/height/derived-field encoding found.")
        else:
            for match in self.field_matches:
                example_text = "; ".join(match.examples)
                lines.append(
                    f"  offset={match.offset:02d} | field={match.field} | "
                    f"encoding={match.encoding} | matches={match.matches}/{match.total} | {example_text}"
                )

        lines.append("")
        lines.append("Strong per-byte correlations with dimensions:")
        if not self.byte_correlations:
            lines.append("  No strong byte/value correlation found (|r| >= 0.95).")
        else:
            for item in self.byte_correlations:
                lines.append(
                    f"  offset={item.offset:02d} | field={item.field} | r={item.correlation:+.5f}"
                )

        lines.append("")
        lines.append("Samples:")
        for row in self.rows:
            lines.append(
                f"  id={row.row_id} | {row.width}x{row.height} | format={row.format or '—'} | "
                f"size={row.cache_size if row.cache_size is not None else '—'} | "
                f"sha512={row.sha512 or '—'} | path={row.path}"
            )
            lines.append(f"    data[{len(row.blob_hex) // 2} B]={row.blob_hex}")

        lines.append("")
        lines.append(
            "Safety: SQLite is opened read-only. Files are only opened by Pillow to read "
            "image metadata; no image is modified and no cache row is changed."
        )
        return "\n".join(lines)


class SimImagesDimensionSpy:
    """Find existing cache files and empirically probe m.data for dimension-related fields."""

    def analyze(
        self,
        database_path: Path,
        *,
        requested_files: int = 100,
        max_cache_rows: int = 10_000,
        sample_display_count: int = 25,
        compute_sha512: bool = False,
    ) -> DimensionSpyResult:
        database_path = database_path.resolve()
        if not database_path.is_file():
            raise ValueError(f"Plik bazy SimImages nie istnieje: {database_path}")
        requested_files = max(1, min(1000, int(requested_files)))
        max_cache_rows = max(requested_files, min(100_000, int(max_cache_rows)))
        sample_display_count = max(0, min(requested_files, int(sample_display_count)))

        connection = self._open_read_only(database_path)
        try:
            connection.row_factory = sqlite3.Row
            connection.text_factory = bytes
            rows = connection.execute(
                """
                SELECT m.id AS mid, d.drive AS drive_record, f.folder AS folder,
                       m.file AS file_name, m.size AS cache_size, m.time AS cache_time,
                       m.data AS data
                FROM m
                JOIN f ON f.id = m.fid
                JOIN d ON d.id = f.did
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (max_cache_rows,),
            ).fetchall()
        finally:
            connection.close()

        drive_map = self._build_drive_map()
        selected: list[DimensionSpyRow] = []
        selected_ids: set[int] = set()
        seen_dimension_pairs: set[tuple[int, int]] = set()
        seen_sizes: set[int] = set()
        seen_formats: set[str] = set()
        cache_inspected = 0
        existing = 0
        readable = 0
        errors = 0
        raw_records: list[tuple[int, int, int, int | None, bytes]] = []
        deferred: list[DimensionSpyRow] = []

        for row in rows:
            cache_inspected += 1
            drive = self._decode_text(row["drive_record"])
            folder = self._decode_text(row["folder"])
            name = self._decode_text(row["file_name"])
            if not drive or folder is None or not name:
                continue
            root = self._resolve_drive_root(drive, drive_map)
            if root is None:
                continue
            path = self._combine_path(root, folder, name)
            data = row["data"]
            if not isinstance(data, (bytes, bytearray, memoryview)):
                continue
            try:
                if not Path(path).is_file():
                    continue
            except OSError:
                continue

            existing += 1
            payload = bytes(data)
            try:
                with Image.open(path) as image:
                    width, height = image.size
                    image_format = image.format
                    image.verify()
            except Exception:
                errors += 1
                continue

            readable += 1
            sha = self._sha512(path) if compute_sha512 else None
            result = DimensionSpyRow(
                row_id=int(row["mid"]),
                path=path,
                cache_size=self._as_int(row["cache_size"]),
                cache_time=self._as_int(row["cache_time"]),
                width=int(width),
                height=int(height),
                format=str(image_format) if image_format else None,
                blob_hex=payload.hex(),
                sha512=sha,
            )

            dimension_key = (result.width, result.height)
            format_key = result.format or "?"
            is_diverse = (
                dimension_key not in seen_dimension_pairs
                or result.cache_size not in seen_sizes
                or format_key not in seen_formats
            )
            if is_diverse and len(selected) < requested_files:
                selected.append(result)
                selected_ids.add(result.row_id)
                seen_dimension_pairs.add(dimension_key)
                if result.cache_size is not None:
                    seen_sizes.add(result.cache_size)
                seen_formats.add(format_key)
                raw_records.append(
                    (result.row_id, result.width, result.height, result.cache_size, payload)
                )
            elif len(deferred) < requested_files * 4:
                deferred.append(result)

            if len(selected) >= requested_files:
                break

        if len(selected) < requested_files:
            for result in deferred:
                if len(selected) >= requested_files or result.row_id in selected_ids:
                    break
                selected.append(result)
                selected_ids.add(result.row_id)
                raw_records.append(
                    (
                        result.row_id,
                        result.width,
                        result.height,
                        result.cache_size,
                        bytes.fromhex(result.blob_hex),
                    )
                )

        field_matches = self._find_scalar_correlations(raw_records)
        byte_correlations = self._find_byte_correlations(raw_records)
        return DimensionSpyResult(
            requested_files=requested_files,
            cache_rows_inspected=cache_inspected,
            existing_files=existing,
            readable_images=readable,
            errors=errors,
            rows=tuple(selected[:sample_display_count]),
            field_matches=field_matches,
            byte_correlations=byte_correlations,
            sha_enabled=compute_sha512,
        )

    @staticmethod
    def _find_scalar_correlations(
        records: list[tuple[int, int, int, int | None, bytes]],
    ) -> tuple[FieldMatch, ...]:
        if not records:
            return ()

        encodings: tuple[tuple[str, int, str], ...] = (
            ("u8", 1, "B"),
            ("u16le", 2, "H_le"),
            ("u16be", 2, "H_be"),
            ("u32le", 4, "I_le"),
            ("u32be", 4, "I_be"),
            ("u64le", 8, "Q_le"),
            ("u64be", 8, "Q_be"),
            ("f32le", 4, "f_le"),
            ("f32be", 4, "f_be"),
            ("f64le", 8, "d_le"),
            ("f64be", 8, "d_be"),
        )
        fields: tuple[tuple[str, tuple[int, int, int | None, int]], ...] = tuple(
            (
                "width",
                (width, height, size, 0),
            )
            for _, width, height, size, _ in records
        )
        # Use a compact per-record tuple for field values. Derived values are
        # deliberately included because a fingerprint might store normalized area
        # or a dimension-derived scalar rather than raw width/height.
        values_by_name: dict[str, list[float]] = {
            "width": [float(r[1]) for r in records],
            "height": [float(r[2]) for r in records],
            "area": [float(r[1] * r[2]) for r in records],
            "aspect_ratio": [float(r[1] / r[2]) if r[2] else math.nan for r in records],
        }
        if all(r[3] is not None for r in records):
            values_by_name["file_size"] = [float(r[3]) for r in records]

        total = len(records)
        matches: list[FieldMatch] = []
        # Only accept repeated matches; one accidental byte sequence is not useful.
        minimum_matches = max(3, math.ceil(total * 0.25))

        for offset in range(0, 84):
            for encoding, width_bytes, decoder in encodings:
                for field_name, expected_values in values_by_name.items():
                    if offset + width_bytes > 84:
                        continue
                    count = 0
                    examples: list[str] = []
                    for index, (row_id, _, _, _, blob) in enumerate(records):
                        observed = SimImagesDimensionSpy._decode_scalar(blob[offset : offset + width_bytes], decoder)
                        if observed is None or not math.isfinite(observed):
                            continue
                        expected = expected_values[index]
                        if field_name == "aspect_ratio":
                            ok = math.isclose(observed, expected, rel_tol=1e-6, abs_tol=1e-6)
                        else:
                            ok = math.isclose(observed, expected, rel_tol=0.0, abs_tol=0.0)
                        if ok:
                            count += 1
                            if len(examples) < 3:
                                examples.append(f"id={row_id}:{expected:g}")
                    if count >= minimum_matches:
                        matches.append(
                            FieldMatch(
                                offset=offset,
                                field=field_name,
                                encoding=encoding,
                                matches=count,
                                total=total,
                                examples=tuple(examples),
                            )
                        )

        matches.sort(key=lambda item: (-item.matches, item.field, item.offset, item.encoding))
        return tuple(matches[:60])

    @staticmethod
    def _decode_scalar(raw: bytes, decoder: str) -> float | None:
        try:
            if decoder == "B":
                return float(raw[0])
            if decoder == "H_le":
                return float(int.from_bytes(raw, "little"))
            if decoder == "H_be":
                return float(int.from_bytes(raw, "big"))
            if decoder == "I_le":
                return float(int.from_bytes(raw, "little"))
            if decoder == "I_be":
                return float(int.from_bytes(raw, "big"))
            if decoder == "Q_le":
                return float(int.from_bytes(raw, "little"))
            if decoder == "Q_be":
                return float(int.from_bytes(raw, "big"))
            fmt = {
                "f_le": "<f",
                "f_be": ">f",
                "d_le": "<d",
                "d_be": ">d",
            }[decoder]
            if len(raw) != struct.calcsize(fmt):
                return None
            return float(struct.unpack(fmt, raw)[0])
        except (IndexError, struct.error, OverflowError):
            return None

    @staticmethod
    def _find_byte_correlations(
        records: list[tuple[int, int, int, int | None, bytes]],
    ) -> tuple[ByteCorrelation, ...]:
        if len(records) < 5:
            return ()
        result: list[ByteCorrelation] = []
        fields = {
            "width": [float(r[1]) for r in records],
            "height": [float(r[2]) for r in records],
        }
        for field_name, ys in fields.items():
            y_mean = sum(ys) / len(ys)
            y_dev = [y - y_mean for y in ys]
            y_norm = math.sqrt(sum(v * v for v in y_dev))
            if y_norm == 0:
                continue
            for offset in range(84):
                xs = [float(blob[offset]) if offset < len(blob) else math.nan for *_, blob in records]
                if any(math.isnan(x) for x in xs):
                    continue
                x_mean = sum(xs) / len(xs)
                x_dev = [x - x_mean for x in xs]
                x_norm = math.sqrt(sum(v * v for v in x_dev))
                if x_norm == 0:
                    continue
                correlation = sum(a * b for a, b in zip(x_dev, y_dev)) / (x_norm * y_norm)
                if abs(correlation) >= 0.95:
                    result.append(
                        ByteCorrelation(offset=offset, field=field_name, correlation=correlation)
                    )
        result.sort(key=lambda item: (-abs(item.correlation), item.offset, item.field))
        return tuple(result[:30])

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
        if not func(root, volume_name, len(volume_name), ctypes.byref(serial),
                    ctypes.byref(max_component), ctypes.byref(flags),
                    filesystem_name, len(filesystem_name)):
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
        return str(Path(root) / folder.replace("/", "\\").lstrip("\\/") /
                   file_name.replace("/", "\\").lstrip("\\/"))

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
