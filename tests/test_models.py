"""AURORA predictive engine tests."""

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.models.baseline import (
    temporal_split,
    fit_climatology,
    regression_metrics
)

from aurora.models.features import monthly_features
from aurora.models.convlstm import AuroraConvLSTM
from aurora.models.dataset import SatellitePatchDataset


def calendar():
    return np.arange(
        np.datetime64("2001-01"),
        np.datetime64("2026-01"),
        dtype="datetime64[M]"
    )


def test_temporal_split():
    dates = calendar()
    split = temporal_split(dates)

    assert len(split["train"]) == 204
    assert len(split["validation"]) == 36
    assert len(split["test"]) == 48

    assert split["train"].max() < split["validation"].min()
    assert split["validation"].max() < split["test"].min()


def test_features_no_future_leakage():
    dates = calendar()

    rng = np.random.default_rng(42)

    X = rng.random(
        (300, 8, 8, 1),
        dtype=np.float32
    )

    original = monthly_features(X, dates, 50)

    X[50:] = 999

    modified = monthly_features(X, dates, 50)

    np.testing.assert_array_equal(original, modified)


def test_climatology_train_only():
    dates = calendar()
    split = temporal_split(dates)

    X = np.ones(
        (300, 2, 2, 1),
        dtype=np.float32
    )

    X[split["validation"]] = 999
    X[split["test"]] = 999

    climate = fit_climatology(
        X, dates, split["train"]
    )

    np.testing.assert_allclose(climate, 1.0)


def test_perfect_prediction():
    y = np.array([0.2, 0.4, 0.6])

    result = regression_metrics(y, y)

    assert result["mae"] == 0
    assert result["rmse"] == 0
    assert result["r2"] == 1


def test_patch_mask():
    X = np.ones(
        (13, 8, 8, 1),
        dtype=np.float32
    )

    X[0, 0, 0, 0] = np.nan
    X[12, 1, 1, 0] = np.nan

    dataset = SatellitePatchDataset(
        X, [12], patch_size=32
    )

    inputs, target, mask = dataset[0]

    assert inputs.shape == (12, 2, 32, 32)
    assert target.shape == (1, 32, 32)
    assert inputs[0, 1, 0, 0] == 0
    assert not mask[0, 1, 1]
    assert mask.sum().item() == 63


def test_convlstm_output():
    model = AuroraConvLSTM()

    X = torch.rand(2, 12, 2, 8, 8)

    with torch.no_grad():
        prediction = model(X)

    assert prediction.shape == (2, 1, 8, 8)
    assert torch.isfinite(prediction).all()
    assert prediction.abs().max() <= 1


def test_convlstm_backward():
    model = AuroraConvLSTM()

    X = torch.rand(1, 12, 2, 8, 8)

    prediction = model(X)
    loss = prediction.square().mean()

    loss.backward()

    for param in model.parameters():
        assert param.grad is not None
        assert torch.isfinite(param.grad).all()
