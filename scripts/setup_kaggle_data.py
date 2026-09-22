"""Download and validate the AQUA-MIND raw and processed Kaggle dataset.

The script deliberately does not run any processing pipeline.  It only copies
the published raw/processed artifacts into the repository's existing layout.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

DATASET = "pindiavinash/aqua-mind"
STATES = ("Andhra_Pradesh", "Karnataka", "Maharashtra", "Tamil_Nadu", "Telangana")
PERIODS = ("2021_2025", "2026_2030")
RAW_COLUMNS = {
    "SlNo", "Station", "Agency", "State", "Latitude", "Longitude",
    "Data Acquisition Time", "Groundwater Level Telemetry 6 Hourly (meter)",
}
NORMALIZED_COLUMNS = {"station_id", "timestamp", "groundwater_level", "latitude", "longitude", "state"}


def _csv_header(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {column.strip() for column in next(csv.reader(handle))}


def validate_data_root(data_dir: Path) -> list[str]:
    """Return explicit validation errors for an AQUA-MIND data directory."""
    errors: list[str] = []
    raw = data_dir / "raw"
    processed = data_dir / "processed"
    if not raw.is_dir():
        errors.append(f"missing directory: {raw}")
    if not processed.is_dir():
        errors.append(f"missing directory: {processed}")

    for state in STATES:
        for period in PERIODS:
            raw_file = raw / state / f"telemetry_{period}.csv"
            if not raw_file.is_file():
                errors.append(f"missing raw file: {raw_file}")
            else:
                try:
                    missing = RAW_COLUMNS - _csv_header(raw_file)
                    if missing:
                        errors.append(f"{raw_file}: missing columns {sorted(missing)}")
                except (OSError, StopIteration, UnicodeError, csv.Error) as exc:
                    errors.append(f"{raw_file}: cannot read CSV header ({exc})")

    normalized_dir = processed / "all_states"
    quality_dir = processed / "quality_filtered"
    for state in STATES:
        state_token = state.lower()
        for period in PERIODS:
            source_kind = "sw_gw" if state == "Tamil_Nadu" else "gw"
            stem = f"gwl_tel_6_hourly_{state_token}_{source_kind}_"
            # State abbreviations are part of the established filenames.
            code = {"Andhra_Pradesh": "ap", "Karnataka": "ka", "Maharashtra": "mh",
                    "Tamil_Nadu": "tn", "Telangana": "ts"}[state]
            stem += f"{code}_{period}"
            normalized = normalized_dir / f"{stem}.normalized.csv"
            stats = normalized_dir / f"{stem}.stats.json"
            quality = quality_dir / f"{stem}.quality_filtered.csv"
            report = quality_dir / f"{stem}.quality_report.json"
            for path in (normalized, stats, quality, report):
                if not path.is_file():
                    errors.append(f"missing processed file: {path}")
            for csv_path in (normalized, quality):
                if csv_path.is_file():
                    try:
                        missing = NORMALIZED_COLUMNS - _csv_header(csv_path)
                        if missing:
                            errors.append(f"{csv_path}: missing columns {sorted(missing)}")
                    except (OSError, StopIteration, UnicodeError, csv.Error) as exc:
                        errors.append(f"{csv_path}: cannot read CSV header ({exc})")
            if stats.is_file():
                _validate_json(stats, {"state", "resource_period", "accepted_records"}, errors)
            if report.is_file():
                _validate_json(report, {"total_rows", "accepted_rows", "lower_bound", "upper_bound"}, errors)

    for name in ("five_state_audit.json", "quality_filter_summary.json"):
        path = normalized_dir / name if name == "five_state_audit.json" else quality_dir / name
        if not path.is_file():
            errors.append(f"missing processed metadata: {path}")
        else:
            try:
                with path.open(encoding="utf-8") as handle:
                    value = json.load(handle)
                if not isinstance(value, dict):
                    errors.append(f"{path}: metadata must be a JSON object")
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"{path}: invalid JSON ({exc})")
    return errors


def _validate_json(path: Path, required: set[str], errors: list[str]) -> None:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            errors.append(f"{path}: metadata must be a JSON object")
        else:
            missing = required - value.keys()
            if missing:
                errors.append(f"{path}: missing metadata keys {sorted(missing)}")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON ({exc})")


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as zipped:
        root = destination.resolve()
        for member in zipped.infolist():
            candidate = (destination / PurePosixPath(member.filename)).resolve()
            if candidate != root and root not in candidate.parents:
                raise ValueError(f"unsafe archive member: {member.filename}")
        zipped.extractall(destination)


def _locate_data_root(staging: Path) -> Path:
    candidates = [staging] + [p for p in staging.rglob("*") if p.is_dir()]
    for candidate in candidates:
        if (candidate / "raw").is_dir() and (candidate / "processed").is_dir():
            return candidate
    raise ValueError("Kaggle archive does not contain both raw/ and processed/ directories")


def copy_dataset(source_data: Path, target_data: Path) -> None:
    """Copy only raw/processed trees, preserving the repository layout."""
    for name in ("raw", "processed"):
        source = source_data / name
        if not source.is_dir():
            raise ValueError(f"archive is missing {name}/")
        shutil.copytree(source, target_data / name, dirs_exist_ok=True)


def download_archive(dataset: str, destination: Path) -> Path:
    archive = destination / "dataset.zip"
    command = ["kaggle", "datasets", "download", "-d", dataset, "-p", str(destination), "-q"]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("Kaggle CLI is not installed; install kaggle and configure authentication") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Kaggle download failed for {dataset}: {detail}") from exc
    if not archive.is_file():
        archives = list(destination.glob("*.zip"))
        if len(archives) == 1:
            archive = archives[0]
        else:
            raise RuntimeError("Kaggle CLI completed but no dataset ZIP was produced")
    return archive


def setup(target_dir: Path, *, dry_run: bool = False, dataset: str = DATASET) -> int:
    target_data = target_dir / "data"
    existing_errors = validate_data_root(target_data)
    if not existing_errors:
        print(f"Dataset already complete: {target_data}")
        return 0
    print(f"Dataset is incomplete ({len(existing_errors)} validation errors).")
    if dry_run:
        print("Dry run: no download or file changes performed.")
        for error in existing_errors:
            print(f"  - {error}")
        return 1
    try:
        with tempfile.TemporaryDirectory(prefix="aqua-mind-kaggle-", dir=target_dir) as temporary:
            archive = download_archive(dataset, Path(temporary))
            staging = Path(temporary) / "extracted"
            staging.mkdir()
            _safe_extract(archive, staging)
            copy_dataset(_locate_data_root(staging), target_data)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    errors = validate_data_root(target_data)
    if errors:
        print("ERROR: downloaded dataset failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 3
    print(f"Dataset installed and validated: {target_data}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dir", type=Path, default=Path.cwd(),
                        help="directory containing data/ (default: current directory)")
    parser.add_argument("--dataset", default=DATASET, help="Kaggle dataset identifier")
    parser.add_argument("--dry-run", action="store_true",
                        help="report missing files without downloading or changing files")
    args = parser.parse_args()
    return setup(args.target_dir.resolve(), dry_run=args.dry_run, dataset=args.dataset)


if __name__ == "__main__":
    raise SystemExit(main())
