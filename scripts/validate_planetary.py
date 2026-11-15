"""Validate the local real cube against its GeoTIFFs and render desktop evidence.

Run with QT_QPA_PLATFORM=offscreen for a display-free local validation.
Does not download, generate, interpolate or modify satellite observations.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/aurora-validation-mpl')
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from PySide6 import __version__ as qt_version
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from aurora.desktop.geospatial import load_observations, orthographic_inverse
from aurora.desktop.globe import PlanetaryExplorer


def validate(output):
    output.mkdir(parents=True, exist_ok=True)
    directory = ROOT/'data/processed/queretaro'
    values, dates, mask, meta, grid = load_observations(directory, 'ndvi')
    package = ROOT/'data/incoming/queretaro'
    declared = json.loads((package/'grid.json').read_text())
    assert grid.crs == CRS.from_user_input(declared['crs'])
    np.testing.assert_array_equal(list(grid.affine)[:6], declared['transform'][:6])
    region = json.loads((package/'region.geojson').read_text())
    polygons = [transform_geom('EPSG:4326', grid.crs, f['geometry']) for f in region['features']]
    expected_mask = geometry_mask(polygons, out_shape=mask.shape,
                                  transform=grid.affine, invert=True, all_touched=False)
    np.testing.assert_array_equal(mask, expected_mask)
    with (package/'manifest.csv').open() as manifest:
        records = list(csv.DictReader(manifest))
    lookup = {str(date): i for i, date in enumerate(dates)}
    compared = 0
    for record in records:
        with rasterio.open(package/record['path']) as src:
            assert src.crs == grid.crs and src.transform == grid.affine
            assert src.shape == mask.shape
            image = src.read(1, masked=True)
            raw = image.data
            observed = mask & ~np.ma.getmaskarray(image) & np.isfinite(raw)
            expected = np.where(observed, raw, np.nan)
            np.testing.assert_array_equal(values[lookup[record['date']]], expected)
            compared += 1
    camera_checks = []
    for center, zoom in [((-99.9, 20.85), 48), ((-102.5, 23.6), 4), ((80, -20), 1)]:
        width, height = 120, 100
        yy, xx = np.indices((height, width)); scale = min(width, height)*.41*zoom
        lon, lat, visible = orthographic_inverse((xx+.5-width/2)/scale,
                                                 (height/2-yy-.5)/scale, *center)
        p, r, c = grid.mapping(lon, lat, visible)
        reference = np.full(width*height, -1); reference[p] = r*grid.width+c
        p, r, c = grid.orthographic_mapping(width, height, center[0], center[1], zoom)
        actual = np.full(width*height, -1); actual[p] = r*grid.width+c
        np.testing.assert_array_equal(actual, reference)
        camera_checks.append({'center': center, 'zoom': zoom, 'mapped_pixels': len(p),
                              'different_pixel_ids': 0})
    app = QApplication.instance() or QApplication([])
    w = PlanetaryExplorer(ROOT); w.resize(1280, 800); w.show(); app.processEvents()
    w.load_dataset(); w.planet.animation.setCurrentTime(650)
    samples = {}
    for name, camera in [('queretaro', (-99.9, 20.85, 48)),
                         ('mexico', (-102.5, 23.6, 4)), ('earth', (-100, 20, 1))]:
        w.planet.lon, w.planet.lat, w.planet.zoom = camera
        times = []
        for _ in range(5):
            t = perf_counter(); w.planet.invalidate(camera=True); app.processEvents()
            times.append((perf_counter()-t)*1000)
        samples[name] = {'camera_median_ms': float(np.median(times)),
                         'camera_max_ms': max(times)}
        w.grab().save(str(output/f'{name}.png'))
    times = []
    for _ in range(20):
        t = perf_counter(); w.step(1); app.processEvents()
        times.append((perf_counter()-t)*1000)
    samples['playback'] = {'frame_median_ms': float(np.median(times)), 'frame_max_ms': max(times)}
    # Measure the lower-resolution movement path independently of idle rendering.
    from PySide6.QtCore import QPointF
    w.planet.drag = QPointF(0, 0)
    times = []
    for _ in range(10):
        t = perf_counter(); w.planet.invalidate(camera=True); app.processEvents()
        times.append((perf_counter()-t)*1000)
    samples['moving_camera'] = {'camera_median_ms': float(np.median(times)),
                                'camera_max_ms': max(times)}
    w.planet.drag = None
    # Observe real camera animation events without asserting machine-specific FPS.
    w.planet.focus(-99.9, 20.85, 48)
    from PySide6.QtTest import QTest
    QTest.qWait(900)
    assert abs(w.planet.zoom-48) < 1e-6
    w.pause(); w.close()
    from aurora.desktop.window import AuroraWindow
    host = AuroraWindow(); host.show()
    host.tabs.setCurrentWidget(host.planetary_explorer)
    host.planetary_explorer.load_dataset()
    host.planetary_explorer.planet.animation.setCurrentTime(650)
    app.processEvents()
    host.grab().save(str(output/'application.png'))
    host.resize(1000, 680); app.processEvents()
    host.grab().save(str(output/'application_minimum.png'))
    assert host.tabs.count() == 9
    host.close()
    result = {'python': platform.python_version(), 'pyside6': qt_version,
              'dataset': meta['source'], 'crs': str(grid.crs),
              'cube_shape': list(values.shape), 'compared_geotiffs': compared,
              'regional_mask_equal': True, 'raster_values_equal': True,
              'camera_checks': camera_checks, 'timings_1280x800_offscreen': samples,
              'first_date': str(dates[0]), 'last_date': str(dates[-1]),
              'first_frame_valid_pixels': int(np.isfinite(values[0]).sum())}
    (output/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/evidence/planetary')
    validate(parser.parse_args().output)
