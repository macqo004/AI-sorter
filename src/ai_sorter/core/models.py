"""Small immutable models shared by the application and database layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FileRecord:
    """Logical file identity. SHA-512 is the primary identity."""

    sha512: str
    size_bytes: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    modified_at: datetime | None = None
    created_at: datetime | None = None
    status: str = "ACTIVE"


@dataclass(frozen=True, slots=True)
class FileLocationRecord:
    """One physical occurrence of a logical file."""

    sha512: str
    absolute_path: str
    file_size: int | None = None
    modified_at: datetime | None = None
    location_status: str = "ACTIVE"
    last_seen_execution_id: int | None = None


@dataclass(frozen=True, slots=True)
class ModuleRecord:
    """Registered executable module."""

    module_id: str
    display_name: str
    module_version: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ModuleExecutionRecord:
    """One execution instance of one module."""

    execution_id: int
    module_id: str
    started_at: datetime
    status: str
    processed_count: int = 0
    success_count: int = 0
    failure_count: int = 0


@dataclass(frozen=True, slots=True)
class DatabaseStatus:
    """Human-readable database health summary."""

    connected: bool
    path: str
    schema_version: int | None
    file_count: int
    location_count: int
    module_count: int
    execution_count: int
