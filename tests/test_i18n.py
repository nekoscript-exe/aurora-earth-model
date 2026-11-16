"""Presentation-only internationalization; mathematical fixtures are not observations."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox
from matplotlib.figure import Figure
import shiboken6
from aurora.desktop.i18n import (DIRECTORY, LanguageController, add_choices, catalog,
    get_language, install_translation, localized_label, metadata_text, set_language, tr)
from aurora.desktop.canvas import FigureCanvasQTAgg


@pytest.fixture
def localized_app(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous_format = QSettings.defaultFormat()
    previous_path = str(Path(QSettings("AURORA", "Desktop").fileName()).parent.parent)
    QSettings.setDefaultFormat(QSettings.Format.NativeFormat)
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp_path))
    install_translation(app, 'en')
    yield app, tmp_path
    install_translation(app, 'en')
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, previous_path)
    QSettings.setDefaultFormat(previous_format)
    app.processEvents()


def test_fresh_preferences_default_english_and_validate_language(localized_app):
    assert get_language() == 'en'
    with pytest.raises(ValueError, match='Unsupported language'):
        set_language('fr')
    QSettings('AURORA', 'Desktop').setValue('language', 'invalid')
    assert get_language() == 'en'


def test_language_preference_survives_process_restart(localized_app):
    _, directory = localized_app
    set_language('es')
    code = """from PySide6.QtCore import QSettings
import os
from aurora.desktop.i18n import get_language
QSettings.setDefaultFormat(QSettings.Format.NativeFormat)
QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, os.environ['AURORA_I18N_TEST_SETTINGS'])
print(get_language())
"""
    env = dict(os.environ, AURORA_I18N_TEST_SETTINGS=str(directory), PYTHONPATH='src')
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'es'


def test_catalog_is_complete_and_compiled(localized_app):
    tree = ET.parse(DIRECTORY/'aurora_es.ts')
    messages = tree.findall('./context/message')
    sources = [m.findtext('source') for m in messages]
    assert len(sources) == len(set(sources)) and len(sources) >= 500
    for message in messages:
        translation = message.find('translation')
        assert translation is not None and translation.text and translation.get('type') != 'unfinished'
    app, _ = localized_app
    install_translation(app, 'es')
    for source, target in catalog().items():
        assert tr(source) == target


def test_ambiguous_captions_roundtrip_without_source_loss(localized_app):
    owner = QWidget(); layout = QVBoxLayout(owner)
    home, start = localized_label('Home'), localized_label('Start')
    layout.addWidget(home); layout.addWidget(start)
    controller = LanguageController(owner)
    controller.change('es')
    assert home.text() == start.text() == 'Inicio'
    controller.change('en')
    assert home.text() == 'Home' and start.text() == 'Start'
    shiboken6.delete(owner)


def test_choices_keep_ids_and_do_not_emit_selection_changes(localized_app):
    owner = QWidget(); layout = QVBoxLayout(owner); combo = QComboBox()
    add_choices(combo, ['Model benchmark', 'Prediction difference']); layout.addWidget(combo)
    combo.setCurrentIndex(1); changes = []; combo.currentIndexChanged.connect(changes.append)
    controller = LanguageController(owner); controller.change('es')
    assert combo.currentText() == 'Diferencia entre predicciones'
    assert combo.currentData() == 'Prediction difference' and combo.currentIndex() == 1 and not changes
    controller.change('en')
    assert combo.currentText() == 'Prediction difference' and not changes
    shiboken6.delete(owner)


def test_switch_localizes_plot_and_preserves_numeric_data(localized_app):
    app, _ = localized_app
    owner = QWidget(); layout = QVBoxLayout(owner)
    figure = Figure(); canvas = FigureCanvasQTAgg(figure); layout.addWidget(canvas)
    ax = figure.add_subplot(111); values = np.array([.1, .2, np.nan, .4])
    line, = ax.plot(values, label='Monthly observations')
    ax.set_title('Regional monthly time series'); ax.set_ylabel('NDVI/year'); ax.legend()
    canvas.draw(); controller = LanguageController(owner); controller.change('es'); canvas.draw()
    assert ax.get_title() == 'Serie temporal mensual regional'
    assert ax.get_ylabel() == 'NDVI/year'
    np.testing.assert_array_equal(line.get_ydata(), values)
    controller.change('en'); canvas.draw()
    assert ax.get_title() == 'Regional monthly time series'
    legend = ax.get_legend()
    assert legend is not None and legend.get_texts()[0].get_text() == 'Monthly observations'
    shiboken6.delete(owner); app.processEvents()


def test_units_identifiers_paths_and_formulas_remain_intact(localized_app):
    app, _ = localized_app; install_translation(app, 'es')
    for value in ('NDVI', 'LST', '°C', 'degC', '1/year', 'NDVI/year', 'MAE', 'RMSE', 'R²',
                  'EPSG:32614', 'lag_12', 'MODIS/061/MOD13Q1', '/tmp/source/coverage.npz'):
        assert tr(value) == value
    assert tr('Native x · EPSG:32614') == 'Coordenada x nativa · EPSG:32614'
    assert 'X(t)' in tr(' · ≥8 pairs per calendar month. Positive lag: X(t) vs Y(t+lag).\n')
    assert 'Y(t+lag)' in tr(' · ≥8 pairs per calendar month. Positive lag: X(t) vs Y(t+lag).\n')


def test_metadata_view_is_localized_without_mutating_result(localized_app):
    app, _ = localized_app; install_translation(app, 'es')
    result = {'unit': 'degC', 'slope_unit': 'degC/year', 'seconds': 1.25,
              'methodology': ['Native-grid annual mean with at least 9 observed months']}
    before = json.dumps(result)
    text = metadata_text(result)
    assert 'Unidad: degC' in text and 'Media anual en malla nativa' in text
    assert json.dumps(result) == before


def test_scientific_report_is_localized_including_limitations(localized_app):
    from aurora.desktop.report import render_report
    app, _ = localized_app; install_translation(app, 'es')
    metrics = {'variable': 'NDVI', 'regional_pixels': 10, 'period': ['2001-01', '2025-12'],
               'significant_increase': 2, 'significant_decrease': 1, 'not_significant': 6, 'not_tested': 1,
               'months': 300, 'mean_temporal_coverage': .9, 'tested_pixels': 9, 'seconds': .1, 'slope_unit': 'NDVI/year'}
    html = render_report(metrics, {'trend': None})
    assert 'Limitaciones científicas' in html and 'evidencia' not in html
    assert 'Scientific limitations' not in html and 'Insufficient observations' not in html
    assert 'no establecen causalidad' in html


@pytest.mark.parametrize('startup', ['en', 'es'])
def test_nine_tabs_and_live_switch_from_both_startup_languages(localized_app, monkeypatch, startup):
    from aurora.desktop import window as module
    app, directory = localized_app
    (directory/'assets').symlink_to(module.ROOT/'assets', target_is_directory=True)
    monkeypatch.setattr(module, 'ROOT', directory)
    set_language(startup)
    install_translation(app, startup)
    window = module.AuroraWindow()
    expected = ['Home', 'Planetary Explorer', 'Time Machine', 'Predictive intelligence',
                'Multivariate Laboratory', 'Scientific results', 'Spatial analysis', 'Temporal analysis', 'Execution log']
    original_camera = (window.planetary_explorer.planet.lon, window.planetary_explorer.planet.lat)
    for language in ('es', 'en', 'es', 'en'):
        window.language_selector.setCurrentIndex(window.language_selector.findData(language)); app.processEvents()
        assert [window.tabs.tabText(i) for i in range(9)] == [tr(name) for name in expected]
        assert get_language() == language
        assert (window.planetary_explorer.planet.lon, window.planetary_explorer.planet.lat) == original_camera
        assert window.variable.currentData() == 'ndvi'
    window.close(); shiboken6.delete(window); app.processEvents()


def test_translation_preserves_html_attributes_styles_and_units(localized_app):
    app, _ = localized_app; install_translation(app, 'es')
    html = '<style>p {border-width:1px;height:20px;}</style><p title="source" style="width:50%">Data coverage</p>'
    expected = '<style>p {border-width:1px;height:20px;}</style><p title="source" style="width:50%">Cobertura de datos</p>'
    assert tr(html) == expected


def test_registry_refresh_captions_are_localized_and_ids_preserved(localized_app):
    from aurora.catalog import DatasetRegistry
    from aurora.desktop.dataset_controls import populate_variables
    app, directory = localized_app; install_translation(app, 'es')
    combo = QComboBox(); registry = DatasetRegistry(directory)
    populate_variables(combo, registry, 'mexico')
    assert combo.itemText(0) == 'NDVI · no disponible'
    assert combo.itemData(0) == 'ndvi'
    assert combo.itemText(1) == 'LST · no disponible'
    shiboken6.delete(combo)


def test_backend_errors_have_localized_user_fallback(localized_app):
    from aurora.desktop.i18n import error_text
    app, _ = localized_app; install_translation(app, 'es')
    assert error_text('Invalid interval or outside dataset availability') == 'El intervalo no es válido o queda fuera de los datos disponibles'
    assert error_text('Some unknown operating-system error') == 'La operación falló. Revisa la entrada e inténtalo de nuevo.'


def test_qt_file_models_and_plot_date_labels_are_localized(localized_app):
    from PySide6.QtCore import QCoreApplication
    app, _ = localized_app; install_translation(app, 'es')
    assert QCoreApplication.translate('QFileSystemModel', 'Folder') == 'Carpeta'
    assert tr('2001-May') == '2001-may'
    assert tr('Files of &type:') == 'Archivos de &tipo:'


def test_partial_worker_messages_are_not_rendered_as_mixed_json(localized_app, monkeypatch):
    from aurora.desktop import window as module
    app, directory = localized_app
    (directory/'assets').symlink_to(module.ROOT/'assets', target_is_directory=True)
    monkeypatch.setattr(module, 'ROOT', directory)
    install_translation(app, 'es')
    window = module.AuroraWindow()
    window.log.clear()
    window.append_worker_log('{"event":"progress","phase":"native-')
    assert not window.log.toPlainText()
    window.append_worker_log('grid-blocks","done":4,"total":10}\n')
    rendered = window.log.toPlainText()
    assert 'Evento: Progreso' in rendered and 'Bloques de malla nativa' in rendered
    assert 'native-grid-blocks' not in rendered and '"event"' not in rendered
    window.close(); shiboken6.delete(window); app.processEvents()


def test_regenerated_category_and_month_ticks_translate_at_render_time(localized_app):
    from matplotlib import dates as mdates
    import datetime
    app, _ = localized_app
    figure = Figure(); canvas = FigureCanvasQTAgg(figure)
    categories, months = figure.subplots(2, 1)
    categories.barh(['Climatology', 'Seasonal persistence', 'Persistence'], [1, 2, 3])
    dates = [datetime.datetime(2001, 1, 1), datetime.datetime(2001, 5, 1)]
    months.plot(dates, [1., 2.]); months.set_xticks(mdates.date2num(dates))
    months.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    install_translation(app, 'es'); canvas.draw()
    assert [tick.get_text() for tick in categories.get_yticklabels()] == ['Climatología', 'Persistencia estacional', 'Persistencia']
    assert [tick.get_text() for tick in months.get_xticklabels()] == ['ene', 'may']
    install_translation(app, 'en'); canvas.draw()
    assert [tick.get_text() for tick in categories.get_yticklabels()] == ['Climatology', 'Seasonal persistence', 'Persistence']
    assert [tick.get_text() for tick in months.get_xticklabels()] == ['Jan', 'May']
    shiboken6.delete(canvas)


def test_plot_editor_apply_keeps_data_units_and_internal_choices(localized_app):
    from matplotlib.backends.qt_editor.figureoptions import figure_edit
    from aurora.desktop.toolbar import NavigationToolbar2QT
    app, _ = localized_app; install_translation(app, 'es')
    owner = QWidget(); layout = QVBoxLayout(owner)
    figure = Figure(); canvas = FigureCanvasQTAgg(figure); layout.addWidget(canvas)
    toolbar = NavigationToolbar2QT(canvas, owner); layout.addWidget(toolbar)
    ax = figure.add_subplot(111)
    values = np.array([.1, .25, .5])
    line, = ax.plot(values, label='Monthly observations')
    ax.set_ylabel('NDVI/year'); canvas.draw()
    controller = LanguageController(owner)
    action_ids = set(toolbar._actions)
    figure_edit(ax, owner); app.processEvents(); app.processEvents()
    editor = getattr(owner, '_fedit_dialog')
    editor.apply()
    np.testing.assert_array_equal(line.get_ydata(), values)
    assert ax.get_ylabel() == 'NDVI/year' and ax.get_xscale() == 'linear'
    assert set(toolbar._actions) == action_ids
    editor.close(); controller.change('en')
    assert set(toolbar._actions) == action_ids
    shiboken6.delete(owner); app.processEvents()



@pytest.mark.parametrize('source,translated', [
    ('Explore', 'Explorar'), ('Research', 'Investigación'),
    ('Dark', 'Oscuro'), ('Light', 'Claro'),
])
def test_navigation_and_appearance_labels_are_catalogued(localized_app, source, translated):
    from aurora.desktop.i18n import catalog
    assert catalog()[source] == translated
    app, _ = localized_app
    install_translation(app, 'es')
    assert tr(source) == translated
    install_translation(app, 'en')
    assert tr(source) == source
