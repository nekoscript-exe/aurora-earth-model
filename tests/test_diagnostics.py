"""AURORA temporal diagnostics and HAC tests."""

import sys
from pathlib import Path

import numpy as np
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.trend import (
    ols_trend,
    residual_diagnostics,
    hac_significance
)


def generate_series(rho=0.0):

    rng = np.random.default_rng(42)

    years = np.arange(2001, 2026)

    noise = rng.normal(0, 0.015, len(years))

    for i in range(1, len(noise)):
        noise[i] += rho * noise[i - 1]

    series = (
        0.35
        + 0.008 * (years - years[0])
        + noise
    )

    return series[:, None, None], years


def test_diagnostics_against_numpy():

    values, years = generate_series(rho=0.7)

    result = ols_trend(values, years)

    diagnostics = residual_diagnostics(
        values, years, result
    )

    predicted = (
        result["intercept"][0, 0]
        + result["slope"][0, 0]
        * (years - years[0])
    )

    residual = values[:, 0, 0] - predicted

    expected = np.corrcoef(
        residual[:-1], residual[1:]
    )[0, 1]

    np.testing.assert_allclose(
        diagnostics["lag1"][0, 0],
        expected,
        atol=1e-10
    )


def test_durbin_watson():

    values, years = generate_series()

    result = ols_trend(values, years)

    diagnostics = residual_diagnostics(
        values, years, result
    )

    predicted = (
        result["intercept"][0, 0]
        + result["slope"][0, 0]
        * (years - years[0])
    )

    residual = values[:, 0, 0] - predicted

    expected = (
        np.sum(np.diff(residual)**2)
        / np.sum(residual**2)
    )

    np.testing.assert_allclose(
        diagnostics["durbin_watson"][0, 0],
        expected,
        atol=1e-10
    )


def test_hac_against_statsmodels():

    values, years = generate_series(rho=0.7)

    result = hac_significance(
        values, years, maxlags=2
    )

    design = sm.add_constant(years - years[0])

    reference = sm.OLS(
        values[:, 0, 0], design
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags": 2,
            "use_correction": True
        },
        use_t=True
    )

    np.testing.assert_allclose(
        result["p_hac"][0, 0],
        reference.pvalues[1]
    )

    np.testing.assert_allclose(
        result["stderr_hac"][0, 0],
        reference.bse[1]
    )


def test_hac_missing_year():

    values, years = generate_series()

    values[5, 0, 0] = np.nan

    result = hac_significance(values, years)

    assert np.isnan(result["p_hac"][0, 0])


def test_hac_constant_series():

    years = np.arange(2001, 2026)

    values = np.full((25, 1, 1), 0.5)

    result = hac_significance(values, years)

    assert np.isnan(result["p_hac"][0, 0])


def test_diagnostics_missing_year():

    values, years = generate_series()

    values[10, 0, 0] = np.nan

    result = ols_trend(values, years)

    diagnostics = residual_diagnostics(
        values, years, result
    )

    assert diagnostics["pairs"][0, 0] == 22

    assert np.isnan(
        diagnostics["durbin_watson"][0, 0]
    )

    assert np.isfinite(
        diagnostics["lag1"][0, 0]
    )
