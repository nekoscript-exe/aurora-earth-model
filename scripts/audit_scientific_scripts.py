"""Compare five historical scientific scripts on identical real Querétaro inputs.

This local audit requires the original GeoTIFF packages and saved historical run.
Inputs are read only. Extracted original source and reports use a new directory.
"""
import argparse
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from affine import Affine
import numpy as np
import pandas as pd


def main():
    if not __debug__:
        raise RuntimeError('Scientific audit assertions require Python without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scientific-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', default='96e7bca')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = args.scientific_root.resolve()
    revision = subprocess.check_output(
        ['git', 'rev-parse', '--verify', '--end-of-options', args.baseline+'^{commit}'],
        cwd=root, text=True).strip()
    sys.path[:0] = [str(root/'src'), str(root/'scripts')]
    output = args.output
    output.mkdir(parents=True, exist_ok=False)

    def load(name, original):
        path = root/'scripts'/f'{name}.py'
        if original:
            path = output/f'{name}_original.py'
            path.write_bytes(subprocess.check_output(
                ['git', 'show', f'{revision}:scripts/{name}.py'], cwd=root))
        spec = importlib.util.spec_from_file_location(f'audit_{name}_{original}', path)
        if spec is None or spec.loader is None:
            raise ImportError(f'Cannot load scientific script: {name}')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    report = {}
    for name, variable in [('qa_grid', 'ndvi'), ('validate_data', 'ndvi'), ('validate_lst', 'lst')]:
        original, current = load(name, True), load(name, False)
        dataset = 'queretaro' if variable == 'ndvi' else 'queretaro_lst'
        package = source/'data/incoming'/dataset
        grid = json.loads((package/'grid.json').read_text())
        grid['affine'] = Affine(*grid['transform'])
        with (package/'manifest.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        with np.load(source/'data/processed'/dataset/'cube.npz', allow_pickle=False) as cube:
            mask = cube['region_mask']
        for row in rows:
            parameters = (package/row['path'], grid, mask)
            if name == 'qa_grid':
                first = original.check_file(*parameters, -.2, 1.)
                second = current.check_file(*parameters, -.2, 1.)
            else:
                first = original.check_raster(*parameters)
                second = current.check_raster(*parameters)
            assert first == second, (name, row['date'], first, second)
        report[name] = {'real_rasters_compared': len(rows), 'outputs_exact': True}

    original, current = load('sensitivity_regional', True), load('sensitivity_regional', False)
    series = source/'outputs/queretaro/history/monthly_series.csv'
    for first, second in zip(original.run(series), current.run(series)):
        pd.testing.assert_frame_equal(first, second, check_exact=True)
    report['sensitivity_regional'] = {'real_monthly_rows': len(pd.read_csv(series)), 'outputs_exact': True}

    original, current = load('validate_independent', True), load('validate_independent', False)
    folder = source/'outputs/queretaro/history'
    pd.testing.assert_frame_equal(original.check_outputs(folder), current.check_outputs(folder), check_exact=True)
    with np.load(source/'data/processed/queretaro/cube.npz', allow_pickle=False) as cube:
        values = cube['X']
        dates = cube['dates'].astype('datetime64[M]')
        for row, col in [(20, 20), (40, 40), (60, 60)]:
            first = original.annual_means(dates, values[:, row, col, 0])
            second = current.annual_means(dates, values[:, row, col, 0])
            for a, b in zip(first, second):
                np.testing.assert_array_equal(a, b)
            assert original.regress(*first) == current.regress(*second)
    report['validate_independent'] = {'real_history_checks': len(current.check_outputs(folder)),
                                      'pixel_series': 3, 'outputs_exact': True}
    (output/'results.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
