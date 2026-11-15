"""AURORA regional time series engine."""

import argparse
import csv
import json

from pathlib import Path

import numpy as np
from scipy.stats import linregress, t


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--cube", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    with np.load(args.cube, allow_pickle=False) as data:

        X = data["X"][..., 0]
        dates = data["dates"]
        region = (
            data["region_mask"]
            if "region_mask" in data.files
            else np.ones(X.shape[1:], dtype=bool)
        )
        variable = str(data["channels"][0])

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    monthly = []
    annual = []

    for i, date in enumerate(dates):

        values = X[i][region]
        values = values[np.isfinite(values)]

        coverage = len(values) / region.sum()

        monthly.append({
            "date": str(date),
            "variable": variable,
            "mean": float(values.mean()) if values.size else None,
            "median": float(np.median(values)) if values.size else None,
            "std": float(values.std()) if values.size else None,
            "valid_pixels": int(values.size),
            "coverage": float(coverage)
        })

    for year in sorted({row["date"][:4] for row in monthly}):

        rows = [
            row for row in monthly
            if row["date"].startswith(year)
            and row["coverage"] >= 0.70
            and row["mean"] is not None
        ]

        annual.append({
            "year": int(year),
            "mean": (
                float(np.mean([r["mean"] for r in rows]))
                if len(rows) >= 9 else None
            ),
            "valid_months": len(rows)
        })

    eligible = [
        row for row in annual
        if row["mean"] is not None
    ]

    trend = None

    if len(eligible) >= 15:

        years = np.array([r["year"] for r in eligible])
        values = np.array([r["mean"] for r in eligible])

        if np.ptp(values) > 0:

            fit = linregress(years, values)

            critical = t.ppf(
                0.975, len(years) - 2
            )

            trend = {
                "slope_per_year": float(fit.slope),
                "slope_per_decade": float(fit.slope * 10),
                "estimated_change": float(
                    fit.slope * (years[-1] - years[0])
                ),
                "p_value": float(fit.pvalue),
                "r_squared": float(fit.rvalue**2),
                "confidence_interval_95": [
                    float(fit.slope - critical * fit.stderr),
                    float(fit.slope + critical * fit.stderr)
                ],
                "years_used": len(years),
                "period": [int(years[0]), int(years[-1])]
            }

    for name, rows in [
        ("monthly_series.csv", monthly),
        ("annual_series.csv", annual)
    ]:

        with open(output / name, "w", newline="") as f:

            writer = csv.DictWriter(
                f, fieldnames=list(rows[0])
            )

            writer.writeheader()
            writer.writerows(rows)

    report = {
        "variable": variable,
        "months": len(monthly),
        "eligible_years": len(eligible),
        "minimum_monthly_coverage": 0.70,
        "minimum_valid_months": 9,
        "minimum_valid_years": 15,
        "trend": trend,
        "limitations": [
            "Unweighted regional pixel means.",
            "Observed spatial composition may vary over time.",
            "OLS p-values and intervals are nominal.",
            "Temporal dependence may inflate significance."
        ]
    }

    (output / "regional_trend.json").write_text(
        json.dumps(report, indent=4, allow_nan=False)
    )

    print(json.dumps(report, indent=4))
    print("REGIONAL TIME SERIES: COMPLETED")


if __name__ == "__main__":
    main()
