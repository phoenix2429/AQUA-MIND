"""Run deterministic GSS, GBIM, and DIE analytics on normalized telemetry CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.analytics.decision import AnalyticsConfig, calculate_die, calculate_gbim, calculate_gss
from backend.app.database.models import Observation


def run(input_path: Path, config: AnalyticsConfig) -> dict[str, object]:
    grouped: dict[str, list[Observation]] = defaultdict(list)
    station_info: dict[str, dict[str, object]] = {}
    with input_path.open("r", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            try:
                timestamp = datetime.fromisoformat(row["timestamp"])
                level = float(row["groundwater_level"])
            except (KeyError, TypeError, ValueError):
                continue
            station_id = row.get("station_id") or ""
            if not station_id:
                continue
            grouped[station_id].append(Observation(timestamp=timestamp, groundwater_level=level))
            station_info[station_id] = {
                key: row.get(key) or None
                for key in ("station_name", "state", "district", "latitude", "longitude", "elevation_msl")
            }
    results = []
    for station_id in sorted(grouped):
        gss = calculate_gss(grouped[station_id], config)
        gbim = calculate_gbim(grouped[station_id], config)
        results.append(
            {
                "station_id": station_id,
                "station_info": station_info[station_id],
                "analytics_version": config.version,
                "gss": gss,
                "gbim": gbim,
                "die": calculate_die(gss, gbim, config),
            }
        )
    return {"analytics_version": config.version, "source": str(input_path), "station_count": len(results), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="normalized CSV containing station_id, timestamp, and groundwater_level")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-observations", type=int, default=None)
    args = parser.parse_args()
    config = AnalyticsConfig.from_environment()
    if args.min_observations is not None:
        config = AnalyticsConfig(min_observations=max(1, args.min_observations), decline_slope_m_per_day=config.decline_slope_m_per_day, volatility_m=config.volatility_m, jump_m=config.jump_m, recent_days=config.recent_days, version=config.version)
    result = run(args.input, config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"station_count": result["station_count"], "output": str(args.output), "analytics_version": config.version}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
