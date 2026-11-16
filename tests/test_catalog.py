import json
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.catalog import CubeReader, DatasetRegistry, ObservationSeries


@pytest.fixture
def observed(tmp_path):
    folder = tmp_path/'data/processed/region_ndvi'; folder.mkdir(parents=True)
    values = np.arange(120, dtype='float32').reshape(3, 5, 8, 1)/200
    valid = np.ones(values.shape, dtype=bool); valid[1, 2, 3, 0] = False
    mask = np.ones((5, 8), dtype=bool); mask[0, 0] = False
    np.savez_compressed(folder/'cube.npz', X=values, valid=valid, region_mask=mask,
                        dates=['2020-01', '2020-02', '2020-03'], channels=['NDVI'])
    m = {'dataset': 'satellite', 'source': 'MODIS/061/MOD13Q1', 'unit': '1', 'variable': 'NDVI',
         'region_id': 'region', 'shape': [3, 5, 8, 1],
         'grid': {'crs': 'EPSG:32614', 'height': 5, 'width': 8, 'transform': [5000, 0, 300000, 0, -5000, 2400000], 'nodata': -9999}}
    (folder/'cube_metadata.json').write_text(json.dumps(m))
    return tmp_path, folder, values


def test_registry_does_not_invent_missing_regions(observed):
    root, folder, _ = observed
    registry = DatasetRegistry(root); record = registry.find('region', 'ndvi')
    assert record.resolution == [5000, 5000]
    assert record.summary()['start'] == '2020-01'
    with pytest.raises(FileNotFoundError): registry.find('mexico', 'ndvi')
    m = json.loads((folder/'cube_metadata.json').read_text()); m['dataset'] = 'synthetic'
    (folder/'cube_metadata.json').write_text(json.dumps(m))
    assert not DatasetRegistry(root).records


def test_windowed_npz_matches_original_and_masks(observed):
    root, folder, values = observed
    reader = CubeReader(folder, cache=root/'cache')
    assert isinstance(reader.arrays['X'], np.memmap)
    actual = reader.read(slice(1, 2), slice(1, 4), slice(2, 6))
    expected = values[1:2, 1:4, 2:6, 0].copy(); expected[0, 1, 1] = np.nan
    np.testing.assert_array_equal(actual, expected)
    assert np.isnan(reader.read(0)[0, 0])
    with pytest.raises(MemoryError): reader.read(max_bytes=1)
    rebuilt = np.full(values.shape[:3], np.nan)
    for key, block in reader.blocks(months=2, rows=2, cols=3): rebuilt[key] = block
    np.testing.assert_array_equal(rebuilt, reader.read())


def test_overview_centers_and_no_interpolation(observed):
    _, folder, values = observed
    series = ObservationSeries(folder, 'ndvi', max_dimension=4)
    assert series.stride == 2
    source = series.reader.grid.affine
    from affine import Affine
    overview = Affine(*series.metadata['grid']['transform'])
    np.testing.assert_allclose(overview @ (.5, .5), source @ (.5, .5))
    np.testing.assert_allclose(overview @ (1.5, 1.5), source @ (2.5, 2.5))
    expected = values[0, ::2, ::2, 0].copy(); expected[0, 0] = np.nan
    np.testing.assert_array_equal(series[0], expected)
