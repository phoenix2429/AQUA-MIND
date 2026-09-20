"""Generate ML features from quality-filtered groundwater observations.

Feature engineering strategy
=============================

All features are derived ONLY from:
  * groundwater_level (the single measured variable)
  * timestamp (calendar decomposition)
  * station metadata (latitude, longitude, elevation_msl)

No rainfall, temperature, extraction, or aquifer data are used because
they are not present in the NWDP telemetry source files.

Features produced
-----------------
Per observation row (station_id + timestamp):

  AUTOREGRESSIVE LAGS (previous actual observations):
    lag_6h     — groundwater_level at t-6h
    lag_12h    — groundwater_level at t-12h
    lag_24h    — groundwater_level at t-24h
    lag_48h    — groundwater_level at t-48h
    lag_7d     — groundwater_level at t-7 days

  ROLLING STATISTICS (computed over trailing windows, no leakage):
    rolling_mean_7d   — 7-day trailing mean (≥ 4 observations required)
    rolling_std_7d    — 7-day trailing std  (≥ 4 observations required)
    rolling_mean_30d  — 30-day trailing mean (≥ 8 observations required)

  RECENT TREND:
    trend_7d   — OLS slope (m per hour) over last 7 days of actual observations

  CALENDAR:
    hour       — 0..23
    day_of_year — 1..366
    month      — 1..12
    season     — 0=winter, 1=spring, 2=summer, 3=monsoon (India-specific)
                  Dec-Feb=winter, Mar-May=spring, Jun-Sep=monsoon, Oct-Nov=autumn(3)

  STATION STATIC (constant per station):
    latitude
    longitude
    elevation_msl  (NaN if not available)

Feature availability
--------------------
Lag features require prior observations within the specified time window.
If a prior observation is not available (first rows of a station, gap in data),
the lag is set to NaN and the row is NOT discarded — the model handles NaN via
imputation at training time.

Rows with no autoregressive information at all (first observation per station)
are excluded from the feature dataset because there is nothing to predict from.

Target variable
---------------
  target — groundwater_level at time t (the value being predicted)

The feature set for each row represents inputs at time t-Δ (the latest
available prior observation), and the target is the observation at t.
This simulates the real inference scenario: given everything known up to
the previous observation, predict the next one.

Chronological integrity
------------------------
Features are computed in strict chronological order per station.
No future information is used to compute any feature for a given row.

Output format
-------------
data/processed/features/
    features_all_states.parquet   (primary — efficient columnar format)
    features_all_states.csv       (backup — readable but large)
    feature_stats.json            (column-level statistics and NaN rates)
    feature_engineering_report.json

Usage
-----
    python scripts/create_features.py
    python scripts/create_features.py --input-dir data/processed/quality_filtered
    python scripts/create_features.py --no-csv   # skip CSV backup for speed
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_READ_BUFFER = 64 << 20

# ------------------------------------------------------------------
# Season mapping (India-centric)
# ------------------------------------------------------------------

def _season(month: int) -> int:
    """0=winter(Dec-Feb), 1=spring(Mar-May), 2=monsoon(Jun-Sep), 3=autumn(Oct-Nov)."""
    if month in (12, 1, 2):
        return 0
    if month in (3, 4, 5):
        return 1
    if month in (6, 7, 8, 9):
        return 2
    return 3  # Oct, Nov


# ------------------------------------------------------------------
# Per-station rolling window state
# ------------------------------------------------------------------

@dataclass
class ObsRecord:
    timestamp: datetime
    gwl: float


@dataclass
class StationFeatureState:
    station_id: str
    state: str
    district: str
    latitude: float | None
    longitude: float | None
    elevation_msl: float | None
    history: list[ObsRecord] = field(default_factory=list)

    def add(self, record: ObsRecord) -> None:
        self.history.append(record)

    def _get_lag(self, current_ts: datetime, delta: timedelta) -> float | None:
        target_ts = current_ts - delta
        # find the closest record at or before target_ts
        best: ObsRecord | None = None
        tol = timedelta(hours=3)  # half a 6-hour interval
        for rec in reversed(self.history):
            if rec.timestamp <= target_ts + tol:
                if best is None or abs((rec.timestamp - target_ts).total_seconds()) < abs((best.timestamp - target_ts).total_seconds()):
                    best = rec
                break
        if best is None:
            return None
        # reject if too far from target
        if abs((best.timestamp - target_ts).total_seconds()) > 2 * 3600:
            return None
        return best.gwl

    def _rolling_stats(self, current_ts: datetime, window_days: int, min_obs: int = 4) -> tuple[float | None, float | None]:
        cutoff = current_ts - timedelta(days=window_days)
        window = [r.gwl for r in self.history if cutoff <= r.timestamp < current_ts]
        if len(window) < min_obs:
            return None, None
        mean = sum(window) / len(window)
        if len(window) < 2:
            return mean, None
        variance = sum((v - mean) ** 2 for v in window) / (len(window) - 1)
        return mean, math.sqrt(variance)

    def _rolling_mean_30d(self, current_ts: datetime, min_obs: int = 8) -> float | None:
        cutoff = current_ts - timedelta(days=30)
        window = [r.gwl for r in self.history if cutoff <= r.timestamp < current_ts]
        if len(window) < min_obs:
            return None
        return sum(window) / len(window)

    def _trend_7d(self, current_ts: datetime, min_obs: int = 4) -> float | None:
        """OLS slope in m/hour over last 7 days."""
        cutoff = current_ts - timedelta(days=7)
        pts = [(r.timestamp, r.gwl) for r in self.history if cutoff <= r.timestamp < current_ts]
        if len(pts) < min_obs:
            return None
        n = len(pts)
        origin = pts[0][0]
        xs = [(t - origin).total_seconds() / 3600.0 for t, _ in pts]
        ys = [gwl for _, gwl in pts]
        xmean = sum(xs) / n
        ymean = sum(ys) / n
        numerator = sum((x - xmean) * (y - ymean) for x, y in zip(xs, ys))
        denominator = sum((x - xmean) ** 2 for x in xs)
        if denominator < 1e-10:
            return 0.0
        return numerator / denominator

    def build_features(self, record: ObsRecord) -> dict[str, object] | None:
        """Compute features for this observation. Returns None if no prior history."""
        if not self.history:
            return None  # first observation — nothing to predict from

        ts = record.timestamp

        lag_6h = self._get_lag(ts, timedelta(hours=6))
        lag_12h = self._get_lag(ts, timedelta(hours=12))
        lag_24h = self._get_lag(ts, timedelta(hours=24))
        lag_48h = self._get_lag(ts, timedelta(hours=48))
        lag_7d = self._get_lag(ts, timedelta(days=7))

        mean_7d, std_7d = self._rolling_stats(ts, 7, min_obs=4)
        mean_30d = self._rolling_mean_30d(ts, min_obs=8)
        trend_7d = self._trend_7d(ts, min_obs=4)

        return {
            "station_id": self.station_id,
            "state": self.state,
            "district": self.district,
            "timestamp": ts.isoformat(),
            "target": record.gwl,
            # lags
            "lag_6h": lag_6h,
            "lag_12h": lag_12h,
            "lag_24h": lag_24h,
            "lag_48h": lag_48h,
            "lag_7d": lag_7d,
            # rolling
            "rolling_mean_7d": mean_7d,
            "rolling_std_7d": std_7d,
            "rolling_mean_30d": mean_30d,
            # trend
            "trend_7d": trend_7d,
            # calendar
            "hour": ts.hour,
            "day_of_year": ts.timetuple().tm_yday,
            "month": ts.month,
            "season": _season(ts.month),
            # station static
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_msl": self.elevation_msl,
        }


# ------------------------------------------------------------------
# Feature columns (in order)
# ------------------------------------------------------------------

FEATURE_COLUMNS = [
    "station_id", "state", "district", "timestamp", "target",
    "lag_6h", "lag_12h", "lag_24h", "lag_48h", "lag_7d",
    "rolling_mean_7d", "rolling_std_7d", "rolling_mean_30d",
    "trend_7d",
    "hour", "day_of_year", "month", "season",
    "latitude", "longitude", "elevation_msl",
]

NUMERIC_FEATURE_COLUMNS = [
    "lag_6h", "lag_12h", "lag_24h", "lag_48h", "lag_7d",
    "rolling_mean_7d", "rolling_std_7d", "rolling_mean_30d",
    "trend_7d",
    "hour", "day_of_year", "month", "season",
    "latitude", "longitude", "elevation_msl",
]


# ------------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------------

def generate_features(files: list[Path]) -> Iterator[dict[str, object]]:
    """Stream feature rows from all files. Files must be sorted (same order as normalization)."""
    # Pass 1: collect station metadata and chronological ordering
    station_states: dict[str, StationFeatureState] = {}
    all_rows: list[tuple[str, datetime, float, str, str, float | None, float | None, float | None]] = []

    print("Pass 1: loading observations and station metadata …", flush=True)
    for fpath in files:
        raw = open(str(fpath), "rb", buffering=_READ_BUFFER)
        with io.TextIOWrapper(raw, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                sid = row["station_id"]
                try:
                    ts = datetime.fromisoformat(row["timestamp"])
                    gwl = float(row["groundwater_level"])
                except (ValueError, KeyError):
                    continue

                lat = _safe_float(row.get("latitude"))
                lon = _safe_float(row.get("longitude"))
                elev = _safe_float(row.get("elevation_msl"))

                if sid not in station_states:
                    station_states[sid] = StationFeatureState(
                        station_id=sid,
                        state=row.get("state") or "",
                        district=row.get("district") or "",
                        latitude=lat,
                        longitude=lon,
                        elevation_msl=elev,
                    )

                all_rows.append((sid, ts, gwl, row.get("state") or "", row.get("district") or "", lat, lon, elev))

    print(f"  Loaded {len(all_rows):,} observations from {len(station_states):,} stations", flush=True)
    print("Pass 2: sorting chronologically …", flush=True)
    all_rows.sort(key=lambda r: (r[0], r[1]))  # sort by station_id then timestamp

    print("Pass 3: computing features …", flush=True)
    emitted = 0
    skipped_no_prior = 0

    for sid, ts, gwl, state, district, lat, lon, elev in all_rows:
        station = station_states[sid]
        record = ObsRecord(timestamp=ts, gwl=gwl)
        features = station.build_features(record)
        station.add(record)  # add AFTER building features (no leakage)

        if features is None:
            skipped_no_prior += 1
            continue

        emitted += 1
        yield features

    print(f"  Emitted: {emitted:,}  Skipped (no prior): {skipped_no_prior:,}", flush=True)


def _safe_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def compute_feature_stats(rows: list[dict]) -> dict[str, object]:
    """Compute per-column NaN rates and basic stats."""
    stats: dict[str, object] = {}
    n = len(rows)
    if n == 0:
        return stats
    for col in NUMERIC_FEATURE_COLUMNS:
        values = [r[col] for r in rows if r.get(col) is not None]
        nan_count = sum(1 for r in rows if r.get(col) is None)
        if values:
            stats[col] = {
                "count": len(values),
                "nan_count": nan_count,
                "nan_rate_pct": round(100.0 * nan_count / n, 2),
                "mean": round(sum(values) / len(values), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
            }
        else:
            stats[col] = {"count": 0, "nan_count": n, "nan_rate_pct": 100.0}
    return stats


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw = open(str(output_path), "wb", buffering=64 << 20)
    with io.TextIOWrapper(raw, encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in FEATURE_COLUMNS})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/quality_filtered"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/features"))
    parser.add_argument("--no-csv", action="store_true", help="Skip CSV backup (faster)")
    args = parser.parse_args()

    patterns = ("*.quality_filtered.csv", "*.normalized.csv")
    seen: set[Path] = set()
    files: list[Path] = []
    for pat in patterns:
        for p in args.input_dir.glob(pat):
            if p.name.startswith("all_observations"):
                continue
            if p not in seen:
                seen.add(p)
                files.append(p)
    files = sorted(files)

    if not files:
        parser.error(f"No quality_filtered or normalized CSVs found in {args.input_dir}")

    print(f"Feature engineering from {len(files)} files …")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Stream and collect (memory-intensive but needed for sort + stats)
    # For 21.5M rows this will use ~8–12 GB RAM peak.
    # If memory is a concern, use --no-csv and skip the in-memory collection;
    # write features directly to CSV in streaming fashion.
    print("Streaming feature rows …")
    feature_rows: list[dict] = list(generate_features(files))

    total_rows = len(feature_rows)
    print(f"\nTotal feature rows generated: {total_rows:,}")

    # Write Parquet (preferred) if pandas/pyarrow available
    csv_path = args.output_dir / "features_all_states.csv"
    parquet_path = args.output_dir / "features_all_states.parquet"
    try:
        import pandas as pd
        df = pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS)
        df.to_parquet(str(parquet_path), index=False)
        print(f"Wrote Parquet: {parquet_path}")
        if not args.no_csv:
            df.to_csv(str(csv_path), index=False)
            print(f"Wrote CSV:     {csv_path}")
    except ImportError:
        print("pandas/pyarrow not available — writing CSV only")
        if not args.no_csv:
            write_csv(feature_rows, csv_path)
            print(f"Wrote CSV: {csv_path}")

    # Feature stats
    print("Computing feature stats …")
    stats = compute_feature_stats(feature_rows)
    stats_path = args.output_dir / "feature_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"Wrote stats: {stats_path}")

    # Report
    nan_report = {col: d["nan_rate_pct"] for col, d in stats.items() if isinstance(d, dict)}
    report = {
        "feature_engineering_policy": "v1",
        "input_files": len(files),
        "total_feature_rows": total_rows,
        "features": NUMERIC_FEATURE_COLUMNS,
        "nan_rates_pct": nan_report,
        "notes": [
            "Lag features: NaN when prior observation not within ±2h of target window",
            "Rolling stats: NaN when fewer than min_obs observations in window",
            "Trend: OLS slope m/hour over 7 days; NaN if fewer than 4 observations",
            "Season: India-specific (0=winter Dec-Feb, 1=spring Mar-May, 2=monsoon Jun-Sep, 3=autumn Oct-Nov)",
            "elevation_msl: NaN for stations without RL_MSL in source data",
        ],
    }
    report_path = args.output_dir / "feature_engineering_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote report: {report_path}")

    print("\nFeature engineering complete.")
    print(f"  Total rows: {total_rows:,}")
    for col, rate in nan_report.items():
        marker = "⚠" if rate > 20 else "✓"
        print(f"  {marker} {col}: NaN {rate:.1f}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
