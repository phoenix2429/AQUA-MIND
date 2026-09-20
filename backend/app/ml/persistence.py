"""Measured persistence forecasting baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import Observation


@dataclass(frozen=True)
class BaselineForecast:
    forecast_time: datetime
    predicted_value: float
    model_name: str = "persistence"
    model_version: str = "1.0"


def persistence_forecast(database: Session, station_id: int, horizon_points: int = 4, step_hours: int = 6) -> list[BaselineForecast]:
    if horizon_points < 1 or step_hours < 1:
        raise ValueError("horizon_points and step_hours must be positive")
    latest = database.scalar(
        select(Observation).where(Observation.station_id == station_id).order_by(Observation.timestamp.desc()).limit(1)
    )
    if latest is None:
        return []
    return [
        BaselineForecast(
            forecast_time=latest.timestamp + timedelta(hours=step_hours * point),
            predicted_value=float(latest.groundwater_level),
        )
        for point in range(1, horizon_points + 1)
    ]