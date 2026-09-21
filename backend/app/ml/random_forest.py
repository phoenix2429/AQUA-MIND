"""Random Forest model wrapper for AQUA-MIND groundwater forecasting.

This module provides a clean, reusable wrapper around scikit-learn's
RandomForestRegressor for one-step-ahead groundwater level forecasting.

Usage
-----
    from backend.app.ml.random_forest import GroundwaterRandomForest

    model = GroundwaterRandomForest()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    model.save("models/random_forest")
    model.load("models/random_forest")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Default hyperparameters — chosen for a good initial accuracy/speed balance
# on the AQUA-MIND 5-state dataset (~21M rows, ~16 numeric features).
_DEFAULT_PARAMS: dict[str, Any] = {
    "n_estimators": 200,
    "max_depth": 20,
    "min_samples_leaf": 10,
    "max_features": 0.5,      # fraction of features considered per split
    "n_jobs": -1,             # use all available CPU cores
    "random_state": 42,
}

MODEL_FILENAME = "model.joblib"
SCHEMA_FILENAME = "feature_schema.json"


class GroundwaterRandomForest:
    """Reusable Random Forest wrapper for groundwater level forecasting.

    Parameters
    ----------
    params : dict, optional
        Override any of the default scikit-learn RandomForestRegressor params.
    """

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        from sklearn.ensemble import RandomForestRegressor  # lazy import

        self.params: dict[str, Any] = {**_DEFAULT_PARAMS, **(params or {})}
        self._model = RandomForestRegressor(**self.params)
        self.feature_names: list[str] = []
        self._is_fitted = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str] | None = None) -> "GroundwaterRandomForest":
        """Train the Random Forest on the provided feature matrix and targets.

        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            Feature matrix. NaN values must be imputed before calling fit().
        y : np.ndarray, shape (n_samples,)
            Target groundwater levels (next-step values).
        feature_names : list[str], optional
            Column names matching the columns of X. Stored in feature_schema.json.
        """
        if feature_names is not None:
            self.feature_names = list(feature_names)
        logger.info("Fitting Random Forest: %d samples × %d features, params=%s", X.shape[0], X.shape[1], self.params)
        self._model.fit(X, y)
        self._is_fitted = True
        logger.info("Random Forest training complete.")
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return predicted next-step groundwater levels.

        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            Feature matrix. Must match the column order used during fit().
        """
        self._require_fitted()
        return self._model.predict(X)

    def save(self, directory: str | Path) -> None:
        """Persist the trained model and feature schema to *directory*.

        Creates the directory if it does not exist.
        Two files are written:
            model.joblib         — sklearn model object
            feature_schema.json  — ordered list of feature names
        """
        self._require_fitted()
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, out / MODEL_FILENAME)
        schema = {"feature_names": self.feature_names, "n_features": len(self.feature_names), "params": self.params}
        (out / SCHEMA_FILENAME).write_text(json.dumps(schema, indent=2), encoding="utf-8")
        logger.info("Random Forest saved to %s", out)

    @classmethod
    def load(cls, directory: str | Path) -> "GroundwaterRandomForest":
        """Load a previously saved model from *directory*.

        Returns a fully fitted GroundwaterRandomForest instance.
        """
        from sklearn.ensemble import RandomForestRegressor  # lazy import

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
        logger.info("Random Forest loaded from %s", src)
        return instance

    @property
    def feature_importances_(self) -> np.ndarray | None:
        """Expose sklearn feature importances (mean decrease in impurity)."""
        if not self._is_fitted:
            return None
        return self._model.feature_importances_

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError("Model is not fitted. Call fit() first.")
