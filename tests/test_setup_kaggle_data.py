import json
import zipfile
from pathlib import Path

from scripts import setup_kaggle_data as setup


def _make_dataset(root: Path) -> None:
    raw_header = "SlNo,Station,Agency,State,Latitude,Longitude,Data Acquisition Time,Groundwater Level Telemetry 6 Hourly (meter)\n"
    normalized_header = "station_id,timestamp,groundwater_level,latitude,longitude,state\n"
    for state in setup.STATES:
        code = {"Andhra_Pradesh": "ap", "Karnataka": "ka", "Maharashtra": "mh",
                "Tamil_Nadu": "tn", "Telangana": "ts"}[state]
        for period in setup.PERIODS:
            (root / "raw" / state).mkdir(parents=True, exist_ok=True)
            (root / "raw" / state / f"telemetry_{period}.csv").write_text(
                raw_header + f"1,S1,Agency,{state},1,2,2025-01-01,-1\n", encoding="utf-8"
            )
            source_kind = "sw_gw" if state == "Tamil_Nadu" else "gw"
            stem = f"gwl_tel_6_hourly_{state.lower()}_{source_kind}_{code}_{period}"
            all_states = root / "processed" / "all_states"
            quality = root / "processed" / "quality_filtered"
            all_states.mkdir(parents=True, exist_ok=True)
            quality.mkdir(parents=True, exist_ok=True)
            (all_states / f"{stem}.normalized.csv").write_text(
                normalized_header + f"{state}::S1,2025-01-01,-1,1,2,{state}\n", encoding="utf-8"
            )
            (quality / f"{stem}.quality_filtered.csv").write_text(
                normalized_header + f"{state}::S1,2025-01-01,-1,1,2,{state}\n", encoding="utf-8"
            )
            (all_states / f"{stem}.stats.json").write_text(
                json.dumps({"state": state, "resource_period": period, "accepted_records": 1}),
                encoding="utf-8",
            )
            (quality / f"{stem}.quality_report.json").write_text(
                json.dumps({"total_rows": 1, "accepted_rows": 1, "lower_bound": -300, "upper_bound": 50}),
                encoding="utf-8",
            )
    (root / "processed" / "all_states" / "five_state_audit.json").write_text("{}", encoding="utf-8")
    (root / "processed" / "quality_filtered" / "quality_filter_summary.json").write_text("{}", encoding="utf-8")


def test_validate_fixture_and_setup_skips_download(tmp_path, monkeypatch):
    _make_dataset(tmp_path / "data")
    assert setup.validate_data_root(tmp_path / "data") == []

    def fail_download(*args, **kwargs):
        raise AssertionError("complete data must not download")

    monkeypatch.setattr(setup, "download_archive", fail_download)
    assert setup.setup(tmp_path) == 0


def test_setup_extracts_mocked_archive_and_validates(tmp_path, monkeypatch):
    source = tmp_path / "source-data"
    _make_dataset(source)
    archive = tmp_path / "mock.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        for path in source.rglob("*"):
            if path.is_file():
                zipped.write(path, Path("published") / path.relative_to(source))

    def mocked_download(dataset, destination):
        target = destination / "download.zip"
        target.write_bytes(archive.read_bytes())
        return target

    monkeypatch.setattr(setup, "download_archive", mocked_download)
    target = tmp_path / "checkout"
    target.mkdir()
    assert setup.setup(target) == 0
    assert setup.validate_data_root(target / "data") == []


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../outside.txt", "no")
    try:
        setup._safe_extract(archive, tmp_path / "extract")
    except ValueError as exc:
        assert "unsafe archive member" in str(exc)
    else:
        raise AssertionError("unsafe archive member was accepted")
