"""XGBoost model wrapper for AQUA-MIND groundwater forecasting.

This module provides a clean, reusable wrapper around XGBoost's
XGBRegressor for one-step-ahead groundwater level forecasting.

Usage
-----
    from backend.app.ml.xgboost_model import GroundwaterXGBoost

    model = GroundwaterXGBoost()
    model.fit(X_train, y_train, X_val, y_val)
    preds = model.predict(X_test)
    model.save("models/xgboost")
    model.load("models/xgboost")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Default hyperparameters — balanced for accuracy/speed on large tabular datasets.
# Early stopping uses the validation set to prevent overfitting without grid search.
_DEFAULT_PARAMS: dict[str, Any] = {
    "n_estimators": 500,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 10,
    "random_state": 42,
    "n_jobs": -1,
    "tree_method": "hist",        # memory-efficient histogram method
    "early_stopping_rounds": 30,  # stop if no improvement for 30 rounds
    "eval_metric": "rmse",
}

MODEL_FILENAME = "model.joblib"
SCHEMA_FILENAME = "feature_schema.json"


class GroundwaterXGBoost:
    """Reusable XGBoost wrapper for groundwater level forecasting.

    Parameters
    ----------
    params : dict, optional
        Override any of the default XGBRegressor params.
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params: dict[str, Any] = {**_DEFAULT_PARAMS, **(params or {})}
        self.feature_names: list[str] = []
        self._is_fitted = False
        self._model: Any = None  # XGBRegressor — lazily instantiated

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> "GroundwaterXGBoost":
        """Train XGBoost on the provided feature matrix and targets.

        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            Training features. NaN values are handled natively by XGBoost.
        y : np.ndarray, shape (n_samples,)
            Training targets (next-step groundwater levels).
        X_val : np.ndarray, optional
            Validation features for early stopping.
        y_val : np.ndarray, optional
            Validation targets for early stopping.
        feature_names : list[str], optional
            Column names matching the columns of X.
        """
        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            raise ImportError("xgboost is required. Install with: pip install xgboost") from exc

        if feature_names is not None:
            self.feature_names = list(feature_names)

        # XGBoost 3.x: early_stopping_rounds must be set on the constructor.
        # eval_metric is also a constructor param in 3.x.
        early_stopping_rounds = self.params.get("early_stopping_rounds", 30)
        init_params = {k: v for k, v in self.params.items() if k not in ("early_stopping_rounds",)}

        if X_val is not None and y_val is not None:
            init_params["early_stopping_rounds"] = early_stopping_rounds

        self._model = XGBRegressor(**init_params)

        fit_kwargs: dict[str, Any] = {}
        if X_val is not None and y_val is not None:
            fit_kwargs["eval_set"] = [(X_val, y_val)]
            fit_kwargs["verbose"] = False

        logger.info(
            "Fitting XGBoost: %d samples × %d features, params=%s",
            X.shape[0], X.shape[1], init_params,
        )
        self._model.fit(X, y, **fit_kwargs)
        self._is_fitted = True
        best = getattr(self._model, "best_iteration", None)
        logger.info("XGBoost training complete. Best iteration: %s", best)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return predicted next-step groundwater levels.

        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            Feature matrix. Must match column order used during fit().
        """
        self._require_fitted()
        return self._model.predict(X)

    def save(self, directory: str | Path) -> None:
        """Persist the trained model and feature schema to *directory*.

        Two files are written:
            model.joblib         — XGBoost model object
            feature_schema.json  — ordered list of feature names
        """
        self._require_fitted()
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, out / MODEL_FILENAME)
        schema = {
            "feature_names": self.feature_names,
            "n_features": len(self.feature_names),
            "params": {k: v for k, v in self.params.items() if not callable(v)},
        }
        (out / SCHEMA_FILENAME).write_text(json.dumps(schema, indent=2), encoding="utf-8")
        logger.info("XGBoost model saved to %s", out)

    @classmethod
    def load(cls, directory: str | Path) -> "GroundwaterXGBoost":
        """Load a previously saved model from *directory*.

        Returns a fully fitted GroundwaterXGBoost instance.
        """
        src = Path(directory)
        schema_path = src / SCHEMA_FILENAME
        schema: dict[str, Any] = {}
        if schema_path.is_file():
            schema = json.loads(schema_path.read_text(encoding="utf-8"))

        instance = cls.__new__(cls)
        instance.params = schema.get("params", _DEFAULT_PARAMS)
        instance.feature_names = schema.get("feature_names", [])
        instance._model = joblib.load(src / MODEL_FILENAME)
        instance._is_fitted = True
        logger.info("XGBoost model loaded from %s", src)
        return instance

    @property
    def feature_importances_(self) -> np.ndarray | None:
        """Expose XGBoost feature importances (gain-based)."""
        if not self._is_fitted or self._model is None:
            return None
        return self._model.feature_importances_

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_fitted(self) -> None:
        if not self._is_fitted or self._model is None:
            raise RuntimeError("Model is not fitted. Call fit() first.")
