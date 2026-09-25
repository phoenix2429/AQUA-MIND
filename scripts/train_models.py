"""Train Random Forest and XGBoost models for AQUA-MIND groundwater forecasting.

This script:
  1. Reads quality-filtered observations from data/processed/quality_filtered/
  2. Builds per-station next-step (t+1) features using the existing
     create_features.py pipeline — chronological, no leakage
  3. Constructs a global chronological 70/15/15 train/val/test split
  4. Imputes NaN lag/rolling features with per-station medians from training set
  5. Trains Random Forest and XGBoost
  6. Evaluates Persistence, RF, and XGBoost on the SAME test set
  7. Saves model artifacts and model_evaluation.json

Memory strategy
---------------
  The full 21.5M-row dataset cannot all be held as a dense float matrix.
  This script processes **state by state** and accumulates only the
  feature rows needed for training/evaluation:
    - One state is loaded, feature-engineered, and appended to shared arrays.
    - Arrays are kept as float32 to halve RAM usage.
  Peak RAM is approximately 4–6 GB for the full 5-state run.

  If you run on a machine with <8 GB RAM, use --sample-frac 0.1 to take a
  reproducible 10% random sample from each station. Sample results are clearly
  labeled in the output JSON to prevent confusion with full-dataset results.

Usage
-----
    python scripts/train_models.py
    python scripts/train_models.py --input-dir data/processed/quality_filtered \\
        --model-dir models --output models/model_evaluation.json
    python scripts/train_models.py --sample-frac 0.1   # 10% sample (dev run)
    python scripts/train_models.py --states Telangana "Tamil Nadu"
"""

from __future__ import annotations

import argparse
import bisect
import csv
import io
import json
import logging
import math
import sys
import tempfile
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.evaluation import aggregate_by_group, compute_metrics
from backend.app.ml.random_forest import GroundwaterRandomForest
from backend.app.ml.xgboost_model import GroundwaterXGBoost

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Feature column definitions  (must match create_features.py)
# ------------------------------------------------------------------

NUMERIC_FEATURE_COLS: list[str] = [
    "lag_6h",
    "lag_12h",
    "lag_24h",
    "lag_48h",
    "lag_7d",
    "rolling_mean_7d",
    "rolling_std_7d",
    "rolling_mean_30d",
    "trend_7d",
    "hour",
    "day_of_year",
    "month",
    "season",
    "latitude",
    "longitude",
    "elevation_msl",
]

_READ_BUF = 64 << 20  # 64 MB I/O buffer


# ------------------------------------------------------------------
# Lightweight feature engineering (mirrors create_features.py logic)
# ------------------------------------------------------------------

@dataclass
class _Obs:
    ts: datetime
    gwl: float


@dataclass
class _StationState:
    sid: str
    state: str
    lat: float | None
    lon: float | None
    elev: float | None
    history: list[_Obs] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    window_7d: deque[_Obs] = field(default_factory=deque)
    window_30d: deque[_Obs] = field(default_factory=deque)
    sum_7d: float = 0.0
    sumsq_7d: float = 0.0
    sum_30d: float = 0.0
    sum_x_7d: float = 0.0
    sum_xx_7d: float = 0.0
    sum_xy_7d: float = 0.0

    def add(self, obs: _Obs) -> None:
        self.history.append(obs)
        self.timestamps.append(obs.ts)
        self.window_7d.append(obs)
        self.sum_7d += obs.gwl
        self.sumsq_7d += obs.gwl * obs.gwl
        self.window_30d.append(obs)
        self.sum_30d += obs.gwl
        x = obs.ts.timestamp() / 3600.0
        self.sum_x_7d += x
        self.sum_xx_7d += x * x
        self.sum_xy_7d += x * obs.gwl
        cutoff_7d = obs.ts - timedelta(days=7)
        cutoff_30d = obs.ts - timedelta(days=30)
        while self.history and self.history[0].ts < cutoff_30d:
            self.history.pop(0)
            self.timestamps.pop(0)
        while self.window_7d and self.window_7d[0].ts < cutoff_7d:
            removed = self.window_7d.popleft()
            self.sum_7d -= removed.gwl
            self.sumsq_7d -= removed.gwl * removed.gwl
            x = removed.ts.timestamp() / 3600.0
            self.sum_x_7d -= x
            self.sum_xx_7d -= x * x
            self.sum_xy_7d -= x * removed.gwl
        while self.window_30d and self.window_30d[0].ts < cutoff_30d:
            self.sum_30d -= self.window_30d.popleft().gwl

    def _lag(self, ts: datetime, delta: timedelta) -> float | None:
        target = ts - delta
        tolerance = timedelta(hours=2)
        timestamps = self.timestamps
        if len(timestamps) != len(self.history):
            timestamps = [rec.ts for rec in self.history]
        left = bisect.bisect_left(timestamps, target - tolerance)
        right = bisect.bisect_right(timestamps, target + tolerance)
        if left == right:
            return None
        return min(
            self.history[left:right],
            key=lambda rec: abs((rec.ts - target).total_seconds()),
        ).gwl

    def _rolling(self, ts: datetime, days: int, min_obs: int = 4):
        vals = self.window_7d if days == 7 else self.window_30d
        if len(vals) < min_obs:
            return None, None
        if days == 7:
            m = self.sum_7d / len(vals)
            variance = (self.sumsq_7d - len(vals) * m * m) / (len(vals) - 1)
        else:
            m = sum(r.gwl for r in vals) / len(vals)
            variance = sum((r.gwl - m) ** 2 for r in vals) / (len(vals) - 1)
        if len(vals) < 2:
            return m, None
        return m, math.sqrt(max(variance, 0.0))

    def _rolling_30d(self, ts: datetime, min_obs: int = 8) -> float | None:
        return self.sum_30d / len(self.window_30d) if len(self.window_30d) >= min_obs else None

    def _trend(self, ts: datetime, min_obs: int = 4) -> float | None:
        n = len(self.window_7d)
        if n < min_obs:
            return None
        num = self.sum_xy_7d - self.sum_x_7d * self.sum_7d / n
        den = self.sum_xx_7d - self.sum_x_7d * self.sum_x_7d / n
        return num / den if den > 1e-10 else 0.0

    def build(self, obs: _Obs) -> dict | None:
        """Build feature dict for obs. Returns None if no prior history."""
        if not self.history:
            return None
        ts = obs.ts
        month = ts.month
        season = 0 if month in (12, 1, 2) else 1 if month in (3, 4, 5) else 2 if month in (6, 7, 8, 9) else 3
        mean7, std7 = self._rolling(ts, 7, 4)
        return {
            "station_id": self.sid,
            "state": self.state,
            "timestamp": ts.isoformat(),
            "target": obs.gwl,
            "lag_6h": self._lag(ts, timedelta(hours=6)),
            "lag_12h": self._lag(ts, timedelta(hours=12)),
            "lag_24h": self._lag(ts, timedelta(hours=24)),
            "lag_48h": self._lag(ts, timedelta(hours=48)),
            "lag_7d": self._lag(ts, timedelta(days=7)),
            "rolling_mean_7d": mean7,
            "rolling_std_7d": std7,
            "rolling_mean_30d": self._rolling_30d(ts, 8),
            "trend_7d": self._trend(ts, 4),
            "hour": ts.hour,
            "day_of_year": ts.timetuple().tm_yday,
            "month": month,
            "season": season,
            "latitude": self.lat,
            "longitude": self.lon,
            "elevation_msl": self.elev,
        }


def _safe_float(v: str | None) -> float | None:
    if not v:
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def _stream_features(paths: list[Path], rng: np.random.Generator | None = None, sample_frac: float = 1.0) -> Iterator[dict]:
    """Stream feature dicts from quality-filtered CSVs, one state file at a time."""
    # For each file: load all rows per station, sort, then generate features.
    for path in paths:
        log.info("  Feature engineering: %s", path.name)
        station_rows: dict[str, list[tuple[datetime, float, str | None, str | None, float | None, float | None, float | None]]] = defaultdict(list)
        raw = open(str(path), "rb", buffering=_READ_BUF)
        with io.TextIOWrapper(raw, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                sid = row.get("station_id", "")
                if not sid:
                    continue
                try:
                    ts = datetime.fromisoformat(row["timestamp"].replace(" ", "T"))
                    gwl = float(row["groundwater_level"])
                except (ValueError, KeyError):
                    continue
                if not math.isfinite(gwl):
                    continue
                state = row.get("state") or ""
                lat = _safe_float(row.get("latitude"))
                lon = _safe_float(row.get("longitude"))
                elev = _safe_float(row.get("elevation_msl"))
                station_rows[sid].append((ts, gwl, state, lat, lon, elev))

        for sid, rows in station_rows.items():
            rows.sort(key=lambda r: r[0])
            if rng is not None and sample_frac < 1.0:
                keep = max(2, int(len(rows) * sample_frac))
                keep = min(keep, len(rows))  # cannot sample more than available
                idx = sorted(rng.choice(len(rows), size=keep, replace=False))
                rows = [rows[i] for i in idx]
            state_val = rows[0][2] if rows else ""
            lat_val = next((r[3] for r in rows if r[3] is not None), None)
            lon_val = next((r[4] for r in rows if r[4] is not None), None)
            elev_val = next((r[5] for r in rows if r[5] is not None), None)
            sstate = _StationState(sid=sid, state=state_val, lat=lat_val, lon=lon_val, elev=elev_val)
            for ts, gwl, *_ in rows:
                obs = _Obs(ts=ts, gwl=gwl)
                feat = sstate.build(obs)
                sstate.add(obs)
                if feat is not None:
                    yield feat


# ------------------------------------------------------------------
# Chronological split
# ------------------------------------------------------------------

def chronological_split(
    timestamps: list[str],
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return boolean index arrays for train/val/test based on sorted timestamps.

    The split is based on the GLOBAL timeline, not per-station.
    Oldest 70% → train, next 15% → val, newest 15% → test.
    No shuffling. Strictly chronological.
    """
    n = len(timestamps)
    order = sorted(range(n), key=lambda i: timestamps[i])
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))
    train_idx = np.zeros(n, dtype=bool)
    val_idx = np.zeros(n, dtype=bool)
    test_idx = np.zeros(n, dtype=bool)
    for pos, orig_i in enumerate(order):
        if pos < train_end:
            train_idx[orig_i] = True
        elif pos < val_end:
            val_idx[orig_i] = True
        else:
            test_idx[orig_i] = True
    return train_idx, val_idx, test_idx


# ------------------------------------------------------------------
# NaN imputation (training-set median per feature)
# ------------------------------------------------------------------

def impute_with_median(
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fill NaNs using median of training set per column.

    Returns imputed X_train, X_val, X_test, and the medians array.
    """
    # Do not call nanmedian for an all-NaN column: NumPy emits a warning and
    # returns NaN.  Those columns have no training signal, so the documented
    # deterministic fallback is zero.
    medians = np.zeros(X_train.shape[1], dtype=np.float32)
    has_values = np.any(~np.isnan(X_train), axis=0)
    if np.any(has_values):
        medians[has_values] = np.nanmedian(X_train[:, has_values], axis=0)

    def _fill(X: np.ndarray, m: np.ndarray) -> np.ndarray:
        out = X.copy()
        for col in range(out.shape[1]):
            mask = np.isnan(out[:, col])
            out[mask, col] = m[col]
        return out

    return _fill(X_train, medians), _fill(X_val, medians), _fill(X_test, medians), medians


# ------------------------------------------------------------------
# Persistence baseline (next value = last observed)
# ------------------------------------------------------------------

def persistence_on_rows(lag6h: np.ndarray, target: np.ndarray) -> tuple[list[float], list[float]]:
    """Persistence prediction: predict next GWL as last observed (lag_6h).

    Only rows where lag_6h is not NaN are evaluated.
    Returns (actuals, predictions).
    """
    actuals, preds = [], []
    for lag, tgt in zip(lag6h, target):
        if not np.isnan(lag):
            actuals.append(float(tgt))
            preds.append(float(lag))
    return actuals, preds


# ------------------------------------------------------------------
# Model artifact metadata
# ------------------------------------------------------------------

def build_metadata(
    model_name: str,
    version: str,
    params: dict,
    feature_names: list[str],
    train_n: int,
    val_n: int,
    test_n: int,
    date_range: tuple[str, str],
    metrics: dict,
    lib_versions: dict[str, str],
) -> dict:
    return {
        "model_name": model_name,
        "version": version,
        "training_timestamp": datetime.utcnow().isoformat() + "Z",
        "target": "groundwater_level_next_step",
        "target_description": "Groundwater level at observation t+1 (next 6-hour reading for same station)",
        "feature_names": feature_names,
        "n_features": len(feature_names),
        "hyperparameters": params,
        "split_methodology": "Global chronological: oldest 70% train, next 15% val, newest 15% test",
        "training_observations": train_n,
        "validation_observations": val_n,
        "test_observations": test_n,
        "training_date_range": {"start": date_range[0], "end": date_range[1]},
        "random_seed": 42,
        "library_versions": lib_versions,
        "evaluation_metrics": metrics,
    }


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", type=Path, default=Path("data/processed/quality_filtered"),
                        help="Directory containing *.quality_filtered.csv files")
    parser.add_argument("--model-dir", type=Path, default=Path("models"),
                        help="Root directory to save model artifacts")
    parser.add_argument("--output", type=Path, default=Path("models/model_evaluation.json"),
                        help="Path for the combined evaluation JSON")
    parser.add_argument("--sample-frac", type=float, default=1.0,
                        help="Fraction of observations per station to keep (1.0 = full run, 0.1 = dev/sample run)")
    parser.add_argument("--states", nargs="*", default=None,
                        help="Limit to specific states (e.g. Telangana Karnataka). Default: all states.")
    args = parser.parse_args()

    is_sample = args.sample_frac < 1.0

    # --- Discover input files ---
    input_files = sorted(args.input_dir.glob("*.quality_filtered.csv"))
    if not input_files:
        log.error("No quality_filtered CSV files found in %s", args.input_dir)
        return 1

    if args.states:
        state_tokens = {s.lower().replace(" ", "_") for s in args.states}
        input_files = [
            p for p in input_files
            if any(tok in p.name.lower() for tok in state_tokens)
        ]
        if not input_files:
            log.error("No files matched --states filter. Available: %s", [p.name for p in sorted(args.input_dir.glob("*.quality_filtered.csv"))])
            return 1

    log.info("=== AQUA-MIND ML Training Pipeline ===")
    log.info("Input files: %d", len(input_files))
    log.info("Sample fraction: %.2f%s", args.sample_frac, " ← DEV/SAMPLE RUN" if is_sample else "")

    # --- Stream all features ---
    rng = np.random.default_rng(42) if is_sample else None
    t0 = time.time()
    log.info("Pass 1: counting feature rows …")
    n_total = sum(1 for _ in _stream_features(input_files, rng=rng, sample_frac=args.sample_frac))
    log.info("Feature rows counted: %d  (%.1f s)", n_total, time.time() - t0)

    if n_total < 100:
        log.error("Too few feature rows (%d). Check input directory.", n_total)
        return 1

    # --- Build disk-backed arrays ---
    # A Python dict per feature row exceeds available memory at full scale.
    # Memmaps retain the full dataset while keeping the process resident set bounded.
    log.info("Pass 2: writing disk-backed feature arrays …")
    temp_dir = tempfile.TemporaryDirectory(prefix="aqua_mind_train_")
    timestamps_path = Path(temp_dir.name) / "timestamps.dat"
    states_path = Path(temp_dir.name) / "states.dat"
    y_path = Path(temp_dir.name) / "targets.dat"
    lag6h_path = Path(temp_dir.name) / "lag6h.dat"
    x_path = Path(temp_dir.name) / "features.dat"
    timestamp_values = np.memmap(timestamps_path, dtype=np.float64, mode="w+", shape=(n_total,))
    state_values = np.memmap(states_path, dtype=np.int8, mode="w+", shape=(n_total,))
    y_all = np.memmap(y_path, dtype=np.float32, mode="w+", shape=(n_total,))
    lag6h_all = np.memmap(lag6h_path, dtype=np.float32, mode="w+", shape=(n_total,))
    X_all = np.memmap(x_path, dtype=np.float32, mode="w+", shape=(n_total, len(NUMERIC_FEATURE_COLS)))
    state_codes: dict[str, int] = {}
    row_index = 0
    rng = np.random.default_rng(42) if is_sample else None
    for feat in _stream_features(input_files, rng=rng, sample_frac=args.sample_frac):
        timestamp_values[row_index] = datetime.fromisoformat(feat["timestamp"]).timestamp()
        state = feat["state"]
        if state not in state_codes:
            state_codes[state] = len(state_codes)
        state_values[row_index] = state_codes[state]
        y_all[row_index] = feat["target"]
        lag6h_all[row_index] = feat["lag_6h"] if feat["lag_6h"] is not None else np.nan
        for j, col in enumerate(NUMERIC_FEATURE_COLS):
            value = feat.get(col)
            X_all[row_index, j] = value if value is not None else np.nan
        row_index += 1
    for array in (timestamp_values, state_values, y_all, lag6h_all, X_all):
        array.flush()
    log.info("Feature arrays written: %d rows  (%.1f s)", row_index, time.time() - t0)

    # --- Chronological split ---
    log.info("Computing chronological 70/15/15 split …")
    order = np.argsort(timestamp_values, kind="stable")
    train_end = int(n_total * 0.70)
    val_end = int(n_total * 0.85)
    train_mask = np.zeros(n_total, dtype=bool)
    val_mask = np.zeros(n_total, dtype=bool)
    test_mask = np.zeros(n_total, dtype=bool)
    train_mask[order[:train_end]] = True
    val_mask[order[train_end:val_end]] = True
    test_mask[order[val_end:]] = True
    log.info("  Train: %d  Val: %d  Test: %d", train_mask.sum(), val_mask.sum(), test_mask.sum())

    date_range = (
        datetime.fromtimestamp(timestamp_values[order[0]]).isoformat(),
        datetime.fromtimestamp(timestamp_values[order[-1]]).isoformat(),
    )

    X_train, y_train = X_all[train_mask], y_all[train_mask]
    X_val, y_val = X_all[val_mask], y_all[val_mask]
    X_test, y_test = X_all[test_mask], y_all[test_mask]
    lag6h_test = lag6h_all[test_mask]
    states_by_code = {code: state for state, code in state_codes.items()}
    states_test = [states_by_code[int(state_values[i])] for i in np.flatnonzero(test_mask)]

    # --- Impute NaN with training medians ---
    log.info("Imputing NaN features with training-set medians …")
    X_train_imp, X_val_imp, X_test_imp, medians = impute_with_median(X_train, X_val, X_test)

    # --- Persistence baseline ---
    log.info("Evaluating Persistence baseline on test set …")
    pers_actuals, pers_preds = persistence_on_rows(lag6h_test.astype(np.float64), y_test.astype(np.float64))
    pers_metrics = compute_metrics(pers_actuals, pers_preds)
    log.info("  Persistence test → MAE=%.4f  RMSE=%.4f  R²=%s",
             pers_metrics["mae"], pers_metrics["rmse"], pers_metrics["r2"])

    # --- Library versions ---
    import sklearn, joblib as jl
    try:
        import xgboost as xgb
        xgb_ver = xgb.__version__
    except ImportError:
        xgb_ver = "not installed"

    lib_versions = {
        "scikit-learn": sklearn.__version__,
        "xgboost": xgb_ver,
        "joblib": jl.__version__,
        "numpy": np.__version__,
    }

    # --- Train Random Forest ---
    log.info("Training Random Forest …")
    t1 = time.time()
    rf = GroundwaterRandomForest()
    rf.fit(X_train_imp, y_train.astype(np.float64), feature_names=NUMERIC_FEATURE_COLS)
    log.info("  RF training time: %.1f s", time.time() - t1)

    log.info("Evaluating RF on validation set …")
    rf_val_preds = rf.predict(X_val_imp)
    rf_val_metrics = compute_metrics(y_val.astype(np.float64).tolist(), rf_val_preds.tolist())
    log.info("  RF val → MAE=%.4f  RMSE=%.4f  R²=%s",
             rf_val_metrics["mae"], rf_val_metrics["rmse"], rf_val_metrics["r2"])

    log.info("Evaluating RF on test set …")
    rf_test_preds = rf.predict(X_test_imp)
    rf_test_metrics = compute_metrics(y_test.astype(np.float64).tolist(), rf_test_preds.tolist())
    rf_state_metrics = aggregate_by_group(y_test.astype(np.float64).tolist(), rf_test_preds.tolist(), states_test)
    log.info("  RF test  → MAE=%.4f  RMSE=%.4f  R²=%s",
             rf_test_metrics["mae"], rf_test_metrics["rmse"], rf_test_metrics["r2"])

    # Save RF
    rf_dir = args.model_dir / "random_forest"
    rf.save(rf_dir)
    rf_meta = build_metadata(
        "Random Forest", "1.0", rf.params, NUMERIC_FEATURE_COLS,
        int(train_mask.sum()), int(val_mask.sum()), int(test_mask.sum()),
        date_range, {"validation": rf_val_metrics, "test": rf_test_metrics}, lib_versions,
    )
    rf_meta["feature_importances"] = dict(zip(NUMERIC_FEATURE_COLS, rf.feature_importances_.tolist()))
    (rf_dir / "metadata.json").write_text(json.dumps(rf_meta, indent=2), encoding="utf-8")

    # --- Train XGBoost ---
    log.info("Training XGBoost …")
    t2 = time.time()
    xgb_model = GroundwaterXGBoost()
    xgb_model.fit(
        X_train_imp, y_train.astype(np.float64),
        X_val=X_val_imp, y_val=y_val.astype(np.float64),
        feature_names=NUMERIC_FEATURE_COLS,
    )
    log.info("  XGBoost training time: %.1f s", time.time() - t2)

    log.info("Evaluating XGBoost on validation set …")
    xgb_val_preds = xgb_model.predict(X_val_imp)
    xgb_val_metrics = compute_metrics(y_val.astype(np.float64).tolist(), xgb_val_preds.tolist())
    log.info("  XGB val → MAE=%.4f  RMSE=%.4f  R²=%s",
             xgb_val_metrics["mae"], xgb_val_metrics["rmse"], xgb_val_metrics["r2"])

    log.info("Evaluating XGBoost on test set …")
    xgb_test_preds = xgb_model.predict(X_test_imp)
    xgb_test_metrics = compute_metrics(y_test.astype(np.float64).tolist(), xgb_test_preds.tolist())
    xgb_state_metrics = aggregate_by_group(y_test.astype(np.float64).tolist(), xgb_test_preds.tolist(), states_test)
    log.info("  XGB test → MAE=%.4f  RMSE=%.4f  R²=%s",
             xgb_test_metrics["mae"], xgb_test_metrics["rmse"], xgb_test_metrics["r2"])

    # Save XGBoost
    xgb_dir = args.model_dir / "xgboost"
    xgb_model.save(xgb_dir)
    xgb_meta = build_metadata(
        "XGBoost", "1.0", xgb_model.params, NUMERIC_FEATURE_COLS,
        int(train_mask.sum()), int(val_mask.sum()), int(test_mask.sum()),
        date_range, {"validation": xgb_val_metrics, "test": xgb_test_metrics}, lib_versions,
    )
    if xgb_model.feature_importances_ is not None:
        xgb_meta["feature_importances"] = dict(zip(NUMERIC_FEATURE_COLS, xgb_model.feature_importances_.tolist()))
    (xgb_dir / "metadata.json").write_text(json.dumps(xgb_meta, indent=2), encoding="utf-8")

    # --- Combined evaluation output ---
    evaluation = {
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "is_sample_run": is_sample,
        "sample_frac": args.sample_frac if is_sample else 1.0,
        "dataset": {
            "input_files": [p.name for p in input_files],
            "total_feature_rows": n_total,
            "train_rows": int(train_mask.sum()),
            "val_rows": int(val_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "date_range": {"start": date_range[0], "end": date_range[1]},
            "features": NUMERIC_FEATURE_COLS,
            "target": "groundwater_level_next_step",
        },
        "split": {
            "method": "Global chronological: oldest 70% train, next 15% val, newest 15% test",
            "train_frac": 0.70,
            "val_frac": 0.15,
            "test_frac": 0.15,
            "shuffle": False,
        },
        "models": {
            "persistence": {
                "description": "Next value = last observed (lag_6h). Rows without lag_6h excluded.",
                "test_metrics": pers_metrics,
                "test_n_evaluated": len(pers_actuals),
            },
            "random_forest": {
                "version": "1.0",
                "params": rf.params,
                "validation_metrics": rf_val_metrics,
                "test_metrics": rf_test_metrics,
                "per_state_test_metrics": rf_state_metrics,
                "artifact_dir": str(rf_dir),
                "library_versions": lib_versions,
            },
            "xgboost": {
                "version": "1.0",
                "params": xgb_model.params,
                "validation_metrics": xgb_val_metrics,
                "test_metrics": xgb_test_metrics,
                "per_state_test_metrics": xgb_state_metrics,
                "artifact_dir": str(xgb_dir),
                "library_versions": lib_versions,
            },
        },
        "comparison_note": (
            "Models are compared on the same held-out chronological test set (newest 15%). "
            "Persistence requires a non-null lag_6h so its n may differ from RF/XGBoost. "
            "No model is declared 'best' automatically — compare MAE, RMSE, R² and per-state results."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    log.info("Evaluation saved to %s", args.output)

    # --- Summary table ---
    log.info("\n%s", "=" * 65)
    log.info("RESULTS SUMMARY (Test Set)")
    log.info("%-20s %10s %12s %8s %8s", "Model", "N evaluated", "MAE", "RMSE", "R²")
    log.info("-" * 65)

    def _row(name, n, m):
        mae_s = f"{m['mae']:.4f}" if m.get("mae") is not None else "N/A"
        rmse_s = f"{m['rmse']:.4f}" if m.get("rmse") is not None else "N/A"
        r2_s = f"{m['r2']:.4f}" if m.get("r2") is not None else "N/A"
        log.info("%-20s %10d %12s %8s %8s", name, n, mae_s, rmse_s, r2_s)

    _row("Persistence", len(pers_actuals), pers_metrics)
    _row("Random Forest", int(test_mask.sum()), rf_test_metrics)
    _row("XGBoost", int(test_mask.sum()), xgb_test_metrics)
    log.info("=" * 65)
    if is_sample:
        log.info("⚠  SAMPLE RUN (%.0f%%). These are NOT full-dataset results.", args.sample_frac * 100)

    del timestamp_values, state_values, y_all, lag6h_all, X_all
    temp_dir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
