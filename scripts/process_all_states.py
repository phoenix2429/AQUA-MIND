"""Discover, normalize, and registry-build the five-state telemetry MVP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ingestion.normalizer import CANONICAL_FIELDS, TelemetryNormalizer
from scripts.build_station_registry import build_registry

STATES = ("Telangana", "Andhra Pradesh", "Karnataka", "Tamil Nadu", "Maharashtra")
NORMALIZER_VERSION = "6-mmap-write-fix"
# 64 MB write buffer — mirrors the read-side fix; bypasses Windows EINVAL
# (OSError 22) that fires when WriteFile() crosses certain offsets on files
# larger than ~300 MB in text mode.
_WRITE_BUFFER = 64 << 20
STATE_TOKENS = {
    "telangana": "Telangana",
    "andhra pradesh": "Andhra Pradesh",
    "andhra_pradesh": "Andhra Pradesh",
    "karnataka": "Karnataka",
    "tamil nadu": "Tamil Nadu",
    "tamil_nadu": "Tamil Nadu",
    "maharashtra": "Maharashtra",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def infer_state(path: Path, columns: list[str]) -> str | None:
    normalized_columns = {re.sub(r"[^a-z]+", " ", column.casefold()).strip() for column in columns}
    if "state" in normalized_columns:
        # The normalized row value remains authoritative; this is only a fallback for missing source state values.
        pass
    haystack = f"{path.as_posix().casefold()}"
    for token, state in sorted(STATE_TOKENS.items(), key=lambda item: len(item[0]), reverse=True):
        if token in haystack:
            return state
    return None


def normalize_source(path: Path, output_dir: Path) -> tuple[dict[str, object], Path | None]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
        columns = next(csv.reader(source), [])
    state = infer_state(path, columns)
    stem_name = path.stem
    if state and state.lower().replace(" ", "_") not in stem_name.lower():
        stem_name = f"{state.lower().replace(' ', '_')}_{stem_name}"
    output_path = output_dir / f"{stem_name}.normalized.csv"
    stats_path = output_dir / f"{stem_name}.stats.json"
    normalizer = TelemetryNormalizer()
    iterator, stats = normalizer.iter_file(path, state_override=state)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Open output in binary mode + TextIOWrapper with a 64 MB write buffer.
    # Python's text-mode WriteFile() path on Windows raises OSError 22 (EINVAL)
    # when the internal file-position counter overflows for files > ~300 MB.
    # Binary mode bypasses that code path entirely.
    _raw_out = open(str(output_path), "wb", buffering=_WRITE_BUFFER)  # noqa: WPS515
    destination = io.TextIOWrapper(_raw_out, encoding="utf-8", newline="")
    try:
        writer = csv.DictWriter(destination, fieldnames=CANONICAL_FIELDS)
        writer.writeheader()
        for observation in iterator:
            writer.writerow(observation.as_dict())
    finally:
        destination.flush()
        destination.close()
    result = {
        "state": state,
        "source_file": str(path),
        "source_sha256": sha256(path),
        "resource_period": "2021_2025" if "2021_2025" in path.name else "2026_2030" if "2026_2030" in path.name else None,
        "processed_file": str(output_path),
        "rows_read": stats.rows_read,
        "rows_emitted": stats.rows_emitted,
        "duplicate_records": stats.duplicate_station_timestamp,
        "invalid_timestamps": stats.invalid_timestamp,
        "invalid_groundwater_values": stats.invalid_groundwater_level,
        "invalid_coordinates": stats.invalid_coordinates,
        "missing_required_columns": stats.missing_required_columns,
        "normalized_columns": stats.detected_columns,
        "accepted_records": stats.rows_emitted,
        "rejected_records": stats.rows_read - stats.rows_emitted,
        "state_counts": dict(stats.state_counts),
        "normalizer_version": NORMALIZER_VERSION,
    }
    stats_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result, output_path


def load_completed_report(path: Path, output_dir: Path) -> tuple[dict[str, object], Path] | None:
    state = infer_state(path, [])
    stem_name = path.stem
    if state and state.lower().replace(" ", "_") not in stem_name.lower():
        stem_name = f"{state.lower().replace(' ', '_')}_{stem_name}"
    stats_path = output_dir / f"{stem_name}.stats.json"
    output_path = output_dir / f"{stem_name}.normalized.csv"
    if not stats_path.is_file() or not output_path.is_file():
        return None
    try:
        report = json.loads(stats_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if report.get("source_sha256") != sha256(path) or report.get("normalizer_version") != NORMALIZER_VERSION:
        return None
    return report, output_path


def discover_csvs(data_root: Path) -> list[Path]:
    processed_root = (data_root / "processed").resolve()
    raw_root = data_root / "raw"
    if raw_root.is_dir():
        raw_csvs = sorted(path for path in raw_root.rglob("*.csv") if processed_root not in path.resolve().parents)
        if raw_csvs:
            return raw_csvs
    return sorted(path for path in data_root.rglob("*.csv") if processed_root not in path.resolve().parents)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/all_states"))
    args = parser.parse_args()
    seen_hashes: dict[str, Path] = {}
    reports: list[dict[str, object]] = []
    normalized_files: list[Path] = []
    for path in discover_csvs(args.data_root):
        digest = sha256(path)
        if digest in seen_hashes:
            reports.append({"source_file": str(path), "skipped_duplicate_of": str(seen_hashes[digest]), "source_sha256": digest})
            continue
        seen_hashes[digest] = path
        completed = load_completed_report(path, args.output_dir)
        if completed is None:
            report, output_path = normalize_source(path, args.output_dir)
        else:
            report, output_path = completed
            report["resumed_from_checkpoint"] = True
        reports.append(report)
        if output_path:
            normalized_files.append(output_path)

    registry_path = args.output_dir / "stations_all_states.csv"
    registry_inputs = args.output_dir / "all_observations.normalized.csv"
    _raw_combined = open(str(registry_inputs), "wb", buffering=_WRITE_BUFFER)  # noqa: WPS515
    combined = io.TextIOWrapper(_raw_combined, encoding="utf-8", newline="")
    try:
        writer = None
        for path in normalized_files:
            _raw_src = open(str(path), "rb", buffering=_WRITE_BUFFER)  # noqa: WPS515
            source = io.TextIOWrapper(_raw_src, encoding="utf-8", newline="")
            try:
                reader = csv.DictReader(source)
                if writer is None:
                    writer = csv.DictWriter(combined, fieldnames=reader.fieldnames or CANONICAL_FIELDS)
                    writer.writeheader()
                for row in reader:
                    writer.writerow(row)
            finally:
                source.close()
    finally:
        combined.flush()
        combined.close()
    registry = build_registry(registry_inputs, registry_path)
    audit = {"states": list(STATES), "discovered_files": len(discover_csvs(args.data_root)), "unique_sources_processed": len(normalized_files), "reports": reports, "registry": registry}
    audit_path = args.output_dir / "five_state_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
