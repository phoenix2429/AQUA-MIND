"""Initialize the schema and load the repository's canonical processed data.

The loader is intentionally additive/idempotent.  It does not delete existing
stations or observations; use ``load_database.py --replace`` only for an
explicit local rebuild.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.database.init_db import initialize_database
from backend.app.database.models import Observation, Station
from backend.app.database.session import SessionLocal
from scripts.load_database import load_csv


def _default_paths(root: Path) -> tuple[Path, Path]:
    data = root / "data" / "processed" / "all_states"
    return data / "all_observations.normalized.csv", data / "stations_all_states.csv"


def _count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def setup_database(root: Path, observations: Path | None = None,
                   stations: Path | None = None) -> dict[str, int]:
    default_observations, default_stations = _default_paths(root)
    observations = observations or default_observations
    stations = stations or default_stations
    for path in (observations, stations):
        if not path.is_file():
            raise FileNotFoundError(f"canonical data file not found: {path}")

    initialize_database()
    result = load_csv(observations, stations)
    with SessionLocal() as session:
        counts = {
            "stations": session.query(Station).count(),
            "observations": session.query(Observation).count(),
        }
    expected = {"stations": _count_rows(stations), "observations": counts["observations"]}
    if counts["stations"] < expected["stations"]:
        raise RuntimeError(f"database validation failed: expected at least {expected}, found {counts}")
    return {**result, "database_stations": counts["stations"], "database_observations": counts["observations"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--stations", type=Path)
    args = parser.parse_args()
    print(setup_database(args.root.resolve(), args.observations, args.stations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
