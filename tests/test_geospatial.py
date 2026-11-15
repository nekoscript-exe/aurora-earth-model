"""Coordinate fixtures are mathematical test data, not satellite observations."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from affine import Affine
from rasterio.crs import CRS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.desktop.geospatial import (
    RasterGrid, orthographic_forward, orthographic_inverse, load_observations,
)


def metadata(affine=Affine(1, 0, -2, 0, -1, 2), crs='EPSG:4326', shape=(4, 4)):
    return {'dataset': 'satellite', 'source': 'MODIS/061/MOD13Q1',
            'variable': 'NDVI', 'unit': '1',
            'grid': {'crs': crs, 'transform': list(affine)[:6],
                     'height': shape[0], 'width': shape[1], 'nodata': -9999}}


@pytest.mark.parametrize('center', [(-100, 20), (179, 0), (0, 90), (0, -90)])
def test_orthographic_roundtrip_and_center(center):
    lon, lat, front = orthographic_inverse(np.array([0, .2, -.3]),
                                           np.array([0, .3, -.2]), *center)
    x, y, visible = orthographic_forward(lon, lat, *center)
    np.testing.assert_allclose(x, [0, .2, -.3], atol=1e-12)
    np.testing.assert_allclose(y, [0, .3, -.2], atol=1e-12)
    assert front.all() and visible.all()
    assert lat[0] == pytest.approx(center[1])
    assert not orthographic_inverse(1.01, 0, *center)[2]
    assert not orthographic_forward(center[0]+180, -center[1], *center)[2]


def test_utm_control_point_and_pixel_orientation():
    # UTM zone 14 north: central meridian -99°, equator = 500000 m E, 0 m N.
    grid = RasterGrid(CRS.from_epsg(32614), Affine(1000, 0, 499500, 0, -1000, 500), 1, 1)
    pos, rows, cols = grid.mapping(np.array([-99., 0]), np.array([0., 0]), [True, True])
    np.testing.assert_array_equal(pos, [0])
    np.testing.assert_array_equal(rows, [0])
    np.testing.assert_array_equal(cols, [0])


@pytest.mark.parametrize('affine', [Affine(1, 0, -2, 0, -1, 2),
                                    Affine(.1, .03, -101, .02, -.1, 22)])
def test_pixel_centers_rotated_affine_and_visibility(affine):
    grid = RasterGrid.from_metadata(metadata(affine), (4, 4))
    rows, cols = np.indices((4, 4))
    lon = affine.a*(cols+.5)+affine.b*(rows+.5)+affine.c
    lat = affine.d*(cols+.5)+affine.e*(rows+.5)+affine.f
    pos, rr, cc = grid.mapping(lon, lat, np.ones((4, 4), bool))
    np.testing.assert_array_equal(pos, np.arange(16))
    np.testing.assert_array_equal(rr, rows.ravel())
    np.testing.assert_array_equal(cc, cols.ravel())
    assert grid.mapping(lon, lat, np.zeros((4, 4), bool))[0].size == 0


def test_half_open_edges_and_invalid_coordinates():
    grid = RasterGrid.from_metadata(metadata(), (4, 4))
    p, r, c = grid.mapping([-2, 2, 0, np.nan, 0], [2, 0, -2, 0, 91], True)
    np.testing.assert_array_equal(p, [0])
    assert r[0] == c[0] == 0


@pytest.mark.parametrize('west', [170, -190])
def test_antimeridian_native_pixel_membership(west):
    grid = RasterGrid.from_metadata(metadata(Affine(1, 0, west, 0, -1, 5), shape=(10, 20)), (10, 20))
    p, r, c = grid.mapping([175, -175, 0], [0, 0, 0], True)
    assert set(p) == {0, 1}
    assert dict(zip(p, c)) == {0: 5, 1: 15}


@pytest.mark.parametrize('change', [{'crs': 'not-a-crs'}, {'width': 5},
                                     {'transform': [0, 0, 0, 0, 0, 0]},
                                     {'transform': [1, 0, float('nan'), 0, -1, 2]},
                                     {'transform': [1, 2]}])
def test_invalid_grid_rejected(change):
    m = metadata(); m['grid'].update(change)
    with pytest.raises(ValueError):
        RasterGrid.from_metadata(m, (4, 4))


@pytest.mark.parametrize('crs,affine,shape,center,zoom', [
    ('EPSG:32614', Affine(1000, 0, 335000, 0, -1000, 2387000), (171, 161), (-99.9, 20.85), 48),
    ('EPSG:32614', Affine(1000, 0, 335000, 0, -1000, 2387000), (171, 161), (80, -20), 1),
    ('EPSG:32614', Affine(1000, 0, 335000, 0, -1000, 2387000), (171, 161), (-100, 20), 1),
    ('EPSG:3857', Affine(10000, 0, -100000, 0, -10000, 100000), (20, 20), (0, 0), 40),
    ('EPSG:4326', Affine(.1, .03, -101, .02, -.1, 22), (30, 30), (-100, 20), 20),
    ('EPSG:4326', Affine(1, 0, 170, 0, -1, 10), (20, 20), (179, 0), 4),
    ('EPSG:4326', Affine(1, 0, -190, 0, -1, 10), (20, 20), (-179, 0), 4),
    ('EPSG:4326', Affine(1, 0, -180, 0, -1, 90), (180, 360), (0, 80), 1),
])
def test_exact_gdal_mapping_matches_analytic_sampling(crs, affine, shape, center, zoom):
    grid = RasterGrid.from_metadata(metadata(affine, crs, shape), shape)
    w, h = 120, 100
    yy, xx = np.indices((h, w))
    scale = min(w, h)*.41*zoom
    lon, lat, visible = orthographic_inverse((xx+.5-w/2)/scale,
                                            (h/2-yy-.5)/scale, *center)
    p, r, c = grid.mapping(lon, lat, visible)
    expected = np.full(w*h, -1); expected[p] = r*grid.width+c
    p, r, c = grid.orthographic_mapping(w, h, center[0], center[1], zoom)
    actual = np.full(w*h, -1); actual[p] = r*grid.width+c
    np.testing.assert_array_equal(actual, expected)


@pytest.fixture
def cube(tmp_path):
    m = metadata(shape=(2, 3))
    values = np.array([[[[0.], [.5], [-9999.]], [[.7], [np.nan], [.8]]]], dtype='float32')
    valid = np.ones_like(values, dtype=bool); valid[0, 0, 1, 0] = False
    mask = np.array([[True, True, True], [False, True, True]])
    arrays = dict(X=values, valid=valid, region_mask=mask,
                  dates=np.array(['2001-01-01']), channels=np.array(['NDVI']))
    def save(change=None, meta_change=None):
        content = dict(arrays); content.update(change or {})
        current_meta = dict(m); current_meta.update(meta_change or {})
        np.savez(tmp_path/'cube.npz', allow_pickle=False, **content)
        (tmp_path/'cube_metadata.json').write_text(json.dumps(current_meta))
        return tmp_path
    return save


def test_masks_nodata_nan_and_real_zero(cube):
    values, dates, mask, _, _ = load_observations(cube(), 'ndvi')
    assert values[0, 0, 0] == 0  # A measured zero is not missing.
    assert values[0, 1, 2] == pytest.approx(.8)
    assert np.isfinite(values).sum() == 2
    assert np.isnan(values[0, 0, 1])  # QA false
    assert np.isnan(values[0, 0, 2])  # finite NoData
    assert np.isnan(values[0, 1, 0])  # outside region


@pytest.mark.parametrize('change', [dict(unit='kelvin'), dict(source='synthetic'),
                                    dict(variable='LST'), dict(dataset='synthetic'),
                                    dict(shape=[4, 5, 6, 1])])
def test_untrusted_metadata_rejected(cube, change):
    with pytest.raises(ValueError):
        load_observations(cube(meta_change=change), 'ndvi')


@pytest.mark.parametrize('change', [dict(region_mask=np.ones((1, 1), bool)),
                                    dict(region_mask=np.zeros((2, 3), bool)),
                                    dict(valid=np.ones((1, 2, 3, 1), dtype='uint8')),
                                    dict(dates=np.array(['NaT'])),
                                    dict(channels=np.array(['LST'])),
                                    dict(X=np.ones((1, 2, 3, 1))*2)])
def test_invalid_cube_rejected(cube, change):
    with pytest.raises(ValueError):
        load_observations(cube(change), 'ndvi')


def test_lst_preserves_celsius_without_double_scaling(cube):
    arrays = {'X': np.full((1, 2, 3, 1), 26.85, dtype='float32'),
              'channels': np.array(['LST'])}
    directory = cube(arrays, {'source': 'MODIS/061/MOD11A2', 'variable': 'LST', 'unit': 'degC'})
    values, _, _, _, _ = load_observations(directory, 'lst')
    np.testing.assert_allclose(values[np.isfinite(values)], 26.85)


def test_duplicate_or_descending_dates_rejected(cube):
    for dates in [['2001-01-01', '2001-01-01'], ['2001-02-01', '2001-01-01']]:
        directory = cube({'X': np.zeros((2, 2, 3, 1), dtype='float32'),
                          'valid': np.ones((2, 2, 3, 1), dtype=bool), 'dates': np.array(dates)})
        with pytest.raises(ValueError, match='strictly increasing'):
            load_observations(directory, 'ndvi')
