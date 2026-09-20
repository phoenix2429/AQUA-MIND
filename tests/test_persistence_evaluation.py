from datetime import datetime, timedelta
from pathlib import Path

from scripts.evaluate_persistence import MetricAccumulator, StationWindow, evaluate


def test_station_window_uses_chronological_splits() -> None:
    window = StationWindow("Telangana", datetime(2026, 1, 1), datetime(2026, 1, 11), 11)
    assert window.split(datetime(2026, 1, 7)) == "train"
    assert window.split(datetime(2026, 1, 9)) == "validation"
    assert window.split(datetime(2026, 1, 10)) == "test"


def test_metric_accumulator_calculates_metrics() -> None:
    metrics = MetricAccumulator()
    metrics.add(2, 1)
    metrics.add(4, 3)
    result = metrics.as_dict()
    assert result["count"] == 2
    assert result["mae"] == 1
    assert result["rmse"] == 1
    assert result["r2"] == 0


def test_evaluation_uses_previous_observation(tmp_path: Path) -> None:
    path = tmp_path / "Telangana.normalized.csv"
    path.write_text(
        "observation_id,station_id,source_station_id,timestamp,groundwater_level,unit,latitude,longitude,elevation_msl,state,district,tehsil,block,village,agency,source,source_file\n"
        "1,Telangana::A,A,2026-01-01T00:00:00,-10,meter,,,,Telangana,,,,,,NWDP,raw.csv\n"
        "2,Telangana::A,A,2026-01-02T00:00:00,-9,meter,,,,Telangana,,,,,,NWDP,raw.csv\n"
        "3,Telangana::A,A,2026-01-03T00:00:00,-7,meter,,,,Telangana,,,,,,NWDP,raw.csv\n",
        encoding="utf-8",
    )
    result = evaluate([path])
    assert sum(split["count"] for split in result["metrics"].values()) == 2
    assert result["metrics"]["test"]["mae"] == 2
