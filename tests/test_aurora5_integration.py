"""Integration against available local observations and exported runs (never fixtures)."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest
import rasterio
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.catalog import CubeReader
from aurora.models.baseline import regression_metrics
ROOT = Path(__file__).resolve().parents[1]


def test_real_common_test_population_and_physical_units():
    run = ROOT/'outputs/aurora5/queretaro_lst'
    if not (run/'metrics.json').exists(): pytest.skip('Local training output unavailable')
    report = json.loads((run/'metrics.json').read_text())
    assert report['unit'] == 'degC'
    assert report['splits'] == {'train': ['2002-01', '2018-12'], 'validation': ['2019-01', '2021-12'], 'test': ['2022-01', '2025-12']}
    with np.load(run/'test_predictions.npz', allow_pickle=False) as data:
        for model, expected in report['evaluations']['test']['results'].items():
            actual = regression_metrics(data['actual'], data[model], data['mask'])
            assert actual['observations'] == report['evaluations']['test']['comparable_observations']
            for metric in ('mae', 'rmse', 'r2'): assert actual[metric] == pytest.approx(expected[metric], rel=1e-10)


def test_saved_models_reproduce_retrospective_maps():
    run, reloaded = ROOT/'outputs/aurora5/queretaro_lst', ROOT/'outputs/aurora5/lst_reloaded'
    if not reloaded.exists(): pytest.skip('Local inference output unavailable')
    for model in ('persistence', 'seasonal', 'climatology', 'xgboost', 'convlstm'):
        with np.load(run/f'forecast/{model}/forecast.npz', allow_pickle=False) as first, np.load(reloaded/f'{model}.npz', allow_pickle=False) as second:
            assert str(first['date']) == str(second['date']) == '2026-01'
            np.testing.assert_allclose(first['prediction'], second['prediction'], atol=2e-5, rtol=2e-6, equal_nan=True)
        with rasterio.open(reloaded/f'{model}_lst.tif') as src:
            assert src.tags()['unit'] == 'degC'
            assert src.crs.to_epsg() == 32614
            assert src.read(1, masked=True).mean() > 1  # Celsius never clipped to NDVI range.


def test_real_npy_partial_reads_equal_npz():
    npy, npz = ROOT/'outputs/aurora5/storage/queretaro_lst', ROOT/'data/processed/queretaro_lst'
    if not npy.exists(): pytest.skip('Prepared local storage unavailable')
    a, b = CubeReader(npy), CubeReader(npz)
    assert a.format == 'npy' and b.format == 'npz'
    for time in (slice(0, 12), slice(240, 252), slice(288, 300)):
        np.testing.assert_array_equal(a.read(time, slice(30, 60), slice(40, 90)), b.read(time, slice(30, 60), slice(40, 90)))


def test_ndvi_historical_outputs_are_byte_identical():
    snapshot = ROOT/'docs/evidence/aurora5/ndvi_preservation.json'
    if not snapshot.exists(): pytest.skip('Local preservation snapshot unavailable')
    for name, digest in json.loads(snapshot.read_text()).items():
        file = ROOT/name
        if not file.exists(): pytest.skip('Historical NDVI products unavailable on this checkout')
        assert hashlib.sha256(file.read_bytes()).hexdigest() == digest


def test_short_period_has_no_trend_artifacts():
    folder = ROOT/'outputs/investigations/queretaro_lst_2025-02_2025-10'
    if not folder.exists(): pytest.skip('Local descriptive run unavailable')
    result = json.loads((folder/'descriptive.json').read_text())
    assert not result['eligible'] and len(result['dates']) == 9
    assert not (folder/'history/trend_p.tif').exists()
