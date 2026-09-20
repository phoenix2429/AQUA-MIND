import csv
from pathlib import Path

from backend.app.ingestion.normalizer import TelemetryNormalizer, detect_columns, parse_timestamp


HEADER = [
    "Station",
    "Data Acquisition Time",
    "Groundwater Level Telemetry 6 Hourly (meter)",
    "Latitude",
    "Longitude",
    "State",
]


def write_fixture(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerow(["Station A", "01-01-2026 00:00", "-10.5", "17.2", "78.4", "Telangana"])
        writer.writerow(["Station A", "01-01-2026 06:00", "-10.1", "17.2", "78.4", "Telangana"])
        writer.writerow(["Station A", "01-01-2026 06:00", "-10.1", "17.2", "78.4", "Telangana"])
        writer.writerow(["Station B", "not-a-time", "-8.0", "91", "181", "Telangana"])
        writer.writerow(["Station C", "01-01-2026 00:00", "", "17.0", "78.0", "Telangana"])


def test_detects_observed_source_aliases() -> None:
    mapping = detect_columns(HEADER)
    assert mapping["station_id"] == "Station"
    assert mapping["timestamp"] == "Data Acquisition Time"
    assert mapping["groundwater_level"] == "Groundwater Level Telemetry 6 Hourly (meter)"


def test_parses_minute_precision_timestamp() -> None:
    assert parse_timestamp("08-01-2021 03:00").hour == 3
    assert parse_timestamp("08-01-2021 03:00").minute == 0


def test_rejects_non_finite_groundwater_values() -> None:
    from backend.app.ingestion.normalizer import parse_float

    assert parse_float("NaN") is None
    assert parse_float("Infinity") is None


def test_normalizer_emits_valid_unique_observations_and_stats(tmp_path: Path) -> None:
    path = tmp_path / "fixture.csv"
    write_fixture(path)

    iterator, stats = TelemetryNormalizer().iter_file(path)
    observations = list(iterator)

    assert [observation.station_id for observation in observations] == ["Telangana::Station A", "Telangana::Station A"]
    assert observations[0].source_station_id == "Station A"
    assert stats.rows_read == 5
    assert stats.rows_emitted == 2
    assert stats.duplicate_station_timestamp == 1
    assert stats.invalid_timestamp == 1
    assert stats.invalid_groundwater_level == 1
    assert stats.invalid_coordinates == 0
    assert observations[0].groundwater_level == -10.5
    assert observations[0].source == "NWDP"
