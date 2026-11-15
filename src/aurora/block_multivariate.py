"""Blocked paired-variable statistics; one FDR family across blocks and lags."""
import csv
import json
import math
from pathlib import Path
from time import perf_counter
import numpy as np
from aurora.catalog import CubeReader, variable_spec
from aurora.jobs import Job, atomic_json
from aurora.area import cell_areas
from aurora.temporal import select_interval
from aurora.multivariate import paired_anomalies, correlation_maps, lagged_pairs, scalar_association, block_bootstrap
from aurora.block_engine import Budget, spatial_blocks, disk_array, external_fdr, export_field, release_arrays, check_output_budget


def run_pair_statistics(x_directory, y_directory, output, start=None, end=None, region=None,
                        memory_mib=64, block_size=32, baseline_start=None, baseline_end=None,
                        lags=(-12, -6, -3, -1, 0, 1, 3, 6, 12), minimum=36, allow_synthetic=False):
    mx = json.loads((Path(x_directory)/'cube_metadata.json').read_text())
    my = json.loads((Path(y_directory)/'cube_metadata.json').read_text())
    if not allow_synthetic and any(m.get('dataset') != 'satellite' for m in (mx, my)):
        raise ValueError('Synthetic input requires explicit infrastructure-test opt-in')
    sx, sy = variable_spec(mx), variable_spec(my)
    job = Job(output, [x_directory, y_directory], 'multivariate', region or mx.get('region_id') or Path(x_directory).name,
              {'start': start, 'end': end, 'memory_mib': memory_mib, 'block_size': block_size,
               'minimum_pairs': minimum}, allow_synthetic)
    readers = []; begun = perf_counter()
    try:
        job.progress(0, 1, 'open-paired-sources')
        a_reader, b_reader = [CubeReader(p, check=job.check) for p in (x_directory, y_directory)]; readers = [a_reader, b_reader]
        if a_reader.grid != b_reader.grid or not np.array_equal(a_reader.dates, b_reader.dates):
            raise ValueError('Exact grid/CRS/calendar alignment required; no implicit interpolation')
        dates = a_reader.dates
        if not np.all(np.diff(dates).astype(int) == 1): raise ValueError('Explicit consecutive monthly calendar required')
        selected = np.flatnonzero(select_interval(dates, start or str(dates[0]), end or str(dates[-1])))
        calendar = dates[selected]
        if baseline_start is None:
            baseline_start = str(max(dates[0], np.datetime64('2002-01')))
            baseline_end = str(min(dates[-1], np.datetime64('2018-12')))
            if np.datetime64(baseline_start) > np.datetime64(baseline_end):
                baseline_start, baseline_end = str(dates[0]), str(dates[min(len(dates)-1, 203)])
        baseline_end = baseline_end or str(dates[-1])
        select_interval(dates, baseline_start, baseline_end)
        lags = [int(lag) for lag in lags if len(calendar)-abs(lag) >= minimum]
        if 0 not in lags: raise ValueError(f'At least {minimum} selected months required')
        h, w = a_reader.shape[1:3]; budget = Budget(len(dates), memory_mib, block_size, multivariate=True)
        output_bytes = check_output_budget(output, h*w, len(lags)*2*7)
        maps = {}
        for mode in ('raw', 'anomaly'):
            for lag in lags:
                maps[f'{mode}_{lag}'] = {name: disk_array(output, f'{mode}_{lag}_{name}', (h, w)) for name in
                    ('pearson', 'spearman', 'pairs', 'effective_n_ar1', 'p_iid_diagnostic', 'p_ar1_diagnostic', 'q_ar1_diagnostic')}
        n = len(calendar); sums = {name: np.zeros(n) for name in ('x', 'y', 'ax', 'ay')}
        observed_area = np.zeros(n); anomaly_area = np.zeros(n); count = np.zeros(n, dtype='int64')
        area_total = 0.; pixels = 0; methods = set(); shape_total = math.ceil(h/budget.side)*math.ceil(w/budget.side)
        for number, (rows, cols) in enumerate(spatial_blocks(h, w, budget.side), 1):
            job.check()
            mask = np.asarray(a_reader.arrays['region_mask'][rows, cols]) & np.asarray(b_reader.arrays['region_mask'][rows, cols])
            if mask.any():
                a = a_reader.read_series(slice(None), rows, cols, max_bytes=budget.bytes)
                b = b_reader.read_series(slice(None), rows, cols, max_bytes=budget.bytes)
                for array, spec in ((a, sx), (b, sy)):
                    if np.any((array < spec.minimum-.0001) | (array > spec.maximum+.0001)): raise ValueError('Physical range violation')
                valid = np.isfinite(a) & np.isfinite(b) & mask
                a, b = np.where(valid, a, np.nan), np.where(valid, b, np.nan)
                an, bn, _ = paired_anomalies(a, b, dates, baseline_start, baseline_end)
                a, b, an, bn = a[selected], b[selected], an[selected], bn[selected]
                area, method = cell_areas(a_reader.grid, rows, cols, check=job.check, mask=mask); methods.add(method)
                area = np.where(mask, area, 0); area_total += float(area.sum()); pixels += int(mask.sum())
                valid, av = np.isfinite(a) & np.isfinite(b), np.isfinite(an) & np.isfinite(bn)
                observed_area += np.where(valid, area, 0).sum(axis=(1, 2)); anomaly_area += np.where(av, area, 0).sum(axis=(1, 2))
                count += valid.sum(axis=(1, 2))
                for name, data, support in (('x', a, valid), ('y', b, valid), ('ax', an, av), ('ay', bn, av)):
                    sums[name] += np.where(support, data*area, 0).sum(axis=(1, 2), dtype='float64')
                for mode, aa, bb in (('raw', a, b), ('anomaly', an, bn)):
                    for lag in lags:
                        result = correlation_maps(*lagged_pairs(aa, bb, lag), minimum)
                        for name, value in result.items(): maps[f'{mode}_{lag}'][name][rows, cols] = np.where(mask, value, np.nan)
            if number % 10 == 0 or number == shape_total:
                release_arrays([array for result in maps.values() for array in result.values()])
                job.progress(number, shape_total, 'paired-native-blocks')
        if not pixels: raise ValueError('No common regional support')
        job.progress(0, 1, 'global-paired-fdr')
        family = [result for result in maps.values()]
        tests = external_fdr([r['p_ar1_diagnostic'] for r in family], [r['q_ar1_diagnostic'] for r in family], Path(output)/'paired_fdr.sqlite', job)
        for name in ('x', 'y', 'ax', 'ay'):
            denominator = observed_area if name in ('x', 'y') else anomaly_area
            sums[name] = np.divide(sums[name], denominator, out=np.full(n, np.nan), where=denominator > 0)
        coverage, ac = observed_area/area_total, anomaly_area/area_total
        sensitivity = {}
        for threshold in (.5, .7, .9, .95):
            sensitivity[str(threshold)] = {mode: scalar_association(np.where(support >= threshold, sums[x], np.nan),
                np.where(support >= threshold, sums[y], np.nan)) for mode, x, y, support in
                (('raw', 'x', 'y', coverage), ('anomaly', 'ax', 'ay', ac))}
        profiles = []
        for lag in range(-12, 13):
            if len(calendar)-abs(lag) >= 12:
                profiles.append({'lag_months': lag, **scalar_association(*lagged_pairs(
                    np.where(ac >= .7, sums['ax'], np.nan), np.where(ac >= .7, sums['ay'], np.nan), lag))})
        stride = max(1, int(np.ceil(max(h, w)/512)))
        preview = {f'{mode}_0_{name}': np.array(array[::stride, ::stride]) for mode in ('raw', 'anomaly')
                   for name, array in maps[f'{mode}_0'].items()}
        np.savez_compressed(Path(output)/'analysis.npz', **preview, dates=calendar.astype(str),
            raw_x=sums['x'], raw_y=sums['y'], anomaly_x=sums['ax'], anomaly_y=sums['ay'],
            raw_ndvi=sums['x'], raw_lst=sums['y'], anomaly_ndvi=sums['ax'], anomaly_lst=sums['ay'],
            coverage=coverage, anomaly_coverage=ac)
        with (Path(output)/'paired_monthly_series.csv').open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['date', 'x', 'y', 'x_anomaly', 'y_anomaly', 'paired_area_coverage', 'anomaly_area_coverage', 'paired_pixels'])
            for i in range(n): writer.writerow([str(calendar[i])]+[float(sums[name][i]) if np.isfinite(sums[name][i]) else '' for name in ('x', 'y', 'ax', 'ay')]+[coverage[i], ac[i], count[i]])
        units = {}
        for mode in ('raw', 'anomaly'):
            for name, array in maps[f'{mode}_0'].items():
                key = f'{mode}_{name}'; unit = 'months' if name in ('pairs', 'effective_n_ar1') else '1'
                export_field(output, key, array, mx['grid'], unit, job); units[key] = unit
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        figure = Figure(figsize=(9, 4), layout='constrained'); FigureCanvasAgg(figure)
        left, right = figure.subplots(1, 2)
        image = left.imshow(preview['anomaly_0_pearson'], vmin=-1, vmax=1, cmap='coolwarm', interpolation='nearest')
        left.set_title('Paired anomaly Pearson r'); figure.colorbar(image, ax=left)
        left.set_xlabel('Sampled native column'); left.set_ylabel('Sampled native row')
        right.scatter(sums['x'], sums['y'], s=8); right.set_xlabel(sx.identifier+' ('+sx.unit+')'); right.set_ylabel(sy.identifier+' ('+sy.unit+')')
        figure.savefig(Path(output)/'summary.png', dpi=130)
        result = {'variables': [mx['variable'].lower(), my['variable'].lower()], 'variable': mx['variable'].lower()+'__'+my['variable'].lower(),
            'units': [sx.unit, sy.unit], 'sources': [mx['source'], my['source']], 'grid': mx['grid'], 'fields': units,
            'datasets': {'ndvi': Path(x_directory).name, 'lst': Path(y_directory).name},
            'period': [str(calendar[0]), str(calendar[-1])], 'paired_observations': int(count.sum()),
            'common_regional_pixels': pixels, 'area_methods': sorted(methods), 'area_weighted': True,
            'display_stride': stride, 'export_precision': 'float64 statistics GeoTIFF/NPY; float64 decimal CSV', 'coverage_sensitivity': sensitivity, 'lag_profiles': profiles,
            'climatology': {'period': [baseline_start, baseline_end], 'minimum_samples_per_calendar_month': 8},
            'map_lags': lags, 'fdr_test_count': tests, 'actual_block_size': budget.side,
            'estimated_block_working_bytes': budget.estimated_working_bytes, 'estimated_output_disk_bytes': output_bytes, 'memory_budget_bytes': budget.bytes,
            'seconds': perf_counter()-begun,
            'methodology': ['Exact native alignment; coincident valid observations only; no gap filling',
                'Pearson/Spearman over time per native pixel; anomaly climatology on paired reference observations',
                'One BH family for raw/anomaly Pearson AR1 diagnostics across all cells and all lags',
                'Regional series weighted by ellipsoidal area; coverage thresholds are observed area fractions',
                'Positive lag pairs X(t) with Y(t+lag); no calendar compression',
                'AR1 and BH are diagnostics; missing-not-at-random bias and residual dependence remain',
                'Association and lag profiles do not establish causality']}
        atomic_json(Path(output)/'report.json', result); job.finish(**result)
        return result
    except BaseException as exc: job.fail(exc); raise
    finally:
        for reader in readers: reader.close()
