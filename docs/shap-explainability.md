# Tree SHAP explainability

`GET /api/stations/{station_id}/explanation?model=xgboost` (and the `/shap`
alias) returns a local Tree SHAP explanation for the latest station feature
row. `random_forest` and `xgboost` are supported; the persistence baseline is
not a tree model and is rejected.

The explanation uses the exact 16-column order saved in each model's
`feature_schema.json`. Results include the model prediction, expected model
value, signed feature contributions, deterministic absolute-impact ranking, and
an additivity error check. A positive contribution means the feature moved the
model output upward relative to its baseline; it is not a causal claim.

SHAP is an optional runtime dependency in deployments that do not serve the
explanation endpoints. Missing model artifacts or SHAP return HTTP 503 rather
than a fabricated response. The in-process cache is bounded and keyed by
station, model, and latest observation timestamp.

For a global ranking, provide a CSV containing all 16 feature columns:

```bash
python scripts/generate_shap_summary.py --features data/features.csv \
  --model xgboost --output models/shap_summary.json
```
