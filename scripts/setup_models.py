"""Verify or deterministically build the AQUA-MIND ML artifacts.

Default mode verifies existing ``models/random_forest`` and ``models/xgboost``
artifacts.  ``--train`` invokes the checked-in training pipeline using the
processed data; no downloaded, synthetic, or placeholder models are created.
Use ``--sample-frac`` only for a clearly labelled development build.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.forecast_service import load_ml_model


def verify_models(model_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in ("random_forest", "xgboost"):
        artifact_dir = model_dir / name
        required = ("model.joblib", "feature_schema.json", "metadata.json")
        missing = [item for item in required if not (artifact_dir / item).is_file()]
        if missing:
            raise FileNotFoundError(f"{name} artifact is incomplete: missing {', '.join(missing)}")
        schema = json.loads((artifact_dir / "feature_schema.json").read_text(encoding="utf-8"))
        features = schema.get("feature_names")
        if not isinstance(features, list) or not features:
            raise ValueError(f"{name} feature_schema.json has no feature_names")
        model = load_ml_model(name, model_dir)
        prediction = np.asarray(model.predict(np.zeros((1, len(features)), dtype=np.float32)))
        if prediction.shape != (1,) or not np.isfinite(prediction[0]):
            raise ValueError(f"{name} artifact failed finite prediction verification")
        result[name] = "verified"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--train", action="store_true",
                        help="run scripts/train_models.py before verification")
    parser.add_argument("--sample-frac", type=float, default=1.0,
                        help="training fraction (only with --train; deterministic seed 42)")
    args = parser.parse_args()
    model_dir = args.model_dir.resolve()
    if args.train:
        if not 0 < args.sample_frac <= 1:
            parser.error("--sample-frac must be in (0, 1]")
        command = [
            sys.executable, str(ROOT / "scripts" / "train_models.py"),
            "--model-dir", str(model_dir),
            "--output", str(model_dir / "model_evaluation.json"),
            "--sample-frac", str(args.sample_frac),
        ]
        subprocess.run(command, check=True, cwd=ROOT)
    print(verify_models(model_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
