"""Build a station registry from canonical normalized observations."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CANONICAL_FIELDS = (
    "station_id",
    "source_station_id",
    "station_name",
    "state",
    "district",
    "tehsil",
    "block",
    "village",
    "agency",
    "latitude",
    "longitude",
    "elevation_msl",
    "latest_observation_timestamp",
    "observation_count",
    "source",
    "source_file",
)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def build_registry(input_path: Path, output_path: Path) -> dict[str, int | str]:
    stations: dict[str, dict[str, object]] = {}
    with input_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        for row in reader:
            station_id = row["station_id"]
            timestamp = parse_timestamp(row["timestamp"])
            station = stations.setdefault(
                station_id,
                {
                    "station_id": station_id,
                    "source_station_id": row.get("source_station_id") or station_id,
                    "station_name": station_id,
                    "state": row.get("state") or None,
                    "district": row.get("district") or None,
                    "tehsil": row.get("tehsil") or None,
                    "block": row.get("block") or None,
                    "village": row.get("village") or None,
                    "agency": row.get("agency") or None,
                    "latitude": row.get("latitude") or None,
                    "longitude": row.get("longitude") or None,
                    "elevation_msl": row.get("elevation_msl") or None,
                    "latest_observation_timestamp": row["timestamp"],
                    "observation_count": 0,
                    "source": row.get("source") or None,
                    "source_file": row.get("source_file") or None,
                },
            )
            station["observation_count"] = int(station["observation_count"]) + 1
            latest = parse_timestamp(str(station["latest_observation_timestamp"]))
            if timestamp > latest:
                station["latest_observation_timestamp"] = row["timestamp"]
                station["source_file"] = row.get("source_file") or station["source_file"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(stations.values(), key=lambda station: str(station["station_id"])))
    return {"input_file": str(input_path), "output_file": str(output_path), "station_count": len(stations)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/processed/stations.csv"))
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"Input file does not exist: {args.input}")
    print(json.dumps(build_registry(args.input, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
