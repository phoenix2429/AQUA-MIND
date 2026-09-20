"""Evaluate a chronological persistence baseline across all normalized resources."""

from __future__ import annotations

import argparse
import csv
import io
import math
import mmap
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_READ_BUFFER = 64 << 20  # 64 MB — avoids Windows OSError 22 on large files

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@dataclass
class StationWindow:
    state: str
    minimum: datetime
    maximum: datetime
    count: int

    @property
    def span_seconds(self) -> float:
        return max(1.0, (self.maximum - self.minimum).total_seconds())

    def split(self, timestamp: datetime) -> str:
        position = (timestamp - self.minimum).total_seconds() / self.span_seconds
        if position < 0.70:
            return "train"
        if position < 0.85:
            return "validation"
        return "test"


@dataclass
class MetricAccumulator:
    count: int = 0
    absolute_error: float = 0.0
    squared_error: float = 0.0
    actual_sum: float = 0.0
    actual_squared_sum: float = 0.0

    def add(self, actual: float, predicted: float) -> None:
        error = actual - predicted
        self.count += 1
        self.absolute_error += abs(error)
        self.squared_error += error * error
        self.actual_sum += actual
        self.actual_squared_sum += actual * actual

    def as_dict(self) -> dict[str, float | int | None]:
        if self.count == 0:
            return {"count": 0, "mae": None, "rmse": None, "r2": None}
        total_variance = self.actual_squared_sum - (self.actual_sum * self.actual_sum / self.count)
        residual_sum = self.squared_error
        return {
            "count": self.count,
            "mae": self.absolute_error / self.count,
            "rmse": math.sqrt(self.squared_error / self.count),
            "r2": 1 - residual_sum / total_variance if total_variance > 0 else None,
        }


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def normalized_files(root: Path) -> list[Path]:
    patterns = ("*.normalized.csv", "*.quality_filtered.csv")
    seen: set[Path] = set()
    results: list[Path] = []
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.name.startswith("all_observations"):
                continue
            if path not in seen:
                seen.add(path)
                results.append(path)
    return sorted(results)


def station_windows(files: list[Path]) -> dict[str, StationWindow]:
    windows: dict[str, StationWindow] = {}
    for path in files:
        _raw = open(str(path), "rb", buffering=_READ_BUFFER)  # noqa: WPS515
        with io.TextIOWrapper(_raw, encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                station_id = row["station_id"]
                timestamp = parse_timestamp(row["timestamp"])
                existing = windows.get(station_id)
                if existing is None:
                    windows[station_id] = StationWindow(row.get("state") or "Unknown", timestamp, timestamp, 1)
                else:
                    existing.minimum = min(existing.minimum, timestamp)
                    existing.maximum = max(existing.maximum, timestamp)
                    existing.count += 1
    return windows


def evaluate(files: list[Path]) -> dict[str, object]:
    windows = station_windows(files)
    metrics: dict[str, MetricAccumulator] = defaultdict(MetricAccumulator)
    state_metrics: dict[str, dict[str, MetricAccumulator]] = defaultdict(lambda: defaultdict(MetricAccumulator))
    previous: dict[str, tuple[datetime, float]] = {}
    for path in files:
        _raw = open(str(path), "rb", buffering=_READ_BUFFER)  # noqa: WPS515
        with io.TextIOWrapper(_raw, encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                station_id = row["station_id"]
                timestamp = parse_timestamp(row["timestamp"])
                actual = float(row["groundwater_level"])
                if not math.isfinite(actual):
                    continue
                prior = previous.get(station_id)
                previous[station_id] = (timestamp, actual)
                if prior is None or timestamp <= prior[0]:
                    continue
                split = windows[station_id].split(timestamp)
                state = row.get("state") or windows[station_id].state
                metrics[split].add(actual, prior[1])
                state_metrics[state][split].add(actual, prior[1])

    return {
        "model_name": "persistence",
        "model_version": "1.0",
        "split_method": "per-station chronological timestamp windows: 70% train, 15% validation, 15% test",
        "resource_count": len(files),
        "station_count": len(windows),
        "metrics": {split: accumulator.as_dict() for split, accumulator in metrics.items()},
        "state_metrics": {
            state: {split: accumulator.as_dict() for split, accumulator in splits.items()}
            for state, splits in sorted(state_metrics.items())
        },
        "station_windows": {
            station: {
                "state": window.state,
                "minimum": window.minimum.isoformat(),
                "maximum": window.maximum.isoformat(),
                "observation_count": window.count,
            }
            for station, window in sorted(windows.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/all_states"))
    parser.add_argument("--output", type=Path, default=Path("models/persistence_evaluation.json"))
    args = parser.parse_args()
    files = normalized_files(args.input_dir)
    if not files:
        parser.error(f"No normalized resources found in {args.input_dir}")
    result = evaluate(files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = {key: result[key] for key in ("model_name", "model_version", "split_method", "resource_count", "station_count", "metrics")}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
