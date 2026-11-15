import sys
from pathlib import Path
import numpy as np
from scipy.stats import pearsonr, spearmanr
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.multivariate import paired_correlation, correlation_maps, lagged_pairs, paired_anomalies


def test_paired_missing_and_rank_ties():
    a = np.array([1., 2, 2, np.nan, 3, 4])[:, None]
    b = np.array([4., 3, 3, 900, np.nan, 0])[:, None]
    maps = correlation_maps(a, b, minimum=3)
    valid = np.isfinite(a[:, 0]) & np.isfinite(b[:, 0])
    assert maps['pairs'][0] == 4
    np.testing.assert_allclose(maps['pearson'][0], pearsonr(a[valid, 0], b[valid, 0]).statistic)
    np.testing.assert_allclose(maps['spearman'][0], spearmanr(a[valid, 0], b[valid, 0]).statistic)
    assert np.isnan(paired_correlation(np.ones((40, 1)), np.ones((40, 1)))[0]).all()


def test_lag_sign_does_not_compress_calendar():
    a, b = np.arange(20.), np.arange(20.)+100
    x, y = lagged_pairs(a, b, 3)
    assert x[0] == 0 and y[0] == 103
    x, y = lagged_pairs(a, b, -3)
    assert x[0] == 3 and y[0] == 100


def test_climate_uses_only_paired_reference_and_minimum_counts():
    dates = np.arange('2001-01', '2026-01', dtype='datetime64[M]')
    a, b = np.ones((300, 1, 1)), np.ones((300, 1, 1))*10
    a[-48:] = 100; b[-48:] = 1000
    an, bn, count = paired_anomalies(a, b, dates)
    assert an[-1, 0, 0] == 99 and bn[-1, 0, 0] == 990
    assert count.min() == 17
    b[12:216:12] = np.nan
    an, bn, _ = paired_anomalies(a, b, dates)
    assert np.isnan(an[0, 0, 0]) and np.isnan(bn[0, 0, 0])
