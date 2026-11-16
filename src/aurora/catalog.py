"""Local observed-dataset registry and bounded, windowed array access."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import threading
from collections import OrderedDict
from contextlib import contextmanager
import numpy as np
from affine import Affine
from aurora.variables import get_variable, VariableSpec
from aurora.geospatial import RasterGrid


class CubeReader:
    """NPZ is streamed to exact NPY members once, then read through memory maps.

    NPZ does not support actual random reads of compressed members. Extraction
    bounds RAM rather than pretending that NPZ is a chunked array format.
    """
    def __init__(self, directory, cache=None, check=lambda: None, cache_limit_bytes=None):
        cache_limit_bytes = cache_limit_bytes if cache_limit_bytes is not None else int(float(os.environ.get('AURORA_CACHE_LIMIT_GIB', 16))*1024**3)
        self.check = check
        self._closed = False
        self.directory = Path(directory)
        self.metadata = json.loads((self.directory/'cube_metadata.json').read_text())
        storage = self.metadata.get('storage', {'format': 'npz', 'path': 'cube.npz'})
        path = (self.directory/storage['path']).resolve()
        if not path.is_relative_to(self.directory.resolve()):
            raise ValueError('Storage must remain inside the dataset directory')
        self.format = storage['format']
        if self.format == 'npz':
            from aurora.array_cache import extract_npz
            target = extract_npz(path, cache, cache_limit_bytes, check)
            self.arrays = {name: np.load(target/f'{name}.npy', mmap_mode='r', allow_pickle=False)
                           for name in ('X', 'valid', 'region_mask', 'dates', 'channels')}
        elif self.format == 'npy':
            self.arrays = {name: np.load(path/f'{name}.npy', mmap_mode='r', allow_pickle=False)
                           for name in ('X', 'valid', 'region_mask', 'dates', 'channels')}
        elif self.format == 'zarr':
            try: import zarr
            except ImportError as exc: raise RuntimeError('Zarr is optional and not installed; use NPY or NPZ') from exc
            zarr.config.set({'async.concurrency': 4, 'threading.max_workers': 4})
            self._zarr_group = zarr.open_group(str(path), mode='r')
            self.arrays = {}

            for name in ('X', 'valid', 'region_mask', 'dates', 'channels'):
                array = self._zarr_group[name]

                if not isinstance(array, zarr.Array):
                    raise ValueError(f'Expected Zarr array: {name}')

                self.arrays[name] = array
            if self.arrays['X'].fill_value is None or not np.isnan(self.arrays['X'].fill_value):
                raise ValueError('Zarr X fill value must be NaN, never an observed zero')
            if self.arrays['valid'].fill_value not in (False, 0):
                raise ValueError('Missing Zarr validity chunks must be false')
            if self.arrays['region_mask'].fill_value not in (False, 0):
                raise ValueError('Missing Zarr regional mask chunks must be false')
        else: raise ValueError('Unsupported storage format')
        self.dates = np.asarray(self.arrays['dates'][:]).astype('datetime64[M]')
        self.shape = self.arrays['X'].shape
        if self.arrays['X'].dtype != np.dtype('float32'):
            raise ValueError('Scientific cube values must be float32 in physical units')
        if len(self.shape) != 4 or self.shape[-1] != 1 or self.shape[0] != len(self.dates):
            raise ValueError('Invalid observed cube shape')
        if self.arrays['valid'].shape != self.shape or self.arrays['valid'].dtype != bool:
            raise ValueError('Invalid validity array')
        if self.arrays['region_mask'].shape != self.shape[1:3] or self.arrays['region_mask'].dtype != bool:
            raise ValueError('Invalid regional mask')
        if np.isnat(self.dates).any() or np.any(np.diff(self.dates).astype(int) <= 0):
            raise ValueError('Invalid observation calendar')
        if 'shape' in self.metadata and list(self.shape) != self.metadata['shape']:
            raise ValueError('Shape differs from dataset metadata')
        if [str(c).lower() for c in self.arrays['channels'][:]] != [self.metadata.get('variable', '').lower()]:
            raise ValueError('Cube channel differs from metadata variable')
        self.grid = RasterGrid.from_metadata(self.metadata, self.shape[1:3])

    def read(self, time: int | slice = slice(None), rows: int | slice = slice(None), cols: int | slice = slice(None), max_bytes=128*1024**2):
        if self._closed: raise ValueError('Reader is closed')
        self.check()
        # Budget checked from indices before touching the mapped observations.
        def size(index, dimension):
            return len(range(*index.indices(dimension))) if isinstance(index, slice) else 1
        cells = size(time, self.shape[0])*size(rows, self.shape[1])*size(cols, self.shape[2])
        if self.format == 'zarr' and any(np.prod(self.arrays[name].chunks)*np.dtype(self.arrays[name].dtype).itemsize > max_bytes//4 for name in ('X', 'valid', 'region_mask')):
            raise MemoryError('Stored Zarr chunks exceed decode budget; rechunk the source')
        if cells*8 > max_bytes:
            raise MemoryError('Requested window exceeds memory budget; read temporal/spatial blocks')
        values = np.asarray(self.arrays['X'][time, rows, cols, 0], dtype='float32').copy()
        valid = np.asarray(self.arrays['valid'][time, rows, cols, 0])
        region = np.asarray(self.arrays['region_mask'][rows, cols])
        observed = valid & region & np.isfinite(values)
        nodata = self.metadata['grid'].get('nodata')
        if nodata is not None: observed &= values != nodata
        values[~observed] = np.nan
        self.release_pages()
        self.check()
        return values

    def release_pages(self):
        import mmap
        if isinstance(self.arrays, dict) and hasattr(mmap, 'MADV_DONTNEED'):
            for value in self.arrays.values():
                mapping = getattr(value, '_mmap', None)
                if mapping is not None and not mapping.closed:
                    mapping.madvise(mmap.MADV_DONTNEED)

    def read_series(self, time, rows, cols, max_bytes=128*1024**2):
        if self._closed: raise ValueError('Reader is closed')
        start, stop, step = time.indices(self.shape[0])
        if step != 1: raise ValueError('Series time slice must be contiguous')
        height, width = len(range(*rows.indices(self.shape[1]))), len(range(*cols.indices(self.shape[2])))
        if (stop-start)*height*width*8 > max_bytes: raise MemoryError('Time series block exceeds budget')
        output = np.empty((stop-start, height, width), dtype='float32')
        for first in range(start, stop, 12):
            last = min(stop, first+12)
            output[first-start:last-start] = self.read(slice(first, last), rows, cols, max_bytes=max_bytes)
        return output

    def close(self):
        if self._closed: return
        self._closed = True
        if self.format == 'zarr':
            self._zarr_group.store.close()
        for value in self.arrays.values() if isinstance(self.arrays, dict) else ():
            mapping = getattr(value, '_mmap', None)
            if mapping is not None and not mapping.closed: mapping.close()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def blocks(self, months=12, rows=256, cols=256):
        for t in range(0, self.shape[0], months):
            for y in range(0, self.shape[1], rows):
                for x in range(0, self.shape[2], cols):
                    key = (slice(t, min(t+months, self.shape[0])),
                           slice(y, min(y+rows, self.shape[1])), slice(x, min(x+cols, self.shape[2])))
                    yield key, self.read(*key)


@dataclass
class DatasetRecord:
    identifier: str
    region: str
    variable: str
    directory: Path
    metadata: dict
    dates: np.ndarray
    priority: int = 0

    @property
    def resolution(self):
        a = Affine(*self.metadata['grid']['transform'][:6])
        return [float(np.hypot(a.a, a.d)), float(np.hypot(a.b, a.e))]

    def summary(self):
        coverage = [row['coverage'] for row in self.metadata.get('coverage', []) if row.get('coverage') is not None]
        return {'id': self.identifier, 'region': self.region, 'variable': self.variable,
                'source': self.metadata['source'], 'unit': self.metadata['unit'],
                'resolution_crs_units': self.resolution, 'crs': self.metadata['grid']['crs'],
                'shape': self.metadata.get('shape'), 'start': str(self.dates[0]), 'end': str(self.dates[-1]),
                'months': len(self.dates), 'mean_declared_coverage': float(np.mean(coverage)) if coverage else None,
                'storage': self.metadata.get('storage', {'format': 'npz', 'path': 'cube.npz'})}


class DatasetRegistry:
    def __init__(self, root):
        self.root = Path(root); self.records = []; self.errors = {}
        paths = {str(path.resolve()): {} for path in (self.root/'data/processed').glob('*/cube_metadata.json')}
        registrations = self.root/'config/datasets.json'
        if registrations.exists():
            for entry in json.loads(registrations.read_text()).get('datasets', []):
                directory = (self.root/entry['path']).resolve()
                paths[str(directory/'cube_metadata.json')] = entry
        for path_string, entry in sorted(paths.items()):
            path = Path(path_string)
            try:
                m = json.loads(path.read_text())
                if m.get('dataset') != 'satellite': continue
                variable = m['variable'].lower(); spec = variable_spec(m)
                directory = path.parent
                storage = m.get('storage', {'format': 'npz', 'path': 'cube.npz'})
                if storage['format'] == 'npz':
                    with np.load(directory/storage['path'], allow_pickle=False) as data:
                        dates = data['dates'].astype('datetime64[M]')
                else:
                    with CubeReader(directory) as reader: dates = reader.dates.copy()
                if not len(dates) or np.isnat(dates).any() or np.any(np.diff(dates).astype(int) <= 0):
                    raise ValueError('Invalid calendar')
                RasterGrid.from_metadata(m, (m['grid']['height'], m['grid']['width']))
                region = entry.get('region_id') or m.get('region_id') or m.get('region') or directory.name.removesuffix('_lst').removesuffix('_ndvi')
                if not isinstance(region, str): raise ValueError('Region id must be a string')
                self.records.append(DatasetRecord(entry.get('id', directory.name), region, variable, directory, m, dates, int(entry.get('priority', 0))))
            except (ValueError, KeyError, OSError, RuntimeError, ImportError) as exc:
                self.errors[str(path)] = str(exc)

    def find(self, region, variable):
        matches = [r for r in self.records if r.region == region and r.variable == variable]
        if not matches: raise FileNotFoundError(f'No observed dataset for {region}/{variable}')
        return max(matches, key=lambda r: (r.priority, len(r.dates)))

    def regions(self):
        return sorted({r.region for r in self.records})


def dataset_mapping(root):
    registry = DatasetRegistry(root)
    return {(r.region, r.variable): r.directory.name for r in registry.records}


class ObservationSeries:
    """Lazy display series with nearest-sample overviews, never gap filling."""
    def __init__(self, directory, variable, max_dimension=1024, check=lambda: None):
        self.reader = CubeReader(directory, check=check); self.metadata = dict(self.reader.metadata)
        spec = variable_spec(self.metadata)
        self._frame_lock = threading.RLock()
        self._frames = OrderedDict(); self.cache_bytes = 0; self.cache_limit = 32*1024**2
        if (self.metadata.get('dataset') != 'satellite' or self.metadata.get('variable', '').lower() != variable
                or self.metadata.get('source') != spec.source or self.metadata.get('unit') != spec.unit
                or [str(v).lower() for v in self.reader.arrays['channels'][:]] != [variable]):
            raise ValueError('Dataset identity, channel or units disagree')
        self.spec = spec
        self.stride = max(1, int(np.ceil(max(self.reader.shape[1:3])/max_dimension)))
        self.slice = slice(None, None, self.stride)
        self.mask = np.array(self.reader.arrays['region_mask'][self.slice, self.slice], copy=True)
        grid = dict(self.metadata['grid'])
        affine = self.reader.grid.affine @ Affine.translation((1-self.stride)/2, (1-self.stride)/2) @ Affine.scale(self.stride)
        grid.update(transform=list(affine)[:6], height=self.mask.shape[0], width=self.mask.shape[1])
        self.metadata['grid'] = grid
        self.dates = self.reader.dates.astype('datetime64[D]')
        from aurora.area import cell_areas
        self.weights, self.area_method = cell_areas(self.reader.grid, self.slice, self.slice, check=self.reader.check, mask=self.mask)
        self.weights = np.where(self.mask, self.weights, 0)

    def __getitem__(self, index):
        with self._frame_lock: return self._read_frame(index)

    def _read_frame(self, index):
        if index in self._frames:
            self._frames.move_to_end(index)
            return self._frames[index]
        values = self.reader.read(index, self.slice, self.slice)
        if np.any((values < self.spec.minimum-.0001) | (values > self.spec.maximum+.0001)):
            raise ValueError('Observed values outside documented physical range')
        values.setflags(write=False)
        while self._frames and self.cache_bytes+values.nbytes > self.cache_limit:
            _, old = self._frames.popitem(last=False); self.cache_bytes -= old.nbytes
        if values.nbytes <= self.cache_limit:
            self._frames[index] = values; self.cache_bytes += values.nbytes
        return values

    def summary(self, frame):
        finite = np.isfinite(frame)
        observed_area = float(np.where(finite, self.weights, 0).sum())
        total = float(self.weights.sum())
        mean = float(np.where(finite, frame*self.weights, 0).sum()/observed_area) if observed_area > 0 else None
        return mean, observed_area/total if total > 0 else 0.

    def __len__(self): return len(self.dates)


def populate_regions(combo, root, paired=False):
    registry = DatasetRegistry(root)
    names = registry.regions()
    if paired:
        names = [name for name in names if len({r.variable for r in registry.records if r.region == name}) >= 2]
    names.sort(key=lambda name: -max(len(r.dates) for r in registry.records if r.region == name))
    combo.clear()
    for name in names: combo.addItem(name.replace('_', ' ').title(), name)
    # A planned region is never a dataset and never produces displayed values.
    config = Path(root)/'config/dataset_targets.json'
    targets = json.loads(config.read_text()) if config.exists() else {'mexico': {'resolution_m': 5000}}
    if not paired:
        for name in targets:
            if name not in names: combo.addItem(f'{name.title()} · awaiting observations', name)
    return registry


def variable_spec(metadata):
    """Known contracts or an explicit physical-unit definition supplied by data owner."""
    identifier = metadata['variable'].lower()
    definition = metadata.get('variable_definition')
    if definition is None:
        from aurora.variables import get_product
        spec = get_product(identifier, metadata['source'])
        if metadata['source'] != spec.source or metadata['unit'] != spec.unit:
            raise ValueError('Source/unit inconsistent with variable registry')
        return spec
    if identifier in ('ndvi', 'lst', 'precip') and metadata['unit'] != get_variable(identifier).unit:
        raise ValueError('Canonical variable units disagree; convert explicitly or register a distinct variable identifier')
    minimum, maximum = float(definition['minimum']), float(definition['maximum'])
    if not np.isfinite([minimum, maximum]).all() or minimum >= maximum or not metadata.get('source') or not metadata.get('unit'):
        raise ValueError('Explicit physical range, source and unit required')
    return VariableSpec(identifier.upper(), definition.get('name', identifier), metadata['source'],
                        definition.get('band', identifier), metadata['unit'],
                        metadata.get('slope_unit', metadata['unit']+'/year'), minimum, maximum,
                        1., 0., definition.get('description', 'Registered observations in physical units'), False)


def display_scale(metadata):
    spec = variable_spec(metadata); variable = metadata['variable'].lower()
    if variable == 'ndvi': return (-.2, 1., 'RdYlGn', 'NDVI · dimensionless')
    if variable == 'lst': return (-10., 70., 'turbo', 'LST · °C')
    if variable == 'precip':
        return (0., 2., 'Blues', 'Precipitation · mm/h')
    display = metadata.get('display', {})
    return (display.get('minimum', spec.minimum), display.get('maximum', spec.maximum),
            display.get('colormap', 'viridis'), spec.identifier+' · '+spec.unit)


def populate_variables(combo, registry, region, preserve=True):
    current = combo.currentData() if preserve else None
    variables = ['ndvi', 'lst']
    variables.extend(sorted({r.variable for r in registry.records if r.region == region}-set(variables)))
    combo.blockSignals(True); combo.clear()
    for variable in variables:
        available = any(r.region == region and r.variable == variable for r in registry.records)
        combo.addItem(variable.upper()+('' if available else ' · unavailable'), variable)
    index = combo.findData(current)
    default = next((i for i in range(combo.count()) if any(r.region == region and r.variable == combo.itemData(i) for r in registry.records)), 0)
    combo.setCurrentIndex(index if index >= 0 else default); combo.blockSignals(False)
