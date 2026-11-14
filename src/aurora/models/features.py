"""AURORA forecasting feature engineering."""

import numpy as np


FEATURE_NAMES = [
    "lag_1",
    "lag_3",
    "lag_6",
    "lag_12",
    "mean_3",
    "mean_6",
    "mean_12",
    "std_12",
    "coverage_12",
    "month_sin",
    "month_cos",
]


def safe_mean(values):
    valid = np.isfinite(values)
    count = valid.sum(axis=0)

    return np.divide(
        np.nansum(values, axis=0),
        count,
        out=np.full(count.shape, np.nan),
        where=count > 0
    )


def monthly_features(X, dates, index):
    if index < 12:
        raise ValueError("12 months of history required")

    history = X[index - 12:index, :, :, 0]

    mean_12 = safe_mean(history)

    variance = safe_mean(
        (history - mean_12[None]) ** 2
    )

    month = int(
        dates[index].astype("datetime64[M]").astype(int)
    ) % 12

    angle = 2 * np.pi * month / 12

    features = [
        history[-1],
        history[-3],
        history[-6],
        history[-12],
        safe_mean(history[-3:]),
        safe_mean(history[-6:]),
        mean_12,
        np.sqrt(variance),
        np.isfinite(history).mean(axis=0),
        np.full(history.shape[1:], np.sin(angle)),
        np.full(history.shape[1:], np.cos(angle))
    ]

    return np.stack(
        features, axis=-1
    ).astype(np.float32)


def build_tabular_dataset(X, dates, indices, masks=None):
    features = []
    targets = []

    for position, index in enumerate(indices):
        F = monthly_features(X, dates, index)
        y = X[index, :, :, 0]

        valid = (
            np.isfinite(y)
            & (F[..., 8] > 0)
        )

        if masks is not None:
            valid &= masks[position, :, :, 0]

        features.append(F[valid])
        targets.append(y[valid])

    return (
        np.concatenate(features, axis=0),
        np.concatenate(targets, axis=0)
    )
