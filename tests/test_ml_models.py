"""Tests for the Random Forest, XGBoost, evaluation utilities, and training pipeline."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.evaluation import aggregate_by_group, compute_metrics, mae, r2, rmse
from backend.app.ml.random_forest import GroundwaterRandomForest
from backend.app.ml.xgboost_model import GroundwaterXGBoost
from scripts.train_models import (
    NUMERIC_FEATURE_COLS,
    _StationState,
    _Obs,
    chronological_split,
    impute_with_median,
    persistence_on_rows,
)
from datetime import datetime, timedelta


# ================================================================
# Helpers
# ================================================================

def make_simple_dataset(n: int = 200, n_features: int = 16, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, n_features)).astype(np.float32)
    # Simple linear target + noise so R² > 0
    y = (X[:, 0] * 2.5 - X[:, 1] * 1.0 + rng.standard_normal(n) * 0.1).astype(np.float64)
    return X, y


def make_timestamps(n: int, start: str = "2021-01-01T00:00:00") -> list[str]:
    base = datetime.fromisoformat(start)
    return [(base + timedelta(hours=6 * i)).isoformat() for i in range(n)]


# ================================================================
# Evaluation utilities
# ================================================================

class TestEvaluationMetrics:
    def test_mae_perfect(self):
        assert mae([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)

    def test_mae_known(self):
        assert mae([1.0, 2.0, 3.0], [2.0, 3.0, 4.0]) == pytest.approx(1.0)

    def test_rmse_perfect(self):
        assert rmse([5.0, 10.0], [5.0, 10.0]) == pytest.approx(0.0)

    def test_rmse_known(self):
        assert rmse([0.0, 0.0], [3.0, 4.0]) == pytest.approx(math.sqrt(12.5))

    def test_r2_perfect(self):
        assert r2([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_r2_constant_actual_returns_none(self):
        assert r2([5.0, 5.0, 5.0], [4.0, 5.0, 6.0]) is None

    def test_r2_can_be_negative(self):
        val = r2([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
        assert val is not None and val < 0

    def test_compute_metrics_empty(self):
        m = compute_metrics([], [])
        assert m["n"] == 0
        assert m["mae"] is None

    def test_compute_metrics_nonempty(self):
        m = compute_metrics([1.0, 2.0], [1.5, 2.5])
        assert m["n"] == 2
        assert m["mae"] == pytest.approx(0.5)

    def test_aggregate_by_group(self):
        actuals = [1.0, 2.0, 3.0, 4.0]
        preds = [1.0, 2.0, 3.0, 4.0]
        groups = ["A", "A", "B", "B"]
        result = aggregate_by_group(actuals, preds, groups)
        assert set(result.keys()) == {"A", "B"}
        assert result["A"]["mae"] == pytest.approx(0.0)
        assert result["B"]["mae"] == pytest.approx(0.0)


# ================================================================
# Chronological split
# ================================================================

class TestChronologicalSplit:
    def test_no_overlap(self):
        ts = make_timestamps(100)
        tr, va, te = chronological_split(ts, 0.70, 0.15)
        assert not (tr & va).any()
        assert not (tr & te).any()
        assert not (va & te).any()

    def test_covers_all(self):
        ts = make_timestamps(100)
        tr, va, te = chronological_split(ts, 0.70, 0.15)
        assert (tr | va | te).all()

    def test_approximate_fractions(self):
        n = 1000
        ts = make_timestamps(n)
        tr, va, te = chronological_split(ts, 0.70, 0.15)
        assert 680 <= tr.sum() <= 720
        assert 140 <= va.sum() <= 160
        assert 140 <= te.sum() <= 160

    def test_train_oldest_test_newest(self):
        ts = make_timestamps(100)
        tr, _, te = chronological_split(ts, 0.70, 0.15)
        train_max = max(ts[i] for i in range(100) if tr[i])
        test_min = min(ts[i] for i in range(100) if te[i])
        assert train_max < test_min


# ================================================================
# NaN imputation
# ================================================================

class TestImputation:
    def test_no_nan_unchanged(self):
        X = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        Xtr, Xv, Xte, m = impute_with_median(X, X.copy(), X.copy())
        np.testing.assert_allclose(Xtr, X, atol=1e-5)

    def test_nan_filled(self):
        X_train = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)
        X_test = np.array([[np.nan, np.nan]], dtype=np.float32)
        _, _, X_test_imp, m = impute_with_median(X_train, X_train.copy(), X_test)
        assert not np.isnan(X_test_imp).any()
        # Median of [1,3,5] = 3, median of [2,4,6] = 4
        assert X_test_imp[0, 0] == pytest.approx(3.0, abs=0.1)
        assert X_test_imp[0, 1] == pytest.approx(4.0, abs=0.1)

    def test_all_nan_column_filled_with_zero(self):
        X_train = np.array([[np.nan, 1.0], [np.nan, 2.0]], dtype=np.float32)
        X_test = np.array([[np.nan, 3.0]], dtype=np.float32)
        _, _, X_test_imp, m = impute_with_median(X_train, X_train.copy(), X_test)
        assert X_test_imp[0, 0] == pytest.approx(0.0)


# ================================================================
# Target construction / persistence
# ================================================================

class TestPersistence:
    def test_persistence_perfect_lag(self):
        lag6h = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        target = np.array([2.0, 3.0, 4.0], dtype=np.float32)
        actuals, preds = persistence_on_rows(lag6h, target)
        assert actuals == [2.0, 3.0, 4.0]
        assert preds == [1.0, 2.0, 3.0]

    def test_persistence_skips_nan_lag(self):
        lag6h = np.array([np.nan, 2.0, np.nan], dtype=np.float32)
        target = np.array([1.0, 3.0, 5.0], dtype=np.float32)
        actuals, preds = persistence_on_rows(lag6h, target)
        assert len(actuals) == 1
        assert actuals[0] == pytest.approx(3.0)
        assert preds[0] == pytest.approx(2.0)

    def test_persistence_all_nan(self):
        lag6h = np.array([np.nan, np.nan], dtype=np.float32)
        target = np.array([1.0, 2.0], dtype=np.float32)
        actuals, preds = persistence_on_rows(lag6h, target)
        assert actuals == []
        assert preds == []


# ================================================================
# Station feature state (target construction)
# ================================================================

class TestStationFeatureState:
    def _make_state(self, sid="S1"):
        return _StationState(sid=sid, state="TestState", lat=17.0, lon=78.0, elev=500.0)

    def _obs(self, ts_str: str, gwl: float):
        return _Obs(ts=datetime.fromisoformat(ts_str), gwl=gwl)

    def test_no_prior_returns_none(self):
        s = self._make_state()
        result = s.build(self._obs("2024-01-01T00:00:00", -10.0))
        assert result is None

    def test_first_obs_after_add_yields_feature(self):
        s = self._make_state()
        s.history.append(self._obs("2024-01-01T00:00:00", -10.0))
        result = s.build(self._obs("2024-01-01T06:00:00", -10.5))
        assert result is not None
        assert result["target"] == pytest.approx(-10.5)

    def test_target_is_current_gwl(self):
        s = self._make_state()
        s.history.append(self._obs("2024-01-01T00:00:00", -10.0))
        r = s.build(self._obs("2024-01-01T06:00:00", -11.0))
        assert r["target"] == pytest.approx(-11.0)

    def test_lag_6h_correct(self):
        s = self._make_state()
        s.history.append(self._obs("2024-01-01T00:00:00", -10.0))
        r = s.build(self._obs("2024-01-01T06:00:00", -11.0))
        assert r["lag_6h"] == pytest.approx(-10.0)

    def test_lag_beyond_window_is_none(self):
        s = self._make_state()
        s.history.append(self._obs("2024-01-01T00:00:00", -10.0))
        r = s.build(self._obs("2024-01-05T00:00:00", -11.0))
        assert r["lag_6h"] is None
        assert r["lag_12h"] is None
        assert r["lag_24h"] is None

    def test_calendar_season_monsoon(self):
        s = self._make_state()
        s.history.append(self._obs("2024-06-01T00:00:00", -10.0))
        r = s.build(self._obs("2024-06-15T12:00:00", -11.0))
        assert r["season"] == 2  # monsoon
        assert r["month"] == 6
        assert r["hour"] == 12


# ================================================================
# Random Forest model
# ================================================================

class TestRandomForest:
    def test_fit_predict(self):
        X, y = make_simple_dataset(200)
        rf = GroundwaterRandomForest({"n_estimators": 10, "n_jobs": 1})
        rf.fit(X, y)
        preds = rf.predict(X)
        assert preds.shape == (200,)
        assert not np.isnan(preds).any()

    def test_save_load_roundtrip(self, tmp_path):
        X, y = make_simple_dataset(100)
        rf = GroundwaterRandomForest({"n_estimators": 5, "n_jobs": 1, "random_state": 42})
        rf.fit(X, y, feature_names=[f"f{i}" for i in range(X.shape[1])])
        rf.save(tmp_path / "rf")
        rf2 = GroundwaterRandomForest.load(tmp_path / "rf")
        preds1 = rf.predict(X)
        preds2 = rf2.predict(X)
        np.testing.assert_allclose(preds1, preds2, atol=1e-5)

    def test_feature_schema_saved(self, tmp_path):
        X, y = make_simple_dataset(50)
        names = [f"feat_{i}" for i in range(X.shape[1])]
        rf = GroundwaterRandomForest({"n_estimators": 3, "n_jobs": 1})
        rf.fit(X, y, feature_names=names)
        rf.save(tmp_path / "rf")
        schema = json.loads((tmp_path / "rf" / "feature_schema.json").read_text())
        assert schema["feature_names"] == names

    def test_predict_before_fit_raises(self):
        rf = GroundwaterRandomForest()
        with pytest.raises(RuntimeError):
            rf.predict(np.zeros((5, 16)))

    def test_feature_importances_available_after_fit(self):
        X, y = make_simple_dataset(100)
        rf = GroundwaterRandomForest({"n_estimators": 5, "n_jobs": 1})
        rf.fit(X, y)
        assert rf.feature_importances_ is not None
        assert rf.feature_importances_.shape == (X.shape[1],)

    def test_r2_better_than_zero_on_clean_data(self):
        X, y = make_simple_dataset(500, seed=1)
        n = len(y)
        split = int(n * 0.8)
        rf = GroundwaterRandomForest({"n_estimators": 20, "n_jobs": 1, "random_state": 42})
        rf.fit(X[:split], y[:split])
        preds = rf.predict(X[split:])
        score = r2(y[split:].tolist(), preds.tolist())
        assert score is not None and score > 0.5


# ================================================================
# XGBoost model
# ================================================================

class TestXGBoost:
    def test_fit_predict(self):
        X, y = make_simple_dataset(200)
        model = GroundwaterXGBoost({"n_estimators": 20, "n_jobs": 1})
        model.fit(X, y)
        preds = model.predict(X)
        assert preds.shape == (200,)
        assert not np.isnan(preds).any()

    def test_fit_with_validation(self):
        X, y = make_simple_dataset(400)
        model = GroundwaterXGBoost({"n_estimators": 50, "n_jobs": 1, "early_stopping_rounds": 5})
        model.fit(X[:300], y[:300], X_val=X[300:], y_val=y[300:])
        preds = model.predict(X[300:])
        assert preds.shape == (100,)

    def test_save_load_roundtrip(self, tmp_path):
        X, y = make_simple_dataset(100)
        model = GroundwaterXGBoost({"n_estimators": 10, "n_jobs": 1, "random_state": 42})
        model.fit(X, y, feature_names=[f"f{i}" for i in range(X.shape[1])])
        model.save(tmp_path / "xgb")
        model2 = GroundwaterXGBoost.load(tmp_path / "xgb")
        preds1 = model.predict(X)
        preds2 = model2.predict(X)
        np.testing.assert_allclose(preds1, preds2, atol=1e-4)

    def test_feature_schema_saved(self, tmp_path):
        X, y = make_simple_dataset(50)
        names = [f"feat_{i}" for i in range(X.shape[1])]
        model = GroundwaterXGBoost({"n_estimators": 5, "n_jobs": 1})
        model.fit(X, y, feature_names=names)
        model.save(tmp_path / "xgb")
        schema = json.loads((tmp_path / "xgb" / "feature_schema.json").read_text())
        assert schema["feature_names"] == names

    def test_predict_before_fit_raises(self):
        model = GroundwaterXGBoost()
        with pytest.raises(RuntimeError):
            model.predict(np.zeros((5, 16)))

    def test_nan_input_handled(self):
        """XGBoost natively handles NaN; should not crash."""
        X, y = make_simple_dataset(200)
        X_nan = X.copy()
        X_nan[::5, 0] = np.nan  # introduce some NaNs
        model = GroundwaterXGBoost({"n_estimators": 10, "n_jobs": 1})
        model.fit(X_nan, y)
        preds = model.predict(X_nan)
        assert not np.isnan(preds).any()

    def test_r2_better_than_zero_on_clean_data(self):
        X, y = make_simple_dataset(500, seed=2)
        n = len(y)
        split = int(n * 0.8)
        model = GroundwaterXGBoost({"n_estimators": 50, "n_jobs": 1, "random_state": 42,
                                    "early_stopping_rounds": 10})
        model.fit(X[:split], y[:split], X_val=X[split:], y_val=y[split:])
        preds = model.predict(X[split:])
        score = r2(y[split:].tolist(), preds.tolist())
        assert score is not None and score > 0.5


# ================================================================
# Edge cases
# ================================================================

class TestEdgeCases:
    def test_rf_single_sample_predict(self):
        X, y = make_simple_dataset(50)
        rf = GroundwaterRandomForest({"n_estimators": 5, "n_jobs": 1})
        rf.fit(X, y)
        pred = rf.predict(X[:1])
        assert pred.shape == (1,)

    def test_split_minimum_dataset(self):
        ts = make_timestamps(10)
        tr, va, te = chronological_split(ts, 0.70, 0.15)
        assert (tr | va | te).all()
        assert not (tr & te).any()

    def test_station_state_one_observation_no_lags(self):
        s = _StationState(sid="X", state="S", lat=None, lon=None, elev=None)
        s.history.append(_Obs(ts=datetime(2024, 1, 1), gwl=-5.0))
        r = s.build(_Obs(ts=datetime(2024, 1, 1, 6), gwl=-5.5))
        assert r is not None
        assert r["lag_6h"] == pytest.approx(-5.0, abs=0.001)
        assert r["latitude"] is None
        assert r["longitude"] is None
        assert r["elevation_msl"] is None

    def test_imputation_empty_val_test(self):
        X_train = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        X_empty = np.empty((0, 2), dtype=np.float32)
        Xtr, Xv, Xte, _ = impute_with_median(X_train, X_empty.copy(), X_empty.copy())
        assert Xv.shape == (0, 2)
        assert Xte.shape == (0, 2)
