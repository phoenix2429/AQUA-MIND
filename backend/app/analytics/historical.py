"""Server-side historical trend aggregation for station observations."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database.models import Observation


class TrendPoint(TypedDict):
    timestamp: datetime
    groundwater_level: float
    observation_count: int


def aggregate_station_history(
    database: Session,
    station_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
    buckets: int = 500,
) -> list[TrendPoint]:
    """Return at most ``buckets`` time-ordered means for one station.

    Bucket assignment is performed in SQL using the observation ordinal. This
    keeps the API response bounded and leaves raw observations in the database.
    """
    if buckets < 1:
        raise ValueError("buckets must be positive")
    filters = [Observation.station_id == station_id]
    if start:
        filters.append(Observation.timestamp >= start)
    if end:
        filters.append(Observation.timestamp <= end)
    total = database.scalar(select(func.count()).select_from(Observation).where(*filters)) or 0
    if total == 0:
        return []
    rows = database.scalars(select(Observation).where(*filters).order_by(Observation.timestamp)).all()
    stride = max(1, (len(rows) + buckets - 1) // buckets)
    points: list[TrendPoint] = []
    for offset in range(0, len(rows), stride):
        group = rows[offset : offset + stride]
        points.append(
            {
                "timestamp": group[0].timestamp,
                "groundwater_level": sum(item.groundwater_level for item in group) / len(group),
                "observation_count": len(group),
            }
        )
    return points[:buckets]