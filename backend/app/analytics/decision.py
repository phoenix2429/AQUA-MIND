"""Deterministic, observation-only GSS, GBIM, and DIE analytics.

These indicators are descriptive decision-support outputs.  They are not
official groundwater classifications and do not infer causes from telemetry.
"""

from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from statistics import mean, median, pstdev
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import Observation, Station

ANALYTICS_VERSION = "1.0.0"


@dataclass(frozen=True)
class AnalyticsConfig:
    min_observations: int = 10
    decline_slope_m_per_day: float = 0.05
    volatility_m: float = 1.0
    jump_m: float = 2.0
    recent_days: int = 30
    version: str = ANALYTICS_VERSION

    @classmethod
    def from_environment(cls) -> "AnalyticsConfig":
        def number(name: str, default: float) -> float:
            try:
                value = float(os.getenv(name, default))
                return value if math.isfinite(value) and value > 0 else default
            except (TypeError, ValueError):
                return default

        try:
            minimum = max(1, int(os.getenv("AQUA_ANALYTICS_MIN_OBSERVATIONS", cls.min_observations)))
        except (TypeError, ValueError):
            minimum = cls.min_observations
        try:
            recent_days = max(1, int(os.getenv("AQUA_ANALYTICS_RECENT_DAYS", cls.recent_days)))
        except (TypeError, ValueError):
            recent_days = cls.recent_days
        return cls(
            min_observations=minimum,
            decline_slope_m_per_day=number("AQUA_ANALYTICS_DECLINE_SLOPE_M_PER_DAY", cls.decline_slope_m_per_day),
            volatility_m=number("AQUA_ANALYTICS_VOLATILITY_M", cls.volatility_m),
            jump_m=number("AQUA_ANALYTICS_JUMP_M", cls.jump_m),
            recent_days=recent_days,
            version=os.getenv("AQUA_ANALYTICS_VERSION", ANALYTICS_VERSION) or ANALYTICS_VERSION,
        )


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, value)), 4)


def _observations(values: Iterable[Observation]) -> list[Observation]:
    return sorted(
        (item for item in values if math.isfinite(float(item.groundwater_level)) and item.timestamp is not None),
        key=lambda item: item.timestamp,
    )


def _slope(values: list[Observation]) -> float:
    """Least-squares groundwater-level change in metres per day."""
    if len(values) < 2:
        return 0.0
    origin = values[0].timestamp
    xs = [(item.timestamp - origin).total_seconds() / 86400 for item in values]
    ys = [float(item.groundwater_level) for item in values]
    x_bar, y_bar = mean(xs), mean(ys)
    denominator = sum((x - x_bar) ** 2 for x in xs)
    return 0.0 if denominator == 0 else sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys)) / denominator


def _base(values: list[Observation], config: AnalyticsConfig) -> dict[str, Any]:
    levels = [float(item.groundwater_level) for item in values]
    first, last = values[0], values[-1]
    slope = _slope(values)
    gaps = [(b.timestamp - a.timestamp).total_seconds() / 86400 for a, b in zip(values, values[1:])]
    jumps = [abs(b.groundwater_level - a.groundwater_level) for a, b in zip(values, values[1:])]
    recent_start = last.timestamp - timedelta(days=config.recent_days)
    recent = [item.groundwater_level for item in values if item.timestamp >= recent_start]
    return {
        "observation_count": len(values),
        "first_timestamp": first.timestamp,
        "last_timestamp": last.timestamp,
        "minimum_level": round(min(levels), 6),
        "maximum_level": round(max(levels), 6),
        "mean_level": round(mean(levels), 6),
        "recent_mean_level": round(mean(recent), 6) if recent else None,
        "volatility_m": round(pstdev(levels), 6) if len(levels) > 1 else 0.0,
        "slope_m_per_day": round(slope, 8),
        "maximum_step_m": round(max(jumps, default=0.0), 6),
        "median_gap_days": round(median(gaps), 6) if gaps else None,
        "thresholds": asdict(config),
    }


def calculate_gss(values: Iterable[Observation], config: AnalyticsConfig | None = None) -> dict[str, Any]:
    """Calculate a 0--100 groundwater signal stability score.

    Higher values mean the observed series is more stable under the configured
    thresholds; this must not be interpreted as a causal sustainability claim.
    """
    config = config or AnalyticsConfig.from_environment()
    ordered = _observations(values)
    base = _base(ordered, config) if ordered else {"observation_count": 0}
    if len(ordered) < config.min_observations:
        return {
            "analytics_version": config.version,
            "result_type": "GSS",
            "score": None,
            "profile": "INSUFFICIENT_DATA",
            "sufficient": False,
            "reason": f"At least {config.min_observations} valid observations are required.",
            "components": base,
        }
    trend = float(base["slope_m_per_day"])
    volatility = float(base["volatility_m"])
    jump = float(base["maximum_step_m"])
    trend_component = _clamp(100 - abs(trend) / config.decline_slope_m_per_day * 100)
    volatility_component = _clamp(100 - volatility / config.volatility_m * 100)
    jump_component = _clamp(100 - jump / config.jump_m * 100)
    score = _clamp(0.5 * trend_component + 0.3 * volatility_component + 0.2 * jump_component)
    profile = "STABLE" if score >= 70 else "WATCH" if score >= 40 else "VARIABLE"
    return {
        "analytics_version": config.version,
        "result_type": "GSS",
        "score": score,
        "profile": profile,
        "sufficient": True,
        "data_sufficiency": "GOOD",
        "observation_count": len(ordered),
        "history_days": round((ordered[-1].timestamp - ordered[0].timestamp).total_seconds() / 86400, 3),
        "history_years": round((ordered[-1].timestamp - ordered[0].timestamp).total_seconds() / 86400 / 365.25, 4),
        "reason": "Descriptive score based only on observed level changes and variability.",
        "components": {**base, "trend_component": trend_component, "volatility_component": volatility_component, "jump_component": jump_component},
    }


def calculate_gbim(values: Iterable[Observation], config: AnalyticsConfig | None = None) -> dict[str, Any]:
    """Classify observed groundwater behaviour without attributing causes."""
    config = config or AnalyticsConfig.from_environment()
    ordered = _observations(values)
    base = _base(ordered, config) if ordered else {"observation_count": 0}
    if len(ordered) < config.min_observations:
        return {"analytics_version": config.version, "result_type": "GBIM", "score": None, "profile": "INSUFFICIENT_DATA", "sufficient": False, "reason": f"At least {config.min_observations} valid observations are required.", "components": base}
    slope, volatility = float(base["slope_m_per_day"]), float(base["volatility_m"])
    if abs(slope) <= config.decline_slope_m_per_day and volatility <= config.volatility_m:
        profile = "STABLE"
    elif slope < -config.decline_slope_m_per_day:
        profile = "DECLINING"
    elif slope > config.decline_slope_m_per_day:
        profile = "RISING"
    else:
        profile = "VOLATILE"
    regularity = _clamp(100 - float(base["maximum_step_m"]) / config.jump_m * 100)
    return {"analytics_version": config.version, "result_type": "GBIM", "score": regularity, "profile": profile, "sufficient": True, "data_sufficiency": "GOOD", "observation_count": len(ordered), "history_days": round((ordered[-1].timestamp - ordered[0].timestamp).total_seconds() / 86400, 3), "history_years": round((ordered[-1].timestamp - ordered[0].timestamp).total_seconds() / 86400 / 365.25, 4), "reason": "Descriptive behaviour profile from level trend, variability, and observed step changes; no cause is inferred.", "components": base}


def calculate_die(gss: dict[str, Any], gbim: dict[str, Any], config: AnalyticsConfig | None = None) -> dict[str, Any]:
    """Produce a cautious, indicator-driven decision-support recommendation."""
    config = config or AnalyticsConfig.from_environment()
    slope = gss.get("components", {}).get("slope_m_per_day", 0.0) or 0.0
    volatility = gbim.get("components", {}).get("volatility_m", 0.0) or 0.0
    score_val = gss.get("score")

    if not gss.get("sufficient") or not gbim.get("sufficient"):
        priority, recommendation = "LOW", "Collect more valid groundwater-level observations before interpreting this indicator."
        crop_rec = "Maintain baseline rainfed cropping; record has fewer than the required observations for confident groundwater-crop matching."
        irrig_rec = "Follow local agricultural extension irrigation guidelines while telemetry record is being established."
        gw_cond = "Insufficient historical telemetry to determine trend profile."
    elif gss["score"] < 40 or gbim["profile"] == "DECLINING":
        priority, recommendation = "HIGH", "Review the observed trend and monitoring coverage; this output does not identify a cause or prescribe extraction action."
        score_str = f"{score_val:.1f}" if score_val is not None else "N/A"
        crop_rec = f"Aquifer indicators signal critical depletion (GSS {score_str}/100, trend {slope:+.4f} m/day). Strictly prioritize drought-resilient, low-water crops (millets, pulses, oilseeds); restrict water-intensive cultivation."
        irrig_rec = "Conserve groundwater: mandate drip or sprinkler irrigation, restrict pumping to cooler hours, and check soil moisture before every irrigation cycle."
        gw_cond = f"Critical stress - declining water table (slope: {slope:+.4f} m/day, GSS: {score_str}/100)"
    elif gss["score"] < 70 or gbim["profile"] == "VOLATILE":
        priority, recommendation = "MEDIUM", "Continue monitoring and review the observed variability against local knowledge; no causal explanation is established."
        score_str = f"{score_val:.1f}" if score_val is not None else "N/A"
        crop_rec = f"Seasonal variability is high (volatility {volatility:.2f} m, GSS {score_str}/100). Suited for moderate water-intensity crops (maize, cotton, coarse grains) with staggered sowing; avoid heavy pre-monsoon pumping."
        irrig_rec = "Practice deficit irrigation and alternate furrow watering; use organic mulching to suppress evaporative soil loss during dry spells."
        gw_cond = f"Volatile / seasonal fluctuations (volatility: {volatility:.2f} m, GSS: {score_str}/100)"
    else:
        priority, recommendation = "LOW", "Continue routine monitoring; the observed series is comparatively stable under the configured thresholds."
        score_str = f"{score_val:.1f}" if score_val is not None else "N/A"
        crop_rec = f"Aquifer levels show relative stability (trend {slope:+.4f} m/day, GSS {score_str}/100). Standard seasonal rotational crops (cereals, vegetables, pulses) supported under sustainable withdrawal limits."
        irrig_rec = "Apply standard crop-stage irrigation matching measured soil moisture; avoid unmetered flood irrigation."
        gw_cond = f"Stable aquifer conditions (slope: {slope:+.4f} m/day, GSS: {score_str}/100)"

    indicators = {"gss_score": gss.get("score"), "trend_m_per_day": gss.get("components", {}).get("slope_m_per_day"), "gbim_profile": gbim.get("profile")}
    return {
        "analytics_version": config.version,
        "result_type": "DIE",
        "score": gss.get("score"),
        "priority": priority,
        "profile": priority,
        "sufficient": gss.get("sufficient", False) and gbim.get("sufficient", False),
        "recommendation": recommendation,
        "action": recommendation,
        "reason": "Decision-support priority derived only from GSS and GBIM outputs.",
        "crop_recommendation": crop_rec,
        "irrigation_recommendation": irrig_rec,
        "groundwater_condition": gw_cond,
        "source_indicators": indicators,
        "components": {"gss": gss, "gbim": gbim, "thresholds": asdict(config)},
    }


def station_analytics(database: Session, station: Station, config: AnalyticsConfig | None = None) -> dict[str, Any]:
    config = config or AnalyticsConfig.from_environment()
    values = database.scalars(select(Observation).where(Observation.station_id == station.id).order_by(Observation.timestamp)).all()
    gss = calculate_gss(values, config)
    gbim = calculate_gbim(values, config)
    return {"station_id": station.station_id, "station_info": {"station_name": station.station_name, "state": station.state, "district": station.district, "latitude": station.latitude, "longitude": station.longitude, "elevation_msl": station.elevation_msl}, "analytics_version": config.version, "gss": gss, "gbim": gbim, "die": calculate_die(gss, gbim, config)}
