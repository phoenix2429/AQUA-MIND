"""SQLAlchemy persistence models for AQUA-MIND."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_station_id: Mapped[str | None] = mapped_column(String(255), index=True)
    station_name: Mapped[str] = mapped_column(String(255))
    state: Mapped[str | None] = mapped_column(String(128), index=True)
    district: Mapped[str | None] = mapped_column(String(128), index=True)
    tehsil: Mapped[str | None] = mapped_column(String(128))
    block: Mapped[str | None] = mapped_column(String(128))
    village: Mapped[str | None] = mapped_column(String(255))
    agency: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    elevation_msl: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64))
    source_file: Mapped[str] = mapped_column(Text)
    latest_observation_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)

    observations: Mapped[list[Observation]] = relationship(back_populates="station")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    groundwater_level: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), default="meter")
    source: Mapped[str] = mapped_column(String(64))

    station: Mapped[Station] = relationship(back_populates="observations")
    __table_args__ = (UniqueConstraint("station_id", "timestamp", name="uq_observation_station_timestamp"), Index("ix_observations_station_timestamp", "station_id", "timestamp"))


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    forecast_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    predicted_value: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(128))
    model_version: Mapped[str] = mapped_column(String(64))


class AnalyticalResult(Base):
    __tablename__ = "analytical_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    result_type: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[float | None] = mapped_column(Float)
    profile: Mapped[str | None] = mapped_column(String(255))
    components: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    priority: Mapped[str] = mapped_column(String(32), index=True)
    recommendation: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    source_indicator: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(64))
    training_start: Mapped[datetime | None] = mapped_column(DateTime)
    training_end: Mapped[datetime | None] = mapped_column(DateTime)
    validation_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    test_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(128), index=True)
    resource_name: Mapped[str] = mapped_column(String(255))
    state: Mapped[str | None] = mapped_column(String(128), index=True)
    period: Mapped[str | None] = mapped_column(String(32))
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime)
    latest_observation_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), index=True)
