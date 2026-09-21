"""Shared evaluation utilities for AQUA-MIND ML models.

Computes MAE, RMSE, and R² for any combination of actual/predicted arrays,
and aggregates per-state / per-station breakdowns.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Sequence


def mae(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean Absolute Error."""
    n = len(actual)
    if n == 0:
        return float("nan")
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / n


def rmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Root Mean Squared Error."""
    n = len(actual)
    if n == 0:
        return float("nan")
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / n)


def r2(actual: Sequence[float], predicted: Sequence[float]) -> float | None:
    """Coefficient of determination R².

    Returns None when variance of actuals is zero (constant series).
    """
    n = len(actual)
    if n == 0:
        return None
    mean_a = sum(actual) / n
    ss_tot = sum((a - mean_a) ** 2 for a in actual)
    if ss_tot < 1e-10:
        return None
    ss_res = sum((a - p) ** 2 for a, p in zip(actual, predicted))
    return 1.0 - ss_res / ss_tot


def compute_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float | None]:
    """Return a dict with n, mae, rmse, r2 for a set of predictions."""
    return {
        "n": len(actual),
        "mae": round(mae(actual, predicted), 6) if actual else None,
        "rmse": round(rmse(actual, predicted), 6) if actual else None,
        "r2": (lambda v: round(v, 6) if v is not None else None)(r2(actual, predicted)),
    }


def aggregate_by_group(
    actuals: list[float],
    predictions: list[float],
    groups: list[str],
) -> dict[str, dict[str, float | None]]:
    """Compute metrics per group (e.g. per state or per station).

    Parameters
    ----------
    actuals : list of float
    predictions : list of float
    groups : list of str — group label for each sample (same length as actuals)

    Returns
    -------
    dict mapping group_name → metrics_dict
    """
    buckets: dict[str, tuple[list[float], list[float]]] = defaultdict(lambda: ([], []))
    for a, p, g in zip(actuals, predictions, groups):
        buckets[g][0].append(a)
        buckets[g][1].append(p)
    return {g: compute_metrics(a_list, p_list) for g, (a_list, p_list) in sorted(buckets.items())}
