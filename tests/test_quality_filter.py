"""Tests for the data quality filter (apply_quality_filter.py)."""
import csv
import io
import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.apply_quality_filter import filter_file, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND

HEADER = [
    "observation_id", "station_id", "source_station_id", "timestamp",
    "groundwater_level", "unit", "latitude", "longitude", "elevation_msl",
    "state", "district", "tehsil", "block", "village", "agency", "source", "source_file",
]


def make_fixture(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow(row)


def _read_output(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------
# Helpers to build minimal rows
# ------------------------------------------------------------------

def row(station: str, ts: str, gwl: str, state: str = "Telangana") -> list[str]:
    return [
        f"{station}:{ts}", station, station, ts,
        gwl, "meter", "17.0", "78.0", "500",
        state, "District1", "Tehsil1", "Block1", "Village1",
        "NWDP", "NWDP", "raw.csv",
    ]


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_accepts_physically_valid_values(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("A", "2024-01-01T00:00:00", "-15.5"),
        row("A", "2024-01-01T06:00:00", "0.0"),
        row("A", "2024-01-01T12:00:00", "-100.0"),
        row("A", "2024-01-01T18:00:00", "10.0"),
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    rows = _read_output(output)
    assert report["accepted_rows"] == 4
    assert report["rejected_out_of_bounds"] == 0
    assert len(rows) == 4


def test_rejects_sentinel_negative_999(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("A", "2024-01-01T00:00:00", "-999.999"),   # Andhra Pradesh sentinel
        row("A", "2024-01-01T06:00:00", "-15.0"),       # valid
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    rows = _read_output(output)
    assert report["rejected_out_of_bounds"] == 1
    assert report["accepted_rows"] == 1
    assert float(rows[0]["groundwater_level"]) == -15.0


def test_rejects_extreme_positive_encoding_error(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("B", "2024-01-01T00:00:00", "9505536.0"),     # Karnataka max
        row("B", "2024-01-01T06:00:00", "459884.47"),     # Maharashtra max
        row("B", "2024-01-01T12:00:00", "4435987.5"),     # Tamil Nadu max
        row("B", "2024-01-01T18:00:00", "-5.0"),          # valid
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    rows = _read_output(output)
    assert report["rejected_out_of_bounds"] == 3
    assert report["accepted_rows"] == 1


def test_rejects_extreme_negative_encoding_error(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("C", "2024-01-01T00:00:00", "-1561912100.0"),  # Karnataka min
        row("C", "2024-01-01T06:00:00", "-10.0"),           # valid
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    rows = _read_output(output)
    assert report["rejected_out_of_bounds"] == 1
    assert report["accepted_rows"] == 1


def test_accepts_boundary_values_exactly(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("D", "2024-01-01T00:00:00", str(DEFAULT_LOWER_BOUND)),  # exactly -300
        row("D", "2024-01-01T06:00:00", str(DEFAULT_UPPER_BOUND)),  # exactly +50
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    assert report["accepted_rows"] == 2
    assert report["rejected_out_of_bounds"] == 0


def test_rejects_just_outside_bounds(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("E", "2024-01-01T00:00:00", "-300.001"),   # just below lower
        row("E", "2024-01-01T06:00:00", "50.001"),     # just above upper
        row("E", "2024-01-01T12:00:00", "-250.0"),     # valid
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    assert report["rejected_out_of_bounds"] == 2
    assert report["accepted_rows"] == 1


def test_rejection_rate_calculated_correctly(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("F", "2024-01-01T00:00:00", "-10.0"),
        row("F", "2024-01-01T06:00:00", "-999.0"),
        row("F", "2024-01-01T12:00:00", "-20.0"),
        row("F", "2024-01-01T18:00:00", "5000.0"),
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    assert report["total_rows"] == 4
    assert report["accepted_rows"] == 2
    assert report["rejected_out_of_bounds"] == 2
    assert report["rejection_rate_pct"] == 50.0


def test_rejection_samples_captured(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("G", "2024-01-01T00:00:00", "999999.0"),
        row("G", "2024-01-01T06:00:00", "-5.0"),
    ])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    assert len(report["rejection_samples"]) == 1
    assert report["rejection_samples"][0]["groundwater_level"] == 999999.0


def test_output_preserves_all_header_fields(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [row("H", "2024-01-01T00:00:00", "-12.5")])
    filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    rows = _read_output(output)
    assert len(rows) == 1
    for field in HEADER:
        assert field in rows[0], f"Field {field!r} missing from output"


def test_empty_input_produces_empty_output(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [])   # header only, no data rows
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    assert report["total_rows"] == 0
    assert report["accepted_rows"] == 0
    assert report["rejected_out_of_bounds"] == 0


def test_custom_bounds_respected(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [
        row("I", "2024-01-01T00:00:00", "-50.0"),   # valid for default, still valid for tight
        row("I", "2024-01-01T06:00:00", "-150.0"),  # valid for default, invalid for tight [-100, 10]
        row("I", "2024-01-01T12:00:00", "20.0"),    # valid for default, invalid for tight [-100, 10]
    ])
    report = filter_file(fixture, output, lower_bound=-100.0, upper_bound=10.0)
    assert report["accepted_rows"] == 1
    assert report["rejected_out_of_bounds"] == 2


def test_policy_note_present_in_report(tmp_path):
    fixture = tmp_path / "test.normalized.csv"
    output = tmp_path / "test.quality_filtered.csv"
    make_fixture(fixture, [row("J", "2024-01-01T00:00:00", "-10.0")])
    report = filter_file(fixture, output, DEFAULT_LOWER_BOUND, DEFAULT_UPPER_BOUND)
    assert "policy_note" in report
    assert "physical plausibility" in report["policy_note"].lower()
    assert "policy_version" in report
