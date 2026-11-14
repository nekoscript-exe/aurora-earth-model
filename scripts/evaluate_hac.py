"""AURORA HAC significance sensitivity analysis."""

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
    hac_significance,
    fdr_correction
)

start = perf_counter()

with np.load(ROOT / "data/synthetic/cube.npz") as data:
    annual, years = annual_composite(
        data["X"], data["dates"]
    )
    truth = data["true_slope"]

ols = ols_trend(annual, years)
hac = hac_significance(annual, years)

common = (
    np.isfinite(ols["p"])
    & np.isfinite(hac["p_hac"])
)

q_ols, sig_ols = fdr_correction(
    np.where(common, ols["p"], np.nan)
)

q_hac, sig_hac = fdr_correction(
    np.where(common, hac["p_hac"], np.nan)
)


def summarize(significant):
    tp = int((significant & (truth != 0)).sum())
    fp = int((significant & (truth == 0)).sum())

    changing = int((common & (truth != 0)).sum())
    stable = int((common & (truth == 0)).sum())

    return {
        "significant": int(significant.sum()),
        "true_positives": tp,
        "false_positives": fp,
        "recall": tp / changing if changing else None,
        "false_positive_rate": fp / stable if stable else None,
        "false_discovery_proportion":
            fp / (tp + fp) if tp + fp else None
    }


report = {
    "dataset": "synthetic",
    "method": "Newey-West HAC",
    "maxlags": 2,
    "alpha": 0.05,
    "comparable_pixels": int(common.sum()),
    "excluded_pixels": int((~common).sum()),
    "ols_fdr": summarize(sig_ols),
    "hac_fdr": summarize(sig_hac),
    "lost_significance": int((sig_ols & ~sig_hac).sum()),
    "gained_significance": int((~sig_ols & sig_hac).sum()),
    "seconds": perf_counter() - start
}

output = ROOT / "outputs/synthetic"
output.mkdir(parents=True, exist_ok=True)

np.savez_compressed(
    output / "trend_hac.npz",
    **hac,
    q_ols=q_ols,
    q_hac=q_hac,
    significant_ols=sig_ols,
    significant_hac=sig_hac,
    comparable=common
)

with open(output / "hac_metrics.json", "w") as f:
    json.dump(report, f, indent=4)

print("=" * 55)
print("AURORA | HAC SENSITIVITY ANALYSIS")
print("=" * 55)
print(json.dumps(report, indent=4))
print("=" * 55)
