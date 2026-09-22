"""Tree SHAP explanations for the trained AQUA-MIND tree models.

Explanations are deliberately descriptive: a positive contribution means that
the feature moved the prediction upward relative to the model baseline.  It
does not imply a causal relationship.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import Observation, Station
from .forecast_service import MODELS_DIR, _extract_station_features, load_ml_model

FEATURE_NAMES = (
    "lag_6h", "lag_12h", "lag_24h", "lag_48h", "lag_7d",
    "rolling_mean_7d", "rolling_std_7d", "rolling_mean_30d", "trend_7d",
    "hour", "day_of_year", "month", "season", "latitude", "longitude",
    "elevation_msl",
)

FEATURE_DISPLAY_NAMES = {
    "lag_6h": "Groundwater level 6 hours earlier",
    "lag_12h": "Groundwater level 12 hours earlier",
    "lag_24h": "Groundwater level 24 hours earlier",
    "lag_48h": "Groundwater level 48 hours earlier",
    "lag_7d": "Groundwater level 7 days earlier",
    "rolling_mean_7d": "7-day rolling mean",
    "rolling_std_7d": "7-day rolling variability",
    "rolling_mean_30d": "30-day rolling mean",
    "trend_7d": "7-day trend",
    "hour": "Hour of day",
    "day_of_year": "Day of year",
    "month": "Month",
    "season": "Season",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "elevation_msl": "Elevation above mean sea level",
}

_CACHE_LIMIT = 256
_CACHE: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()
_CACHE_LOCK = threading.RLock()


class ExplanationUnavailable(RuntimeError):
    """Raised when a model cannot safely be explained."""


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    display_name: str
    value: float | None
    shap_value: float
    rank: int
    direction: str


def _model_feature_names(model: Any) -> list[str]:
    names = list(getattr(model, "feature_names", []) or [])
    estimator = getattr(model, "_model", model)
    expected_count = getattr(estimator, "n_features_in_", None)
    if not names or (expected_count is not None and len(names) != int(expected_count)):
        raise ExplanationUnavailable(
            "Model feature schema is missing or incompatible with the explanation schema"
        )
    return names


def _tree_explainer(model: Any) -> Any:
    try:
        import shap
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise ExplanationUnavailable("SHAP is not installed") from exc
    # Wrappers intentionally keep the fitted estimator private.
    estimator = getattr(model, "_model", model)
    return shap.TreeExplainer(estimator)


def _scalar_expected_value(value: Any) -> float:
    return float(np.asarray(value, dtype=float).reshape(-1)[0])


def explain_model(model_name: str, features: np.ndarray, model_dir: Path | None = None) -> dict[str, Any]:
    """Explain one feature row for ``random_forest`` or ``xgboost``."""
    if model_name == "persistence":
        raise ExplanationUnavailable("Persistence baseline has no tree SHAP explanation")
    if model_name not in {"random_forest", "xgboost"}:
        raise ValueError(f"Unsupported explanation model: {model_name}")
    model = load_ml_model(model_name, model_dir=model_dir)
    names = _model_feature_names(model)
    row = np.asarray(features, dtype=np.float32)
    if row.ndim != 2 or row.shape[0] != 1 or row.shape[1] != len(names):
        raise ExplanationUnavailable("Feature vector does not match the trained model schema")
    if model_name == "random_forest":
        row = np.nan_to_num(row, nan=0.0)
    prediction = float(np.asarray(model.predict(row)).reshape(-1)[0])
    explainer = _tree_explainer(model)
    values = np.asarray(explainer.shap_values(row), dtype=float)
    if values.ndim == 3:
        values = values[0]
    values = values.reshape(1, -1)[0]
    base_value = _scalar_expected_value(explainer.expected_value)
    additivity_error = float(abs(base_value + float(values.sum()) - prediction))
    tolerance = 1e-4 * max(1.0, abs(prediction))
    if additivity_error > tolerance:
        raise ExplanationUnavailable("SHAP additivity validation failed")

    order = sorted(range(len(names)), key=lambda i: (-abs(float(values[i])), i))
    ranks = {index: rank + 1 for rank, index in enumerate(order)}
    contributions = []
    for index, name in enumerate(names):
        value = float(features[0, index]) if np.isfinite(features[0, index]) else None
        contribution = float(values[index])
        direction = "increases" if contribution > tolerance else "decreases" if contribution < -tolerance else "neutral"
        contributions.append(FeatureContribution(
            feature=name,
            display_name=FEATURE_DISPLAY_NAMES.get(name, name.replace("_", " ").title()),
            value=value,
            shap_value=round(contribution, 8),
            rank=ranks[index],
            direction=direction,
        ))
    contributions.sort(key=lambda item: item.rank)
    return {
        "model_name": model_name,
        "prediction": round(prediction, 8),
        "base_value": round(base_value, 8),
        "additivity_error": additivity_error,
        "feature_schema": names,
        "contributions": [item.__dict__ for item in contributions],
    }


def explain_station(
    database: Session,
    station: Station,
    model_name: str = "xgboost",
    model_dir: Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic explanation from the station's latest observations."""
    if model_name == "persistence":
        raise ExplanationUnavailable("Persistence baseline has no tree SHAP explanation")
    observations = list(database.scalars(
        select(Observation)
        .where(Observation.station_id == station.id)
        .order_by(Observation.timestamp.desc())
        .limit(200)
    ).all())
    if not observations:
        raise ExplanationUnavailable("Explanation unavailable because the station has no observations")
    latest = max(observations, key=lambda item: item.timestamp)
    key = (station.id, model_name, latest.timestamp.isoformat(), str(model_dir or MODELS_DIR))
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return deepcopy(cached)
    features = _extract_station_features(station, observations)
    if features is None:
        raise ExplanationUnavailable("Explanation unavailable because features could not be computed")
    result = explain_model(model_name, features, model_dir=model_dir)
    result["station_id"] = station.station_id
    result["observation_timestamp"] = latest.timestamp
    with _CACHE_LOCK:
        _CACHE[key] = deepcopy(result)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_LIMIT:
            _CACHE.popitem(last=False)
    return deepcopy(result)


def clear_explanation_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
