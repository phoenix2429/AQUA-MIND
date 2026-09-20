"""Pydantic response schemas for the public telemetry API."""

from __future__ import annotations

from datetime import datetime

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
