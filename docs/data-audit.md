# AQUA-MIND Data Audit

**Audit date:** 2026-09-19  
**Audit scope:** Repository and `data/raw/` contents  
**Audit status:** Source files found; schema and representative resource audited

## Executive finding

The official-looking telemetry files are currently present directly under `data/`, rather than under the requested `data/raw/` directory. Eleven CSV files were found: two resources for each of the five target states, plus an exact duplicate of the Maharashtra 2026–2030 resource. The duplicate files have matching SHA-256 hashes and must not both be ingested.

The files are approximately 3.3 GB in total, so full field-level aggregates must be computed with streaming tools. No data-dependent ML, analytics, or database implementation has been started.

## Repository inspection

| Area | Result |
|---|---|
| `backend/` | Empty |
| `frontend/` | Empty |
| `data/` | Contains 11 CSV files directly; `data/raw/` is not present |
| `docs/` | Contains this report |
| `models/` | Empty |
| `notebooks/` | Empty |
| `scripts/` | Contains `inspect_data.py` |
| `tests/` | Empty |
| `README.md` | Empty before project implementation |
| `.env.example` | Empty before project implementation |

## Dataset inventory (verified)

| State | Resource files | Approx. size | First-record timestamp | Last-record timestamp | Notes |
|---|---:|---:|---|---|---|
| Andhra Pradesh | 2 | 350 MB | 08-01-2021 03:00 / 24-02-2026 03:00 | 18-09-2025 21:00 / 12-06-2026 03:00 | Same schema |
| Karnataka | 2 | 868 MB | 07-03-2022 00:00 / 01-01-2026 00:00 | 30-12-2025 18:00 / 17-09-2026 18:00 | Same schema |
| Maharashtra | 3 files, 2 unique | 750 MB | 08-01-2023 00:00 / 01-01-2026 00:00 | 22-11-2025 00:00 / 14-09-2026 00:00 | Two 2026 files are exact duplicates |
| Tamil Nadu | 2 | 539 MB | 09-11-2023 13:34 / 01-01-2026 00:00 | 31-12-2025 18:00 / 17-09-2026 18:00 | Sample shows sub-six-hour timestamps in 2021–2025 |
| Telangana | 2 | 461 MB | 28-11-2022 15:47 / 01-01-2026 00:00 | 31-12-2025 18:00 / 17-09-2026 18:00 | Sample shows irregular initial timestamp |

The first and last timestamps above are file endpoint records, not yet claimed as global minimum or maximum timestamps. The ingestion pipeline must calculate `MIN(timestamp)` and `MAX(timestamp)` after parsing every row. A real parser validation on the Andhra Pradesh 2026–2030 file returned 259,916 rows, 404 stations, and an actual range of `2026-01-01 03:00` through `2026-09-17 21:00`.

## Observed schema

All 11 CSV headers currently match exactly and contain 21 columns:

```text
SlNo, Station, Agency, State LGD Code, State, District LGD Code,
District, Tehsil, Block, Village, River, Basin, Tributary, Subtributary,
SubSubtributary, Local River, Latitude, Longitude, RL_MSL,
Data Acquisition Time, Groundwater Level Telemetry 6 Hourly (meter)
```

Verified available fields include station, agency, state and district identifiers, administrative hierarchy, latitude/longitude, optional `RL_MSL`, observation timestamp, and groundwater level in meters. Additional hydrological descriptors are present in the header and must be treated as nullable until their actual population rates are measured.

The source column `Groundwater Level Telemetry 6 Hourly (meter)` must be normalized to `groundwater_level`; `Data Acquisition Time` must be normalized to `timestamp`. The name “6 Hourly” describes the resource label, not a guaranteed interval: the Tamil Nadu sample contains observations at 13:34 and 13:37.

## Important data findings

- The resource period `2026–2030` does not mean the file contains observations through 2030. Verified file endpoints currently reach June–September 2026.
- Forecasting must use the measured latest actual timestamp per station, never a hardcoded 2026 or 2030 boundary.
- Maharashtra `gwl_tel_6_hourly_maharashtra_gw_mh_2026_2030.csv` and `gwl_tel_6_hourly_maharashtra_gw_mh_2026_2030 (1).csv` are exact duplicates by SHA-256 and only one may be ingested.
- State resources are not equivalent in their actual start dates or sampling behavior.
- The validated Andhra Pradesh 2026–2030 resource contains 164,124 six-hour intervals, 88,261 three-minute intervals, and additional zero, three-, six-, twelve-, eighteen-, and twenty-four-hour gaps in the parsed station sequence. The resource label must therefore never be treated as a guaranteed sampling frequency.
- The files are stored in `data/` today. The normalizer will support this current location and the intended recursive `data/raw/` layout; raw files will remain unmodified.

## Required next input

Place the official downloaded files in the following structure, without changing the raw files:

```text
data/raw/
  Telangana/
    telemetry_2021_2025.csv
    telemetry_2026_2030.csv
  Andhra_Pradesh/
    telemetry_2021_2025.csv
    telemetry_2026_2030.csv
  Karnataka/
    telemetry_2021_2025.csv
    telemetry_2026_2030.csv
  Tamil_Nadu/
    telemetry_2021_2025.csv
    telemetry_2026_2030.csv
  Maharashtra/
    telemetry_2021_2025.csv
    telemetry_2026_2030.csv
```

The expected names are conventions only. The audit script discovers all CSV files recursively and reports the actual file names, schemas, and observation timestamps.

## Audit method

Run:

```text
python scripts/inspect_data.py
```

The script scans `data/raw/` when it exists, otherwise the current `data/` location. It detects a likely encoding and delimiter, and reports:

- file inventory and byte size
- headers and inferred value types
- row count and missing values
- timestamp candidates and observed range
- station candidates and station counts
- duplicate rows and station/timestamp duplicates in a bounded first-100,000-row sample
- coordinate validity
- groundwater value validity and observed range
- common observation intervals and gaps
- state/district coverage
- schema differences across files

It never writes to, renames, or overwrites source files. Re-run it after any source update and attach its JSON output to the audit process before beginning normalization or ML work.

## Data-dependent implementation decision

The following remain intentionally unimplemented until full per-file aggregate measurements have been produced for the selected MVP source:

- canonical column mapping
- normalized observations
- station registry
- PostgreSQL schema populated from source data
- forecasting features and model evaluation
- SHAP explanations
- GSS, GBIM, and DIE outputs

## Analytical indicator audit (STEP 7)

The implemented GSS, GBIM, and DIE services are deterministic and versioned
(`1.0.0` by default). They use only parsed groundwater level and timestamp
values, with station coordinates, elevation, and administrative station
information retained as context. A configurable minimum observation count
prevents scores for insufficient series. Trend, volatility, and step-change
thresholds can be set with `AQUA_ANALYTICS_MIN_OBSERVATIONS`,
`AQUA_ANALYTICS_DECLINE_SLOPE_M_PER_DAY`, `AQUA_ANALYTICS_VOLATILITY_M`, and
`AQUA_ANALYTICS_JUMP_M`; `AQUA_ANALYTICS_VERSION` identifies the calculation
contract. These are descriptive AQUA-MIND indicators, not official standards,
causal explanations, or extraction orders. Run the reproducible batch with
`python scripts/run_analytics.py <normalized.csv> --output <report.json>`.

This prevents fabricated measurements, timestamps, metrics, explanations, and recommendations.