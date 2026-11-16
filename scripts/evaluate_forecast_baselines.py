"""AURORA forecasting baseline evaluation."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.models.baseline import (
    temporal_split,
    fit_climatology,
    predict_baselines,
    regression_metrics
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cube",
        default="data/synthetic/cube.npz"
    )
    parser.add_argument(
        "--output",
        default="outputs/synthetic/forecast_baselines.json"
    )

    args = parser.parse_args()

    with np.load(args.cube, allow_pickle=False) as data:
        X = data["X"]
        dates = data["dates"].astype("datetime64[M]")

    if not np.all(np.diff(dates).astype(int) == 1):
        raise ValueError("Monthly calendar must be consecutive")

    splits = temporal_split(dates)

    if any(len(v) == 0 for v in splits.values()):
        raise ValueError("Insufficient historical data")

    climate = fit_climatology(
        X, dates, splits["train"]
    )

    report = {
        "cube": args.cube,
        "history_months": 12,
        "forecast_horizon": 1,
        "splits": {
            name: {
                "months": int(len(idx)),
                "start": str(dates[idx[0]]),
                "end": str(dates[idx[-1]])
            }
            for name, idx in splits.items()
        },
        "results": {}
    }

    indices = splits["validation"]
    actual = X[indices]

    predictions = predict_baselines(
        X, dates, indices, climate
    )

    common = np.isfinite(actual)

    for predicted in predictions.values():
        common &= np.isfinite(predicted)

    report["results"]["validation"] = {
        name: regression_metrics(
            actual, predicted, common
        )
        for name, predicted in predictions.items()
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        json.dump(report, f, indent=4)

    print("=" * 60)
    print("AURORA | FORECAST BASELINES")
    print("=" * 60)
    print(json.dumps(report, indent=4))
    print("=" * 60)


if __name__ == "__main__":
    main()
