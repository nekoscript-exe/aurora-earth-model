"""Real-data scientific equivalence, export and functional UI evidence.

Conventional full-array comparison is intentionally restricted to the small real
Querétaro cubes; it is not a claim of national or global scientific validation.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path
import resource
import sys
from time import perf_counter, monotonic, sleep
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if 'MPLCONFIGDIR' not in os.environ:
    os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp(prefix='aurora-validation-mpl-')
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))
import numpy as np
import pandas as pd
import zarr
import pyproj
from aurora.catalog import CubeReader, DatasetRegistry
from aurora.trend import annual_composite, ols_trend, sen_trend, hac_significance, fdr_correction
from aurora.area import cell_areas
from aurora.multivariate import paired_anomalies, correlation_maps, lagged_pairs
from aurora.exports import export_bundle
from aurora.model_catalog import ModelRegistry
from aurora.model_exports import export_model_bundle
from aurora.jobs import atomic_json


def wait_ui(app, condition, seconds=30):
    deadline = monotonic()+seconds
    while not condition() and monotonic() < deadline:
        app.processEvents(); sleep(.005)
    app.processEvents()
    if not condition(): raise TimeoutError('Asynchronous UI operation did not finish')


def validate_real(output, export_root=None):
    registry = DatasetRegistry(ROOT); results = {}; native = {}; masks = {}
    for variable, original_name in [('ndvi', 'queretaro'), ('lst', 'queretaro_lst')]:
        original = ROOT/'data/processed'/original_name
        store = ROOT/'outputs/global_engine/stores'/f'queretaro_{variable}_zarr'
        with CubeReader(original) as a, CubeReader(store) as b:
            for first in range(0, a.shape[0], 12):
                for name in ('X', 'valid'):
                    np.testing.assert_array_equal(a.arrays[name][first:first+12], b.arrays[name][first:first+12])
            for name in ('region_mask', 'dates', 'channels'): np.testing.assert_array_equal(a.arrays[name][:], b.arrays[name][:])
            values = a.read_series(slice(None), slice(None), slice(None))
            mask = np.array(a.arrays['region_mask'][:]); dates = a.dates.copy(); grid = a.grid
        native[variable] = values; masks[variable] = mask
        annual, years = annual_composite(values[..., None], dates)
        fit = ols_trend(annual, years); hac = hac_significance(annual, years)
        references = {'trend_slope': fit['slope'], 'trend_p': fit['p'], 'trend_change': fit['change'],
                      'trend_n': fit['n'], 'trend_sen': sen_trend(annual, years), 'trend_hac_p': hac['p_hac'],
                      'trend_q': fdr_correction(fit['p'])[0], 'trend_hac_q': fdr_correction(hac['p_hac'])[0]}
        directory = ROOT/'outputs/global_engine'/f'queretaro_{variable}_final'
        maximum = {}
        for name, expected in references.items():
            expected = np.where(mask, expected, np.nan); actual = np.load(directory/f'{name}.npy', mmap_mode='r')
            np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12, equal_nan=True)
            finite = np.isfinite(expected); maximum[name] = float(np.max(np.abs(actual[finite]-expected[finite]), initial=0))
        areas, method = cell_areas(grid, mask=mask); areas = np.where(mask, areas, 0)
        observed = np.isfinite(values)
        observed_area = np.where(observed, areas, 0).sum(axis=(1, 2))
        mean = np.divide(np.where(observed, values*areas, 0).sum(axis=(1, 2)), observed_area,
                         out=np.full(len(values), np.nan), where=observed_area > 0)
        series = pd.read_csv(directory/'monthly_series.csv')
        np.testing.assert_allclose(series['mean'], mean, rtol=1e-12, atol=1e-12, equal_nan=True)
        np.testing.assert_allclose(series['coverage'], observed_area/areas.sum(), rtol=1e-12)
        manifest = json.loads((directory/'manifest.json').read_text()); assert manifest['status'] == 'complete'
        results[variable] = {'exact_raw_zarr_roundtrip': True, 'max_absolute_map_differences': maximum,
            'area_weighted_monthly_series_matches': True, 'area_method': method,
            'seconds': manifest['seconds'], 'block_size': manifest['actual_block_size'],
            'configured_working_memory_mib': manifest['memory_budget_bytes']/1024**2,
            'estimated_block_working_mib': manifest['estimated_block_working_bytes']/1024**2}
    a, b = native['ndvi'], native['lst']; valid = np.isfinite(a) & np.isfinite(b)
    a, b = np.where(valid, a, np.nan), np.where(valid, b, np.nan)
    an, bn, _ = paired_anomalies(a, b, dates)
    pairs = ROOT/'outputs/global_engine/queretaro_paired_final'
    pair_report = json.loads((pairs/'report.json').read_text()); p_family = []; order = []
    max_coefficient_difference = 0.
    for mode, x, y in [('raw', a, b), ('anomaly', an, bn)]:
        for lag in pair_report['map_lags']:
            reference = correlation_maps(*lagged_pairs(x, y, lag))
            mask = masks['ndvi'] & masks['lst']
            for field in ('pearson', 'spearman', 'p_ar1_diagnostic'):
                expected = np.where(mask, reference[field], np.nan)
                actual = np.load(pairs/f'{mode}_{lag}_{field}.npy', mmap_mode='r')
                np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-12, equal_nan=True)
                if field in ('pearson', 'spearman'):
                    finite = np.isfinite(expected); max_coefficient_difference = max(max_coefficient_difference,
                        float(np.max(np.abs(actual[finite]-expected[finite]), initial=0)))
            p_family.append(np.where(mask, reference['p_ar1_diagnostic'], np.nan)); order.append(f'{mode}_{lag}')
    q, _ = fdr_correction(np.stack(p_family))
    for i, name in enumerate(order):
        np.testing.assert_allclose(np.load(pairs/f'{name}_q_ar1_diagnostic.npy'), q[i], rtol=1e-11, atol=1e-12, equal_nan=True)
    results['paired'] = {'max_coefficient_difference': max_coefficient_difference, 'global_fdr_matches_full_family': True,
        'paired_observations': pair_report['paired_observations'], 'seconds': pair_report['seconds'],
        'block_size': pair_report['actual_block_size'], 'area_weighted': True}
    # Preserve all previous predictive artifacts included in AURORA 5's audit.
    preserved = json.loads((ROOT/'docs/evidence/aurora5/ndvi_preservation.json').read_text())
    previous = json.loads((ROOT/'docs/evidence/aurora5/artifact_manifest.json').read_text())['files']
    for name, data in previous.items():
        if name.startswith('outputs/'):
            preserved[name] = data['sha256']
    for name, digest in preserved.items():
        with (ROOT/name).open('rb') as file: assert hashlib.file_digest(file, 'sha256').hexdigest() == digest, name
    results['preserved_historical_files'] = len(preserved)
    export_root = Path(export_root) if export_root is not None else ROOT/'outputs/global_exports'
    bundle = export_root/'queretaro_ndvi_scientific'
    if not bundle.exists(): export_bundle(ROOT/'outputs/global_engine/queretaro_ndvi_final', bundle)
    models = ModelRegistry(ROOT, registry)
    model = models.find('queretaro', 'lst')
    model_bundle = export_root/'queretaro_lst_predictive'
    if not model_bundle.exists(): export_model_bundle(model, model_bundle)
    for folder in (bundle, model_bundle):
        assert all(list(folder.glob('*.'+ext)) for ext in ('csv', 'json', 'tif', 'png'))
    results['four_format_exports'] = [str(folder.relative_to(output)) if folder.is_relative_to(output)
                                    else str(folder.relative_to(ROOT)) for folder in (bundle, model_bundle)]
    results['available_models'] = [{'region': m['region'], 'variable': m['variable']} for m in models.models]
    atomic_json(output/'scientific_validation.json', results)
    return results


def validate_ui(output):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    import shiboken6
    from aurora.desktop.window import AuroraWindow
    qt_errors = []
    old_hook = sys.excepthook
    def hook(kind, value, trace):
        qt_errors.append(str(value)); old_hook(kind, value, trace)
    sys.excepthook = hook
    app = QApplication.instance() or QApplication([]); window = AuroraWindow(); window.show()
    wait_ui(app, lambda: window.ai_lab.model_registry is not None and not window.io_jobs.busy('results'))
    assert window.result_selector.count() > 0
    visual = output/'visual'; visual.mkdir(exist_ok=True)
    window.tabs.setCurrentWidget(window.summary); window.grab().save(str(visual/'scientific_results.png'))
    window.tabs.setCurrentWidget(window.map_panel); window.grab().save(str(visual/'spatial_analysis.png'))
    window.tabs.setCurrentWidget(window.series_canvas); window.grab().save(str(visual/'temporal_analysis.png'))
    explorer = window.planetary_explorer; window.tabs.setCurrentWidget(explorer)
    explorer.load_dataset(asynchronous=True)
    wait_ui(app, lambda: explorer.values is not None and not explorer.reader_jobs.busy('dataset') and not explorer.reader_jobs.busy('frame'))
    explorer.planet.animation.setCurrentTime(650); app.processEvents(); window.grab().save(str(visual/'zarr_planetary.png'))
    machine = window.time_machine
    wait_ui(app, lambda: not machine.reader_jobs.busy('dataset') and not machine.reader_jobs.busy('frame'))
    assert machine.values is not None and hasattr(machine, 'image'), machine.details.text()
    window.tabs.setCurrentWidget(machine); app.processEvents(); window.grab().save(str(visual/'zarr_time_machine.png'))
    lab = window.multivariate_lab; window.tabs.setCurrentWidget(lab); app.processEvents()
    assert lab.output and (lab.output/'manifest.json').exists()
    window.grab().save(str(visual/'blocked_multivariate.png'))
    ai = window.ai_lab; window.tabs.setCurrentWidget(ai); app.processEvents()
    assert {ai.variable.itemData(i) for i in range(ai.variable.count())} == {'ndvi', 'lst'}
    assert {ai.region.itemData(i) for i in range(ai.region.count())} == {'queretaro'}
    for variable in ('ndvi', 'lst'):
        ai.variable.setCurrentIndex(ai.variable.findData(variable))
        for index in range(ai.view.count()):
            ai.view.setCurrentIndex(index); app.processEvents()
            assert not any(text.get_text() == 'Predictive results unavailable' for ax in ai.figure.axes for text in ax.texts), ai.details.text()
        ai.view.setCurrentIndex(0); app.processEvents(); window.grab().save(str(visual/f'evaluated_{variable}.png'))
    # An actual GUI-created short job must publish a result and preserve responsiveness.
    window.variable.setCurrentIndex(window.variable.findData('lst')); window.temporal.set_interval('2025-01', '2025-12')
    window.run(); job_directory = window.output_path
    assert job_directory is not None, window.status.text()
    from PySide6.QtCore import QProcess
    wait_ui(app, lambda: window.process.state() == QProcess.ProcessState.NotRunning, 60)
    assert json.loads((job_directory/'manifest.json').read_text())['status'] == 'complete'
    assert json.loads((job_directory/'metrics.json').read_text())['eligibility']['eligible'] is False
    window.temporal.set_interval('2001-01', '2025-12'); window.run(); cancelled = window.output_path
    assert cancelled is not None, window.status.text()
    window.cancel_operation()
    wait_ui(app, lambda: window.process.state() == QProcess.ProcessState.NotRunning, 60)
    assert json.loads((cancelled/'manifest.json').read_text())['status'] == 'cancelled'
    result = {'scientific_result_choices': window.result_selector.count(), 'ui_tabs': window.tabs.count(),
              'zarr_loads': ['Planetary Explorer', 'Time Machine'], 'evaluated_predictive_views': 16,
              'gui_descriptive_job': str(job_directory.relative_to(ROOT)), 'gui_cancelled_job': str(cancelled.relative_to(ROOT))}
    window.close(); shiboken6.delete(window); app.processEvents()
    sys.excepthook = old_hook
    assert not qt_errors, qt_errors
    result['unhandled_qt_errors'] = qt_errors
    atomic_json(output/'ui_validation.json', result)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--ui-only', action='store_true')
    mode.add_argument('--scientific-only', action='store_true')
    parser.add_argument('--output', type=Path, help='Independent evidence/export directory')
    parser.add_argument('--data-root', type=Path, help='Read-only historical scientific checkout; requires --scientific-only')
    args = parser.parse_args()
    if args.data_root is not None:
        if not args.scientific_only:
            parser.error('--data-root requires --scientific-only; GUI jobs must not write to an alternate source')
        ROOT = args.data_root.resolve()
    output = args.output or ROOT/'docs/evidence/global_engine'
    output.mkdir(parents=True, exist_ok=True)
    if not args.ui_only:
        export_root = output/'exports' if args.output is not None else None
        print(json.dumps(validate_real(output, export_root=export_root), indent=2), flush=True)
    if not args.scientific_only:
        print(json.dumps(validate_ui(output), indent=2), flush=True)
    atomic_json(output/'environment.json', {'python': sys.version, 'zarr': zarr.__version__, 'pyproj': pyproj.__version__,
        'validation_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
