"""EXPLICIT SYNTHETIC storage pressure benchmark; not satellite observations."""
import json
from pathlib import Path
import resource
import sys
from time import perf_counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import zarr
from aurora.catalog import CubeReader
from aurora.jobs import atomic_json

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    directory = root/'outputs/global_test_fixtures/EXPLICIT_SYNTHETIC_LOGICAL_161GB'
    directory.mkdir(parents=True, exist_ok=False)
    group = zarr.open_group(str(directory/'cube.zarr'), mode='w', zarr_format=2)
    shape = (300, 8192, 16384, 1)
    group.create_array('X', shape=shape, chunks=(12, 32, 32, 1), dtype='float32', fill_value=np.nan)
    group.create_array('valid', shape=shape, chunks=(12, 32, 32, 1), dtype=bool, fill_value=False)
    group.create_array('region_mask', shape=shape[1:3], chunks=(32, 32), dtype=bool, fill_value=False)
    group.create_array('dates', data=np.arange('2001-01', '2026-01', dtype='datetime64[M]').astype(str))
    group.create_array('channels', data=np.array(['TEST']))
    group['X'][:12, 4096:4128, 8192:8224, :] = np.full((12, 32, 32, 1), .25, dtype='float32')
    group['valid'][:12, 4096:4128, 8192:8224, :] = True
    group['region_mask'][4096:4128, 8192:8224] = True
    metadata = {'dataset': 'synthetic_test', 'source': 'EXPLICIT MATHEMATICAL STORAGE FIXTURE, NOT SATELLITE OBSERVATIONS',
        'variable': 'test', 'unit': '1', 'variable_definition': {'minimum': -1, 'maximum': 1},
        'shape': list(shape), 'storage': {'format': 'zarr', 'path': 'cube.zarr'},
        'grid': {'crs': 'EPSG:4326', 'height': shape[1], 'width': shape[2], 'transform': [360/shape[2], 0, -180, 0, -180/shape[1], 90]}}
    atomic_json(directory/'cube_metadata.json', metadata)
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with CubeReader(directory) as reader:
        t = perf_counter(); data = reader.read(slice(0, 12), slice(4096, 4128), slice(8192, 8224), max_bytes=1024**2)
        seconds = perf_counter()-t; np.testing.assert_array_equal(data, .25)
        try: reader.read(max_bytes=64*1024**2)
        except MemoryError: full_read_rejected = True
        else: raise AssertionError('Unbounded read must be rejected')
    report = {'kind': 'EXPLICIT SYNTHETIC INFRASTRUCTURE BENCHMARK, NOT SCIENTIFIC GLOBAL COVERAGE',
        'logical_shape': list(shape), 'logical_X_bytes': int(np.prod(shape))*4,
        'physical_store_bytes': sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()),
        'read_shape': list(data.shape), 'read_array_bytes': data.nbytes, 'seconds': seconds,
        'peak_rss_before_kib': before, 'peak_rss_after_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'full_read_rejected_by_budget': full_read_rejected, 'zarr_version': zarr.__version__}
    atomic_json(root/'docs/evidence/global_engine/pressure_validation.json', report)
    print(json.dumps(report, indent=2))
