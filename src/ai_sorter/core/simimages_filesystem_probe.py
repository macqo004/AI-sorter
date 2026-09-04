"""Read-only filesystem probe for SimImages cache records."""

from __future__ import annotations

import ctypes
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_FILETIME_EPOCH = 116_444_736_000_000_000
_HEX_SERIAL_RE = re.compile(r"^[0-9a-fA-F]+$")


@dataclass(frozen=True, slots=True)
class SimImagesFilesystemRow:
    row_id: int
    drive_record: str
    folder: str
    file_name: str
    resolved_path: str | None
    cache_size: int | None
    actual_size: int | None
    cache_time: int | None
    actual_time_ns: int | None
    status: str


@dataclass(frozen=True, slots=True)
class SimImagesFilesystemAnalysis:
    requested_rows: int
    inspected_rows: int
    existing_files: int
    missing_files: int
    unresolved_drives: int
    invalid_text_rows: int
    size_matches: int
    time_matches: int
    size_and_time_matches: int
    rows: tuple[SimImagesFilesystemRow, ...]
    blob_samples: tuple[tuple[int, str, int, str], ...]

    def format_text(self) -> str:
        lines = [
            "Filesystem verification of SimImages cache",
            f"Requested existing-file sample: {self.requested_rows:,}",
            f"Cache rows inspected: {self.inspected_rows:,}",
            f"Files currently existing: {self.existing_files:,}",
            f"Files missing: {self.missing_files:,}",
            f"Unresolved drive records: {self.unresolved_drives:,}",
            f"Invalid text rows: {self.invalid_text_rows:,}",
            f"Size matches: {self.size_matches:,}",
            f"Timestamp matches: {self.time_matches:,}",
            f"Size + timestamp matches: {self.size_and_time_matches:,}",
            "",
            "Cache/path samples:",
        ]
        for row in self.rows:
            cache_size = "—" if row.cache_size is None else str(row.cache_size)
            actual_size = "—" if row.actual_size is None else str(row.actual_size)
            cache_time = "—" if row.cache_time is None else str(row.cache_time)
            lines.append(
                f"  {row.status} | id={row.row_id} | drive={row.drive_record} | "
                f"size={cache_size}/{actual_size} | cache_time={cache_time} | "
                f"{row.resolved_path or row.file_name}"
            )

        lines.append("")
        lines.append("Existing-file BLOB samples:")
        if not self.blob_samples:
            lines.append("  none")
        else:
            for row_id, file_name, blob_length, blob_hex in self.blob_samples:
                lines.append(
                    f"  id={row_id} | file={file_name} | length={blob_length} | data={blob_hex}"
                )

        lines.append("")
        lines.append(
            "Safety: the SimImages database is opened read-only. "
            "Filesystem verification uses metadata only (stat); file contents are never read. "
            "Invalid TEXT/BLOB path values are reported and skipped, never allowed to abort the analysis."
        )
        return "\n".join(lines)


class SimImagesFilesystemProbe:
    """Resolve SimImages cache paths and verify which cached files still exist."""

    def analyze(
        self,
        database_path: Path,
        sample_size: int = 1000,
        max_rows_to_probe: int = 5000,
        blob_sample_size: int = 20,
    ) -> SimImagesFilesystemAnalysis:
        database_path = database_path.resolve()
        if not database_path.is_file():
            raise ValueError(f"Plik bazy SimImages nie istnieje: {database_path}")
        if not self._looks_like_sqlite(database_path):
            raise ValueError(f"Plik nie wygląda na poprawną bazę SQLite: {database_path}")

        sample_size = max(1, min(5000, int(sample_size)))
        max_rows_to_probe = max(sample_size, min(20000, int(max_rows_to_probe)))
        blob_sample_size = max(0, min(100, int(blob_sample_size)))

        uri = f"file:{database_path.as_posix()}?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True, timeout=10)
            connection.row_factory = sqlite3.Row
            # SimImages cache may contain legacy/non-UTF-8 TEXT values. Read TEXT
            # as raw bytes so one corrupt/legacy filename cannot abort the scan.
            connection.text_factory = bytes
            try:
                rows = connection.execute(
                    """
                    SELECT
                        m.id AS mid,
                        d.drive AS drive_record,
                        f.folder AS folder,
                        m.file AS file_name,
                        m.size AS cache_size,
                        m.time AS cache_time,
                        m.data AS data
                    FROM m
                    JOIN f ON f.id = m.fid
                    JOIN d ON d.id = f.did
                    ORDER BY m.id DESC
                    LIMIT ?
                    """,
                    (max_rows_to_probe,),
                ).fetchall()
            finally:
                connection.close()
        except sqlite3.Error as exc:
            raise RuntimeError(
                "Nie udało się odczytać cache SimImages w trybie tylko do odczytu. "
                f"SQLite zgłosił: {exc}. Baza nie została zmieniona."
            ) from exc

        drive_map = self._build_drive_map()
        inspected = 0
        existing = 0
        missing = 0
        unresolved = 0
        invalid_text = 0
        size_matches = 0
        time_matches = 0
        size_time_matches = 0
        result_rows: list[SimImagesFilesystemRow] = []
        blob_samples: list[tuple[int, str, int, str]] = []

        for row in rows:
            inspected += 1

            drive_record = self._decode_text(row["drive_record"])
            folder = self._decode_text(row["folder"])
            file_name = self._decode_text(row["file_name"])

            if drive_record is None or folder is None or file_name is None:
                invalid_text += 1
                result_rows.append(
                    SimImagesFilesystemRow(
                        row_id=int(row["mid"]),
                        drive_record=drive_record or "<invalid text>",
                        folder=folder or "<invalid text>",
                        file_name=file_name or "<invalid text>",
                        resolved_path=None,
                        cache_size=self._as_int(row["cache_size"]),
                        actual_size=None,
                        cache_time=self._as_int(row["cache_time"]),
                        actual_time_ns=None,
                        status="INVALID TEXT",
                    )
                )
                if len(result_rows) >= sample_size:
                    # Keep inspecting up to max_rows_to_probe so invalid legacy
                    # rows do not consume the entire existing-file sample.
                    pass
                continue

            root = self._resolve_drive_root(drive_record, drive_map)
            resolved = self._combine_path(root, folder, file_name) if root else None

            cache_size = self._as_int(row["cache_size"])
            cache_time = self._as_int(row["cache_time"])
            actual_size: int | None = None
            actual_time_ns: int | None = None

            if resolved is None:
                unresolved += 1
                status = "UNRESOLVED DRIVE"
            else:
                try:
                    stat = Path(resolved).stat()
                except OSError:
                    missing += 1
                    status = "MISSING"
                else:
                    existing += 1
                    actual_size = int(stat.st_size)
                    actual_time_ns = int(stat.st_mtime_ns)
                    size_ok = cache_size is None or actual_size == cache_size
                    time_ok = self._times_match(cache_time, actual_time_ns)
                    if size_ok:
                        size_matches += 1
                    if time_ok:
                        time_matches += 1
                    if size_ok and time_ok:
                        size_time_matches += 1
                        status = "EXISTS + SIZE/TIME MATCH"
                    elif size_ok:
                        status = "EXISTS + SIZE MATCH"
                    elif time_ok:
                        status = "EXISTS + TIME MATCH"
                    else:
                        status = "EXISTS + SIZE/TIME MISMATCH"

                    data = row["data"]
                    if len(blob_samples) < blob_sample_size and isinstance(data, (bytes, bytearray, memoryview)):
                        blob = bytes(data)
                        blob_samples.append((int(row["mid"]), file_name, len(blob), blob.hex()))

            if len(result_rows) < sample_size:
                result_rows.append(
                    SimImagesFilesystemRow(
                        row_id=int(row["mid"]),
                        drive_record=drive_record,
                        folder=folder,
                        file_name=file_name,
                        resolved_path=resolved,
                        cache_size=cache_size,
                        actual_size=actual_size,
                        cache_time=cache_time,
                        actual_time_ns=actual_time_ns,
                        status=status,
                    )
                )

            if existing >= sample_size:
                break

        return SimImagesFilesystemAnalysis(
            requested_rows=sample_size,
            inspected_rows=inspected,
            existing_files=existing,
            missing_files=missing,
            unresolved_drives=unresolved,
            invalid_text_rows=invalid_text,
            size_matches=size_matches,
            time_matches=time_matches,
            size_and_time_matches=size_time_matches,
            rows=tuple(result_rows),
            blob_samples=tuple(blob_samples),
        )

    @staticmethod
    def _decode_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            raw = bytes(value)
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                # Some legacy database values may use a Windows code page.
                # Decode losslessly enough for display, but only a valid UTF-8
                # value is considered safe for filesystem path resolution.
                try:
                    return raw.decode("cp1252")
                except UnicodeDecodeError:
                    return None
        return str(value)

    @staticmethod
    def _build_drive_map() -> dict[str, str]:
        mapping: dict[str, str] = {}
        for root in SimImagesFilesystemProbe._logical_drive_roots():
            serial = SimImagesFilesystemProbe._volume_serial(root)
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
        if written <= 0:
            return []
        return [root for root in buffer[:written].split("\x00") if root]

    @staticmethod
    def _volume_serial(root: str) -> int | None:
        if os.name != "nt":
            return None
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        func = kernel32.GetVolumeInformationW
        func.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_wchar_p,
            ctypes.c_uint32,
        ]
        func.restype = ctypes.c_int
        serial = ctypes.c_uint32()
        max_component = ctypes.c_uint32()
        flags = ctypes.c_uint32()
        filesystem_name = ctypes.create_unicode_buffer(261)
        volume_name = ctypes.create_unicode_buffer(261)
        ok = func(
            root,
            volume_name,
            len(volume_name),
            ctypes.byref(serial),
            ctypes.byref(max_component),
            ctypes.byref(flags),
            filesystem_name,
            len(filesystem_name),
        )
        if not ok:
            return None
        return int(serial.value)

    @staticmethod
    def _resolve_drive_root(drive_record: str, drive_map: dict[str, str]) -> str | None:
        text = drive_record.strip()
        first = text.split("|", 1)[0].strip() if "|" in text else text
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
        relative_folder = folder.replace("/", "\\").lstrip("\\/")
        relative_file = file_name.replace("/", "\\").lstrip("\\/")
        return str(Path(root) / relative_folder / relative_file)

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _times_match(cache_time: int | None, actual_time_ns: int | None) -> bool:
        if cache_time is None or actual_time_ns is None:
            return False
        if cache_time < 100_000_000_000_000_000:
            return False
        cache_ns = (cache_time - _FILETIME_EPOCH) * 100
        return abs(cache_ns - actual_time_ns) <= 2_000_000_000

    @staticmethod
    def _looks_like_sqlite(path: Path) -> bool:
        with path.open("rb") as stream:
            return stream.read(16) == b"SQLite format 3\x00"
