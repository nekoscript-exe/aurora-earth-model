"""AURORA statistical robustness under temporal dependence."""

import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.trend import (
    ols_trend,
    hac_significance,
    fdr_correction
)


def main():

    rng = np.random.default_rng(42)

    years = np.arange(2001, 2026)
    height, width = 64, 64

    alpha = 0.05
    results = []

    start = perf_counter()

    for rho in [0.0, 0.3, 0.6, 0.9]:

        noise = np.empty(
            (len(years), height, width)
        )

        noise[0] = rng.normal(
            0, 0.03, (height, width)
        )

        for t in range(1, len(years)):

            innovation = rng.normal(
                0,
                0.03 * np.sqrt(1 - rho**2),
                (height, width)
            )

            noise[t] = (
                rho * noise[t - 1]
                + innovation
            )

        values = 0.5 + noise

        ols = ols_trend(values, years)

        hac = hac_significance(
            values, years, maxlags=2
        )

        p_ols = ols["p"]
        p_hac = hac["p_hac"]

        _, sig_ols = fdr_correction(
            p_ols, alpha=alpha
        )

        _, sig_hac = fdr_correction(
            p_hac, alpha=alpha
        )

        record = {
            "rho": rho,
            "pixels": height * width,
            "ols_nominal_false_positive_rate": float(
                (p_ols < alpha).mean()
            ),
            "hac_nominal_false_positive_rate": float(
                (p_hac < alpha).mean()
            ),
            "ols_fdr_false_discoveries": int(
                sig_ols.sum()
            ),
            "hac_fdr_false_discoveries": int(
                sig_hac.sum()
            )
        }

        results.append(record)

        print(
            json.dumps(record, indent=4),
            flush=True
        )

    report = {
        "experiment": "AR1 stationary null simulation",
        "true_slope": 0,
        "seed": 42,
        "years": 25,
        "alpha": alpha,
        "results": results,
        "seconds": perf_counter() - start
    }

    output = Path(
        "docs/evidence/model/statistical_stress_test.json"
    )

    output.write_text(json.dumps(report, indent=4))

    print("STATISTICAL STRESS TEST: COMPLETED")


if __name__ == "__main__":
    main()
