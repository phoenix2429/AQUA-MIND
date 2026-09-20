from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.app.database.models import Base, Observation, Station


@pytest.fixture()
def database_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_station_and_observation_persist(database_session) -> None:
    station = Station(
        station_id="A",
        station_name="Station A",
        state="Telangana",
        source="NWDP",
        source_file="raw.csv",
    )
    database_session.add(station)
    database_session.flush()
    database_session.add(
        Observation(
            station_id=station.id,
            timestamp=datetime(2026, 1, 1),
            groundwater_level=-10.5,
            source="NWDP",
        )
    )
    database_session.commit()
    assert database_session.query(Observation).count() == 1


def test_station_timestamp_is_unique(database_session) -> None:
    station = Station(station_id="A", station_name="Station A", source="NWDP", source_file="raw.csv")
    database_session.add(station)
    database_session.flush()
    values = {"station_id": station.id, "timestamp": datetime(2026, 1, 1), "groundwater_level": -1, "source": "NWDP"}
    database_session.add_all([Observation(**values), Observation(**values)])
    with pytest.raises(IntegrityError):
        database_session.commit()
