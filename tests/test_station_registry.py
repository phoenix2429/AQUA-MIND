import csv
from pathlib import Path

from scripts.build_station_registry import build_registry


FIELDS = [
    "observation_id",
    "station_id",
    "timestamp",
    "groundwater_level",
    "unit",
    "latitude",
    "longitude",
    "elevation_msl",
    "state",
    "district",
    "tehsil",
    "block",
    "village",
    "agency",
    "source",
    "source_file",
]


def test_registry_uses_latest_timestamp_not_input_order(tmp_path: Path) -> None:
    input_path = tmp_path / "observations.csv"
    output_path = tmp_path / "stations.csv"
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        base = {
            "observation_id": "x",
            "station_id": "A",
            "groundwater_level": "-1",
            "unit": "meter",
            "latitude": "17",
            "longitude": "78",
            "elevation_msl": "",
            "state": "Telangana",
            "district": "Demo",
            "tehsil": "",
            "block": "",
            "village": "",
            "agency": "Demo GW",
            "source": "NWDP",
            "source_file": "raw.csv",
        }
        writer.writerow({**base, "timestamp": "2026-01-02T00:00:00"})
        writer.writerow({**base, "timestamp": "2026-01-01T00:00:00"})

    result = build_registry(input_path, output_path)

    assert result["station_count"] == 1
    with output_path.open(encoding="utf-8", newline="") as handle:
        station = next(csv.DictReader(handle))
    assert station["latest_observation_timestamp"] == "2026-01-02T00:00:00"
    assert station["observation_count"] == "2"
