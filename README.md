# AQUA-MIND

**Explainable Groundwater Decision Intelligence Platform Using Groundwater Telemetry Data**

AQUA-MIND converts official NWDP groundwater telemetry into a reproducible pipeline for station discovery, historical analysis, forecasting, explainability, sustainability scoring, behavior intelligence, and analytical recommendations.

## Current checkpoint

Phase 0 and the first Phase 1/2 slices are implemented:

- Official telemetry files are stored under `data/` and are never modified.
- All supplied CSVs currently expose the same 21-column source schema.
- All five selected states are now processed through the same generalized pipeline.
- Ten unique official resources were normalized; the exact duplicate Maharashtra resource was skipped.
- The unified normalized dataset contains 21,660,687 accepted observations and 5,426 stations.
- Per-resource reports and the comparative audit are in `data/processed/all_states/`.
- A unified PostgreSQL load is the production target. The 21.6M-row local SQLite import is not claimed complete because index maintenance is too slow in this environment; the prior Telangana-only SQLite file is preserved separately.
- Duplicate station/timestamp rows are rejected during normalization.
- Timestamps are parsed from the source values; resource names are never treated as observation dates.
- The data audit is documented in [docs/data-audit.md](docs/data-audit.md).

The current database defaults to local SQLite for development. PostgreSQL is supported through `DATABASE_URL`; credentials must be supplied through environment variables.

## Reproducible commands

Create the local schema:

```powershell
python -m backend.app.database.init_db
```

Normalize an official source file:

```powershell
python scripts/normalize_data.py data/gwl_tel_6_hourly_telangana_gw_ts_2026_2030.csv
```

Build the station registry:

```powershell
python scripts/build_station_registry.py data/processed/gwl_tel_6_hourly_telangana_gw_ts_2026_2030.normalized.csv
```

Load canonical data into the configured database:

```powershell
python scripts/load_database.py data/processed/gwl_tel_6_hourly_telangana_gw_ts_2026_2030.normalized.csv data/processed/stations.csv
```

Run tests:

```powershell
python -m pytest tests -q
```

Train ML models (Random Forest & XGBoost with Persistence comparison):

```powershell
# Dev/sample run (5% per station)
python scripts/train_models.py --sample-frac 0.05

# Full run (all 5 states)
python scripts/train_models.py
```

Run the backend API locally:

```powershell
python -m uvicorn backend.app.main:app --reload --port 8001
```

The current read-only API includes:

- `GET /health`
- `GET /api/states`
- `GET /api/states/{state}/districts`
- `GET /api/stations?state=&district=&page=&page_size=`
- `GET /api/stations/{station_id}`
- `GET /api/stations/{station_id}/observations?page=&page_size=&start=&end=`
- `GET /api/stations/{station_id}/history?start=&end=&buckets=`
- `GET /api/stations/{station_id}/forecast?horizon_points=&model=` (`persistence` [default], `random_forest`, `xgboost`)
- `GET /api/stations/nearby?latitude=&longitude=&radius_km=&limit=`
- `GET /api/models` (model listing, deployment status, and test evaluation metrics)

Interactive API documentation is available at `http://127.0.0.1:8001/docs` while the server is running.

## Data integrity rules

- Raw files are immutable inputs.
- Actual observation timestamps determine the latest available observation.
- Forecasting must begin after the latest actual timestamp, never after a hardcoded resource boundary.
- Unavailable variables such as rainfall, extraction, aquifer type, or temperature are not fabricated.
- GSS, GBIM, and recommendations will be explicitly labeled as AQUA-MIND analytical outputs, not official government standards or orders.
