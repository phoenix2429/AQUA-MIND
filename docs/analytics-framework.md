# AQUA-MIND analytics framework

GSS (Groundwater Stability Score), GBIM (Groundwater Behaviour Intelligence
Model), and DIE (Decision Intelligence Engine) are deterministic,
versioned, descriptive indicators. They use only `groundwater_level`,
`timestamp`, station `latitude`, `longitude`, `elevation_msl`, and station
information. Coordinates and elevation are retained as context; they are not
used to invent hydrological variables.

## Outputs

- **GSS** is a 0–100 stability score combining level trend, population
  variability, and maximum observed step change.
- **GBIM** reports one of `STABLE`, `DECLINING`, `RISING`, `VOLATILE`, or
  `INSUFFICIENT_DATA`.
- **DIE** returns exact priorities `HIGH`, `MEDIUM`, or `LOW` and a cautious
  monitoring recommendation. Insufficient data uses `LOW` and explicitly
  requests more observations.

The default minimum is 10 valid observations. Thresholds and the output
version are configurable with `AQUA_ANALYTICS_*` environment variables. A
series below the minimum receives no GSS/GBIM score. No output identifies a
cause, proves sustainability, or prescribes extraction; these are
AQUA-MIND decision-support indicators rather than official standards.

## Interfaces

For a station, the API exposes `/api/stations/{station_id}/sustainability`,
`/behavior`, `/recommendations`, and `/analytics`. Historical aliases
`/gss`, `/gbim`, and `/die` remain available. Batch computation defaults to:

```powershell
python scripts/compute_analytics.py
python scripts/compute_analytics.py --state Telangana --output models/telangana-analytics.json
```

The batch report includes `stations_processed`, `successful`, `insufficient`,
and `failed` audit counts. It also persists GSS and GBIM rows in
`analytical_results` and DIE recommendations in `recommendations` for station
records present in the configured database.
