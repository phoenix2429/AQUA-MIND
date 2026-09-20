"""Streaming normalization for official groundwater telemetry CSV files."""

from __future__ import annotations

import csv
import io
import math
import mmap
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

# Buffer size for the encoding-probe read (64 MB).
_READ_BUFFER = 64 << 20


class _MmapRaw(io.RawIOBase):
    """Wraps a read-only mmap as a RawIOBase stream.

    Windows raises OSError 22 (EINVAL) during sequential read() syscalls on
    files larger than ~300 MB because an internal kernel file-position counter
    overflows.  mmap bypasses sequential read() entirely — it uses Windows
    page-fault demand paging, which is immune to the overflow bug.
    """

    def __init__(self, file_obj, mm: mmap.mmap) -> None:
        self._file = file_obj
        self._mm = mm

    def readinto(self, b: bytearray) -> int:  # type: ignore[override]
        data = self._mm.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        if not self.closed:
            self._mm.close()
            self._file.close()
        super().close()


CANONICAL_FIELDS = (
    "observation_id",
    "station_id",
    "source_station_id",
    "timestamp",
    "groundwater_level",
    "unit",
    "latitude",
    "longitude",
    "elevation_msl",
    "state",
    "district",
    "tehsil",
    "block",
    "village",
    "agency",
    "source",
    "source_file",
)

ALIASES = {
    "station_id": ("station", "station id", "station code", "well", "site"),
    "timestamp": ("data acquisition time", "timestamp", "datetime", "date time", "time"),
    "groundwater_level": (
        "groundwater level telemetry 6 hourly meter",
        "groundwater level",
        "groundwater",
        "water level",
        "gwl",
    ),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng"),
    "elevation_msl": ("rl msl", "elevation", "elevation msl", "altitude"),
    "state": ("state",),
    "district": ("district",),
    "tehsil": ("tehsil", "taluk", "mandal"),
    "block": ("block",),
    "village": ("village",),
    "agency": ("agency",),
}


def normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def detect_columns(columns: Iterable[str]) -> dict[str, str]:
    """Map available source columns to canonical fields using normalized aliases."""
    available = [(column, normalize_column_name(column)) for column in columns]
    mapping: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        normalized_aliases = {normalize_column_name(alias) for alias in aliases}
        for source, normalized_source in available:
            if normalized_source in normalized_aliases:
                mapping[canonical] = source
                break
    return mapping


def parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    for format_string in (
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
    ):
        try:
            return datetime.strptime(value, format_string)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip().replace(",", "")
    if not value or value in {"-", "NA", "N/A", "null", "None"}:
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except ValueError:
        return None


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value if value and value not in {"-", "NA", "N/A", "null", "None"} else None


def valid_coordinates(latitude: float | None, longitude: float | None) -> bool:
    return latitude is not None and longitude is not None and -90 <= latitude <= 90 and -180 <= longitude <= 180


@dataclass(frozen=True)
class NormalizedObservation:
    observation_id: str
    station_id: str
    source_station_id: str
    timestamp: datetime
    groundwater_level: float
    unit: str
    latitude: float | None
    longitude: float | None
    elevation_msl: float | None
    state: str | None
    district: str | None
    tehsil: str | None
    block: str | None
    village: str | None
    agency: str | None
    source: str
    source_file: str

    def as_dict(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in CANONICAL_FIELDS}


@dataclass
class IngestionStats:
    source_file: str
    rows_read: int = 0
    rows_emitted: int = 0
    invalid_timestamp: int = 0
    invalid_groundwater_level: int = 0
    invalid_coordinates: int = 0
    duplicate_station_timestamp: int = 0
    missing_required_columns: list[str] = field(default_factory=list)
    detected_columns: dict[str, str] = field(default_factory=dict)
    state_counts: Counter[str] = field(default_factory=Counter)


class TelemetryNormalizer:
    """Normalize one CSV while keeping raw input untouched."""

    def __init__(self, source: str = "NWDP", unit: str = "meter") -> None:
        self.source = source
        self.unit = unit

    def iter_file(self, path: Path, state_override: str | None = None) -> tuple[Iterator[NormalizedObservation], IngestionStats]:
        encoding = self._detect_encoding(path)
        # Use mmap to open the file via Windows demand-paging instead of
        # sequential read() syscalls.  This is immune to OSError 22 (EINVAL)
        # that Windows raises when the internal file-position counter overflows
        # for files larger than ~300 MB.
        _file = open(str(path), "rb")  # noqa: WPS515
        _mm = mmap.mmap(_file.fileno(), 0, access=mmap.ACCESS_READ)
        raw = _MmapRaw(_file, _mm)
        buffered = io.BufferedReader(raw, buffer_size=_READ_BUFFER)
        source = io.TextIOWrapper(buffered, encoding=encoding, errors="replace", newline="")
        reader = csv.DictReader(source)
        mapping = detect_columns(reader.fieldnames or [])
        stats = IngestionStats(source_file=str(path), detected_columns=mapping)
        stats.missing_required_columns = [field for field in ("station_id", "timestamp", "groundwater_level") if field not in mapping]
        if stats.missing_required_columns:
            source.close()
            return iter(()), stats
        return self._rows(reader, source, path, mapping, stats, state_override), stats

    def _rows(self, reader: csv.DictReader, source, path: Path, mapping: dict[str, str], stats: IngestionStats, state_override: str | None) -> Iterator[NormalizedObservation]:
        last_timestamp_by_station: dict[str, datetime] = {}
        try:
            for row_number, row in enumerate(reader, start=2):
                stats.rows_read += 1
                station_id = clean_text(row.get(mapping["station_id"]))
                timestamp = parse_timestamp(row.get(mapping["timestamp"]))
                groundwater_level = parse_float(row.get(mapping["groundwater_level"]))
                state = clean_text(row.get(mapping.get("state", ""))) or state_override
                if not station_id or timestamp is None:
                    stats.invalid_timestamp += 1
                    continue
                if groundwater_level is None:
                    stats.invalid_groundwater_level += 1
                    continue
                qualified_station_id = f"{state}::{station_id}" if state else station_id
                previous_timestamp = last_timestamp_by_station.get(qualified_station_id)
                if previous_timestamp == timestamp:
                    stats.duplicate_station_timestamp += 1
                    continue
                last_timestamp_by_station[qualified_station_id] = timestamp
                latitude = parse_float(row.get(mapping.get("latitude", "")))
                longitude = parse_float(row.get(mapping.get("longitude", "")))
                if (latitude is not None or longitude is not None) and not valid_coordinates(latitude, longitude):
                    stats.invalid_coordinates += 1
                    latitude = None
                    longitude = None
                stats.state_counts[state or "Unknown"] += 1
                observation = NormalizedObservation(
                    observation_id=f"{qualified_station_id}:{timestamp.isoformat()}",
                    station_id=qualified_station_id,
                    source_station_id=station_id,
                    timestamp=timestamp,
                    groundwater_level=groundwater_level,
                    unit=self.unit,
                    latitude=latitude,
                    longitude=longitude,
                    elevation_msl=parse_float(row.get(mapping.get("elevation_msl", ""))),
                    state=state,
                    district=clean_text(row.get(mapping.get("district", ""))),
                    tehsil=clean_text(row.get(mapping.get("tehsil", ""))),
                    block=clean_text(row.get(mapping.get("block", ""))),
                    village=clean_text(row.get(mapping.get("village", ""))),
                    agency=clean_text(row.get(mapping.get("agency", ""))),
                    source=self.source,
                    source_file=str(path),
                )
                stats.rows_emitted += 1
                yield observation
        finally:
            source.close()

    @staticmethod
    def _detect_encoding(path: Path) -> str:
        # Read a 4 MB sample for more reliable detection on large government CSVs.
        # Use io.open with the large buffer to avoid OSError 22 on Windows even
        # during the encoding-probe read.
        with io.open(str(path), "rb", buffering=_READ_BUFFER) as source:
            sample = source.read(4_000_000)
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
            try:
                sample.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        return "latin-1"
