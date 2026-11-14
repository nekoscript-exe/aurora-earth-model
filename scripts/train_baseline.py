"""AURORA OLS baseline evaluation."""

from pathlib import Path
from time import perf_counter
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.trend import annual_composite, ols_trend


def main():
    start = perf_counter()

    with np.load(ROOT / "data/synthetic/cube.npz") as data:
        X = data["X"]
        dates = data["dates"]
        truth = data["true_slope"]

    annual, years = annual_composite(X, dates)
    result = ols_trend(annual, years)

    slope = result["slope"]
    error = slope - truth

    mae = np.nanmean(np.abs(error))
    rmse = np.sqrt(np.nanmean(error**2))

    output = ROOT / "outputs/synthetic"
    output.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output / "trend_ols.npz",
        **result,
        true_slope=truth
    )

    elapsed = perf_counter() - start

    print("=" * 55)
    print("AURORA | STATISTICAL TREND ENGINE")
    print("=" * 55)
    print("Method: Ordinary Least Squares")
    print("Dataset: SYNTHETIC")
    print("Annual cube:", annual.shape)
    print("Pixels:", slope.size)
    print("Valid regressions:", np.isfinite(slope).sum())
    print("Mean absolute error:", mae)
    print("Root mean squared error:", rmse)
    print("Mean R2:", np.nanmean(result["r2"]))
    print("Execution time:", round(elapsed, 4), "seconds")
    print("Output:", output / "trend_ols.npz")
    print("=" * 55)


if __name__ == "__main__":
    main()
