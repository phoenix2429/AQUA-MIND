# Kaggle data setup

The raw telemetry and generated processed artifacts are intentionally excluded
from Git. They are published together in [`pindiavinash/aqua-mind`](https://www.kaggle.com/datasets/pindiavinash/aqua-mind).

## Setup

Install the Kaggle CLI and authenticate using Kaggle's normal mechanism
(environment variables or a user-level `kaggle.json`; never commit either):

```powershell
pip install kaggle
kaggle datasets files pindiavinash/aqua-mind
python scripts/setup_kaggle_data.py
```

The command downloads only when the complete local dataset is not already
present. It safely extracts the archive and copies only `raw/` and
`processed/` into the existing `data/` layout. It does not normalize, filter,
regenerate, or otherwise modify the ML pipeline outputs.

Use a different checkout or a disposable test directory with
`--target-dir C:\path\to\checkout`. Use `--dry-run` to report missing files
without contacting Kaggle. A non-zero exit code means the data is incomplete,
the CLI/authentication is unavailable, the archive is unsafe, or validation
failed.

## Validation

Validation checks all ten raw files (five states × two periods), normalized and
quality-filtered CSV headers, ten per-resource statistics/reports, and the
five-state and quality-filter summaries. The script reports every missing or
malformed path explicitly. Raw and processed CSV/JSON files remain covered by
`.gitignore`.

The repository's current working copy was checked on 2026-09-22. The Kaggle
CLI was not installed in that environment, so a live listing/download could
not be performed; authentication and dataset accessibility must be verified
on the machine running setup.
