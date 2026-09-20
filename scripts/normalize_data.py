"""Normalize official telemetry CSV files into a canonical processed CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ingestion.normalizer import CANONICAL_FIELDS, TelemetryNormalizer


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_file(input_path: Path, output_path: Path) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalizer = TelemetryNormalizer()
    iterator, stats = normalizer.iter_file(input_path)
    with output_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        for observation in iterator:
            writer.writerow(observation.as_dict())
    return {
        "source_file": str(input_path),
        "source_sha256": file_sha256(input_path),
        "processed_file": str(output_path),
        "rows_read": stats.rows_read,
        "rows_emitted": stats.rows_emitted,
        "invalid_timestamp": stats.invalid_timestamp,
        "invalid_groundwater_level": stats.invalid_groundwater_level,
        "invalid_coordinates": stats.invalid_coordinates,
        "duplicate_station_timestamp": stats.duplicate_station_timestamp,
        "missing_required_columns": stats.missing_required_columns,
        "detected_columns": stats.detected_columns,
        "state_counts": dict(stats.state_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Source CSV file; it is never modified")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory for normalized CSV and ingestion stats",
    )
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"Input CSV does not exist: {args.input}")
    output_path = args.output_dir / f"{args.input.stem}.normalized.csv"
    stats_path = args.output_dir / f"{args.input.stem}.stats.json"
    result = normalize_file(args.input, output_path)
    stats_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
