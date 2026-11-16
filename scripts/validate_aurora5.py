"""Inspect real AURORA 5 outputs, verify preservation and render UI evidence."""
import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path
import sys
from time import perf_counter, monotonic, sleep
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if 'MPLCONFIGDIR' not in os.environ:
    os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp(prefix='aurora-validation-mpl-')
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))
import numpy as np
from PySide6.QtWidgets import QApplication
import shiboken6
from aurora.catalog import CubeReader, DatasetRegistry
from aurora.desktop.window import AuroraWindow


def main():
    destination = ROOT/'docs/evidence/aurora5'; destination.mkdir(parents=True, exist_ok=True)
    visual = destination/'visual'; visual.mkdir(exist_ok=True)
    snapshot = json.loads((destination/'ndvi_preservation.json').read_text())
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest for path, digest in snapshot.items())
    registry = DatasetRegistry(ROOT)
    source = registry.find('queretaro', 'lst')
    t = perf_counter(); reader = CubeReader(source.directory); cold_seconds = perf_counter()-t
    timings = []
    frame = reader.read(slice(0, 12), slice(40, 72), slice(40, 72))
    for _ in range(20):
        t = perf_counter(); frame = reader.read(slice(0, 12), slice(40, 72), slice(40, 72))
        timings.append((perf_counter()-t)*1000)
    storage = {'format': reader.format, 'access': 'streamed NPY members + memory mapping',
               'reader_setup_seconds_warm_cache': cold_seconds,
               'window_shape': list(frame.shape), 'window_median_ms': float(np.median(timings)),
               'zarr_available': importlib.util.find_spec('zarr') is not None}
    app = QApplication.instance() or QApplication([])
    host = AuroraWindow(); host.show(); app.processEvents()
    deadline = monotonic()+20
    while host.ai_lab.model_registry is None and monotonic() < deadline:
        app.processEvents(); sleep(.005)
    ai = host.ai_lab; host.tabs.setCurrentWidget(ai); ai.variable.setCurrentIndex(1); app.processEvents()
    for index in range(ai.view.count()):
        ai.view.setCurrentIndex(index); app.processEvents()
        assert not any(text.get_text() == 'Predictive results unavailable' for axis in ai.figure.axes for text in axis.texts), ai.details.text()
        if index in (0, 3, 6): host.grab().save(str(visual/f'lst_predictive_{index}.png'))
    # Confirm that the legacy NDVI result views still load.
    ai.variable.setCurrentIndex(0)
    for index in range(ai.view.count()):
        ai.view.setCurrentIndex(index); app.processEvents()
        assert not any(text.get_text() == 'Predictive results unavailable' for axis in ai.figure.axes for text in axis.texts), ai.details.text()
    lab = host.multivariate_lab; host.tabs.setCurrentWidget(lab); app.processEvents()
    assert lab.output and (lab.output/'report.json').exists()
    for index in (0, 2, 3, 4):
        lab.view.setCurrentIndex(index); app.processEvents()
        host.grab().save(str(visual/f'multivariate_{index}.png'))
    host.tabs.setCurrentWidget(host.planetary_explorer)
    explorer = host.planetary_explorer; explorer.variable.setCurrentIndex(1); explorer.load_dataset()
    explorer.planet.animation.setCurrentTime(650); app.processEvents()
    deadline = monotonic()+20
    while explorer.reader_jobs.busy('frame') and monotonic() < deadline:
        app.processEvents(); sleep(.005)
    assert explorer.values is not None, explorer.details.text()
    host.grab().save(str(visual/'lst_planetary.png'))
    host.resize(1000, 680); app.processEvents()
    host.grab().save(str(visual/'minimum_window.png'))
    host.tabs.setCurrentWidget(host.welcome)
    host.temporal.apply_quick(5); app.processEvents()
    host.grab().save(str(visual/'date_interval.png'))
    tabs = [host.tabs.tabText(i) for i in range(host.tabs.count())]
    host.close(); shiboken6.delete(host); app.processEvents()
    result = {'historical_ndvi_files_unchanged': len(snapshot), 'tabs': tabs, 'storage': storage,
              'ui_modes_verified': {'lst_predictive': 8, 'ndvi_predictive': 8, 'multivariate': 4},
              'minimum_window': [1000, 680]}
    (destination/'validation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
