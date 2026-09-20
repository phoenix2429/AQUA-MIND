"""Apply a documented physical quality filter to normalized groundwater observations.

QUALITY POLICY — VERSION 1
===========================

Physical plausibility bounds for Indian groundwater telemetry (meters, depth
convention — negative values mean depth below land surface, positive values
mean water above land surface / artesian):

    Lower bound:  -300.0 m  (very deep wells; deepest known monitored wells in India)
    Upper bound:  +50.0 m   (artesian / flowing wells; highly conservative upper limit)

Rationale
---------
* The Central Ground Water Board (CGWB) monitors wells up to ~300 m depth.
* Artesian wells (positive head) rarely exceed +10 m in Indian basins; +50 m is
  a highly conservative upper bound.
* Values outside [-300, +50] are physically impossible for these sensors and
  are treated as encoding errors, sentinel/null markers, or unit mismatches
  (e.g. coordinates accidentally stored in the GWL column).
* Observed examples confirming this:
    - Karnataka: min = -1,561,912,100 (clearly a coordinate or sentinel)
    - Maharashtra: max = +459,884 (impossible in meters)
    - Andhra Pradesh: -999.999 (classic sentinel null)
    - Tamil Nadu: max = +4,435,987 (impossible in meters)
    - Telangana: max = +2,839,585 (impossible in meters)

What this filter does
---------------------
* Reads each state's normalized CSV from data/processed/all_states/
* Rejects rows where groundwater_level is outside [LOWER_BOUND, UPPER_BOUND]
* Writes accepted rows to data/processed/quality_filtered/
* Writes a per-file rejection report to data/processed/quality_filtered/
* Does NOT modify raw or normalized files

Output files
------------
data/processed/quality_filtered/
    <stem>.quality_filtered.csv     — accepted observations only
    <stem>.quality_report.json      — exclusion counts and thresholds
    quality_filter_summary.json     — five-state summary

Usage
-----
    python scripts/apply_quality_filter.py
    python scripts/apply_quality_filter.py --lower -300 --upper 50
    python scripts/apply_quality_filter.py --input-dir data/processed/all_states --output-dir data/processed/quality_filtered
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from collections import defaultdict
from pathlib import Path

# Physical plausibility bounds for Indian groundwater (meters)
DEFAULT_LOWER_BOUND = -300.0
DEFAULT_UPPER_BOUND = 50.0

_READ_BUFFER = 64 << 20   # 64 MB — avoids Windows OSError 22 on large files
_WRITE_BUFFER = 64 << 20

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


def filter_file(
    input_path: Path,
    output_path: Path,
    lower_bound: float,
    upper_bound: float,
) -> dict[str, object]:
    """Filter one normalized CSV.  Returns a quality report dict."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    accepted = 0
    rejected_oob = 0        # outside physical bounds
    rejected_nonfinite = 0  # NaN / inf (should be 0 after normalizer, but defensive)

    state_counts: dict[str, int] = defaultdict(int)
    rejection_samples: list[dict[str, object]] = []  # up to 20 examples

    _raw_in = open(str(input_path), "rb", buffering=_READ_BUFFER)
    _raw_out = open(str(output_path), "wb", buffering=_WRITE_BUFFER)
    source = io.TextIOWrapper(_raw_in, encoding="utf-8", newline="")
    destination = io.TextIOWrapper(_raw_out, encoding="utf-8", newline="")

    try:
        reader = csv.DictReader(source)
        # Use field names from input; fall back to canonical if header missing
        fieldnames = reader.fieldnames or list(CANONICAL_FIELDS)
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total += 1
            raw_val = row.get("groundwater_level", "")
            try:
                value = float(raw_val)
            except (ValueError, TypeError):
                rejected_nonfinite += 1
                continue

            if not math.isfinite(value):
                rejected_nonfinite += 1
                continue

            if value < lower_bound or value > upper_bound:
                rejected_oob += 1
                if len(rejection_samples) < 20:
                    rejection_samples.append({
                        "station_id": row.get("station_id"),
                        "timestamp": row.get("timestamp"),
                        "groundwater_level": value,
                        "state": row.get("state"),
                        "district": row.get("district"),
                    })
                continue

            accepted += 1
            state_counts[row.get("state") or "Unknown"] += 1
            writer.writerow(row)
    finally:
        destination.flush()
        destination.close()
        source.close()

    return {
        "source_file": str(input_path),
        "output_file": str(output_path),
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "total_rows": total,
        "accepted_rows": accepted,
        "rejected_out_of_bounds": rejected_oob,
        "rejected_nonfinite": rejected_nonfinite,
        "rejection_rate_pct": round(100.0 * (total - accepted) / total, 4) if total else 0.0,
        "state_counts": dict(state_counts),
        "rejection_samples": rejection_samples,
        "policy_version": "1",
        "policy_note": (
            f"Physical plausibility filter: groundwater_level must be in "
            f"[{lower_bound}, {upper_bound}] meters. Values outside this range "
            "are treated as encoding errors, sentinel/null markers, or unit "
            "mismatches. Raw and normalized files are not modified."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/all_states"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/quality_filtered"))
    parser.add_argument(
        "--lower",
        type=float,
        default=DEFAULT_LOWER_BOUND,
        help=f"Lower bound for groundwater_level (default {DEFAULT_LOWER_BOUND} m)",
    )
    parser.add_argument(
        "--upper",
        type=float,
        default=DEFAULT_UPPER_BOUND,
        help=f"Upper bound for groundwater_level (default {DEFAULT_UPPER_BOUND} m)",
    )
    args = parser.parse_args()

    input_files = sorted(
        p for p in args.input_dir.glob("*.normalized.csv")
        if p.name != "all_observations.normalized.csv"
    )
    if not input_files:
        parser.error(f"No normalized CSVs found in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, object]] = []
    for path in input_files:
        stem = path.stem.replace(".normalized", "")
        output_path = args.output_dir / f"{stem}.quality_filtered.csv"
        print(f"Filtering {path.name} …", flush=True)
        report = filter_file(path, output_path, args.lower, args.upper)
        report_path = args.output_dir / f"{stem}.quality_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        reports.append(report)
        print(
            f"  total={report['total_rows']:,}  accepted={report['accepted_rows']:,}  "
            f"rejected_oob={report['rejected_out_of_bounds']:,}  "
            f"rejection_rate={report['rejection_rate_pct']:.2f}%"
        )

    # Five-state summary
    grand_total = sum(r["total_rows"] for r in reports)
    grand_accepted = sum(r["accepted_rows"] for r in reports)
    grand_rejected_oob = sum(r["rejected_out_of_bounds"] for r in reports)
    summary = {
        "lower_bound": args.lower,
        "upper_bound": args.upper,
        "policy_version": "1",
        "files_processed": len(reports),
        "grand_total_rows": grand_total,
        "grand_accepted_rows": grand_accepted,
        "grand_rejected_out_of_bounds": grand_rejected_oob,
        "grand_rejection_rate_pct": round(100.0 * (grand_total - grand_accepted) / grand_total, 4) if grand_total else 0.0,
        "per_file": reports,
    }
    summary_path = args.output_dir / "quality_filter_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"QUALITY FILTER COMPLETE")
    print(f"  Bounds:          [{args.lower}, {args.upper}] m")
    print(f"  Files processed: {len(reports)}")
    print(f"  Total rows:      {grand_total:,}")
    print(f"  Accepted:        {grand_accepted:,}")
    print(f"  Rejected (OOB):  {grand_rejected_oob:,}")
    print(f"  Rejection rate:  {summary['grand_rejection_rate_pct']:.2f}%")
    print(f"  Output dir:      {args.output_dir}")
    print(f"  Summary:         {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
