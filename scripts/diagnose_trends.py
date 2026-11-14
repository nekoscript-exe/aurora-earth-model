"""AURORA temporal residual diagnostics."""

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.trend import (
    annual_composite,
    ols_trend,
    residual_diagnostics
)

with np.load(ROOT / "data/synthetic/cube.npz") as data:
    annual, years = annual_composite(
        data["X"], data["dates"]
    )

ols = ols_trend(annual, years)
result = residual_diagnostics(annual, years, ols)

rho = result["lag1"]
dw = result["durbin_watson"]

valid = np.isfinite(rho)

print("=" * 55)
print("AURORA | TEMPORAL DIAGNOSTICS")
print("=" * 55)
print("Valid diagnostics:", valid.sum())
print("Mean lag-1:", np.nanmean(rho))
print("Median lag-1:", np.nanmedian(rho))
print("Mean Durbin-Watson:", np.nanmean(dw))
print("Pixels with |rho| > 0.3:",
      (np.abs(rho) > 0.3).sum())
print("Percentage flagged:",
      100 * (np.abs(rho) > 0.3).sum() / valid.sum())
print("=" * 55)

np.savez_compressed(
    ROOT / "outputs/synthetic/diagnostics.npz",
    **result
)
