import csv
from pathlib import Path

from scripts.process_all_states import discover_csvs, normalize_source


def test_discovery_excludes_processed_outputs(tmp_path: Path) -> None:
    (tmp_path / "source.csv").write_text("Station,Data Acquisition Time,Groundwater Level Telemetry 6 Hourly (meter),State\nA,01-01-2026 00:00,-1,Telangana\n", encoding="utf-8")
    (tmp_path / "processed").mkdir()
    (tmp_path / "processed" / "generated.csv").write_text("not a source", encoding="utf-8")
    assert discover_csvs(tmp_path) == [tmp_path / "source.csv"]


def test_normalize_source_qualifies_station_by_state(tmp_path: Path) -> None:
    source = tmp_path / "gwl_tel_6_hourly_karnataka_gw_ka_2026_2030.csv"
    source.write_text(
        "Station,Data Acquisition Time,Groundwater Level Telemetry 6 Hourly (meter),State\n"
        "A,01-01-2026 00:00,-1,Karnataka\n",
        encoding="utf-8",
    )
    report, output = normalize_source(source, tmp_path / "processed")
    assert report["state"] == "Karnataka"
    with output.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["station_id"] == "Karnataka::A"
    assert row["source_station_id"] == "A"