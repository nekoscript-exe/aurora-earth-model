"""Security/robustness fixtures are explicit synthetic arrays, never observations."""
import importlib
import json
import os
from pathlib import Path
import sys
import types

import numpy as np
import pytest

from aurora.catalog import CubeReader
from aurora.distribution import safe_path


@pytest.fixture
def cube(tmp_path):
    folder = tmp_path / 'synthetic_fixture'
    folder.mkdir()
    values = np.full((3, 2, 2, 1), .25, dtype='float32')
    np.savez(folder / 'cube.npz', X=values, valid=np.ones(values.shape, bool),
             region_mask=np.ones((2, 2), bool), dates=['2020-01', '2020-02', '2020-03'], channels=['NDVI'])
    (folder / 'cube_metadata.json').write_text(json.dumps({
        'variable': 'NDVI', 'dataset': 'synthetic_test', 'shape': list(values.shape),
        'grid': {'crs': 'EPSG:32614', 'height': 2, 'width': 2,
                 'transform': [1000, 0, 335000, 0, -1000, 2387000]}}))
    return folder


def test_cache_rejects_substituted_same_shape_values(cube, tmp_path):
    cache = tmp_path / 'cache'
    with CubeReader(cube, cache=cache) as reader:
        expected = reader.read().copy()
    cached = next(cache.glob('aurora-arrays-v2/*/X.npy'))
    np.save(cached, np.full((3, 2, 2, 1), .75, dtype='float32'))
    with pytest.raises(ValueError, match='integrity'):
        CubeReader(cube, cache=cache)
    with CubeReader(cube, cache=tmp_path / 'independent') as reader:
        np.testing.assert_array_equal(reader.read(), expected)


def test_cache_source_content_changes_even_when_stat_preserved(cube, tmp_path):
    path = cube / 'cube.npz'
    before = path.stat()
    cache = tmp_path / 'cache'
    with CubeReader(cube, cache=cache) as reader:
        first = reader.read().copy()
    with np.load(path, allow_pickle=False) as original:
        arrays = {name: original[name] for name in original.files}
    arrays['X'] = np.full((3, 2, 2, 1), .5, dtype='float32')
    np.savez(path, **arrays)
    assert path.stat().st_size == before.st_size
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with CubeReader(cube, cache=cache) as reader:
        np.testing.assert_array_equal(reader.read(), first * 2)
    assert len(list(cache.glob('aurora-arrays-v2/*/manifest.json'))) == 2


def test_cache_rejects_precreated_symlink(cube, tmp_path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    target = tmp_path / 'attacker'
    target.mkdir()
    (cache / 'aurora-arrays-v2').symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='symbolic link'):
        CubeReader(cube, cache=cache)
    assert not list(target.iterdir())


@pytest.mark.skipif(os.name != 'posix', reason='POSIX permission contract')
def test_cache_rejects_group_writable_leaf(cube, tmp_path):
    leaf = tmp_path / 'cache' / 'aurora-arrays-v2'
    leaf.mkdir(parents=True)
    leaf.chmod(0o770)
    with pytest.raises(ValueError, match='0700'):
        CubeReader(cube, cache=tmp_path / 'cache')




def test_acquisition_import_is_offline_and_uses_repository_helper(monkeypatch):
    ee = types.ModuleType('ee')
    def forbidden(*args, **kwargs):
        raise AssertionError('Import must not initialize Earth Engine or submit jobs')
    monkeypatch.setattr(ee, 'Initialize', forbidden, raising=False)
    monkeypatch.setitem(sys.modules, 'ee', ee)
    monkeypatch.setitem(sys.modules, 'requests', types.ModuleType('requests'))
    module = importlib.import_module('scripts.acquisition.export_mexico_missing')
    assert module.SCRIPTS == Path(__file__).resolve().parents[1] / 'scripts'
    helper = sys.modules['export_grid']
    assert helper.__file__ is not None
    assert Path(helper.__file__).resolve() == module.SCRIPTS / 'export_grid.py'




def test_direct_forecast_rejects_changed_weights_before_parsing(tmp_path):
    from aurora.models.forecasting import forecast_saved
    run = tmp_path / 'run'
    (run / 'xgboost').mkdir(parents=True)
    (run / 'xgboost/model.ubj').write_bytes(b'EXPLICIT CORRUPT MODEL TEST BYTES')
    (run / 'metrics.json').write_text(json.dumps({'model_sha256': {'xgboost/model.ubj': '0' * 64}}))
    with pytest.raises(ValueError, match='Saved model integrity'):
        forecast_saved(tmp_path / 'no-input-required', run, tmp_path / 'output', device='cpu')
    assert not (tmp_path / 'output').exists()


def test_export_rejects_empty_mask_before_writing(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'ee', types.ModuleType('ee'))
    monkeypatch.setitem(sys.modules, 'requests', types.ModuleType('requests'))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from export_grid import finalize
    output = tmp_path / 'must-not-be-created.tif'
    with pytest.raises(ValueError, match='mask is empty'):
        finalize(np.ones((2, 2)), output, {'height': 2, 'width': 2}, np.zeros((2, 2), bool))
    assert not output.exists()


def test_cancelled_cache_extraction_removes_its_temporary_files(cube, tmp_path):
    from aurora.jobs import Cancelled
    cache = tmp_path / 'cache'
    def cancel_during_write():
        if list(cache.glob('aurora-arrays-v2/*/tmp*')):
            raise Cancelled('Explicit regression-test cancellation')
    with pytest.raises(Cancelled):
        CubeReader(cube, cache=cache, check=cancel_during_write)
    assert not list(cache.glob('aurora-arrays-v2/*/tmp*'))
    assert not list(cache.glob('aurora-arrays-v2/*/manifest.json'))
    with CubeReader(cube, cache=cache) as reader:
        np.testing.assert_array_equal(reader.read(), np.full((3, 2, 2), .25, dtype='float32'))
