"""AURORA temporal forecasting baselines."""

import numpy as np


def temporal_split(dates):
    dates = np.asarray(dates).astype("datetime64[M]")
    years = dates.astype("datetime64[Y]").astype(int) + 1970

    available = np.arange(len(dates)) >= 12

    return {
        "train": np.flatnonzero(
            available & (years >= 2002) & (years <= 2018)
        ),
        "validation": np.flatnonzero(
            available & (years >= 2019) & (years <= 2021)
        ),
        "test": np.flatnonzero(
            available & (years >= 2022) & (years <= 2025)
        ),
    }


def fit_climatology(X, dates, train_indices):
    months = (
        dates.astype("datetime64[M]").astype(int) % 12
    )

    climate = np.full(
        (12, *X.shape[1:]),
        np.nan,
        dtype=np.float32
    )

    for month in range(12):
        indices = train_indices[
            months[train_indices] == month
        ]

        if not len(indices):
            continue

        values = X[indices]
        count = np.isfinite(values).sum(axis=0)

        climate[month] = np.divide(
            np.nansum(values, axis=0),
            count,
            out=np.full(count.shape, np.nan),
            where=count > 0
        )

    return climate


def predict_baselines(X, dates, indices, climate):
    months = (
        dates.astype("datetime64[M]").astype(int) % 12
    )

    return {
        "persistence": X[indices - 1],
        "seasonal": X[indices - 12],
        "climatology": climate[months[indices]]
    }


def regression_metrics(actual, predicted, mask=None):
    valid = (
        np.isfinite(actual)
        & np.isfinite(predicted)
    )

    if mask is not None:
        valid &= mask

    y = actual[valid].astype(np.float64)
    p = predicted[valid].astype(np.float64)

    if not y.size:
        raise ValueError("No comparable observations")

    error = y - p

    sse = np.sum(error**2)
    sst = np.sum((y - y.mean())**2)

    return {
        "observations": int(y.size),
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "r2": float(1 - sse / sst) if sst > 0 else None
    }
