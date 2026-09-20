"""Audit extreme groundwater values and one-step transition errors by state."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


STATE_LIMIT = 100.0
TRANSITION_LIMIT = 100.0


def audit(files: list[Path]) -> dict[str, dict[str, float | int | None]]:
    result: dict[str, dict[str, float | int | None]] = defaultdict(
        lambda: {
            "observations": 0,
            "non_finite_values": 0,
            "absolute_value_over_100": 0,
            "minimum": None,
            "maximum": None,
            "transitions": 0,
            "absolute_transition_over_100": 0,
            "maximum_absolute_transition": 0.0,
        }
    )
    previous: dict[str, tuple[object, float, str]] = {}
    for path in files:
        with path.open(encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                state = row.get("state") or "Unknown"
                stats = result[state]
                try:
                    value = float(row["groundwater_level"])
                except (KeyError, TypeError, ValueError):
                    stats["non_finite_values"] += 1
                    continue
                if not math.isfinite(value):
                    stats["non_finite_values"] += 1
                    continue
                stats["observations"] += 1
                stats["minimum"] = value if stats["minimum"] is None else min(float(stats["minimum"]), value)
                stats["maximum"] = value if stats["maximum"] is None else max(float(stats["maximum"]), value)
                if abs(value) > STATE_LIMIT:
                    stats["absolute_value_over_100"] += 1
                station_id = row["station_id"]
                prior = previous.get(station_id)
                if prior is not None and row["timestamp"] > prior[0]:
                    transition = abs(value - prior[1])
                    stats["transitions"] += 1
                    stats["maximum_absolute_transition"] = max(float(stats["maximum_absolute_transition"]), transition)
                    if transition > TRANSITION_LIMIT:
                        stats["absolute_transition_over_100"] += 1
                previous[station_id] = (row["timestamp"], value, state)
    return {state: dict(stats) for state, stats in sorted(result.items())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/all_states"))
    parser.add_argument("--output", type=Path, default=Path("models/forecast_quality_audit.json"))
    args = parser.parse_args()
    files = sorted(path for path in args.input_dir.glob("*.normalized.csv") if path.name != "all_observations.normalized.csv")
    if not files:
        parser.error(f"No normalized resources found in {args.input_dir}")
    result = audit(files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
