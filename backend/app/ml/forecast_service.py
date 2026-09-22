"""Unified forecasting service supporting Persistence, Random Forest, and XGBoost.

This module provides a production-grade interface for generating station forecasts
across available ML models while preserving the persistence baseline.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import Observation, Station
from .persistence import BaselineForecast, persistence_forecast
from .random_forest import GroundwaterRandomForest
from .xgboost_model import GroundwaterXGBoost

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"


@dataclass(frozen=True)
class MLForecastPoint:
    forecast_time: datetime
    predicted_value: float
    model_name: str
    model_version: str = "1.0"


_MODEL_CACHE: dict[tuple[str, str], Any] = {}


def load_ml_model(model_name: str, model_dir: Path | None = None) -> Any:
    """Load and cache a trained ML model (RandomForest or XGBoost)."""
    base_dir = model_dir or MODELS_DIR
    cache_key = (model_name, str(base_dir.resolve()))
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
    target_dir = base_dir / model_name
    if not target_dir.is_dir() or not (target_dir / "model.joblib").is_file():
        raise FileNotFoundError(f"Model artifacts for '{model_name}' not found at {target_dir}")

    if model_name == "random_forest":
        model = GroundwaterRandomForest.load(target_dir)
    elif model_name == "xgboost":
        model = GroundwaterXGBoost.load(target_dir)
    else:
        raise ValueError(f"Unsupported ML model: {model_name}")

    _MODEL_CACHE[cache_key] = model
    return model


def _extract_station_features(
    station: Station, observations: list[Observation]
) -> np.ndarray | None:
    """Extract 16 feature columns from historical observations up to latest timestamp."""
    if not observations:
        return None

    # Observations sorted chronologically
    sorted_obs = sorted(observations, key=lambda o: o.timestamp)
    latest = sorted_obs[-1]
    t = latest.timestamp

    # Build timestamp -> gwl map
    ts_map = {o.timestamp: float(o.groundwater_level) for o in sorted_obs}

    def _get_lag(delta: timedelta) -> float:
        target_t = t - delta
        # Look for exact match or nearest within 1 hour
        if target_t in ts_map:
            return ts_map[target_t]
        for dt_secs in (1800, 3600):
            for candidate in (target_t + timedelta(seconds=dt_secs), target_t - timedelta(seconds=dt_secs)):
                if candidate in ts_map:
                    return ts_map[candidate]
        return np.nan

    lag_6h = _get_lag(timedelta(hours=6))
    lag_12h = _get_lag(timedelta(hours=12))
    lag_24h = _get_lag(timedelta(hours=24))
    lag_48h = _get_lag(timedelta(hours=48))
    lag_7d = _get_lag(timedelta(days=7))

    # Rolling windows
    obs_7d = [o.groundwater_level for o in sorted_obs if o.timestamp >= t - timedelta(days=7)]
    obs_30d = [o.groundwater_level for o in sorted_obs if o.timestamp >= t - timedelta(days=30)]

    rolling_mean_7d = float(np.mean(obs_7d)) if obs_7d else np.nan
    rolling_std_7d = float(np.std(obs_7d)) if len(obs_7d) > 1 else 0.0
    rolling_mean_30d = float(np.mean(obs_30d)) if obs_30d else np.nan

    # Trend 7d (OLS slope)
    if len(obs_7d) >= 2:
        recent = [o for o in sorted_obs if o.timestamp >= t - timedelta(days=7)]
        xs = np.array([(o.timestamp - (t - timedelta(days=7))).total_seconds() / 3600.0 for o in recent])
        ys = np.array([float(o.groundwater_level) for o in recent])
        cov = np.cov(xs, ys)
        trend_7d = cov[0, 1] / cov[0, 0] if cov[0, 0] > 0 else 0.0
    else:
        trend_7d = 0.0

    # Calendar features
    hour = float(t.hour)
    day_of_year = float(t.timetuple().tm_yday)
    month = float(t.month)
    if month in (1, 2):
        season = 0.0  # Winter
    elif month in (3, 4, 5):
        season = 1.0  # Pre-monsoon
    elif month in (6, 7, 8, 9):
        season = 2.0  # Monsoon
    else:
        season = 3.0  # Post-monsoon

    # Geospatial
    latitude = float(station.latitude) if station.latitude is not None else np.nan
    longitude = float(station.longitude) if station.longitude is not None else np.nan
    elevation_msl = float(station.elevation_msl) if station.elevation_msl is not None else np.nan

    feat_vector = np.array([
        lag_6h,
        lag_12h,
        lag_24h,
        lag_48h,
        lag_7d,
        rolling_mean_7d,
        rolling_std_7d,
        rolling_mean_30d,
        trend_7d,
        hour,
        day_of_year,
        month,
        season,
        latitude,
        longitude,
        elevation_msl,
    ], dtype=np.float32).reshape(1, -1)

    return feat_vector


def generate_forecast(
    database: Session,
    station: Station,
    model_name: str = "persistence",
    horizon_points: int = 4,
    step_hours: int = 6,
    model_dir: Path | None = None,
) -> list[BaselineForecast | MLForecastPoint]:
    """Generate groundwater forecasts using specified model.

    Supported models:
      - 'persistence': Last-known value baseline (default)
      - 'random_forest': Trained scikit-learn Random Forest model
      - 'xgboost': Trained XGBoost model
    """
    if horizon_points < 1 or step_hours < 1:
        raise ValueError("horizon_points and step_hours must be positive")

    if model_name == "persistence":
        return persistence_forecast(database, station.id, horizon_points=horizon_points, step_hours=step_hours)

    if model_name not in ("random_forest", "xgboost"):
        raise ValueError(f"Unknown model '{model_name}'. Choose from 'persistence', 'random_forest', 'xgboost'.")

    # Load trained model
    model = load_ml_model(model_name, model_dir=model_dir)

    # Fetch station observations needed for 30d window
    observations = list(
        database.scalars(
            select(Observation)
            .where(Observation.station_id == station.id)
            .order_by(Observation.timestamp.desc())
            .limit(200)
        ).all()
    )

    if not observations:
        return []

    X = _extract_station_features(station, observations)
    if X is None:
        return []

    # Replace NaNs with zero or mean if needed for models that don't handle NaN
    if model_name == "random_forest":
        nan_mask = np.isnan(X)
        if np.any(nan_mask):
            X = np.nan_to_num(X, nan=0.0)

    # Generate one-step forecast
    pred_val = float(model.predict(X)[0])
    latest_ts = max(o.timestamp for o in observations)

    # Multi-step projections using step interval
    results: list[BaselineForecast | MLForecastPoint] = []
    for step in range(1, horizon_points + 1):
        results.append(
            MLForecastPoint(
                forecast_time=latest_ts + timedelta(hours=step_hours * step),
                predicted_value=round(pred_val, 4),
                model_name=model_name,
                model_version="1.0",
            )
        )
    return results


def get_available_models_info(model_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return list and status of supported forecasting models."""
    base_dir = model_dir or MODELS_DIR
    eval_file = base_dir / "model_evaluation.json"
    eval_data: dict[str, Any] = {}
    if eval_file.is_file():
        try:
            eval_data = json.loads(eval_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Could not read model_evaluation.json: %s", exc)

    models_info = [
        {
            "model_name": "persistence",
            "display_name": "Persistence Baseline",
            "type": "baseline",
            "version": "1.0",
            "status": "ready",
            "test_metrics": eval_data.get("models", {}).get("persistence", {}).get("test_metrics"),
        },
        {
            "model_name": "random_forest",
            "display_name": "Random Forest Regressor",
            "type": "machine_learning",
            "version": "1.0",
            "status": "ready" if (base_dir / "random_forest" / "model.joblib").is_file() else "not_trained",
            "test_metrics": eval_data.get("models", {}).get("random_forest", {}).get("test_metrics"),
        },
        {
            "model_name": "xgboost",
            "display_name": "XGBoost Regressor",
            "type": "machine_learning",
            "version": "1.0",
            "status": "ready" if (base_dir / "xgboost" / "model.joblib").is_file() else "not_trained",
            "test_metrics": eval_data.get("models", {}).get("xgboost", {}).get("test_metrics"),
        },
    ]
    return models_info
