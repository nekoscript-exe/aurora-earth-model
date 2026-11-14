"""AURORA Synthetic Engine."""

import numpy as np


def generate_synthetic_cube(height=128, width=128, seed=42):
    rng = np.random.default_rng(seed)

    dates = np.arange(
        np.datetime64("2001-01"),
        np.datetime64("2026-01"),
        dtype="datetime64[M]",
    )

    months = len(dates)
    years = np.arange(months) / 12.0

    yy, xx = np.mgrid[0:height, 0:width]

    baseline = (
        0.45
        + 0.12 * np.sin(xx / 15)
        + 0.08 * np.cos(yy / 20)
    )

    slope = np.zeros((height, width), dtype=np.float32)

    slope[:height // 2, :width // 2] = 0.008
    slope[:height // 2, width // 2:] = -0.008

    seasonal = 0.12 * np.sin(
        2 * np.pi * np.arange(months) / 12
    )

    noise = rng.normal(0, 0.025, (months, height, width))

    cube = (
        baseline[None, :, :]
        + years[:, None, None] * slope[None, :, :]
        + seasonal[:, None, None]
        + noise
    )

    cube = np.clip(cube, -1, 1).astype(np.float32)

    valid = rng.random(cube.shape) >= 0.08
    cube[~valid] = np.nan

    return {
        "X": cube[..., None],
        "valid": valid[..., None],
        "dates": dates.astype("datetime64[D]").astype(str),
        "channels": np.array(["NDVI"]),
        "true_slope": slope,
    }
