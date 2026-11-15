"""Explicit synthetic mathematical fixtures; never production satellite coverage."""
import json
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.catalog import CubeReader
from aurora.storage import to_zarr
from aurora.jobs import Job, Cancelled, fresh
from aurora.block_engine import run_statistics, external_fdr, disk_array, Budget
from aurora.trend import annual_composite, ols_trend, sen_trend, hac_significance, fdr_correction
from aurora.geospatial import RasterGrid
from aurora.area import cell_areas


@pytest.fixture
def mathematical_cube(tmp_path):
    directory = tmp_path/'synthetic_test'; directory.mkdir()
    dates = np.arange('2001-01', '2026-01', dtype='datetime64[M]')
    rng = np.random.default_rng(58)
    X = (.2+np.arange(300)[:, None, None, None]*.0002+rng.normal(0, .02, (300, 6, 7, 1))).astype('float32')
    valid = np.ones(X.shape, bool); valid[::10, 1, 1] = False; X[::10, 1, 1] = np.nan
    valid[3:200, 2, 2] = False; X[3:200, 2, 2] = np.nan
    mask = np.ones((6, 7), bool); mask[0, 0] = False
    meta = {'dataset': 'synthetic_test', 'region_id': 'explicit_test', 'source': 'EXPLICIT MATHEMATICAL TEST, NOT SATELLITE',
            'variable': 'ndvi', 'unit': '1', 'shape': list(X.shape),
            'variable_definition': {'minimum': -1, 'maximum': 1, 'description': 'synthetic infrastructure fixture'},
            'grid': {'height': 6, 'width': 7, 'crs': 'EPSG:32614', 'transform': [1000, 0, 335000, 0, -1000, 2387000], 'nodata': -9999}}
    np.savez_compressed(directory/'cube.npz', X=X, valid=valid, region_mask=mask, channels=['NDVI'], dates=dates.astype(str))
    (directory/'cube_metadata.json').write_text(json.dumps(meta))
    return directory


def test_zarr_roundtrip_raw_values_masks_and_windows(mathematical_cube, tmp_path):
    to_zarr(mathematical_cube, tmp_path/'zarr', chunks=(12, 4, 4, 1))
    with CubeReader(mathematical_cube) as a, CubeReader(tmp_path/'zarr') as b:
        assert b.format == 'zarr'
        for name in ('X', 'valid', 'region_mask', 'dates', 'channels'):
            np.testing.assert_array_equal(a.arrays[name][:], b.arrays[name][:])
        np.testing.assert_array_equal(a.read(slice(8, 25), slice(1, 4), slice(2, 6)), b.read(slice(8, 25), slice(1, 4), slice(2, 6)))
        np.testing.assert_array_equal(a.read(5, slice(None, None, 2), slice(None, None, 2)), b.read(5, slice(None, None, 2), slice(None, None, 2)))
        with pytest.raises(MemoryError): b.read(max_bytes=1)


def test_missing_zarr_chunks_are_missing_not_zero(mathematical_cube, tmp_path):
    import zarr
    to_zarr(mathematical_cube, tmp_path/'zarr', chunks=(12, 4, 4, 1))
    group = zarr.open_group(str(tmp_path/'zarr/cube.zarr'), mode='a')
    # A genuinely absent chunk in a synthetic store, not a simulated observation.
    group['X'][0:12, :4, :4, :] = np.nan
    group['valid'][0:12, :4, :4, :] = False
    with CubeReader(tmp_path/'zarr') as reader: assert np.isnan(reader.read(slice(0, 12), slice(0, 4), slice(0, 4))).all()
    group.create_array('region_mask', shape=(6, 7), chunks=(4, 4), dtype=bool, fill_value=True, overwrite=True)
    with pytest.raises(ValueError, match='regional mask chunks'): CubeReader(tmp_path/'zarr')


def test_external_fdr_entire_family_matches_conventional(tmp_path):
    from statsmodels.stats.multitest import multipletests
    p1 = np.array([[.01, .01, np.nan], [.2, 1., .04]])
    p2 = np.array([[.5, .001, .09], [np.nan, .1, .9]])
    q = [disk_array(tmp_path, f'q{i}', (2, 3)) for i in range(2)]
    count = external_fdr([p1, p2], q, tmp_path/'bh.sqlite')
    stacked = np.stack([p1, p2]); expected = np.full_like(stacked, np.nan); valid = np.isfinite(stacked)
    expected[valid] = multipletests(stacked[valid], method='fdr_bh')[1]
    assert count == valid.sum()
    np.testing.assert_allclose(np.stack(q), expected, rtol=1e-14, equal_nan=True)


@pytest.mark.parametrize('block', [2, 5])
def test_blocked_statistics_matches_conventional(mathematical_cube, tmp_path, block):
    result = run_statistics(mathematical_cube, tmp_path/f'result{block}', memory_mib=8, block_size=block, allow_synthetic=True)
    with CubeReader(mathematical_cube) as reader:
        X = reader.read()[..., None]; dates = reader.dates
    annual, years = annual_composite(X, dates)
    expected = ols_trend(annual, years)
    for name, ref in [('trend_slope', expected['slope']), ('trend_p', expected['p']),
                      ('trend_change', expected['change']), ('trend_sen', sen_trend(annual, years)),
                      ('trend_hac_p', hac_significance(annual, years)['p_hac'])]:
        actual = np.load(tmp_path/f'result{block}/{name}.npy')
        np.testing.assert_allclose(actual, ref, atol=1e-12, equal_nan=True)
    q, _ = fdr_correction(expected['p'])
    np.testing.assert_allclose(np.load(tmp_path/f'result{block}/trend_q.npy'), q, atol=1e-13, equal_nan=True)
    assert result['estimated_block_working_bytes'] <= result['memory_budget_bytes']//2
    assert (tmp_path/f'result{block}/summary.png').exists()
    assert json.loads((tmp_path/f'result{block}/manifest.json').read_text())['observation_kind'] == 'synthetic_test'


def test_geographic_world_area_poles_and_antimeridian():
    metadata = {'grid': {'height': 180, 'width': 360, 'crs': 'EPSG:4326', 'transform': [1, 0, -180, 0, -1, 90]}}
    grid = RasterGrid.from_metadata(metadata, (180, 360))
    area, _ = cell_areas(grid)
    # WGS84 ellipsoid total surface area, independent of any satellite values.
    np.testing.assert_allclose(area.sum(), 510065621724088.5, rtol=2e-14)
    assert 0 < area[0, 0] < area[89, 0]
    metadata['grid'].update(height=10, width=20, transform=[1, 0, 170, 0, -1, 5])
    a, _ = cell_areas(RasterGrid.from_metadata(metadata, (10, 20)))
    metadata['grid']['transform'][2] = -190
    b, _ = cell_areas(RasterGrid.from_metadata(metadata, (10, 20)))
    np.testing.assert_array_equal(a, b)


def test_equal_area_projection_uses_metric_cell_area():
    meta = {'grid': {'height': 2, 'width': 3, 'crs': 'EPSG:6933', 'transform': [50000, 0, -100000, 0, -50000, 100000]}}
    area, method = cell_areas(RasterGrid.from_metadata(meta, (2, 3)))
    np.testing.assert_allclose(area, 50000**2)
    assert 'equal-area' in method


def test_cancellation_does_not_publish_complete_result(mathematical_cube, tmp_path, monkeypatch):
    original = Job.progress
    def progress(self, done, total, phase):
        if phase == 'native-grid-blocks': self.cancel_path.touch()
        original(self, done, total, phase)
    monkeypatch.setattr(Job, 'progress', progress)
    with pytest.raises(Cancelled): run_statistics(mathematical_cube, tmp_path/'cancelled', allow_synthetic=True, block_size=2)
    manifest = json.loads((tmp_path/'cancelled/manifest.json').read_text())
    assert manifest['status'] == 'cancelled'
    assert not (tmp_path/'cancelled/summary.png').exists()


def test_stale_inputs_detected_and_sources_never_overwritten(mathematical_cube, tmp_path):
    job = Job(tmp_path/'job', [mathematical_cube], 'test', 'explicit_test', {}, allow_synthetic=True)
    assert fresh(job.manifest)
    meta = mathematical_cube/'cube_metadata.json'
    value = json.loads(meta.read_text()); value['provenance_note'] = 'metadata changed'
    meta.write_text(json.dumps(value))
    assert not fresh(job.manifest)
    with pytest.raises(RuntimeError): job.finish()
    with pytest.raises(FileExistsError): Job(tmp_path/'job', [mathematical_cube], 'test', 'test', {})


def test_budget_shrinks_block_for_longer_calendar():
    assert Budget(1200, 8, 256).side < Budget(300, 8, 256).side
    with pytest.raises(ValueError): Budget(300, 1, 256)


def test_blocked_pairs_and_global_fdr_match_conventional(mathematical_cube, tmp_path):
    from aurora.block_multivariate import run_pair_statistics
    from aurora.multivariate import paired_anomalies, correlation_maps, lagged_pairs
    other = tmp_path/'explicit_synthetic_y'; other.mkdir()
    with np.load(mathematical_cube/'cube.npz', allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files}
    arrays['X'] = (-arrays['X']*.7+np.random.default_rng(4).normal(0, .005, arrays['X'].shape)).astype('float32')
    arrays['channels'] = np.array(['TEST_Y'])
    np.savez_compressed(other/'cube.npz', **arrays)
    meta = json.loads((mathematical_cube/'cube_metadata.json').read_text()); meta['variable'] = 'test_y'
    (other/'cube_metadata.json').write_text(json.dumps(meta))
    run_pair_statistics(mathematical_cube, other, tmp_path/'pairs', memory_mib=8, block_size=2,
                        lags=(-1, 0, 1), allow_synthetic=True)
    with CubeReader(mathematical_cube) as x, CubeReader(other) as y:
        a, b, dates = x.read(), y.read(), x.dates
        mask = np.asarray(x.arrays['region_mask']).copy()
    valid = np.isfinite(a) & np.isfinite(b); a, b = np.where(valid, a, np.nan), np.where(valid, b, np.nan)
    an, bn, _ = paired_anomalies(a, b, dates)
    p_family = []; q_expected_names = []
    for name, xx, yy in [('raw', a, b), ('anomaly', an, bn)]:
        for lag in (-1, 0, 1):
            expected = correlation_maps(*lagged_pairs(xx, yy, lag))
            for field in ('pearson', 'spearman'):
                actual = np.load(tmp_path/f'pairs/{name}_{lag}_{field}.npy')
                np.testing.assert_allclose(actual, np.where(mask, expected[field], np.nan), atol=1e-11, equal_nan=True)
            p_family.append(np.where(mask, expected['p_ar1_diagnostic'], np.nan)); q_expected_names.append(f'{name}_{lag}')
    q, _ = fdr_correction(np.stack(p_family))
    for i, name in enumerate(q_expected_names):
        np.testing.assert_allclose(np.load(tmp_path/f'pairs/{name}_q_ar1_diagnostic.npy'), q[i], atol=1e-12, equal_nan=True)


def test_export_four_formats_and_stale_rejection(mathematical_cube, tmp_path):
    from aurora.exports import export_bundle
    run_statistics(mathematical_cube, tmp_path/'result', start='2020-01', end='2025-12', allow_synthetic=True)
    export_bundle(tmp_path/'result', tmp_path/'export')
    assert all(list((tmp_path/'export').glob('*.'+extension)) for extension in ('csv', 'json', 'tif', 'png'))
    assert json.loads((tmp_path/'export/manifest.json').read_text())['status'] == 'complete'
    meta = mathematical_cube/'cube_metadata.json'; m = json.loads(meta.read_text()); m['changed'] = True; meta.write_text(json.dumps(m))
    with pytest.raises(ValueError): export_bundle(tmp_path/'result', tmp_path/'stale_export')


def test_cancel_before_worker_creates_output(mathematical_cube, tmp_path):
    from aurora.jobs import request_cancel
    target = tmp_path/'not_created'
    request_cancel(target)
    with pytest.raises(Cancelled): run_statistics(mathematical_cube, target, allow_synthetic=True)
    assert json.loads((target/'manifest.json').read_text())['status'] == 'cancelled'


def test_npz_disk_cache_quota_and_series_budget(mathematical_cube, tmp_path):
    with pytest.raises(MemoryError): CubeReader(mathematical_cube, cache=tmp_path/'tiny_cache', cache_limit_bytes=1)
    with CubeReader(mathematical_cube) as reader:
        with pytest.raises(MemoryError): reader.read_series(slice(None), slice(None), slice(None), max_bytes=1)
    with pytest.raises(ValueError, match='closed'): reader.read()


def test_logical_161gb_zarr_is_read_partially(tmp_path):
    import zarr
    directory = tmp_path/'EXPLICIT_SYNTHETIC_PRESSURE_TEST'; directory.mkdir()
    group = zarr.open_group(str(directory/'cube.zarr'), mode='w', zarr_format=2)
    shape = (300, 8192, 16384, 1)
    group.create_array('X', shape=shape, chunks=(12, 32, 32, 1), dtype='float32', fill_value=np.nan)
    group.create_array('valid', shape=shape, chunks=(12, 32, 32, 1), dtype=bool, fill_value=False)
    group.create_array('region_mask', shape=shape[1:3], chunks=(32, 32), dtype=bool, fill_value=False)
    group.create_array('dates', data=np.arange('2001-01', '2026-01', dtype='datetime64[M]').astype(str))
    group.create_array('channels', data=np.array(['TEST']))
    meta = {'dataset': 'synthetic_test', 'source': 'EXPLICIT SYNTHETIC MEMORY TEST; NO OBSERVATIONS', 'variable': 'test', 'unit': '1',
        'variable_definition': {'minimum': -1, 'maximum': 1}, 'shape': list(shape),
        'storage': {'format': 'zarr', 'path': 'cube.zarr'},
        'grid': {'crs': 'EPSG:4326', 'height': shape[1], 'width': shape[2], 'transform': [360/shape[2], 0, -180, 0, -180/shape[1], 90]}}
    (directory/'cube_metadata.json').write_text(json.dumps(meta))
    with CubeReader(directory) as reader:
        block = reader.read(slice(0, 12), slice(4096, 4128), slice(8192, 8224), max_bytes=1024**2)
        assert block.shape == (12, 32, 32) and block.nbytes == 49152 and np.isnan(block).all()
        assert np.prod(reader.shape)*4 == 161061273600
        with pytest.raises(MemoryError): reader.read(max_bytes=64*1024**2)


def test_custom_variable_registered_without_source_change(mathematical_cube, tmp_path):
    from aurora.catalog import DatasetRegistry
    # Header/catalog test only: the source explicitly retains its mathematical-test provenance.
    m = json.loads((mathematical_cube/'cube_metadata.json').read_text())
    m['dataset'] = 'satellite'; m['variable'] = 'custom_index'; m['region_id'] = 'header_fixture_only'
    m['source'] = 'EXPLICIT HEADER FIXTURE, NOT REAL OBSERVATIONS'
    with np.load(mathematical_cube/'cube.npz', allow_pickle=False) as data: arrays = {name: data[name] for name in data.files}
    arrays['channels'] = np.array(['CUSTOM_INDEX']); np.savez_compressed(mathematical_cube/'cube.npz', **arrays)
    (mathematical_cube/'cube_metadata.json').write_text(json.dumps(m))
    (tmp_path/'config').mkdir(); (tmp_path/'config/datasets.json').write_text(json.dumps({'datasets': [{'id': 'custom', 'region_id': 'header_fixture_only', 'path': str(mathematical_cube)}]}))
    record = DatasetRegistry(tmp_path).find('header_fixture_only', 'custom_index')
    assert record.identifier == 'custom' and record.metadata['unit'] == '1'


def test_canonical_units_cannot_be_relabelled_as_celsius(mathematical_cube):
    from aurora.catalog import variable_spec
    m = json.loads((mathematical_cube/'cube_metadata.json').read_text())
    m.update(variable='lst', unit='K')
    with pytest.raises(ValueError, match='Canonical variable units'): variable_spec(m)
    m['variable'] = 'lst_kelvin'
    assert variable_spec(m).unit == 'K'  # Explicitly distinct identifier; never plotted as Celsius.


def test_result_disk_quota_prevents_unbounded_output(tmp_path, monkeypatch):
    from aurora.block_engine import check_output_budget
    monkeypatch.setenv('AURORA_RESULT_DISK_LIMIT_GIB', '.001')
    with pytest.raises(MemoryError, match='disk exceeds budget'): check_output_budget(tmp_path, 1000000, 11)
