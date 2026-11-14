"""AURORA Statistical Trend Engine."""

import numpy as np
from scipy import stats


def annual_composite(X, dates, min_months=9):
    """Aggregate monthly NDVI observations into annual means."""

    values = np.asarray(X[..., 0], dtype=np.float64)
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    unique_years = np.unique(years)

    annual = np.full(
        (len(unique_years), *values.shape[1:]),
        np.nan,
        dtype=np.float64
    )

    for i, year in enumerate(unique_years):
        subset = values[years == year]
        count = np.isfinite(subset).sum(axis=0)

        annual[i] = np.divide(
            np.nansum(subset, axis=0),
            count,
            out=np.full(count.shape, np.nan),
            where=count >= min_months
        )

    return annual, unique_years


def ols_trend(values, years, min_years=15):
    """Calculate vectorized OLS trends for individual pixels."""

    y = np.asarray(values, dtype=np.float64)
    t = np.asarray(years, dtype=np.float64)

    t = (t - t[0])[:, None, None]

    valid = np.isfinite(y)
    n = valid.sum(axis=0)

    x = np.where(valid, t, 0.0)
    z = np.where(valid, y, 0.0)

    sx = x.sum(axis=0)
    sy = z.sum(axis=0)
    sxx = (x * x).sum(axis=0)
    sxy = (x * z).sum(axis=0)

    with np.errstate(divide="ignore", invalid="ignore"):
        denominator = n * sxx - sx**2

        slope = (n * sxy - sx * sy) / denominator
        intercept = (sy - slope * sx) / n

        prediction = intercept[None] + slope[None] * t
        residual = np.where(valid, y - prediction, 0.0)

        sse = (residual**2).sum(axis=0)
        sst = np.where(valid, (y - sy / n)**2, 0).sum(axis=0)

        r2 = 1 - sse / sst

        centered_x = sxx - sx**2 / n
        stderr = np.sqrt((sse / (n - 2)) / centered_x)

        statistic = slope / stderr
        p = 2 * stats.t.sf(np.abs(statistic), df=n - 2)

    eligible = (n >= min_years) & (denominator > 0)

    first = np.min(np.where(valid, t, np.inf), axis=0)
    last = np.max(np.where(valid, t, -np.inf), axis=0)

    with np.errstate(invalid="ignore"):
        change = slope * (last - first)

    result = {
        "slope": slope,
        "intercept": intercept,
        "p": p,
        "r2": r2,
        "stderr": stderr,
        "change": change,
    }

    for key in result:
        result[key] = np.where(
            eligible, result[key], np.nan
        )

    result["n"] = n

    return result


def sen_trend(values, years, min_years=15):
    """Estimate robust Theil-Sen slopes for each pixel."""

    y = np.asarray(values, dtype=np.float64)
    t = np.asarray(years, dtype=np.float64)

    height, width = y.shape[1:]
    flat = y.reshape(len(t), -1)

    slopes = np.full(flat.shape[1], np.nan)

    for i in range(flat.shape[1]):
        series = flat[:, i]
        valid = np.isfinite(series)

        if valid.sum() >= min_years:
            slopes[i] = stats.theilslopes(
                series[valid],
                t[valid]
            ).slope

    return slopes.reshape(height, width)


def fdr_correction(p_values, alpha=0.05):
    """Apply Benjamini-Hochberg FDR correction."""

    from statsmodels.stats.multitest import multipletests

    p = np.asarray(p_values, dtype=np.float64)

    q = np.full(p.shape, np.nan)
    significant = np.zeros(p.shape, dtype=bool)

    valid = np.isfinite(p)

    if valid.any():
        rejected, corrected, _, _ = multipletests(
            p[valid],
            alpha=alpha,
            method="fdr_bh"
        )

        q[valid] = corrected
        significant[valid] = rejected

    return q, significant


def residual_diagnostics(values, years, result):
    """Diagnose temporal dependence in OLS residuals."""

    y = np.asarray(values, dtype=np.float64)
    years = np.asarray(years, dtype=np.float64)

    t = (years - years[0])[:, None, None]

    prediction = (
        result["intercept"][None]
        + result["slope"][None] * t
    )

    residuals = y - prediction

    previous = residuals[:-1]
    current = residuals[1:]

    consecutive = (
        np.diff(years) == 1
    )[:, None, None]

    valid = (
        np.isfinite(previous)
        & np.isfinite(current)
        & consecutive
    )

    n = valid.sum(axis=0)

    a = np.where(valid, previous, 0.0)
    b = np.where(valid, current, 0.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        covariance = (
            (a * b).sum(axis=0)
            - a.sum(axis=0) * b.sum(axis=0) / n
        )

        variance_a = (
            (a**2).sum(axis=0)
            - a.sum(axis=0)**2 / n
        )

        variance_b = (
            (b**2).sum(axis=0)
            - b.sum(axis=0)**2 / n
        )

        rho = covariance / np.sqrt(
            variance_a * variance_b
        )

        dw = (
            ((b - a)**2).sum(axis=0)
            / np.nansum(residuals**2, axis=0)
        )

    rho = np.where(
        (n >= 10) & np.isfinite(rho),
        rho, np.nan
    )

    complete = np.isfinite(residuals).all(axis=0)

    dw = np.where(
        complete
        & consecutive.all()
        & np.isfinite(dw),
        dw, np.nan
    )

    return {
        "lag1": rho,
        "durbin_watson": dw,
        "pairs": n
    }


def hac_significance(values, years, maxlags=2, min_years=15):
    """Newey-West HAC sensitivity analysis for complete series."""

    import statsmodels.api as sm

    y = np.asarray(values, dtype=np.float64)
    years = np.asarray(years, dtype=np.float64)

    height, width = y.shape[1:]
    flat = y.reshape(len(years), -1)

    p = np.full(flat.shape[1], np.nan)
    stderr = np.full(flat.shape[1], np.nan)

    if len(years) < min_years:
        return {
            "p_hac": p.reshape(height, width),
            "stderr_hac": stderr.reshape(height, width)
        }

    if not np.all(np.diff(years) == 1):
        raise ValueError("HAC requires consecutive annual dates")

    design = sm.add_constant(years - years[0])

    for i in range(flat.shape[1]):
        series = flat[:, i]

        if not np.isfinite(series).all():
            continue

        if np.ptp(series) < 1e-12:
            continue

        model = sm.OLS(series, design).fit(
            cov_type="HAC",
            cov_kwds={
                "maxlags": maxlags,
                "use_correction": True
            },
            use_t=True
        )

        p[i] = model.pvalues[1]
        stderr[i] = model.bse[1]

    return {
        "p_hac": p.reshape(height, width),
        "stderr_hac": stderr.reshape(height, width)
    }
