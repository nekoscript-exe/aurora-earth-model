"""AURORA historical satellite trend analysis."""

import argparse
import json
import sys
import subprocess

from pathlib import Path
from time import perf_counter

import numpy as np
import rasterio

from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.trend import (
    annual_composite,
    ols_trend,
    sen_trend,
    fdr_correction,
    residual_diagnostics,
    hac_significance
)


def write_raster(path, values, grid, region):

    nodata = -9999.0

    values = np.where(
        region & np.isfinite(values),
        values,
        nodata
    ).astype(np.float32)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=grid["height"],
        width=grid["width"],
        count=1,
        dtype="float32",
        crs=grid["crs"],
        transform=Affine(*grid["transform"][:6]),
        nodata=nodata,
        compress="deflate"
    ) as dst:
        dst.write(values, 1)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--cube", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    start = perf_counter()

    with np.load(args.cube, allow_pickle=False) as data:
        X = data["X"]
        valid = data["valid"]
        dates = data["dates"]
        region = data["region_mask"]
        channels = data["channels"]

    with open(args.metadata) as f:
        metadata = json.load(f)

    grid = metadata["grid"]

    variable = str(channels[0])

    if metadata.get("variable", variable) != variable:
        raise ValueError("Cube variable does not match metadata")

    unit = metadata.get("unit", "1")
    slope_unit = metadata.get("slope_unit", f"{variable}/year")

    if not np.array_equal(valid, np.isfinite(X)):
        raise ValueError("Invalid cube mask")

    if not np.all(
        np.diff(dates.astype("datetime64[M]")).astype(int) == 1
    ):
        raise ValueError("Invalid monthly calendar")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    print("Building annual composites...", flush=True)

    annual, years = annual_composite(
        X, dates, min_months=9
    )

    if len(years) < 15:
        raise ValueError("At least 15 years required")

    print("Calculating OLS...", flush=True)
    ols = ols_trend(annual, years)

    print("Calculating Theil-Sen...", flush=True)
    sen = sen_trend(annual, years)

    q, significant = fdr_correction(ols["p"])

    print("Temporal diagnostics...", flush=True)
    diagnostics = residual_diagnostics(
        annual, years, ols
    )

    print("HAC sensitivity analysis...", flush=True)
    hac = hac_significance(annual, years)

    q_hac, sig_hac = fdr_correction(hac["p_hac"])

    coverage = valid[..., 0].mean(axis=0)

    eligible = region & np.isfinite(ols["slope"])
    tested = eligible & np.isfinite(q)

    significant &= tested

    positive = significant & (ols["slope"] > 0)
    negative = significant & (ols["slope"] < 0)

    rasters = {
        "trend_slope": ols["slope"],
        "trend_sen": sen,
        "trend_p": ols["p"],
        "trend_q": q,
        "trend_change": ols["change"],
        "trend_n": ols["n"],
        "trend_significant": np.where(
            tested, significant.astype(float), np.nan
        ),
        "trend_lag1": diagnostics["lag1"],
        "trend_hac_q": q_hac,
        "coverage": coverage
    }

    print("Exporting GeoTIFF results...", flush=True)

    for name, values in rasters.items():
        write_raster(
            output / f"{name}.tif",
            values,
            grid,
            region
        )

    n_region = int(region.sum())
    n_tested = int(tested.sum())

    metrics = {
        "dataset": metadata["dataset"],
        "variable": variable,
        "unit": unit,
        "slope_unit": slope_unit,
        "period": [str(dates[0]), str(dates[-1])],
        "months": len(dates),
        "regional_pixels": n_region,
        "eligible_pixels": int(eligible.sum()),
        "tested_pixels": n_tested,
        "mean_temporal_coverage": float(
            coverage[region].mean()
        ),
        "significant_increase": int(positive.sum()),
        "significant_decrease": int(negative.sum()),
        "not_significant": int(
            (tested & ~significant).sum()
        ),
        "not_tested": int((region & ~tested).sum()),
        "mean_slope": (
            float(np.mean(ols["slope"][eligible]))
            if eligible.any() else None
        ),
        "hac_tested_pixels": int(np.isfinite(q_hac).sum()),
        "hac_significant_pixels": int(sig_hac.sum()),
        "seconds": perf_counter() - start
    }

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True
    ).stdout.strip()

    run_metadata = {
        "source": metadata["source"],
        "grid": grid,
        "period": metrics["period"],
        "primary_method": "OLS",
        "secondary_method": "Theil-Sen",
        "annual_min_months": 9,
        "minimum_valid_years": 15,
        "multiple_testing": "Benjamini-Hochberg",
        "alpha": 0.05,
        "hac_maxlags": 2,
        "hac_role": "sensitivity_analysis",
        "variable": variable,
        "unit": unit,
        "slope_unit": slope_unit,
        "significance_warning": (
            "Temporal dependence may inflate false positives. "
            "HAC is exploratory and does not guarantee calibration."
        ),
        "commit": commit
    }

    for name, report in [
        ("metrics.json", metrics),
        ("run_metadata.json", run_metadata)
    ]:
        with open(output / name, "w") as f:
            json.dump(report, f, indent=4)

    print("=" * 60)
    print("AURORA | HISTORICAL TREND ANALYSIS")
    print(json.dumps(metrics, indent=4))
    print("=" * 60)


if __name__ == "__main__":
    main()
