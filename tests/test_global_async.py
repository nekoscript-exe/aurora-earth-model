"""UI responsiveness and stale generation tests; no simulated satellite coverage."""
import os
import sys
import time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtTest import QTest
import shiboken6
from aurora.desktop.tasks import ReaderJobs


def test_background_read_keeps_qt_responsive_and_delivers_on_main_thread():
    app = QApplication.instance() or QApplication([]); owner = QWidget(); results = []; errors = []; ticks = []
    def ready(kind, value):
        assert QThread.currentThread() == app.thread(); results.append(value)
    jobs = ReaderJobs(owner, ready, errors.append)
    timer = QTimer(owner); timer.setInterval(5); timer.timeout.connect(lambda: ticks.append(1)); timer.start()
    def slow(check): time.sleep(.06); check(); return 'ready'
    jobs.start('read', slow)
    deadline = time.monotonic()+3
    while not results and time.monotonic() < deadline:
        app.processEvents(); time.sleep(.005)
    app.processEvents()
    assert results == ['ready'] and not errors and len(ticks) >= 5
    timer.stop(); shiboken6.delete(owner); app.processEvents()


def test_cancelled_generation_never_replaces_new_result():
    app = QApplication.instance() or QApplication([]); owner = QWidget(); results = []; errors = []
    jobs = ReaderJobs(owner, lambda kind, value: results.append(value), errors.append)
    def old(check): time.sleep(.06); check(); return 'obsolete'
    jobs.start('frame', old); jobs.start('frame', lambda check: 'current')
    deadline = time.monotonic()+3
    while (not results or jobs.busy('frame')) and time.monotonic() < deadline:
        app.processEvents(); time.sleep(.005)
    # Let the cancelled older generation also attempt delivery.
    deadline = time.monotonic()+.1
    while time.monotonic() < deadline: app.processEvents(); time.sleep(.005)
    assert results == ['current'] and not errors
    shiboken6.delete(owner); app.processEvents()


def test_destroy_owner_during_read_is_quiet(capfd):
    app = QApplication.instance() or QApplication([]); owner = QWidget(); results = []
    jobs = ReaderJobs(owner, lambda kind, value: results.append(value), results.append)
    def delayed(check): time.sleep(.03); check(); return 'obsolete'
    jobs.start('read', delayed); shiboken6.delete(owner)
    deadline = time.monotonic()+.15
    while time.monotonic() < deadline: app.processEvents(); time.sleep(.005)
    assert not results
    assert 'Signal source has been deleted' not in capfd.readouterr().err


def test_result_callback_failure_is_reported_not_unhandled():
    app = QApplication.instance() or QApplication([]); owner = QWidget(); errors = []
    def fail(kind, value): raise ValueError('explicit render failure')
    jobs = ReaderJobs(owner, fail, errors.append); jobs.start('read', lambda check: 1)
    deadline = time.monotonic()+3
    while not errors and time.monotonic() < deadline: app.processEvents(); time.sleep(.005)
    assert errors == ['explicit render failure']
    shiboken6.delete(owner)


def test_hidden_time_machine_handles_zero_sized_figure(tmp_path):
    import json
    import numpy as np
    from aurora.desktop.time_machine import TimeMachine
    directory = tmp_path/'data/processed/explicit_header_fixture'; directory.mkdir(parents=True)
    # A tiny, explicitly identified UI fixture, not a scientific observation export.
    values = np.ones((3, 2, 2, 1), dtype='float32')*.2
    np.savez_compressed(directory/'cube.npz', X=values, valid=np.ones_like(values, dtype=bool), region_mask=np.ones((2, 2), bool),
                        dates=['2001-01', '2001-02', '2001-03'], channels=['NDVI'])
    metadata = {'dataset': 'satellite', 'source': 'EXPLICIT UI HEADER FIXTURE, NOT REAL OBSERVATIONS', 'variable': 'ndvi', 'unit': '1',
        'variable_definition': {'minimum': -1, 'maximum': 1, 'description': 'mathematical UI fixture only'},
        'shape': list(values.shape), 'grid': {'height': 2, 'width': 2, 'crs': 'EPSG:4326', 'transform': [1, 0, -101, 0, -1, 22]}}
    (directory/'cube_metadata.json').write_text(json.dumps(metadata))
    app = QApplication.instance() or QApplication([]); widget = TimeMachine(tmp_path); errors = []
    widget.reader_jobs.error_callback = errors.append
    widget.figure.set_size_inches(4, 0, forward=False)
    deadline = time.monotonic()+3
    while widget.reader_jobs.busy('dataset') and time.monotonic() < deadline: app.processEvents(); time.sleep(.005)
    assert widget.values is not None and hasattr(widget, 'image') and not errors
    # Restricted playback must wrap inside the selected months, not clamp at the end.
    widget.period.set_interval('2001-02', '2001-03')
    widget.slider.setValue(widget.slider.maximum())
    widget.step(1)
    assert widget.slider.value() == widget.slider.minimum() == 1
    widget.step(-1)
    assert widget.slider.value() == widget.slider.maximum() == 2
    old_frame = np.full((2, 2), .9)
    widget.apply_frame(999, old_frame)
    assert not errors
    widget.reset_dataset()
    label = widget.date_label.text()
    widget.apply_frame(0, old_frame)
    assert widget.values is None and widget.dates is None and widget.date_label.text() == label
    assert widget.figure.get_figheight() > 0
    shiboken6.delete(widget); app.processEvents()


def test_temporal_slider_crossings_and_empty_state():
    import numpy as np
    from aurora.desktop.temporal import TemporalSelector
    app = QApplication.instance() or QApplication([])
    selector = TemporalSelector()
    selector.update_sliders()  # No dataset selected yet.
    selector.set_dates(np.arange('2001-01', '2002-01', dtype='datetime64[M]'))
    selector.high.setValue(3)
    selector.low.setValue(5)
    assert selector.interval() == ('2001-06', '2001-06')
    selector.high.setValue(2)
    assert selector.interval() == ('2001-03', '2001-03')
    selector.set_dates([])
    selector.update_sliders()
    assert not selector.isEnabled()
    shiboken6.delete(selector)
    app.processEvents()


def test_cancelled_failure_does_not_reset_new_generation():
    app = QApplication.instance() or QApplication([])
    owner = QWidget(); results = []; errors = []
    jobs = ReaderJobs(owner, lambda kind, value: results.append(value), errors.append)
    import threading
    started = threading.Event()
    def old_failure(check):
        started.set()
        time.sleep(.05)
        raise ValueError('obsolete failure')
    jobs.start('dataset', old_failure)
    assert started.wait(1), 'Worker did not start'
    jobs.start('dataset', lambda check: 'current')
    deadline = time.monotonic()+.3
    while time.monotonic() < deadline:
        app.processEvents(); time.sleep(.005)
    assert results == ['current'] and not errors and not jobs.busy('dataset')
    shiboken6.delete(owner)
