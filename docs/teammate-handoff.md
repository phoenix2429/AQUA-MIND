# AQUA-MIND Teammate Handoff

## Project status

AQUA-MIND is a five-state groundwater telemetry research platform. The official source files currently cover Telangana, Andhra Pradesh, Karnataka, Tamil Nadu, and Maharashtra.

Completed:

- Repository scaffold and Phase 0 audit.
- Generalized CSV schema detection and normalization.
- State-qualified station IDs in the form `State::source_station_id`.
- Streaming ingestion that preserves raw files and rejects malformed required values.
- Duplicate station/timestamp handling.
- Five-state processing pipeline with checkpoint resumption.
- Ten unique official resources processed; the exact duplicate Maharashtra resource was skipped.
- Unified normalized output and per-resource JSON ingestion reports under `data/processed/all_states/`.
- Unified station registry with 5,426 stations from the completed audit run.
- Read-only FastAPI APIs for states, districts, stations, observations, nearby search, historical data, and persistence forecast.
- SQLAlchemy models for users, stations, observations, forecasts, analytical results, recommendations, model runs, and data sources.
- Historical aggregation service and persistence forecast service.
- Chronological persistence evaluation script and forecast-quality audit script.
- Tests currently cover ingestion, registry, database models, API endpoints, analytics, loading, and persistence evaluation.

## Important data facts

- Raw CSVs are the source of truth and must never be modified.
- The resource name `2026_2030` does not mean observations exist through 2030.
- Forecasting must begin after the measured latest observation timestamp.
- The five-state normalized corpus contains approximately 21.6 million accepted observations from the previous valid audit run; rerun the corrected pipeline after any source or normalizer change and use its new report as authoritative.
- Some states contain extreme groundwater values and extreme consecutive jumps. Do not train or report Random Forest/XGBoost metrics until the quality policy is agreed and measured. Never silently clip values.
- The full five-state SQLite import was intentionally not completed because index maintenance was too slow. PostgreSQL is the intended production database target.

## Current known issue and fix

An earlier rebuild failed with `MemoryError` because an old encoding detector loaded an entire file with `Path.read_bytes()`. The current implementation uses a bounded 1 MB sample in `backend/app/ingestion/normalizer.py`. The five-state pipeline should be rerun and verified after checkout.

## Recommended next order

1. Run the full test suite.
2. Run `scripts/process_all_states.py` and inspect `data/processed/all_states/five_state_audit.json`.
3. Run `scripts/audit_forecast_quality.py` and review outliers by state.
4. Define a documented data-quality policy using actual source evidence. Keep raw and quality-filtered analyses distinguishable.
5. Rerun `scripts/evaluate_persistence.py` and record state-level MAE, RMSE, and R2.
6. Implement chronological feature generation using only available variables: lagged groundwater level, rolling statistics, trend, calendar fields, coordinates, and elevation when present.
7. Train Random Forest and XGBoost using chronological train/validation/test splits. Compare both against persistence; do not call a model best without measured metrics.
8. Store model artifacts, feature lists, data periods, state scope, station scope, and metrics.
9. Add SHAP TreeExplainer only after real tree models are trained.
10. Implement deterministic GSS, GBIM, and DIE analytics from actual indicators.
11. Finish PostgreSQL migrations/import, then frontend dashboards, map, authentication, roles, scenarios, and reports.

## Commands after checkout

```powershell
python -m pytest tests -q
python scripts/process_all_states.py --data-root data --output-dir data/processed/all_states
python scripts/audit_forecast_quality.py --input-dir data/processed/all_states --output models/forecast_quality_audit.json
python scripts/evaluate_persistence.py --input-dir data/processed/all_states --output models/persistence_evaluation.json
```

Do not commit raw CSVs, generated processed CSVs, local databases, secrets, or model artifacts unless the team deliberately chooses Git LFS or external artifact storage.