from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.analytics.historical import aggregate_station_history
from backend.app.database.models import Base, Observation
from backend.app.ml.persistence import persistence_forecast


def make_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_history_is_bounded_and_aggregated() -> None:
    session = make_session()
    start = datetime(2026, 1, 1)
    session.add_all([Observation(station_id=1, timestamp=start + timedelta(hours=index), groundwater_level=-10 + index, source="NWDP") for index in range(10)])
    session.commit()
    points = aggregate_station_history(session, station_id=1, buckets=3)
    assert len(points) <= 3
    assert sum(point["observation_count"] for point in points) == 10
    session.close()


def test_persistence_forecast_starts_after_latest_actual() -> None:
    session = make_session()
    latest = datetime(2026, 1, 1, 18)
    session.add(Observation(station_id=1, timestamp=latest, groundwater_level=-7.5, source="NWDP"))
    session.commit()
    forecast = persistence_forecast(session, station_id=1)
    assert forecast[0].forecast_time == latest + timedelta(hours=6)
    assert all(item.predicted_value == -7.5 for item in forecast)
    session.close()