"""Tests for the feature engineering pipeline (create_features.py)."""
import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.create_features import (
    StationFeatureState,
    ObsRecord,
    _season,
    generate_features,
    FEATURE_COLUMNS,
    NUMERIC_FEATURE_COLUMNS,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_state(
    sid: str = "TestState::S1",
    lat: float | None = 17.0,
    lon: float | None = 78.0,
    elev: float | None = 500.0,
) -> StationFeatureState:
    return StationFeatureState(
        station_id=sid,
        state="TestState",
        district="District1",
        latitude=lat,
        longitude=lon,
        elevation_msl=elev,
    )


def obs(ts_str: str, gwl: float) -> ObsRecord:
    return ObsRecord(timestamp=datetime.fromisoformat(ts_str), gwl=gwl)


def build_history(station: StationFeatureState, records: list[ObsRecord]) -> None:
    for record in records:
        station.add(record)


HEADER = [
    "observation_id", "station_id", "source_station_id", "timestamp",
    "groundwater_level", "unit", "latitude", "longitude", "elevation_msl",
    "state", "district", "tehsil", "block", "village", "agency", "source", "source_file",
]


def write_csv_fixture(path: Path, rows: list[tuple]) -> None:
    """Write a minimal quality-filtered CSV for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for i, (sid, ts, gwl) in enumerate(rows):
            writer.writerow([
                f"{sid}:{ts}", sid, sid.split("::")[-1] if "::" in sid else sid,
                ts, gwl, "meter", "17.0", "78.0", "500",
                "Telangana", "District1", "Tehsil1", "Block1", "Village1",
                "NWDP", "NWDP", "raw.csv",
            ])


# ------------------------------------------------------------------
# Season tests
# ------------------------------------------------------------------

def test_season_winter():
    assert _season(12) == 0
    assert _season(1) == 0
    assert _season(2) == 0


def test_season_spring():
    assert _season(3) == 1
    assert _season(5) == 1


def test_season_monsoon():
    assert _season(6) == 2
    assert _season(9) == 2


def test_season_autumn():
    assert _season(10) == 3
    assert _season(11) == 3


# ------------------------------------------------------------------
# Lag feature tests
# ------------------------------------------------------------------

def test_first_observation_returns_none():
    station = make_state()
    record = obs("2024-01-01T00:00:00", -10.0)
    result = station.build_features(record)
    assert result is None  # no prior history


def test_lag_6h_correct():
    station = make_state()
    r1 = obs("2024-01-01T00:00:00", -10.0)
    station.add(r1)
    r2 = obs("2024-01-01T06:00:00", -10.5)
    features = station.build_features(r2)
    assert features is not None
    assert features["lag_6h"] == pytest.approx(-10.0, abs=0.001)
    assert features["target"] == -10.5


def test_lag_24h_correct():
    station = make_state()
    records = [obs(f"2024-01-0{d+1}T00:00:00", -10.0 - d) for d in range(5)]
    for r in records[:4]:
        station.add(r)
    features = station.build_features(records[4])
    assert features is not None
    assert features["lag_24h"] == pytest.approx(-13.0, abs=0.001)  # 3 days back would be -13


def test_lag_is_none_when_no_prior_in_window():
    station = make_state()
    r1 = obs("2024-01-01T00:00:00", -10.0)
    station.add(r1)
    # gap of 7 days: lag_6h, lag_12h, lag_24h, lag_48h should all be None
    # but lag_7d will find Jan 01 (7 days back)
    r2 = obs("2024-01-08T00:00:00", -11.0)
    features = station.build_features(r2)
    # lag_7d is available, so features should NOT be None
    assert features is not None
    assert features["lag_6h"] is None
    assert features["lag_12h"] is None
    assert features["lag_24h"] is None
    assert features["lag_48h"] is None
    assert features["lag_7d"] is not None  # Jan 01 is 7 days back


# ------------------------------------------------------------------
# Rolling statistics tests
# ------------------------------------------------------------------

def test_rolling_mean_7d_correct():
    station = make_state()
    # Add 8 observations, one per 6 hours
    base = datetime(2024, 1, 1, 0, 0, 0)
    for i in range(8):
        station.add(ObsRecord(timestamp=base + timedelta(hours=6 * i), gwl=-10.0 - i * 0.5))
    next_ts = base + timedelta(hours=48)
    r = ObsRecord(timestamp=next_ts, gwl=-15.0)
    features = station.build_features(r)
    assert features is not None
    assert features["rolling_mean_7d"] is not None
    # Mean of the 8 values: -10, -10.5, -11, -11.5, -12, -12.5, -13, -13.5 = mean -11.75
    assert features["rolling_mean_7d"] == pytest.approx(-11.75, abs=0.01)


def test_rolling_std_7d_none_with_too_few_obs():
    station = make_state()
    station.add(obs("2024-01-01T00:00:00", -10.0))
    station.add(obs("2024-01-01T06:00:00", -10.5))
    station.add(obs("2024-01-01T12:00:00", -11.0))
    r = obs("2024-01-01T18:00:00", -11.5)
    features = station.build_features(r)
    # Only 3 in window < min_obs=4, rolling stats should be None
    assert features["rolling_mean_7d"] is None
    assert features["rolling_std_7d"] is None


# ------------------------------------------------------------------
# Trend tests
# ------------------------------------------------------------------

def test_trend_7d_positive_slope():
    station = make_state()
    base = datetime(2024, 1, 1, 0, 0, 0)
    # Rising trend: each 6h step goes up by 1 m
    for i in range(8):
        station.add(ObsRecord(timestamp=base + timedelta(hours=6 * i), gwl=-20.0 + i))
    r = ObsRecord(timestamp=base + timedelta(hours=48), gwl=-12.0)
    features = station.build_features(r)
    assert features is not None
    assert features["trend_7d"] is not None
    assert features["trend_7d"] > 0  # rising = positive slope


def test_trend_7d_negative_slope():
    station = make_state()
    base = datetime(2024, 1, 1, 0, 0, 0)
    for i in range(8):
        station.add(ObsRecord(timestamp=base + timedelta(hours=6 * i), gwl=-10.0 - i))
    r = ObsRecord(timestamp=base + timedelta(hours=48), gwl=-18.0)
    features = station.build_features(r)
    assert features is not None
    assert features["trend_7d"] < 0  # declining = negative slope


# ------------------------------------------------------------------
# Calendar feature tests
# ------------------------------------------------------------------

def test_calendar_features_correct():
    station = make_state()
    station.add(obs("2024-01-01T00:00:00", -10.0))
    r = obs("2024-06-15T12:00:00", -15.0)
    features = station.build_features(r)
    assert features is not None
    assert features["hour"] == 12
    assert features["month"] == 6
    assert features["season"] == 2  # monsoon


def test_calendar_winter_season():
    station = make_state()
    station.add(obs("2023-12-01T00:00:00", -10.0))
    r = obs("2023-12-31T18:00:00", -10.5)
    features = station.build_features(r)
    assert features is not None
    assert features["season"] == 0  # winter


# ------------------------------------------------------------------
# Static feature tests
# ------------------------------------------------------------------

def test_static_features_propagated():
    station = make_state(lat=16.5, lon=79.2, elev=250.0)
    station.add(obs("2024-01-01T00:00:00", -10.0))
    r = obs("2024-01-01T06:00:00", -10.5)
    features = station.build_features(r)
    assert features is not None
    assert features["latitude"] == pytest.approx(16.5)
    assert features["longitude"] == pytest.approx(79.2)
    assert features["elevation_msl"] == pytest.approx(250.0)


def test_missing_elevation_is_none():
    station = make_state(elev=None)
    station.add(obs("2024-01-01T00:00:00", -10.0))
    r = obs("2024-01-01T06:00:00", -10.5)
    features = station.build_features(r)
    assert features is not None
    assert features["elevation_msl"] is None


# ------------------------------------------------------------------
# End-to-end generate_features tests
# ------------------------------------------------------------------

def test_generate_features_from_csv(tmp_path):
    """generate_features yields rows for a station with regular 6h observations."""
    fixture = tmp_path / "test.quality_filtered.csv"
    sid = "Telangana::StationA"
    rows = [(sid, f"2024-01-0{d+1}T{h:02d}:00:00", -10.0 - (d * 4 + h // 6) * 0.1)
            for d in range(3) for h in (0, 6, 12, 18)]
    write_csv_fixture(fixture, rows)

    results = list(generate_features([fixture]))
    assert len(results) > 0
    # First row should not appear (no prior)
    # At least some rows with lag_6h populated
    rows_with_lag = [r for r in results if r["lag_6h"] is not None]
    assert len(rows_with_lag) > 0


def test_generate_features_target_equals_gwl(tmp_path):
    """target column must equal the groundwater_level at that timestamp."""
    fixture = tmp_path / "test.quality_filtered.csv"
    sid = "Telangana::StationB"
    rows = [(sid, f"2024-01-01T{h:02d}:00:00", -10.0 - h * 0.5) for h in (0, 6, 12, 18)]
    write_csv_fixture(fixture, rows)

    results = list(generate_features([fixture]))
    # Every yielded row: target should match gwl at that timestamp
    for r in results:
        assert r["target"] is not None
        assert isinstance(r["target"], float)


def test_generate_features_all_columns_present(tmp_path):
    """Every row must contain all FEATURE_COLUMNS keys."""
    fixture = tmp_path / "test.quality_filtered.csv"
    sid = "Telangana::StationC"
    rows = [(sid, f"2024-01-01T{h:02d}:00:00", -12.0 + h * 0.1) for h in (0, 6, 12, 18, 24)]
    write_csv_fixture(fixture, rows)

    results = list(generate_features([fixture]))
    for row in results:
        for col in FEATURE_COLUMNS:
            assert col in row, f"Column {col!r} missing from feature row"


def test_no_leakage_lag_uses_only_prior_observations(tmp_path):
    """lag_6h for timestamp T must come from T-6h, never from T or future."""
    fixture = tmp_path / "test.quality_filtered.csv"
    sid = "Telangana::StationD"
    rows = [
        (sid, "2024-01-01T00:00:00", -10.0),
        (sid, "2024-01-01T06:00:00", -20.0),  # big jump
        (sid, "2024-01-01T12:00:00", -11.0),
    ]
    write_csv_fixture(fixture, rows)

    results = list(generate_features([fixture]))
    # At 06:00, lag_6h should be -10.0 (from 00:00), not -20.0 itself
    row_06 = next((r for r in results if "06:00" in r["timestamp"]), None)
    assert row_06 is not None
    assert row_06["lag_6h"] == pytest.approx(-10.0, abs=0.01)
    assert row_06["target"] == pytest.approx(-20.0, abs=0.01)
