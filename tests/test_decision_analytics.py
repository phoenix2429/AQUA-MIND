from datetime import datetime, timedelta

from backend.app.analytics.decision import AnalyticsConfig, calculate_gbim, calculate_gss
from backend.app.database.models import Observation


def observations(levels: list[float]) -> list[Observation]:
    start = datetime(2026, 1, 1)
    return [Observation(timestamp=start + timedelta(days=index), groundwater_level=value) for index, value in enumerate(levels)]


def test_gss_is_deterministic_and_versioned() -> None:
    config = AnalyticsConfig(min_observations=3)
    values = observations([-10.0, -10.01, -10.0, -10.02])
    first = calculate_gss(values, config)
    assert first == calculate_gss(values, config)
    assert first["sufficient"] is True
    assert first["analytics_version"] == "1.0.0"
    assert 0 <= first["score"] <= 100


def test_insufficient_data_does_not_fabricate_score() -> None:
    result = calculate_gbim(observations([-10.0, -11.0]), AnalyticsConfig(min_observations=3))
    assert result["sufficient"] is False
    assert result["score"] is None
    assert result["profile"] == "INSUFFICIENT_DATA"
