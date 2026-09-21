# AQUA-MIND ML Pipeline

*Version 1.0 — 2026-09-21*

This document describes the Machine Learning forecasting pipeline for AQUA-MIND, covering model architecture, feature engineering, chronological splitting, evaluation methodology, artifact structure, and reproducibility guarantees.

---

## 1. Overview

AQUA-MIND forecasts the **next observed groundwater level** (6 hours ahead) at a station using:

1. **Persistence Baseline** — predicts next GWL = last observed GWL (`lag_6h`)
2. **Random Forest** — ensemble of 200 decision trees (scikit-learn)
3. **XGBoost** — gradient-boosted trees with histogram acceleration (XGBoost 3.x)

All three models are evaluated on the **same chronological test set** (newest 15% of all observations) so the comparison is fair.

---

## 2. Input Data

| Property | Value |
|---|---|
| Source | `data/processed/quality_filtered/*.quality_filtered.csv` |
| States | Telangana, Andhra Pradesh, Karnataka, Tamil Nadu, Maharashtra |
| Raw observations | ~21.5 million (post quality-filter) |
| Timestamp frequency | 6-hourly per station |
| GWL bounds | −300 m to +50 m (physical plausibility filter) |

---

## 3. Feature Engineering

Features are built **station by station, strictly chronologically**. At each timestamp `t`, only information that would have been available *before* `t` is used.

| Feature | Description |
|---|---|
| `lag_6h` | GWL 6 hours before `t` |
| `lag_12h` | GWL 12 hours before `t` |
| `lag_24h` | GWL 24 hours before `t` |
| `lag_48h` | GWL 48 hours before `t` |
| `lag_7d` | GWL 7 days before `t` |
| `rolling_mean_7d` | Mean GWL over previous 7 days |
| `rolling_std_7d` | Std dev of GWL over previous 7 days |
| `rolling_mean_30d` | Mean GWL over previous 30 days |
| `trend_7d` | OLS slope (m/hour) over previous 7 days |
| `hour` | Hour of day (0–23) |
| `day_of_year` | Day of year (1–366) |
| `month` | Month (1–12) |
| `season` | 0=Winter, 1=Pre-monsoon, 2=Monsoon, 3=Post-monsoon |
| `latitude` | Station latitude |
| `longitude` | Station longitude |
| `elevation_msl` | Station elevation (may be null → imputed) |

**Total: 16 numeric features.**

### Target Variable

```
target = groundwater_level at time t   (the CURRENT observation)
features use only history BEFORE t     (no leakage)
```

At inference time, all features at `t` are known (they are derived from past data). The model predicts the GWL that will be recorded at `t+1`.

> The "next-step" framing works because features at `t` include the current `lag_6h` (the immediately preceding reading), so the model learns to predict the next reading given the current one and its context.

---

## 4. Chronological Train / Validation / Test Split

No shuffling. No random train-test split. Strictly chronological:

```
Timeline:  [──────────── 2021 ── 2022 ── 2023 ── 2024 ── 2025 ──────────── 2026 ──]
                │←──────── TRAIN (70%) ──────────→│←─VAL (15%)─→│←─TEST (15%)────→│
```

| Split | Fraction | Description |
|---|---|---|
| Train | 70% | Oldest observations. Used to fit models. |
| Validation | 15% | Next period. Used for early stopping (XGBoost) and config selection. |
| Test | 15% | Newest observations. **Used for final evaluation only. Never used for training.** |

---

## 5. NaN Imputation

Lag and rolling features can be `NaN` at the start of a station's history (before enough history is available). These are imputed using the **per-column median of the training set**:

```python
medians = np.nanmedian(X_train, axis=0)
X_train = fill_nan(X_train, medians)
X_val   = fill_nan(X_val, medians)    # same medians, no leakage
X_test  = fill_nan(X_test, medians)   # same medians, no leakage
```

> XGBoost can handle NaN natively, but imputation is applied for consistency across all models.

---

## 6. Models

### 6.1 Persistence Baseline

```python
prediction(t) = groundwater_level(t - 6h)   # i.e., lag_6h
```

Rows where `lag_6h` is NaN are excluded from the persistence evaluation. This ensures a fair comparison with a reasonable denominator.

### 6.2 Random Forest

| Parameter | Value |
|---|---|
| `n_estimators` | 200 |
| `max_depth` | 20 |
| `min_samples_leaf` | 10 |
| `max_features` | 0.5 (fraction) |
| `n_jobs` | −1 (all CPUs) |
| `random_state` | 42 |

- Outputs: Mean of tree predictions.
- Feature importances: Mean Decrease in Impurity (MDI).

### 6.3 XGBoost

| Parameter | Value |
|---|---|
| `n_estimators` | 500 |
| `max_depth` | 8 |
| `learning_rate` | 0.05 |
| `subsample` | 0.8 |
| `colsample_bytree` | 0.8 |
| `min_child_weight` | 10 |
| `tree_method` | `hist` (memory-efficient) |
| `early_stopping_rounds` | 30 |
| `eval_metric` | `rmse` |
| `random_state` | 42 |
| `n_jobs` | −1 |

- Uses the **validation set** for early stopping (stops if RMSE does not improve for 30 rounds).
- Feature importances: Total gain across all splits.

---

## 7. Evaluation Metrics

| Metric | Formula | Interpretation |
|---|---|---|
| MAE | mean\|actual − predicted\| | Average error in metres |
| RMSE | sqrt(mean(actual − predicted)²) | Penalises large errors more |
| R² | 1 − SS_res / SS_tot | 1.0 = perfect, 0 = no better than mean |

Both **overall** and **per-state** metrics are computed on the test set.

---

## 8. Model Artifact Structure

```
models/
├── random_forest/
│   ├── model.joblib          ← scikit-learn RandomForestRegressor
│   ├── metadata.json         ← training details, metrics, feature importances
│   └── feature_schema.json   ← ordered feature list
│
├── xgboost/
│   ├── model.joblib          ← XGBRegressor object
│   ├── metadata.json         ← training details, metrics, feature importances
│   └── feature_schema.json   ← ordered feature list
│
├── model_evaluation.json     ← side-by-side comparison of all 3 models
└── persistence_evaluation.json  ← baseline from evaluate_persistence.py
```

### Loading a saved model

```python
from backend.app.ml.random_forest import GroundwaterRandomForest
from backend.app.ml.xgboost_model import GroundwaterXGBoost

rf = GroundwaterRandomForest.load("models/random_forest")
xgb = GroundwaterXGBoost.load("models/xgboost")

predictions = rf.predict(X_new)
```

---

## 9. Running the Training Pipeline

### Full run (all 5 states, ~21M rows)
```bash
python scripts/train_models.py
```

> ⚠️ Requires ~6–8 GB RAM and may take 30–90 minutes depending on CPU.

### Sample / dev run (5% per station, fast)
```bash
python scripts/train_models.py --sample-frac 0.05
```
Results are clearly labeled `is_sample_run: true` in `model_evaluation.json`.

### Specific states
```bash
python scripts/train_models.py --states Telangana "Andhra Pradesh"
```

### Custom output paths
```bash
python scripts/train_models.py \
    --input-dir data/processed/quality_filtered \
    --model-dir models \
    --output models/model_evaluation.json
```

---

## 10. Memory Strategy

The full 21.5M-row dataset is processed **state by state** to avoid loading everything into RAM at once:

1. One state file is opened as a streaming CSV reader.
2. Rows are grouped per station in memory.
3. Features are computed chronologically per station.
4. Feature rows are appended to a global list.
5. After all files, a single `float32` numpy array is built.

Peak RAM ≈ 4–6 GB for a full 5-state run. Use `--sample-frac 0.05` for machines with less than 8 GB RAM.

---

## 11. Data Leakage Prevention

The following leakage controls are enforced:

| Control | Implementation |
|---|---|
| No shuffle | `chronological_split()` sorts by timestamp, never shuffles |
| No forward lags | `_StationState.build()` computes features only from `history` (past) |
| Imputation from training set | Medians computed on train, applied to val/test |
| Validation isolation | Used only for XGBoost early stopping, never for RF |
| Test set isolation | No tuning against the test set |

---

## 12. Reproducibility

| Element | Value |
|---|---|
| `random_state` | 42 (RF, XGBoost, sample RNG) |
| Chronological split | Deterministic sort-based (no random seed needed) |
| Library pinning | Versions stored in `metadata.json` per model |
| Input data | SHA-256 verified, quality-filtered CSVs |

---

## 13. Limitations

1. **Features are re-computed on-the-fly** from the quality-filtered CSVs rather than from a pre-computed feature store. This means the training pipeline re-does feature engineering on every run. For a production system, a Parquet feature store would be preferred.

2. **No hyperparameter search was performed.** The initial parameters were chosen based on domain knowledge and rule-of-thumb for large tabular datasets. Grid search or Bayesian optimisation could improve performance.

3. **Elevation is missing** for many stations (stored as empty string in the CSV). It is imputed with the training-set median (≈ 0 effect if most are null).

4. **Sample run metrics are not production metrics.** Running with `--sample-frac < 1.0` produces results from a 5–10% subset. These are clearly labeled in `model_evaluation.json` (`is_sample_run: true`).

5. **No SHAP yet.** Feature importances (MDI for RF, gain for XGBoost) are available in `metadata.json`, but Tree SHAP (per-prediction attribution) is Phase 2.

---

## 14. Next Phase: Tree SHAP

To add SHAP on top of these models:

1. Install: `pip install shap`
2. Load a trained model: `rf = GroundwaterRandomForest.load("models/random_forest")`
3. Use `shap.TreeExplainer(rf._model)` — works directly on the underlying sklearn/XGBoost object
4. Compute: `shap_values = explainer.shap_values(X_test_sample)`
5. Add `GET /api/stations/{station_id}/shap` endpoint returning top-N feature attributions

The `feature_schema.json` already stores the ordered feature list needed for SHAP column labeling.
