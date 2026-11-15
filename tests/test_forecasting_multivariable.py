"""Explicit mathematical fixtures, never exported as satellite observations."""
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.models.forecasting import training_normalization, common_mask, neural_predictions
from aurora.models.convlstm import AuroraConvLSTM


def test_normalization_ignores_future_and_missing():
    X = np.array([1., 3., np.nan, 9999.])
    norm = training_normalization(X, [0, 1, 2])
    assert norm == {'mean': 2., 'std': 1.}
    X[3] = -9999
    assert training_normalization(X, [0, 1, 2]) == norm


def test_common_mask_all_models_same_population():
    target = np.array([0., 1., 2., np.nan])
    mask = common_mask(target, {'a': [0., np.nan, 2., 4.], 'b': [0., 1., 2., 4.]}, [True]*4)
    np.testing.assert_array_equal(mask, [True, False, True, False])


def test_linear_lst_and_legacy_tanh_heads():
    legacy, lst = AuroraConvLSTM(), AuroraConvLSTM('linear')
    with torch.no_grad():
        for m in (legacy, lst):
            m.head.weight.zero_(); assert m.head.bias is not None; m.head.bias.fill_(5)
        X = torch.zeros(1, 12, 2, 4, 4)
        assert legacy(X).max() <= 1
        assert lst(X).min() == 5


def test_future_inference_no_target_needed():
    model = AuroraConvLSTM('linear')
    X = np.ones((12, 3, 4, 1), dtype='float32')
    result = neural_predictions(model, X, [12], torch.device('cpu'), patch_size=4)
    assert result.shape == (1, 3, 4, 1)
    assert np.isfinite(result).all()


def test_empty_convlstm_sequence_is_rejected_explicitly():
    model = AuroraConvLSTM('linear')
    with pytest.raises(ValueError, match='at least one input time step'):
        model(torch.zeros(1, 0, 2, 4, 4))
