"""Pydantic response schemas for the public telemetry API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: str
    source_station_id: str | None
    station_name: str
    state: str | None
    district: str | None
    tehsil: str | None
    block: str | None
    village: str | None
    agency: str | None
    latitude: float | None
    longitude: float | None
    elevation_msl: float | None
    source: str
    latest_observation_timestamp: datetime | None
    observation_count: int


class StationList(BaseModel):
    items: list[StationSummary]
    total: int
    page: int
    page_size: int


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    groundwater_level: float
    unit: str
    source: str


class ObservationList(BaseModel):
    items: list[ObservationResponse]
    total: int
    page: int
    page_size: int


class HistoricalPoint(BaseModel):
    timestamp: datetime
    groundwater_level: float
    observation_count: int


class ForecastPoint(BaseModel):
    forecast_time: datetime
    predicted_value: float
    model_name: str
    model_version: str


class NearbyStation(StationSummary):
    distance_km: float = Field(ge=0)


class NearbyStationList(BaseModel):
    items: list[NearbyStation]
    latitude: float
    longitude: float
    radius_km: float


class GSSResponse(BaseModel):
    analytics_version: str
    result_type: str = "GSS"
    score: float | None
    profile: Literal["STABLE", "WATCH", "VARIABLE", "INSUFFICIENT_DATA"]
    sufficient: bool
    data_sufficiency: str = "INSUFFICIENT"
    observation_count: int = 0
    history_days: float | None = None
    history_years: float | None = None
    reason: str
    components: dict


class GBIMResponse(BaseModel):
    analytics_version: str
    result_type: str = "GBIM"
    score: float | None
    profile: Literal["STABLE", "DECLINING", "RISING", "VOLATILE", "INSUFFICIENT_DATA"]
    sufficient: bool
    data_sufficiency: str = "INSUFFICIENT"
    observation_count: int = 0
    history_days: float | None = None
    history_years: float | None = None
    reason: str
    components: dict


class RecommendationResponse(BaseModel):
    analytics_version: str
    result_type: str = "DIE"
    score: float | None
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    profile: str
    sufficient: bool
    recommendation: str
    action: str | None = None
    reason: str
    components: dict
    source_indicators: dict = {}


class StationAnalyticsSummary(BaseModel):
    station_id: str
    station_info: dict
    analytics_version: str
    gss: GSSResponse
    gbim: GBIMResponse
    die: RecommendationResponse
