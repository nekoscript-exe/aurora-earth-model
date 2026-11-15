"""Native-grid blocked statistics with global FDR and area-weighted summaries."""
import csv
import json
import math
import os
import shutil
import sqlite3
from pathlib import Path
from time import perf_counter
import numpy as np
import rasterio
from rasterio.windows import Window
from affine import Affine
from aurora.catalog import CubeReader, variable_spec
from aurora.temporal import select_interval, trend_eligibility
from aurora.trend import annual_composite, ols_trend, sen_trend, residual_diagnostics, hac_significance
from aurora.area import cell_areas
from aurora.jobs import Job, Cancelled, atomic_json


class Budget:
    def __init__(self, months, memory_mib=64, block_size=32, multivariate=False):
        if memory_mib < 8 or block_size < 1: raise ValueError('Need memory_mib >=8 and positive block size')
        self.bytes = int(memory_mib*1024**2)
        # Conservative live-array accounting, excluding interpreter/library base RSS.
        self.per_cell = months*(256 if multivariate else 80)+int(math.ceil(months/12))*512+256
        if self.per_cell > self.bytes//2: raise MemoryError('Even one complete time series exceeds the requested budget')
        cells = max(1, (self.bytes//2)//self.per_cell)
        self.side = min(block_size, max(1, math.isqrt(cells)))
        self.estimated_working_bytes = self.side**2*self.per_cell


def spatial_blocks(height, width, side):
    for y in range(0, height, side):
        for x in range(0, width, side):
            yield slice(y, min(height, y+side)), slice(x, min(width, x+side))


def disk_array(directory, name, shape):
    array = np.lib.format.open_memmap(Path(directory)/f'{name}.npy', mode='w+', dtype='float64', shape=shape)
    for start in range(0, shape[0], 64): array[start:start+64] = np.nan
    array.flush()
    return array


def external_fdr(p_maps, q_maps, database, job=None):
    """Exact BH over ALL maps/cells, using SQLite's disk-backed sort, not per tile."""
    connection = sqlite3.connect(database)
    connection.execute('PRAGMA cache_size=-4096'); connection.execute('PRAGMA temp_store=FILE')
    connection.execute('CREATE TABLE p (id INTEGER PRIMARY KEY, value REAL)')
    def check():
        if job: job.check()
    if job:
        connection.set_progress_handler(lambda: int(job.cancel_path.exists() or job.output.with_suffix('.cancel').exists()), 10000)
    try:
        offset = 0
        for array in p_maps:
            width = array.shape[1]
            for start in range(0, array.shape[0], 32):
                check(); data = np.asarray(array[start:start+32]).ravel(); good = np.flatnonzero(np.isfinite(data))
                if np.any((data[good] < 0) | (data[good] > 1)): raise ValueError('Invalid p-value')
                connection.executemany('INSERT INTO p VALUES (?,?)',
                    ((int(offset+start*width+i), float(data[i])) for i in good))
            offset += array.size
        connection.commit(); count = connection.execute('SELECT COUNT(*) FROM p').fetchone()[0]
        connection.execute('CREATE INDEX ordered ON p(value DESC)')
        cursor = connection.execute('SELECT id,value FROM p ORDER BY value DESC, id DESC')
        sizes = np.cumsum([0]+[array.size for array in q_maps]); rank = count; running = 1.
        for batch_start in range(0, count, 4096):
            check()
            for position, value in cursor.fetchmany(4096):
                running = min(running, value*count/rank, 1.); rank -= 1
                which = int(np.searchsorted(sizes, position, side='right')-1)
                q_maps[which].flat[position-sizes[which]] = running
            release_arrays(q_maps)
        release_arrays(q_maps)
        return count
    except sqlite3.OperationalError:
        check(); raise
    finally: connection.close()


def export_field(output, name, values, grid, unit, job=None):
    height, width = values.shape
    with rasterio.open(Path(output)/f'{name}.tif', 'w', driver='GTiff', height=height, width=width,
                       count=1, dtype='float64', crs=grid['crs'], transform=Affine(*grid['transform'][:6]),
                       nodata=-9999, compress='deflate', tiled=True, blockxsize=256, blockysize=256) as dst:
        dst.update_tags(unit=unit, method='native-grid scientific statistic', metadata='manifest.json')
        for y in range(0, height, 128):
            if job: job.check()
            data = values[y:y+128]
            dst.write(np.where(np.isfinite(data), data, -9999).astype('float64'), 1,
                      window=Window(0, y, width, data.shape[0]))
        levels = [factor for factor in (2, 4, 8, 16, 32, 64) if max(height, width)/factor >= 256 and min(height, width)//factor >= 1]
        for factor in levels:
            if job: job.check()
        if levels:
            from rasterio.enums import Resampling
            dst.build_overviews(levels, Resampling.nearest)
            dst.update_tags(ns='rio_overview', resampling='nearest')


def export_preview(output, fields, grid, variable, unit):
    # Bounded PNG is a visualization, never a replacement observation product.
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    figure = Figure(figsize=(9, 4), layout='constrained'); FigureCanvasAgg(figure)
    axes = figure.subplots(1, 2)
    stride = max(1, int(np.ceil(max(next(iter(fields.values())).shape)/512)))
    first = 'trend_slope' if 'trend_slope' in fields else 'coverage'
    for ax, name in zip(axes, [first, 'coverage']):
        image = ax.imshow(fields[name][::stride, ::stride], cmap='coolwarm' if name == 'trend_slope' else 'viridis', interpolation='nearest')
        ax.set_title(f'{variable} · {name}'); ax.set_xlabel('Native column'); ax.set_ylabel('Native row')
        figure.colorbar(image, ax=ax, label=unit+'/year' if name == 'trend_slope' else 'valid fraction')
    figure.savefig(Path(output)/'summary.png', dpi=130)


def run_statistics(dataset, output, start=None, end=None, region=None, memory_mib=64,
                   block_size=32, allow_synthetic=False, include_hac=True, include_sen=True):
    metadata = json.loads((Path(dataset)/'cube_metadata.json').read_text())
    if metadata.get('dataset') != 'satellite' and not allow_synthetic:
        raise ValueError('Non-observational input requires explicit --allow-synthetic')
    spec = variable_spec(metadata)
    region = region or metadata.get('region_id') or Path(dataset).name
    job = Job(output, [dataset], 'statistics', region,
              {'start': start, 'end': end, 'memory_mib': memory_mib, 'requested_block_size': block_size,
               'min_months_per_year': 9, 'min_valid_years': 15, 'alpha': .05,
               'sen': include_sen, 'hac': include_hac}, allow_synthetic)
    began = perf_counter(); reader = None
    try:
        job.progress(0, 1, 'open-source')
        reader = CubeReader(dataset, check=job.check)
        dates = reader.dates
        start, end = start or str(dates[0]), end or str(dates[-1])
        selected = np.flatnonzero(select_interval(dates, start, end))
        calendar = dates[selected]; time = slice(int(selected[0]), int(selected[-1])+1)
        if not np.all(np.diff(calendar).astype(int) == 1):
            # Annual aggregation still works but explicit gaps require an explicit calendar first.
            raise ValueError('Calendar has gaps; provide explicit monthly missing frames, never compressed time')
        eligibility = trend_eligibility(calendar)
        budget = Budget(len(calendar), memory_mib, block_size)
        h, w = reader.shape[1:3]; shape = (h, w)
        names = ['coverage']
        if eligibility['eligible']:
            names += ['trend_slope', 'trend_p', 'trend_q', 'trend_change', 'trend_n', 'trend_lag1', 'trend_significant']
            if include_sen: names += ['trend_sen']
            if include_hac: names += ['trend_hac_p', 'trend_hac_q']
        output_bytes = check_output_budget(output, h*w, len(names))
        fields = {name: disk_array(output, name, shape) for name in names}
        n = len(calendar); sums = np.zeros(n); weights = np.zeros(n); counts = np.zeros(n, dtype='int64')
        area_total = 0.; region_pixels = 0; area_methods = set()
        total = math.ceil(h/budget.side)*math.ceil(w/budget.side)
        for number, (rows, cols) in enumerate(spatial_blocks(h, w, budget.side), 1):
            job.check(); mask = np.asarray(reader.arrays['region_mask'][rows, cols])
            if mask.any():
                X = reader.read_series(time, rows, cols, max_bytes=budget.bytes)
                if np.any((X < spec.minimum-.0001) | (X > spec.maximum+.0001)):
                    raise ValueError('Observed physical range violated')
                area, method = cell_areas(reader.grid, rows, cols, check=job.check, mask=mask); area_methods.add(method)
                cell_weight = np.where(mask, area, 0)
                area_total += float(cell_weight.sum()); region_pixels += int(mask.sum())
                valid = np.isfinite(X)
                sums += np.where(valid, X*cell_weight, 0).sum(axis=(1, 2), dtype='float64')
                weights += np.where(valid, cell_weight, 0).sum(axis=(1, 2), dtype='float64')
                counts += valid.sum(axis=(1, 2))
                fields['coverage'][rows, cols] = np.where(mask, valid.mean(axis=0), np.nan)
                if eligibility['eligible']:
                    annual, years = annual_composite(X[..., None], calendar, min_months=9)
                    fit = ols_trend(annual, years)
                    for key, name in [('slope', 'trend_slope'), ('p', 'trend_p'), ('change', 'trend_change'), ('n', 'trend_n')]:
                        fields[name][rows, cols] = np.where(mask, fit[key], np.nan)
                    fields['trend_lag1'][rows, cols] = residual_diagnostics(annual, years, fit)['lag1']
                    if include_sen: fields['trend_sen'][rows, cols] = sen_trend(annual, years)
                    if include_hac: fields['trend_hac_p'][rows, cols] = hac_significance(annual, years)['p_hac']
            if number % 10 == 0 or number == total:
                release_arrays(list(fields.values())); job.progress(number, total, 'native-grid-blocks')
        if region_pixels == 0: raise ValueError('Empty regional mask')
        if eligibility['eligible']:
            job.progress(0, 1, 'global-fdr')
            tests = external_fdr([fields['trend_p']], [fields['trend_q']], Path(output)/'fdr.sqlite', job)
            if include_hac:
                external_fdr([fields['trend_hac_p']], [fields['trend_hac_q']], Path(output)/'fdr_hac.sqlite', job)
            for rows, cols in spatial_blocks(h, w, budget.side):
                q = fields['trend_q'][rows, cols]
                fields['trend_significant'][rows, cols] = np.where(np.isfinite(q), (q <= .05).astype(float), np.nan)
        else: tests = 0
        mean = np.divide(sums, weights, out=np.full(n, np.nan), where=weights > 0)
        with (Path(output)/'monthly_series.csv').open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['date', 'mean', 'coverage', 'valid_pixels', 'observed_area_m2', 'unit'])
            for i in range(n): writer.writerow([str(calendar[i]), float(mean[i]) if np.isfinite(mean[i]) else '',
                                               float(weights[i]/area_total), int(counts[i]), float(weights[i]), spec.unit])
        # Native coordinates accompany every CSV cell, exported in blocks.
        with (Path(output)/'spatial_statistics.csv').open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['row', 'column', 'x_center', 'y_center']+list(fields))
            for rows, cols in spatial_blocks(h, w, budget.side):
                job.check(); mask = np.asarray(reader.arrays['region_mask'][rows, cols])
                for yy, xx in zip(*np.nonzero(mask)):
                    y, x = rows.start+yy, cols.start+xx
                    east, north = reader.grid.affine @ (x+.5, y+.5)
                    writer.writerow([y, x, east, north]+[float(a[y, x]) if np.isfinite(a[y, x]) else '' for a in fields.values()])
        units = {}
        for i, (name, array) in enumerate(fields.items()):
            units[name] = (spec.unit+'/year' if name in ('trend_slope', 'trend_sen') else spec.unit if name == 'trend_change'
                           else 'years' if name == 'trend_n' else '1')
            array.flush(); export_field(output, name, array, metadata['grid'], units[name], job)
            job.progress(i+1, len(fields), 'export')
        export_preview(output, fields, metadata['grid'], spec.identifier, spec.unit)
        result = {'variable': metadata['variable'].lower(), 'unit': spec.unit, 'slope_unit': spec.slope_unit,
                  'source': metadata['source'], 'period': [str(calendar[0]), str(calendar[-1])], 'grid': metadata['grid'],
                  'fields': units, 'region_pixels': region_pixels, 'region_area_m2': area_total,
                  'area_methods': sorted(area_methods), 'export_precision': 'float64 statistics GeoTIFF/NPY; float64 decimal CSV', 'eligibility': eligibility, 'fdr_test_count': tests,
                  'methodology': ['Native-grid annual mean with at least 9 observed months',
                     'OLS/Sen require 15 valid years per pixel; HAC requires complete consecutive annual series',
                     'BH applied to the entire regional family, independently for OLS and HAC, never per block',
                     'Area-weighted means and observed-area coverage; no filling or resampling of observations',
                     'Nominal significance does not remove all temporal or spatial dependence; no causal inference'],
                  'actual_block_size': budget.side, 'estimated_block_working_bytes': budget.estimated_working_bytes,
                  'memory_budget_bytes': budget.bytes, 'estimated_output_disk_bytes': output_bytes, 'seconds': perf_counter()-began}
        atomic_json(Path(output)/'metrics.json', result)
        job.finish(**result)
        return result
    except BaseException as exc:
        job.fail(exc); raise
    finally:
        if reader: reader.close()


def release_arrays(arrays):
    import mmap
    for array in arrays:
        array.flush()
        mapping = getattr(array, '_mmap', None)
        if mapping is not None and hasattr(mmap, 'MADV_DONTNEED'): mapping.madvise(mmap.MADV_DONTNEED)


def check_output_budget(directory, cells, fields):
    # Native arrays, double-precision raster products, CSV and FDR scratch allowance.
    estimate = int(cells)*(int(fields)*32+128)
    limit = int(float(os.environ.get('AURORA_RESULT_DISK_LIMIT_GIB', 16))*1024**3)
    if estimate > limit or estimate > shutil.disk_usage(directory).free:
        raise MemoryError('Estimated result/scratch disk exceeds budget; use a coarser native dataset or explicitly increase AURORA_RESULT_DISK_LIMIT_GIB')
    return estimate
