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


def test_forecast_persistence_default() -> None:
    client = make_client()
    resp = client.get("/api/stations/A/forecast")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    assert data[0]["model_name"] == "persistence"
    assert data[0]["predicted_value"] == -9.0


def test_forecast_ml_models() -> None:
    client = make_client()
    # Random Forest
    resp_rf = client.get("/api/stations/A/forecast?model=random_forest&horizon_points=2")
    assert resp_rf.status_code == 200
    data_rf = resp_rf.json()
    assert len(data_rf) == 2
    assert data_rf[0]["model_name"] == "random_forest"
    assert isinstance(data_rf[0]["predicted_value"], float)

    # XGBoost
    resp_xgb = client.get("/api/stations/A/forecast?model=xgboost&horizon_points=2")
    assert resp_xgb.status_code == 200
    data_xgb = resp_xgb.json()
    assert len(data_xgb) == 2
    assert data_xgb[0]["model_name"] == "xgboost"
    assert isinstance(data_xgb[0]["predicted_value"], float)


def test_forecast_invalid_model_fails_validation() -> None:
    client = make_client()
    resp = client.get("/api/stations/A/forecast?model=unknown_deep_net")
    assert resp.status_code == 422


def test_list_models_endpoint() -> None:
    client = make_client()
    resp = client.get("/api/models")
    assert resp.status_code == 200
    models = resp.json()
    names = [m["model_name"] for m in models]
    assert "persistence" in names
    assert "random_forest" in names
    assert "xgboost" in names

