"""Investigate extreme groundwater values to inform quality policy."""
import csv
import io
import sys
import json
import collections
from pathlib import Path

_BUF = 64 << 20
THRESHOLD = 200.0
ROOT = Path(__file__).resolve().parent.parent

def investigate(state_files, threshold=THRESHOLD, max_samples=5):
    extremes = collections.defaultdict(list)  # station_id -> sample rows
    station_ranges = collections.defaultdict(lambda: {"min": None, "max": None, "count": 0, "extreme_count": 0, "state": "", "district": ""})

    for fpath in state_files:
        raw = open(str(fpath), "rb", buffering=_BUF)
        with io.TextIOWrapper(raw, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    v = float(row["groundwater_level"])
                except (ValueError, KeyError):
                    continue
                sid = row["station_id"]
                sr = station_ranges[sid]
                sr["count"] += 1
                sr["state"] = row.get("state", "")
                sr["district"] = row.get("district", "")
                if sr["min"] is None or v < sr["min"]:
                    sr["min"] = v
                if sr["max"] is None or v > sr["max"]:
                    sr["max"] = v
                if abs(v) > threshold:
                    sr["extreme_count"] += 1
                    if len(extremes[sid]) < max_samples:
                        extremes[sid].append({"ts": row["timestamp"], "gwl": v})

    return extremes, station_ranges


def main():
    input_dir = ROOT / "data" / "processed" / "all_states"
    files = sorted(p for p in input_dir.glob("*.normalized.csv") if p.name != "all_observations.normalized.csv")

    print(f"Investigating {len(files)} normalized files with threshold |gwl| > {THRESHOLD} m\n")

    for fpath in files:
        state_tag = fpath.stem.replace(".normalized", "")
        print(f"=== {state_tag} ===")
        extremes, station_ranges = investigate([fpath])

        extreme_stations = [(sid, sr) for sid, sr in station_ranges.items() if sr["extreme_count"] > 0]
        extreme_stations.sort(key=lambda x: abs(x[1]["min"] if x[1]["min"] and abs(x[1]["min"]) > abs(x[1]["max"] or 0) else (x[1]["max"] or 0)), reverse=True)

        print(f"  Total stations: {len(station_ranges)}")
        print(f"  Stations with |gwl|>{THRESHOLD}: {len(extreme_stations)}")
        if extreme_stations:
            print(f"  Top offenders:")
            for sid, sr in extreme_stations[:5]:
                samples = extremes.get(sid, [])
                sample_str = ", ".join(f"{s['ts']}={s['gwl']}" for s in samples[:2])
                print(f"    {sid} | district={sr['district']} | min={sr['min']} max={sr['max']} | extreme_count={sr['extreme_count']}")
                print(f"      samples: {sample_str}")
        print()


if __name__ == "__main__":
    main()
