"""Compute versioned GSS, GBIM and DIE reports from normalized telemetry."""

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
from backend.app.database.models import AnalyticalResult, Observation, Recommendation, Station
from backend.app.database.session import SessionLocal
from sqlalchemy import select


def compute(paths: list[Path], state: str | None, config: AnalyticsConfig) -> dict:
    grouped = defaultdict(list)
    info = {}
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                if state and (row.get("state") or "").casefold() != state.casefold():
                    continue
                try:
                    item = Observation(timestamp=datetime.fromisoformat(row["timestamp"]), groundwater_level=float(row["groundwater_level"]))
                except (KeyError, TypeError, ValueError):
                    continue
                station_id = row.get("station_id")
                if not station_id:
                    continue
                grouped[station_id].append(item)
                info[station_id] = {key: row.get(key) or None for key in ("station_name", "state", "district", "latitude", "longitude", "elevation_msl")}
    results, insufficient, failed = [], 0, 0
    for station_id in sorted(grouped):
        try:
            gss = calculate_gss(grouped[station_id], config)
            gbim = calculate_gbim(grouped[station_id], config)
            die = calculate_die(gss, gbim, config)
            if not gss["sufficient"]:
                insufficient += 1
            results.append({"station_id": station_id, "station_info": info[station_id], "analytics_version": config.version, "gss": gss, "gbim": gbim, "die": die})
        except Exception:
            failed += 1
    return {
        "analytics_version": config.version,
        "state": state,
        "source_files": [str(path) for path in paths],
        "stations_processed": len(grouped),
        "successful": len(results) - insufficient,
        "insufficient": insufficient,
        "failed": failed,
        "results": results,
    }


def persist(report: dict) -> None:
    calculated_at = datetime.utcnow()
    with SessionLocal() as database:
        for item in report["results"]:
            station = database.scalar(select(Station).where(Station.station_id == item["station_id"]))
            if station is None:
                continue
            for result in (item["gss"], item["gbim"]):
                database.add(
                    AnalyticalResult(
                        station_id=station.id,
                        calculated_at=calculated_at,
                        result_type=result["result_type"],
                        version=report["analytics_version"],
                        score=result.get("score"),
                        profile=result.get("profile"),
                        components=result.get("components"),
                    )
                )
            die = item["die"]
            database.add(
                Recommendation(
                    station_id=station.id,
                    generated_at=calculated_at,
                    priority=die["priority"],
                    recommendation=die["action"],
                    reason=die["reason"],
                    source_indicator=die["source_indicators"],
                )
            )
        database.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/all_states"))
    parser.add_argument("--output", type=Path, default=Path("models/analytics.json"))
    parser.add_argument("--state")
    parser.add_argument("--min-observations", type=int)
    args = parser.parse_args()
    paths = sorted(path for path in args.input_dir.glob("*.normalized.csv") if not path.name.startswith("all_observations"))
    if not paths:
        parser.error(f"No normalized CSV files found in {args.input_dir}")
    config = AnalyticsConfig.from_environment()
    if args.min_observations is not None:
        config = AnalyticsConfig(min_observations=max(1, args.min_observations), decline_slope_m_per_day=config.decline_slope_m_per_day, volatility_m=config.volatility_m, jump_m=config.jump_m, recent_days=config.recent_days, version=config.version)
    report = compute(paths, args.state, config)
    persist(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("stations_processed", "successful", "insufficient", "failed")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
