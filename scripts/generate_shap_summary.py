"""Generate a global mean-absolute Tree SHAP summary from a feature matrix.

The script is intentionally input-driven so it never invents environmental
variables or silently retrains a model.  Example:
    python scripts/generate_shap_summary.py --features data/features.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.ml.shap_explainer import FEATURE_DISPLAY_NAMES, FEATURE_NAMES, _tree_explainer
from backend.app.ml.forecast_service import load_ml_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--model", choices=("random_forest", "xgboost"), default="xgboost")
    parser.add_argument("--output", type=Path, default=Path("models/shap_summary.json"))
    parser.add_argument("--max-rows", type=int, default=10000)
    args = parser.parse_args()
    frame = pd.read_csv(args.features, usecols=list(FEATURE_NAMES), nrows=args.max_rows)
    values = frame.to_numpy(dtype=np.float32)
    if args.model == "random_forest":
        values = np.nan_to_num(values, nan=0.0)
    model = load_ml_model(args.model)
    shap_values = np.asarray(_tree_explainer(model).shap_values(values), dtype=float)
    if shap_values.ndim == 3:
        shap_values = shap_values[:, :, 0]
    means = np.mean(np.abs(shap_values), axis=0)
    ranking = sorted(
        ({"feature": name, "display_name": FEATURE_DISPLAY_NAMES[name],
          "mean_abs_shap": round(float(score), 8)}
         for name, score in zip(FEATURE_NAMES, means)),
        key=lambda item: (-item["mean_abs_shap"], item["feature"]),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"model_name": args.model, "rows": len(values), "features": ranking}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
