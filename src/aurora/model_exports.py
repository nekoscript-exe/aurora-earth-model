"""Portable predictive result exports, qualified against the evaluated source."""
import csv
import json
from pathlib import Path
import shutil
import numpy as np
import rasterio
from rasterio.windows import Window
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from aurora.jobs import atomic_json, Cancelled, fingerprint
from aurora.model_catalog import artifact_stamp


def export_model_bundle(model, output):
    output = Path(output)
    if fingerprint(model['source']['directory'])['fingerprint'] != model['source']['fingerprint'] or artifact_stamp(model['directory']) != model['artifacts']:
        raise ValueError('Stale predictive run')
    if output.with_suffix('.cancel').exists(): raise Cancelled('Export cancelled before start')
    output.mkdir(parents=True, exist_ok=False)
    def check():
        if (output/'CANCEL').exists() or output.with_suffix('.cancel').exists(): raise Cancelled('Predictive export cancelled')
    try:
        folder = Path(model['directory']); benchmark = model['benchmark']
        with (output/'benchmark.csv').open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['model', 'mae', 'rmse', 'r2', 'observations', 'mae_rmse_unit', 'test_start', 'test_end'])
            for name, values in benchmark['results'].items():
                writer.writerow([name, values['mae'], values['rmse'], values['r2'], values['observations'], model['unit'], *model['period']])
        atomic_json(output/'benchmark.json', benchmark)
        for engine in ('xgboost', 'convlstm'):
            check(); source = folder/'forecast'/engine/f"forecast_{model['variable']}.tif"
            target = output/f"{engine}_{model['variable']}.tif"; shutil.copyfile(source, target)
            metadata = json.loads((source.parent/'forecast_metadata.json').read_text())
            atomic_json(output/f'{engine}_metadata.json', metadata)
            with rasterio.open(source) as src, (output/f'{engine}_estimates.csv').open('w', newline='') as stream:
                writer = csv.writer(stream); writer.writerow(['row', 'column', 'x_center', 'y_center', 'estimate', 'unit', 'forecast_date', 'product'])
                for _, window in src.block_windows(1):
                    check(); values = src.read(1, window=window, masked=True)
                    for y, x in zip(*np.nonzero(~np.ma.getmaskarray(values))):
                        row, col = int(window.row_off+y), int(window.col_off+x)
                        east, north = src.transform @ (col+.5, row+.5)
                        writer.writerow([row, col, east, north, float(values[y, x]), model['unit'], metadata['forecast_date'], 'model estimate; not an observation'])
                scale = max(1, int(np.ceil(max(src.height, src.width)/512)))
                image = src.read(1, out_shape=(max(1, src.height//scale), max(1, src.width//scale)), masked=True)
            figure = Figure(figsize=(6, 4), layout='constrained'); FigureCanvasAgg(figure); axis = figure.add_subplot(111)
            handle = axis.imshow(image, interpolation='nearest'); axis.set_title(f"{engine} · {metadata['forecast_date']} · model estimate")
            figure.colorbar(handle, ax=axis, label=model['unit']); figure.savefig(output/f'{engine}.png', dpi=120)
        check()
        if fingerprint(model['source']['directory'])['fingerprint'] != model['source']['fingerprint'] or artifact_stamp(model['directory']) != model['artifacts']:
            raise RuntimeError('Source or model artifacts changed during export')
        atomic_json(output/'export_status.json', {'status': 'complete', 'region': model['region'], 'variable': model['variable'],
            'source': model['source'], 'test_period': model['period'], 'unit': model['unit'], 'methodology': 'held-out evaluated rolling one-month forecasts; estimates are not observations'})
    except BaseException as exc:
        atomic_json(output/'export_status.json', {'status': 'cancelled' if isinstance(exc, Cancelled) else 'failed', 'error': str(exc)})
        raise
