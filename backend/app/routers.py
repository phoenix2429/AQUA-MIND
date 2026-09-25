"""Read-only station and observation REST endpoints."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database.models import AnalyticalResult, Observation, Station
from .database.session import get_db
from .analytics.historical import aggregate_station_history
from .analytics.decision import station_analytics
from .ml.forecast_service import generate_forecast, get_available_models_info
from .ml.persistence import persistence_forecast
from .ml.shap_explainer import ExplanationUnavailable, explain_station
from .schemas import ForecastPoint, HistoricalPoint, NearbyStation, NearbyStationList, ObservationList, StationList, StationSummary, GSSResponse, GBIMResponse, RecommendationResponse, StationAnalyticsSummary, SHAPExplanation

router = APIRouter(prefix="/api", tags=["telemetry"])


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    radius_km = 6371.0088
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


@router.get("/states", response_model=list[str])
def list_states(database: Session = Depends(get_db)) -> list[str]:
    values = database.scalars(select(Station.state).where(Station.state.is_not(None)).distinct().order_by(Station.state)).all()
    return list(values)


@router.get("/states/{state}/districts", response_model=list[str])
def list_districts(state: str, database: Session = Depends(get_db)) -> list[str]:
    values = database.scalars(
        select(Station.district)
        .where(Station.state == state, Station.district.is_not(None))
        .distinct()
        .order_by(Station.district)
    ).all()
    return list(values)


@router.get("/stations", response_model=StationList)
def list_stations(
    state: str | None = None,
    district: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    database: Session = Depends(get_db),
) -> StationList:
    statement = select(Station)
    count_statement = select(func.count()).select_from(Station)
    filters = []
    if state:
        filters.append(Station.state == state)
    if district:
        filters.append(Station.district == district)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    total = database.scalar(count_statement) or 0
    items = database.scalars(statement.order_by(Station.station_name).offset((page - 1) * page_size).limit(page_size)).all()
    return StationList(items=items, total=total, page=page, page_size=page_size)


@router.get("/stations/nearby", response_model=NearbyStationList)
def nearby_stations(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50, gt=0, le=500),
    limit: int = Query(10, ge=1, le=100),
    database: Session = Depends(get_db),
) -> NearbyStationList:
    stations = database.scalars(select(Station).where(Station.latitude.is_not(None), Station.longitude.is_not(None))).all()
    nearby = []
    for station in stations:
        distance = haversine_km(latitude, longitude, station.latitude, station.longitude)
        if distance <= radius_km:
            nearby.append(NearbyStation.model_validate({**StationSummary.model_validate(station).model_dump(), "distance_km": round(distance, 3)}))
    nearby.sort(key=lambda station: station.distance_km)
    return NearbyStationList(items=nearby[:limit], latitude=latitude, longitude=longitude, radius_km=radius_km)


@router.get("/stations/{station_id:path}/observations", response_model=ObservationList)
def list_observations(
    station_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=2000),
    database: Session = Depends(get_db),
) -> ObservationList:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")
    station = database.scalar(select(Station).where(Station.station_id == station_id))
    if station is None:
        raise HTTPException(status_code=404, detail="Station was not found")
    filters = [Observation.station_id == station.id]
    if start:
        filters.append(Observation.timestamp >= start)
    if end:
        filters.append(Observation.timestamp <= end)
    total = database.scalar(select(func.count()).select_from(Observation).where(*filters)) or 0
    items = database.scalars(
        select(Observation)
        .where(*filters)
        .order_by(Observation.timestamp)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ObservationList(items=items, total=total, page=page, page_size=page_size)


@router.get("/stations/{station_id:path}/history", response_model=list[HistoricalPoint])
def station_history(
    station_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    buckets: int = Query(500, ge=1, le=2000),
    database: Session = Depends(get_db),
) -> list[HistoricalPoint]:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")
    station = database.scalar(select(Station).where(Station.station_id == station_id))
    if station is None:
        raise HTTPException(status_code=404, detail="Station was not found")
    return aggregate_station_history(database, station.id, start=start, end=end, buckets=buckets)


@router.get("/stations/{station_id:path}/forecast", response_model=list[ForecastPoint])
def station_forecast(
    station_id: str,
    horizon_points: int = Query(4, ge=1, le=24),
    model: str = Query("persistence", pattern="^(persistence|random_forest|xgboost)$"),
    database: Session = Depends(get_db),
) -> list[ForecastPoint]:
    station = database.scalar(select(Station).where(Station.station_id == station_id))
    if station is None:
        raise HTTPException(status_code=404, detail="Station was not found")
    try:
        forecast = generate_forecast(database, station, model_name=model, horizon_points=horizon_points)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not forecast:
        raise HTTPException(status_code=422, detail="Forecast unavailable because the station has no observations")
    return forecast


def _station_explanation(station_id: str, model: str, database: Session) -> SHAPExplanation:
    station = database.scalar(select(Station).where(Station.station_id == station_id))
    if station is None:
        raise HTTPException(status_code=404, detail="Station was not found")
    try:
        return explain_station(database, station, model_name=model)
    except (FileNotFoundError, ExplanationUnavailable) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/stations/{station_id:path}/explanation", response_model=SHAPExplanation)
def station_explanation(
    station_id: str,
    model: str = Query("xgboost", pattern="^(random_forest|xgboost)$"),
    database: Session = Depends(get_db),
) -> SHAPExplanation:
    return _station_explanation(station_id, model, database)


@router.get("/stations/{station_id:path}/shap", response_model=SHAPExplanation)
def station_shap(
    station_id: str,
    model: str = Query("xgboost", pattern="^(random_forest|xgboost)$"),
    database: Session = Depends(get_db),
) -> SHAPExplanation:
    return _station_explanation(station_id, model, database)


@router.get("/stations/{station_id:path}/analytics", response_model=StationAnalyticsSummary)
def station_decision_analytics(station_id: str, database: Session = Depends(get_db)) -> dict[str, Any]:
    """Return versioned descriptive GSS, GBIM, and DIE outputs."""
    station = database.scalar(select(Station).where(Station.station_id == station_id))
    if station is None:
        raise HTTPException(status_code=404, detail="Station was not found")
    return station_analytics(database, station)


@router.get("/stations/{station_id:path}/gss", response_model=GSSResponse)
def station_gss(station_id: str, database: Session = Depends(get_db)) -> dict[str, Any]:
    result = station_decision_analytics(station_id, database)
    return result["gss"]


@router.get("/stations/{station_id:path}/gbim", response_model=GBIMResponse)
def station_gbim(station_id: str, database: Session = Depends(get_db)) -> dict[str, Any]:
    result = station_decision_analytics(station_id, database)
    return result["gbim"]


@router.get("/stations/{station_id:path}/die", response_model=RecommendationResponse)
def station_die(station_id: str, database: Session = Depends(get_db)) -> dict[str, Any]:
    result = station_decision_analytics(station_id, database)
    return result["die"]


@router.get("/stations/{station_id:path}/sustainability", response_model=GSSResponse)
def station_sustainability(station_id: str, database: Session = Depends(get_db)) -> dict[str, Any]:
    return station_gss(station_id, database)


@router.get("/stations/{station_id:path}/behavior", response_model=GBIMResponse)
def station_behavior(station_id: str, database: Session = Depends(get_db)) -> dict[str, Any]:
    return station_gbim(station_id, database)


@router.get("/stations/{station_id:path}/recommendations", response_model=RecommendationResponse)
def station_recommendations(station_id: str, database: Session = Depends(get_db)) -> dict[str, Any]:
    return station_die(station_id, database)


@router.get("/stations/{station_id:path}", response_model=StationSummary)
def get_station(station_id: str, database: Session = Depends(get_db)) -> Station:
    station = database.scalar(select(Station).where(Station.station_id == station_id))
    if station is None:
        raise HTTPException(status_code=404, detail="Station was not found")
    return station


@router.get("/models")
def list_models() -> list[dict[str, Any]]:
    return get_available_models_info()


@router.get("/admin/health")
def admin_health(database: Session = Depends(get_db)) -> dict[str, Any]:
    latest = database.scalar(select(func.max(Observation.timestamp)))
    station_count = database.scalar(select(func.count()).select_from(Station)) or 0
    observation_count = database.scalar(select(func.count()).select_from(Observation)) or 0
    now = datetime.utcnow()
    age_hours = (now - latest).total_seconds() / 3600 if latest else None
    return {
        "status": "ok",
        "database": "ok",
        "station_count": station_count,
        "observation_count": observation_count,
        "latest_observation_timestamp": latest,
        "freshness_hours": round(age_hours, 2) if age_hours is not None else None,
        "pipeline_status": "loaded" if observation_count else "empty",
    }


@router.get("/regional/summary")
def regional_summary(
    state: str | None = None,
    district: str | None = None,
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    filters = []
    if state:
        filters.append(Station.state == state)
    if district:
        filters.append(Station.district == district)
    station_query = select(Station).where(*filters)
    station_ids = select(Station.id).where(*filters)
    stations = database.scalars(station_query).all()
    rows = database.execute(
        select(
            func.count(Observation.id),
            func.avg(Observation.groundwater_level),
            func.min(Observation.groundwater_level),
            func.max(Observation.groundwater_level),
            func.max(Observation.timestamp),
        ).where(
            Observation.station_id.in_(station_ids),
            Observation.groundwater_level >= -300,
            Observation.groundwater_level <= 50,
        )
    ).one()
    distribution = database.execute(
        select(Station.state, func.count(Station.id)).where(*filters).group_by(Station.state)
    ).all()
    return {
        "state": state,
        "district": district,
        "station_count": len(stations),
        "observation_count": rows[0] or 0,
        "average_groundwater_level": rows[1],
        "minimum_groundwater_level": rows[2],
        "maximum_groundwater_level": rows[3],
        "latest_observation_timestamp": rows[4],
        "state_station_distribution": [{"state": item[0], "stations": item[1]} for item in distribution],
        "persisted_analytics_count": database.scalar(
            select(func.count()).select_from(AnalyticalResult).where(AnalyticalResult.station_id.in_(station_ids))
        ) or 0,
    }
