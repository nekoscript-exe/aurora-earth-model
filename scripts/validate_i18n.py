"""Read-only scientific UI validation and actual Qt screenshots in both languages."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if 'MPLCONFIGDIR' not in os.environ:
    os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp(prefix='aurora-validation-mpl-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='aurora-i18n-settings-')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QAbstractButton, QComboBox, QPlainTextEdit, QTextBrowser, QFileDialog, QMessageBox
from matplotlib.figure import Figure
from matplotlib.text import Text
import shiboken6
from aurora.desktop.i18n import install_translation, get_language, source_text, tr, error_text, _translation_audit
from aurora.desktop.window import AuroraWindow


def wait(app, predicate, seconds=30):
    deadline = time.monotonic()+seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents(); time.sleep(.01)
    assert predicate(), 'UI did not reach the required state'
    app.processEvents()


def texts(root):
    result = []
    for widget in [root, *root.findChildren(QLabel), *root.findChildren(QAbstractButton), *root.findChildren(QComboBox), *root.findChildren(QPlainTextEdit), *root.findChildren(QTextBrowser)]:
        if isinstance(widget, (QLabel, QAbstractButton)): result.append(widget.text())
        if isinstance(widget, QComboBox): result.extend(widget.itemText(i) for i in range(widget.count()))
        if isinstance(widget, QPlainTextEdit): result.append(widget.toPlainText())
        if isinstance(widget, QTextBrowser): result.append(widget.toPlainText())
        result.append(widget.toolTip())
    for canvas in root.findChildren(QWidget):
        figure = getattr(canvas, 'figure', None)
        if isinstance(figure, Figure): result.extend(t.get_text() for t in figure.findobj(match=Text))
    return sorted(set(filter(None, result)))


def main(output=None):
    output = Path(output) if output is not None else ROOT/'docs/evidence/i18n'; output.mkdir(parents=True, exist_ok=True)
    visual = output/'visual'; visual.mkdir(exist_ok=True)
    app = QApplication.instance() or QApplication([])
    assert get_language() == 'en'
    install_translation(app, 'en')
    errors = []
    old_hook = sys.excepthook
    sys.excepthook = lambda kind, value, trace: errors.append(str(value))
    window = AuroraWindow(); window.resize(1440, 960); window.show()
    wait(app, lambda: window.ai_lab.model_registry is not None and not window.io_jobs.busy('results'))
    explorer = window.planetary_explorer
    explorer.load_dataset(asynchronous=True)
    wait(app, lambda: explorer.values is not None and not explorer.reader_jobs.busy('dataset') and not explorer.reader_jobs.busy('frame'))
    explorer.planet.animation.setCurrentTime(650)
    machine = window.time_machine
    wait(app, lambda: machine.values is not None and not machine.reader_jobs.busy('dataset') and not machine.reader_jobs.busy('frame'))
    report = {'source': 'current working tree; historical products read only', 'new_install_language': get_language(), 'languages': {}, 'qt_errors': errors}
    # Read-only sample of real worker messages, with no new scientific jobs.
    from aurora.desktop.i18n import log_text
    window.log.setPlainText(log_text('{"event":"progress","phase":"native-grid-blocks","done":4,"total":10}\n'))
    for language in ('en', 'es', 'en'):
        window.language_selector.setCurrentIndex(window.language_selector.findData(language)); app.processEvents()
        assert get_language() == language
        data = {'tabs': [window.tabs.tabText(i) for i in range(window.tabs.count())], 'views': [], 'text': []}
        for index in range(window.tabs.count()):
            window.tabs.setCurrentIndex(index); app.processEvents(); time.sleep(.03); app.processEvents()
            assert window.grab().save(str(visual/f'{language}_tab_{index+1:02d}.png'))
            data['text'].extend(texts(window))
        ai = window.ai_lab; window.tabs.setCurrentWidget(ai)
        for variable in ('ndvi', 'lst'):
            ai.variable.setCurrentIndex(ai.variable.findData(variable)); app.processEvents()
            for index in range(ai.view.count()):
                ai.view.setCurrentIndex(index); app.processEvents()
                assert 'Predictive results unavailable' not in source_text(ai.details.text())
                if language == 'es':
                    assert not any(text.get_text() in ('Climatology', 'Seasonal persistence', 'Persistence')
                                   for text in ai.figure.findobj(match=Text))
                data['views'].append({'variable': variable, 'view': ai.view.currentText()})
                data['text'].extend(texts(ai))
            ai.view.setCurrentIndex(0); app.processEvents()
            window.grab().save(str(visual/f'{language}_predictive_{variable}.png'))
        lab = window.multivariate_lab; window.tabs.setCurrentWidget(lab)
        for index in range(lab.view.count()):
            lab.view.setCurrentIndex(index); app.processEvents(); data['text'].extend(texts(lab))
            window.grab().save(str(visual/f'{language}_multivariate_{index}.png'))
        window.tabs.setCurrentWidget(window.map_panel)
        for index in range(window.layer_selector.count()):
            window.layer_selector.setCurrentIndex(index); app.processEvents(); data['text'].extend(texts(window.map_panel))
        # Real native pixel dialog, using an observed location on the existing raster.
        from types import SimpleNamespace
        import numpy as np
        import rasterio
        history = window.current_history
        assert history is not None
        with rasterio.open(history/'coverage.tif') as source:
            coverage = source.read(1, masked=True)
            locations = np.argwhere(~np.ma.getmaskarray(coverage) & (coverage.filled(0) > 0))
            row, col = locations[len(locations)//2]
            x, y = source.xy(int(row), int(col))
        window.inspect_global_pixel(SimpleNamespace(xdata=x, ydata=y, dblclick=True))
        wait(app, lambda: not window.io_jobs.busy('pixel'))
        pixel = window._pixel_dialog; app.processEvents()
        pixel.grab().save(str(visual/f'{language}_native_pixel.png')); data['text'].extend(texts(pixel)); pixel.reject()
        # Qt file/error dialogs and Matplotlib's real axis/curve editor.
        browser = QFileDialog(window, tr('Export scientific bundle into a new subdirectory'))
        browser.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        browser.setFileMode(QFileDialog.FileMode.Directory)
        browser.setDirectory(str(ROOT)); browser.show(); app.processEvents(); app.processEvents()
        browser.grab().save(str(visual/f'{language}_file_dialog.png')); data['text'].extend(texts(browser)); browser.reject()
        message = QMessageBox(QMessageBox.Icon.Warning, tr('Invalid investigation'),
                              error_text('Invalid interval or outside dataset availability'), parent=window)
        message.show(); app.processEvents(); app.processEvents()
        message.grab().save(str(visual/f'{language}_error_dialog.png')); data['text'].extend(texts(message)); message.accept()
        from matplotlib.backends.qt_editor.figureoptions import figure_edit
        figure_edit(window.map_figure.axes[0], window)
        editor = getattr(window, '_fedit_dialog')
        app.processEvents(); app.processEvents()
        editor.grab().save(str(visual/f'{language}_plot_editor.png')); data['text'].extend(texts(editor))
        editor.close()
        data['text'] = sorted(set(data['text']))
        report['languages'][language] = data
    assert len(report['languages']['en']['tabs']) == len(report['languages']['es']['tabs']) == 9
    assert report['languages']['es']['tabs'] != report['languages']['en']['tabs']
    assert report['languages']['en']['tabs'][0] == 'Home'
    assert not errors, errors
    window.close(); shiboken6.delete(window); app.processEvents()
    sys.excepthook = old_hook
    (output/'ui_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (output/'translation-audit.json').write_text(json.dumps(_translation_audit, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k != 'languages'}, indent=2))
    print('Validated nine tabs and all predictive/multivariate/map views in both languages; returned to English.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Independent evidence directory')
    main(parser.parse_args().output)
