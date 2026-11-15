"""Headless UI regression checks; fixtures are explicitly artificial test arrays."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/aurora-test-mpl')
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPointF, QPoint, QAbstractAnimation
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import shiboken6

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from aurora.desktop.globe import PlanetaryExplorer


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def explorer(tmp_path, app):
    (tmp_path/'assets').symlink_to(ROOT/'assets', target_is_directory=True)
    directory = tmp_path/'data/processed/queretaro'; directory.mkdir(parents=True)
    m = {'dataset': 'satellite', 'source': 'MODIS/061/MOD13Q1',
         'variable': 'NDVI', 'unit': '1', 'shape': [3, 2, 2, 1],
         'grid': {'height': 2, 'width': 2, 'crs': 'EPSG:4326',
                  'transform': [1, 0, -101, 0, -1, 22], 'nodata': -9999}}
    (directory/'cube_metadata.json').write_text(json.dumps(m))
    values = np.zeros((3, 2, 2, 1), dtype='float32')
    values[1] = np.nan; values[2] = .8
    np.savez(directory/'cube.npz', X=values, valid=np.isfinite(values),
             region_mask=np.ones((2, 2), bool), channels=['NDVI'],
             dates=['2001-01-01', '2001-02-01', '2001-03-01'])
    w = PlanetaryExplorer(tmp_path); w.resize(1100, 760); w.show()
    app.processEvents()
    yield w
    w.pause(); w.planet.rotation.stop(); w.planet.animation.stop(); w.close()
    shiboken6.delete(w)
    app.processEvents()


def test_controls_and_unavailable_dataset(explorer):
    w = explorer
    assert not w.play.isEnabled()
    w.variable.setCurrentIndex(1)
    assert w.legend.variable == 'lst'
    w.load_dataset()
    assert 'unavailable' in w.details.text()
    assert w.values is None and w.planet.frame is None
    assert not w.play.isEnabled()
    w.opacity.setValue(37)
    assert w.opacity_value.text() == '37%'
    assert w.planet.opacity == .37


def test_playback_preserves_empty_observation_and_resets(explorer):
    w = explorer; w.load_dataset(); w.planet.animation.stop()
    assert w.play.isEnabled()
    w.toggle_play(); assert w.timer.isActive()
    w.step(1)
    assert np.isnan(w.planet.frame).all()
    assert '2001-02-01' in w.date.text() and 'Coverage: 0.00%' in w.details.text()
    assert 'Mean: N/A' in w.details.text()
    w.step(1); np.testing.assert_allclose(w.planet.frame, .8)
    w.step(1); assert w.slider.value() == 0
    w.region.setCurrentIndex(1)
    assert not w.timer.isActive() and w.planet.frame is None
    assert w.dates is None


def test_camera_short_arc_and_log_zoom(explorer):
    p = explorer.planet; p.lon, p.lat, p.zoom = 179, 0, 1
    p.focus(-179, 20, 4)
    p.animation.setCurrentTime(325)
    assert abs(p.lon) == pytest.approx(180)
    assert p.lat == pytest.approx(10) and p.zoom == pytest.approx(2)
    p.animation.setCurrentTime(650)
    assert p.lon == pytest.approx(-179)
    assert p.lat == pytest.approx(20) and p.zoom == pytest.approx(4)
    assert p.animation.state() == QAbstractAnimation.State.Stopped


def test_wheel_without_previous_focus_and_rotation(explorer):
    p = explorer.planet
    event = QWheelEvent(QPointF(50, 50), QPointF(50, 50), QPoint(0, 0), QPoint(0, 120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    p.wheelEvent(event)
    assert p.camera_end[2] == pytest.approx(1.18)
    p.animation.setCurrentTime(650)
    before = p.lon
    p.last_rotation -= .05
    p.rotate()
    assert p.lon > before


def test_pins_limb_occlusion_and_drag_interrupt(explorer):
    p = explorer.planet
    QTest.mouseDClick(p, Qt.MouseButton.LeftButton, pos=p.rect().center())
    assert len(p.pins) == 1
    _, lon, lat = p.pins[0]
    assert lon == pytest.approx(p.lon, abs=1)
    assert lat == pytest.approx(p.lat, abs=1)
    QTest.mouseDClick(p, Qt.MouseButton.LeftButton, pos=QPoint(1, 1))
    assert len(p.pins) == 1
    assert not p.screen_point(p.lon+180, -p.lat)[2]
    p.focus(0, 0, 2)
    QTest.mousePress(p, Qt.MouseButton.LeftButton, pos=p.rect().center())
    assert p.animation.state() == QAbstractAnimation.State.Stopped
    QTest.mouseRelease(p, Qt.MouseButton.LeftButton, pos=p.rect().center())
    explorer.clear_pins(); assert not p.pins


def test_frame_caches_and_transparent_missing_data(explorer, app):
    w = explorer; w.load_dataset(); p = w.planet; p.animation.setCurrentTime(650)
    p.invalidate(camera=True); app.processEvents()
    mapping, base = p.mapping, p.base
    w.step(1); app.processEvents()
    assert p.mapping is mapping and p.base is base
    no_data = p.image.copy()
    p.clear_layer(); app.processEvents()
    assert no_data == p.image
    p.resize(p.width()-30, p.height()); app.processEvents()
    assert p.render_size[0] <= 960


def test_hiding_pauses_playback(explorer, app):
    explorer.load_dataset(); explorer.toggle_play(); explorer.hide(); app.processEvents()
    assert not explorer.timer.isActive()


def test_host_retains_all_tabs_and_investigation_controls(app):
    from aurora.desktop.window import AuroraWindow
    w = AuroraWindow(); w.show(); app.processEvents()
    assert w.tabs.count() == 9
    assert any(w.tabs.tabText(i) == "Multivariate Laboratory" for i in range(w.tabs.count()))
    w.tabs.setCurrentWidget(w.planetary_explorer); app.processEvents()
    assert not w.investigation_panel.isVisible()
    w.planetary_explorer.setup_toggle.click()
    assert w.investigation_panel.isVisible()
    w.tabs.setCurrentWidget(w.time_machine)
    assert w.investigation_panel.isVisible()
    w.tabs.setCurrentWidget(w.planetary_explorer)
    assert not w.investigation_panel.isVisible()
    w.close(); shiboken6.delete(w)


def test_shared_monthly_interval_calendars_and_timeline(explorer):
    w = explorer; w.load_dataset(); w.planet.animation.stop()
    w.period.set_interval('2001-02-17', '2001-03-20')
    assert w.slider.minimum() == 1 and w.slider.maximum() == 2
    assert w.period.start.calendarPopup() and not w.period.start.keyboardTracking()
    w.slider.setValue(2); w.step(1)
    assert w.slider.value() == 1
    w.period.low.setValue(2)
    assert w.period.interval() == ('2001-03', '2001-03')
