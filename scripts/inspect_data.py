"""Audit official telemetry CSV files without modifying the raw data."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"

TIMESTAMP_HINTS = ("time", "timestamp", "date", "datetime")
STATION_HINTS = ("station", "well", "site", "location")
LATITUDE_HINTS = ("latitude", "lat")
LONGITUDE_HINTS = ("longitude", "lon", "lng")
GROUNDWATER_HINTS = ("groundwater", "water level", "gwl", "level")


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def choose_column(columns: list[str], hints: tuple[str, ...]) -> str | None:
    normalized = [(column, normalize_name(column)) for column in columns]
    for column, name in normalized:
        if any(hint in name for hint in hints):
            return column
    return None


def detect_encoding(path: Path) -> str:
    sample = path.read_bytes()[:1_000_000]
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_dialect(text: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(text, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def parse_number(value: str) -> float | None:
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_timestamp(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    candidates = (value, value.replace("Z", "+00:00"))
    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass
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
            pass
    return None


def summarize_file(path: Path) -> dict:
    path = path.resolve()
    encoding = detect_encoding(path)
    with path.open("r", encoding=encoding, errors="replace", newline="") as source:
        sample = source.read(100_000)
    dialect = detect_dialect(sample)
    source = path.open("r", encoding=encoding, errors="replace", newline="")
    reader = csv.DictReader(source, dialect=dialect)
    columns = reader.fieldnames or []
    timestamp_column = choose_column(columns, TIMESTAMP_HINTS)
    station_column = choose_column(columns, STATION_HINTS)
    latitude_column = choose_column(columns, LATITUDE_HINTS)
    longitude_column = choose_column(columns, LONGITUDE_HINTS)
    groundwater_column = choose_column(columns, GROUNDWATER_HINTS)

    row_count = 0
    min_timestamp = None
    max_timestamp = None
    interval_counts = Counter()
    previous_timestamps = {}
    groundwater_count = 0
    groundwater_min = None
    groundwater_max = None
    invalid_coordinates = 0
    missing = Counter()

    station_counts = Counter()
    state_values = set()
    district_values = set()
    duplicate_rows = 0
    duplicate_station_timestamp = 0
    duplicate_sample_rows = 0
    duplicate_sample_station_timestamp = 0
    sample_rows = set()
    sample_station_timestamps = set()
    sample_limit = 100_000
    for row in reader:
        row_count += 1
        if row_count <= sample_limit:
            row_hash = hashlib.blake2b(
                "\x1f".join(row.get(column, "") for column in columns).encode("utf-8"), digest_size=16
            ).digest()
            if row_hash in sample_rows:
                duplicate_sample_rows += 1
            else:
                sample_rows.add(row_hash)
        for column in columns:
            if not (row.get(column) or "").strip():
                missing[column] += 1
        timestamp = parse_timestamp(row.get(timestamp_column, "")) if timestamp_column else None
        if timestamp:
            min_timestamp = timestamp if min_timestamp is None else min(min_timestamp, timestamp)
            max_timestamp = timestamp if max_timestamp is None else max(max_timestamp, timestamp)
        station = (row.get(station_column, "") or "").strip() if station_column else ""
        if station:
            station_counts[station] += 1
        if station and timestamp:
            if row_count <= sample_limit:
                key = (station, timestamp.isoformat())
                if key in sample_station_timestamps:
                    duplicate_sample_station_timestamp += 1
                else:
                    sample_station_timestamps.add(key)
            previous = previous_timestamps.get(station)
            if previous is not None and timestamp >= previous:
                interval_counts[round((timestamp - previous).total_seconds() / 3600, 3)] += 1
            previous_timestamps[station] = timestamp
        if groundwater_column:
            number = parse_number(row.get(groundwater_column, ""))
            if number is not None:
                groundwater_count += 1
                groundwater_min = number if groundwater_min is None else min(groundwater_min, number)
                groundwater_max = number if groundwater_max is None else max(groundwater_max, number)
        if latitude_column or longitude_column:
            latitude = parse_number(row.get(latitude_column, "")) if latitude_column else None
            longitude = parse_number(row.get(longitude_column, "")) if longitude_column else None
            if latitude is None or longitude is None or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                invalid_coordinates += 1
        if state_column := choose_column(columns, ("state",)):
            state_values.add((row.get(state_column) or "").strip())
        if district_column := choose_column(columns, ("district",)):
            district_values.add((row.get(district_column) or "").strip())
    source.close()

    intervals = list(interval_counts.elements())
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "encoding": encoding,
        "delimiter": dialect.delimiter,
        "columns": columns,
        "row_count": row_count,
        "missing_values": dict(missing),
        "timestamp_column": timestamp_column,
        "min_timestamp": min_timestamp.isoformat() if min_timestamp else None,
        "max_timestamp": max_timestamp.isoformat() if max_timestamp else None,
        "station_column": station_column,
        "station_count": len(station_counts) if station_column else None,
        "stations_with_counts": station_counts.most_common() if station_column else [],
        "duplicate_rows_in_first_100k": duplicate_sample_rows,
        "duplicate_station_timestamp_in_first_100k": duplicate_sample_station_timestamp,
        "duplicate_check_sample_size": min(row_count, sample_limit),
        "coordinate_columns": {"latitude": latitude_column, "longitude": longitude_column},
        "invalid_coordinate_rows": invalid_coordinates,
        "groundwater_column": groundwater_column,
        "groundwater_numeric_count": groundwater_count,
        "groundwater_min": groundwater_min,
        "groundwater_max": groundwater_max,
        "common_intervals_hours": interval_counts.most_common(10),
        "median_interval_hours": median(intervals) if intervals else None,
        "state_values": sorted(state_values),
        "district_values": sorted(district_values),
    }


def main() -> int:
    search_root = RAW_ROOT if RAW_ROOT.exists() else DATA_ROOT
    files = sorted(search_root.rglob("*.csv")) if search_root.exists() else []
    if not files:
        print(f"No CSV files found under {DATA_ROOT}", file=sys.stderr)
        return 2
    summaries = []
    for path in files:
        try:
            summaries.append(summarize_file(path))
        except (OSError, csv.Error, UnicodeError) as error:
            summaries.append({"file": str(path.relative_to(ROOT)).replace("\\", "/"), "error": str(error)})
    output = {"search_root": str(search_root.relative_to(ROOT)).replace("\\", "/"), "files": summaries}
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())