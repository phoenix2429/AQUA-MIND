from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database.models import Base, Observation, Station
from backend.app.database.session import get_db
from backend.app.main import create_app


def make_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    station = Station(station_id="A", station_name="Station A", state="Telangana", district="Demo", agency="NWDP", source="NWDP", source_file="raw.csv", latitude=17.0, longitude=78.0, observation_count=2, latest_observation_timestamp=datetime(2026, 1, 1, 6))
    second = Station(station_id="B", station_name="Station B", state="Telangana", district="Other", agency="NWDP", source="NWDP", source_file="raw.csv", latitude=18.0, longitude=79.0, observation_count=1, latest_observation_timestamp=datetime(2026, 1, 1))
    session.add_all([station, second])
    session.flush()
    session.add_all([
        Observation(station_id=station.id, timestamp=datetime(2026, 1, 1), groundwater_level=-10, source="NWDP"),
        Observation(station_id=station.id, timestamp=datetime(2026, 1, 1, 6), groundwater_level=-9, source="NWDP"),
    ])
    session.commit()
    session.close()

    application = create_app()
    application.dependency_overrides[get_db] = lambda: session_factory()
    return TestClient(application)


def test_health_and_station_pagination() -> None:
    client = make_client()
    assert client.get("/health").json()["status"] == "ok"
    response = client.get("/api/stations?page=1&page_size=1")
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


def test_observations_and_nearby_search() -> None:
    client = make_client()
    observations = client.get("/api/stations/A/observations?page_size=10")
    assert observations.status_code == 200
    assert observations.json()["total"] == 2
    nearby = client.get("/api/stations/nearby?latitude=17&longitude=78&radius_km=10")
    assert nearby.status_code == 200
    assert nearby.json()["items"][0]["station_id"] == "A"
    assert nearby.json()["items"][0]["distance_km"] == 0


def test_unknown_station_returns_404() -> None:
    client = make_client()
    assert client.get("/api/stations/missing").status_code == 404
