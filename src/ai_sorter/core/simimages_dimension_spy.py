"""Read-only SimImages dimension/fingerprint reverse-engineering probe."""

from __future__ import annotations

import ctypes
import hashlib
import os
import re
import sqlite3
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
class DimensionMatch:
    offset: int
    width_endian: str
    height_endian: str
    matches: int
    examples: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DimensionSpyResult:
    requested_files: int
    cache_rows_inspected: int
    existing_files: int
    readable_images: int
    errors: int
    rows: tuple[DimensionSpyRow, ...]
    matches: tuple[DimensionMatch, ...]
    sha_enabled: bool

    def format_text(self) -> str:
        lines = [
            "SimImages dimension/fingerprint spy",
            f"Requested files: {self.requested_files:,}",
            f"Cache rows inspected: {self.cache_rows_inspected:,}",
            f"Existing files: {self.existing_files:,}",
            f"Readable images: {self.readable_images:,}",
            f"Errors: {self.errors:,}",
            f"SHA-512: {'enabled' if self.sha_enabled else 'disabled'}",
            "",
            "Dimension/fingerprint correlations:",
        ]
        if not self.matches:
            lines.append("  No exact width/height byte-field correlation found.")
        else:
            for match in self.matches:
                examples = "; ".join(match.examples)
                lines.append(
                    f"  offset={match.offset} | width={match.width_endian} | "
                    f"height={match.height_endian} | matches={match.matches} | {examples}"
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
    """Find existing cache files, read dimensions, and correlate them with m.data."""

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
        seen_dimensions: set[tuple[int, int]] = set()
        seen_sizes: set[int] = set()
        cache_inspected = 0
        existing = 0
        readable = 0
        errors = 0
        raw_payloads: list[tuple[int, int, int, bytes]] = []

        # First pass favors different cache sizes/dimensions. This avoids filling the
        # sample with one large duplicate set such as the user's SHA-identical groups.
        candidates: list[tuple[Any, str, bytes]] = []
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
            payload = bytes(data)
            try:
                if Path(path).is_file():
                    candidates.append((row, path, payload))
            except OSError:
                continue
            if len(candidates) >= max_cache_rows:
                break

        def inspect_candidate(item: tuple[Any, str, bytes]) -> DimensionSpyRow | None:
            nonlocal existing, readable, errors
            row, path, payload = item
            existing += 1
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
            return DimensionSpyRow(
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

        # Prefer unique (dimension, size) pairs, but fall back to any readable files.
        deferred: list[DimensionSpyRow] = []
        for item in candidates:
            result = inspect_candidate(item)
            if result is None:
                continue
            if len(selected) < requested_files and (
                (result.width, result.height) not in seen_dimensions
                or result.cache_size not in seen_sizes
            ):
                selected.append(result)
                seen_dimensions.add((result.width, result.height))
                if result.cache_size is not None:
                    seen_sizes.add(result.cache_size)
                raw_payloads.append((result.row_id, result.width, result.height, bytes.fromhex(result.blob_hex)))
            else:
                deferred.append(result)
            if len(selected) >= requested_files:
                break

        if len(selected) < requested_files:
            for result in deferred:
                if len(selected) >= requested_files:
                    break
                if result.row_id in {row.row_id for row in selected}:
                    continue
                selected.append(result)
                raw_payloads.append((result.row_id, result.width, result.height, bytes.fromhex(result.blob_hex)))

        matches = self._find_dimension_correlations(raw_payloads)
        display_rows = tuple(selected[:sample_display_count])
        return DimensionSpyResult(
            requested_files=requested_files,
            cache_rows_inspected=cache_inspected,
            existing_files=existing,
            readable_images=readable,
            errors=errors,
            rows=display_rows,
            matches=matches,
            sha_enabled=compute_sha512,
        )

    @staticmethod
    def _find_dimension_correlations(
        records: list[tuple[int, int, int, bytes]],
    ) -> tuple[DimensionMatch, ...]:
        if not records:
            return ()
        result: list[DimensionMatch] = []
        for width_endian in ("le", "be"):
            for height_endian in ("le", "be"):
                for offset in range(0, 81, 2):
                    matches = 0
                    examples: list[str] = []
                    for row_id, width, height, blob in records:
                        if offset + 4 > len(blob):
                            continue
                        w4 = blob[offset : offset + 4]
                        h4 = blob[offset + 4 : offset + 8] if offset + 8 <= len(blob) else b""
                        if width_endian == "le":
                            observed_width = int.from_bytes(w4, "little")
                        else:
                            observed_width = int.from_bytes(w4, "big")
                        if height_endian == "le":
                            observed_height = int.from_bytes(h4, "little") if len(h4) == 4 else -1
                        else:
                            observed_height = int.from_bytes(h4, "big") if len(h4) == 4 else -1
                        if observed_width == width and observed_height == height:
                            matches += 1
                            if len(examples) < 3:
                                examples.append(f"id={row_id}:{width}x{height}")
                    if matches:
                        result.append(
                            DimensionMatch(
                                offset=offset,
                                width_endian=width_endian,
                                height_endian=height_endian,
                                matches=matches,
                                examples=tuple(examples),
                            )
                        )
        result.sort(key=lambda item: (-item.matches, item.offset, item.width_endian, item.height_endian))
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
