"""Load canonical station and observation CSVs into the configured database."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import datetime
from pathlib import Path

_READ_BUFFER = 64 << 20  # 64 MB — avoids Windows OSError 22 on large files

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from backend.app.database.models import Observation, Station
from backend.app.database.session import SessionLocal


def _observation_insert(session: Session, rows: list[dict[str, object]]):
    """Insert a batch without re-querying every station/timestamp pair."""
    dialect = session.bind.dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
        return dialect_insert(Observation).values(rows).on_conflict_do_nothing(
            index_elements=["station_id", "timestamp"]
        )
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
        return dialect_insert(Observation).values(rows).on_conflict_do_nothing(
            constraint="uq_observation_station_timestamp"
        )
    return insert(Observation), rows


def load_csv(
    observations_path: Path,
    stations_path: Path,
    batch_size: int = 2_000,
    *,
    replace: bool = False,
) -> dict[str, int]:
    """Load canonical CSVs idempotently.

    Existing rows are retained by default.  ``replace=True`` is an explicit
    destructive operation for local rebuilds and is never used by setup.
    """
    session: Session = SessionLocal()
    station_rows = 0
    observation_rows = 0
    try:
        if replace:
            from sqlalchemy import delete
            session.execute(delete(Observation))
            session.execute(delete(Station))
            session.commit()
        station_rows_to_insert = []
        with stations_path.open("r", encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                station = {"station_id": row["station_id"], "source_station_id": row.get("source_station_id"), "station_name": row["station_name"], "source": row["source"], "source_file": row["source_file"]}
                for field in ("state", "district", "tehsil", "block", "village", "agency", "latitude", "longitude", "elevation_msl", "latest_observation_timestamp", "observation_count"):
                    value = row.get(field) or None
                    if value is not None and field in {"latitude", "longitude", "elevation_msl"}:
                        value = float(value)
                    if value is not None and field == "observation_count":
                        value = int(value)
                    if value is not None and field == "latest_observation_timestamp":
                        value = datetime.fromisoformat(value)
                    station[field] = value
                station_rows_to_insert.append(station)
                station_rows += 1
        existing_stations = {
            station_id: station
            for station_id, station in session.execute(
                select(Station.station_id, Station)
            ).all()
        }
        unique_station_rows = {
            row["station_id"]: row for row in station_rows_to_insert
        }
        new_stations = [
            row for station_id, row in unique_station_rows.items()
            if station_id not in existing_stations
        ]
        if new_stations:
            session.execute(insert(Station), new_stations)
        session.commit()

        station_map = {
            station.station_id: station
            for station in session.scalars(select(Station)).all()
        }
        station_map = dict(session.execute(select(Station.station_id, Station.id)).all())
        pending: list[dict[str, object]] = []
        pending_keys: set[tuple[int, datetime]] = set()
        _raw_obs = open(str(observations_path), "rb", buffering=_READ_BUFFER)  # noqa: WPS515
        with io.TextIOWrapper(_raw_obs, encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                station_id = station_map.get(row["station_id"])
                if station_id is None:
                    raise ValueError(f"Observation references missing station: {row['station_id']}")
                timestamp = datetime.fromisoformat(row["timestamp"])
                key = (station_id, timestamp)
                if key in pending_keys:
                    continue
                pending_keys.add(key)
                pending.append({"station_id": station_id, "timestamp": timestamp, "groundwater_level": float(row["groundwater_level"]), "unit": row["unit"], "source": row["source"]})
                if len(pending) >= batch_size:
                    statement = _observation_insert(session, pending)
                    if isinstance(statement, tuple):
                        result = session.execute(statement[0], pending)
                    else:
                        result = session.execute(statement)
                    session.commit()
                    observation_rows += result.rowcount if result.rowcount is not None else len(pending)
                    pending.clear()
                    pending_keys.clear()
        if pending:
            statement = _observation_insert(session, pending)
            if isinstance(statement, tuple):
                result = session.execute(statement[0], pending)
            else:
                result = session.execute(statement)
            session.commit()
            observation_rows += result.rowcount if result.rowcount is not None else len(pending)
        return {"stations": station_rows, "observations": observation_rows}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("stations", type=Path)
    parser.add_argument("--replace", action="store_true",
                        help="Delete existing telemetry before loading (destructive)")
    args = parser.parse_args()
    print(load_csv(args.observations, args.stations, replace=args.replace))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())