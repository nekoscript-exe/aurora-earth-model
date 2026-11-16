"""Evaluate AURORA statistical trend estimators."""

from pathlib import Path
from time import perf_counter
import sys
import json

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.trend import (
    annual_composite,
    ols_trend,
    sen_trend,
    fdr_correction
)


def metrics(prediction, truth):
    error = prediction - truth

    return {
        "mae": float(np.nanmean(np.abs(error))),
        "rmse": float(np.sqrt(np.nanmean(error**2)))
    }


def main():
    with np.load(ROOT / "data/synthetic/cube.npz") as data:
        annual, years = annual_composite(
            data["X"], data["dates"]
        )
        truth = data["true_slope"]

    start = perf_counter()
    ols = ols_trend(annual, years)
    ols_time = perf_counter() - start

    start = perf_counter()
    sen = sen_trend(annual, years)
    sen_time = perf_counter() - start

    q, significant = fdr_correction(ols["p"])

    stable = truth == 0
    changing = truth != 0

    detected = significant & changing
    false_positive = significant & stable

    tp = int(detected.sum())
    fp = int(false_positive.sum())

    report = {
        "dataset": "synthetic",
        "alpha": 0.05,
        "ols": {
            **metrics(ols["slope"], truth),
            "seconds": ols_time
        },
        "sen": {
            **metrics(sen, truth),
            "seconds": sen_time
        },
        "significance": {
            "nominal_significant": int(
                (ols["p"] < 0.05).sum()
            ),
            "fdr_significant": int(significant.sum()),
            "true_positives": tp,
            "false_positives": fp,
            "recall": float(tp / changing.sum()),
            "false_positive_rate": float(
                fp / stable.sum()
            ),
            "false_discovery_proportion": (
                fp / (tp + fp) if tp + fp else 0.0
            )
        }
    }

    output = ROOT / "outputs/synthetic"
    output.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output / "trend_comparison.npz",
        **ols,
        sen_slope=sen,
        q=q,
        significant=significant,
        true_slope=truth
    )

    with open(output / "trend_metrics.json", "w") as f:
        json.dump(report, f, indent=4)

    print("=" * 55)
    print("AURORA | TREND EVALUATION")
    print("=" * 55)
    print(json.dumps(report, indent=4))
    print("=" * 55)


if __name__ == "__main__":
    main()
