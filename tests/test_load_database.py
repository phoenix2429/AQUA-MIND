import csv
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.models import Base, Observation, Station
from scripts import load_database


def test_load_database_imports_canonical_files(tmp_path: Path, monkeypatch) -> None:
    observations = tmp_path / "observations.csv"
    stations = tmp_path / "stations.csv"
    with stations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "station_id", "station_name", "state", "district", "tehsil", "block", "village", "agency",
            "latitude", "longitude", "elevation_msl", "latest_observation_timestamp", "observation_count", "source", "source_file",
        ])
        writer.writeheader()
        writer.writerow({"station_id": "A", "station_name": "A", "state": "Telangana", "source": "NWDP", "source_file": "raw.csv", "latest_observation_timestamp": "2026-01-01 06:00:00", "observation_count": 1})
    with observations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["station_id", "timestamp", "groundwater_level", "unit", "source"])
        writer.writeheader()
        writer.writerow({"station_id": "A", "timestamp": "2026-01-01 06:00:00", "groundwater_level": "-10", "unit": "meter", "source": "NWDP"})

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(load_database, "SessionLocal", sessionmaker(bind=engine))

    result = load_database.load_csv(observations, stations)
    session = sessionmaker(bind=engine)()
    assert result == {"stations": 1, "observations": 1}
    assert session.query(Station).count() == 1
    assert session.query(Observation).count() == 1
    session.close()
