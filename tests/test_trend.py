"""Automated tests for AURORA Statistical Engine."""

import sys
from pathlib import Path

import numpy as np
from scipy.stats import linregress

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.trend import (
    annual_composite,
    ols_trend,
    sen_trend,
    fdr_correction,
)


def test_positive_trend():
    years = np.arange(2001, 2026)
    values = (0.3 + 0.008 * (years - 2001))

    result = ols_trend(values[:, None, None], years)

    np.testing.assert_allclose(
        result["slope"], 0.008, atol=1e-10
    )


def test_negative_trend():
    years = np.arange(2001, 2026)
    values = (0.6 - 0.008 * (years - 2001))

    result = ols_trend(values[:, None, None], years)

    np.testing.assert_allclose(
        result["slope"], -0.008, atol=1e-10
    )


def test_stable_trend():
    years = np.arange(2001, 2026)
    values = np.full((25, 1, 1), 0.5)

    result = ols_trend(values, years)

    np.testing.assert_allclose(
        result["slope"], 0.0, atol=1e-10
    )


def test_missing_years():
    years = np.arange(2001, 2026)
    values = (0.3 + 0.008 * (years - 2001))

    values[[2, 5, 9]] = np.nan

    result = ols_trend(values[:, None, None], years)

    assert result["n"].item() == 22

    np.testing.assert_allclose(
        result["slope"], 0.008, atol=1e-10
    )


def test_insufficient_observations():
    years = np.arange(2001, 2026)
    values = np.full((25, 1, 1), np.nan)

    values[:10] = 0.5

    result = ols_trend(values, years)

    assert np.isnan(result["slope"]).all()


def test_against_scipy():
    rng = np.random.default_rng(42)
    years = np.arange(2001, 2026)

    values = (
        0.4 + 0.008 * (years - 2001)
        + rng.normal(0, 0.02, 25)
    )

    reference = linregress(years, values)
    result = ols_trend(values[:, None, None], years)

    np.testing.assert_allclose(
        result["slope"], reference.slope, atol=1e-10
    )

    np.testing.assert_allclose(
        result["p"], reference.pvalue, atol=1e-10
    )


def test_sen_resistant_to_outlier():
    years = np.arange(2001, 2026)
    values = (0.3 + 0.008 * (years - 2001))

    values[-1] = 0.95

    slope = sen_trend(values[:, None, None], years)

    np.testing.assert_allclose(
        slope, 0.008, atol=1e-10
    )


def test_fdr_correction():
    p = np.array([0.001, 0.01, 0.04, 0.2, np.nan])

    q, significant = fdr_correction(p)

    np.testing.assert_allclose(
        q[:4], [0.004, 0.02, 0.0533333333, 0.2]
    )

    assert significant.sum() == 2
    assert np.isnan(q[-1])


def test_annual_composite():
    dates = np.arange(
        np.datetime64("2001-01"),
        np.datetime64("2003-01"),
        dtype="datetime64[M]"
    )

    X = np.full((24, 1, 1, 1), 0.5)

    X[:3] = np.nan
    X[12:16] = np.nan

    annual, years = annual_composite(X, dates)

    assert annual[0].item() == 0.5
    assert np.isnan(annual[1]).all()
    assert len(years) == 2
