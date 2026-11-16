"""Qt translation and presentation-only language switching.

Scientific identifiers, data, and computations never pass through this layer.
Composed messages are translated in one regex pass using catalogued fragments;
whole messages take precedence. Bindings retain their English source so changing
language never translates a translation or changes a selector's internal value.
"""
from collections import OrderedDict
from pathlib import Path
import re
import weakref
import xml.etree.ElementTree as ET

from PySide6.QtCore import QCoreApplication, Qt, QEvent, QLibraryInfo, QLocale, QObject, QSettings, QTranslator, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QAbstractButton, QComboBox, QGroupBox,
    QLabel, QPushButton, QLineEdit, QPlainTextEdit, QProgressBar, QTabWidget, QTextBrowser, QWidget)
from matplotlib.figure import Figure
from matplotlib.text import Text
import shiboken6

LANGUAGES = {"en": "English", "es": "Español"}
DIRECTORY = Path(__file__).resolve().parent / "translations"
_translator = None
_qt_translator = None
_language = "en"
_rendered_sources: OrderedDict[str, str] = OrderedDict()
_bindings = weakref.WeakKeyDictionary()
_translation_audit: OrderedDict[str, str] = OrderedDict()


def catalog() -> dict[str, str]:
    tree = ET.parse(DIRECTORY / 'aurora_es.ts')
    return {(m.findtext('source') or ''): (m.findtext('translation') or '')
            for m in tree.findall('./context/message')}


_catalog = catalog()
# Match phrase boundaries, preserving identifiers such as EPSG codes and paths.
_phrases = sorted(_catalog, key=len, reverse=True)
_patterns = {f'm{i}': source for i, source in enumerate(_phrases) if source}
_pattern = re.compile('|'.join(
    f'(?P<{name}>' + (r'(?<!\w)' if source[0].isalnum() else '')
    + r'\s+'.join(re.escape(part) for part in source.split(' '))
    + (r'(?!\w)' if source[-1].isalnum() else '') + ')'
    for name, source in _patterns.items()))
_protected = re.compile(r'(?:https?://[^\s<>]+|/?[\w.-]+(?:/[\w.+-]+)+|[a-z][a-z0-9]*_[a-z0-9_]+|EPSG:\d+|[0-9a-f]{32,64})')


def _replace_plain(text):
    spans = [m.span() for m in _protected.finditer(text)]
    def replace(match):
        if any(start <= match.start() and match.end() <= end for start, end in spans):
            return match.group()
        return _catalog[_patterns[match.lastgroup]]
    return _pattern.sub(replace, text)


def _replace_phrases(text):
    # Translation must never alter HTML attributes, URLs, styles, or markup.
    chunks = re.split(r'(<style\b[^>]*>.*?</style>|<[!/A-Za-z][^>]*>)', text, flags=re.S | re.I)
    return ''.join(part if index % 2 else _replace_plain(part) for index, part in enumerate(chunks))


def source_text(text: str) -> str:
    """Canonical display key; never use a translated label as a model/map ID."""
    return _rendered_sources.get(text, text)


def tr(text: str) -> str:
    text = str(text)
    if _language == 'en':
        return text
    translated = QCoreApplication.translate('AURORA', text)
    if translated == text:
        translated = _replace_phrases(text)
    _translation_audit[text] = translated
    _translation_audit.move_to_end(text)
    while len(_translation_audit) > 16384:
        _translation_audit.popitem(last=False)
    if translated != text:
        _rendered_sources[translated] = text
        _rendered_sources.move_to_end(translated)
        while len(_rendered_sources) > 16384:
            _rendered_sources.popitem(last=False)
    return translated


def get_language():
    language = QSettings('AURORA', 'Desktop').value('language', 'en')
    return language if language in LANGUAGES else 'en'


def set_language(language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported language')
    settings = QSettings('AURORA', 'Desktop')
    settings.setValue('language', language)
    settings.sync()


class InterfaceTranslator(QTranslator):
    """Also translate known captions in Qt file models and third-party dialogs."""
    def translate(self, context, sourceText, /, disambiguation=None, n=-1):
        translated = super().translate(context, sourceText, disambiguation, n)
        return translated or _catalog.get(sourceText)


def install_translation(app, language=None):
    global _translator, _qt_translator, _language
    # Native OS dialogs follow the OS language, not this interface preference.
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
    language = get_language() if language is None else language
    if language not in LANGUAGES:
        raise ValueError('Unsupported language')
    candidate = InterfaceTranslator(app)
    qt_candidate = QTranslator(app)
    if language == 'es':
        if not candidate.load(str(DIRECTORY / 'aurora_es.qm')):
            raise RuntimeError('Spanish translation catalog unavailable')
        if not qt_candidate.load('qtbase_es', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            raise RuntimeError('Spanish Qt translation catalog unavailable')
    for translator in (_translator, _qt_translator):
        if translator is not None:
            app.removeTranslator(translator)
            translator.deleteLater()
    _translator, _qt_translator = candidate, qt_candidate
    _language = language
    if language == 'es':
        app.installTranslator(qt_candidate)
        app.installTranslator(candidate)
    QLocale.setDefault(QLocale('es_MX' if language == 'es' else 'en_US'))

    # Keep date formatter source strings independent of the OS language.
    import locale
    locale.setlocale(locale.LC_TIME, "C")
    return True


def _bound(obj, key, text):
    bindings = _bindings.setdefault(obj, {})
    previous = bindings.get(key)
    source = previous[0] if previous is not None and text == previous[1] else source_text(text)
    rendered = tr(source)
    bindings[key] = (source, rendered)
    return rendered


def translate_tree(root):
    """Update existing controls/plots, with signals blocked and state preserved."""
    if not shiboken6.isValid(root):
        return
    for widget in [root, *root.findChildren(QWidget)]:
        widget.setToolTip(_bound(widget, 'tooltip', widget.toolTip()))
        widget.setStatusTip(_bound(widget, 'status', widget.statusTip()))
        widget.setWindowTitle(_bound(widget, 'title', widget.windowTitle()))
        widget.setLocale(QLocale())
        if isinstance(widget, (QLabel, QAbstractButton, QGroupBox)):
            if isinstance(widget, QGroupBox):
                widget.setTitle(_bound(widget, 'text', widget.title()))
            else:
                text = _bound(widget, 'text', widget.text())
                if text != widget.text(): widget.setText(text)
        if isinstance(widget, QComboBox):
            blocked = widget.blockSignals(True)
            for i in range(widget.count()):
                source = widget.itemData(i, 257)
                widget.setItemText(i, tr(source) if isinstance(source, str) else _bound(widget, f'item:{i}', widget.itemText(i)))
            widget.blockSignals(blocked)
        if isinstance(widget, QTabWidget):
            for i in range(widget.count()):
                widget.setTabText(i, _bound(widget, f'tab:{i}', widget.tabText(i)))
        if isinstance(widget, QTextBrowser):
            widget.setHtml(_bound(widget, 'html', widget.toHtml()))
        elif isinstance(widget, QPlainTextEdit) and widget.isReadOnly():
            text = _bound(widget, 'plain', widget.toPlainText())
            if text != widget.toPlainText(): widget.setPlainText(text)
        if isinstance(widget, QLineEdit):
            widget.setPlaceholderText(_bound(widget, 'placeholder', widget.placeholderText()))
        if isinstance(widget, QProgressBar):
            widget.setFormat(_bound(widget, 'format', widget.format()))
        figure = getattr(widget, 'figure', None)
        if isinstance(figure, Figure):
            for artist in figure.findobj(match=Text):
                artist.set_text(_bound(artist, 'text', artist.get_text()))
            figure.canvas.draw_idle()
        widget.update()
    for action in root.findChildren(QAction):
        action.setText(_bound(action, 'text', action.text()))
        action.setToolTip(_bound(action, 'tooltip', action.toolTip()))
        action.setStatusTip(_bound(action, 'status', action.statusTip()))


class LanguageController(QObject):
    """Observe new dialogs and switch language without recreating scientific views."""
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        app = QApplication.instance()
        if app is not None: app.installEventFilter(self)
        translate_tree(window)

    def change(self, language):
        app = QApplication.instance()
        if app is None: return
        install_translation(app, language)
        set_language(language)
        translate_tree(self.window)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget) and watched.isWindow():
            QTimer.singleShot(0, lambda: translate_tree(watched) if shiboken6.isValid(watched) else None)
        return super().eventFilter(watched, event)


def metadata_text(value, indent=0):
    """Readable localized view; original result JSON and scientific values are intact."""
    if isinstance(value, dict):
        return '\n'.join(' '*indent + tr(str(key).replace('_', ' ')) + ':\n' + metadata_text(item, indent+2)
                         if isinstance(item, (dict, list)) else ' '*indent + tr(str(key).replace('_', ' ')) + ': ' + tr(str(item))
                         for key, item in value.items())
    if isinstance(value, list):
        return '\n'.join(metadata_text(item, indent) for item in value)
    if value is None: return ' '*indent + tr('Not available')
    return ' '*indent + tr(str(value))


def tr_items(items):
    return [tr(item) for item in items]


def active_language():
    return _language


def log_text(text):
    """Localize the log view, without changing worker messages on disk."""
    import json
    lines = []
    for line in text.splitlines(keepends=True):
        try:
            value = json.loads(line)
        except ValueError:
            lines.append(tr(line))
        else:
            lines.append(metadata_text(value) + '\n')
    return ''.join(lines)


def localized_label(text='', parent=None):
    widget = QLabel(tr(text), parent)
    _bindings.setdefault(widget, {})['text'] = (str(text), str(widget.text()))
    return widget


def localized_button(text='', parent=None):
    widget = QPushButton(tr(text), parent)
    _bindings.setdefault(widget, {})['text'] = (str(text), str(widget.text()))
    return widget


def add_choices(combo, choices):
    for source in choices:
        combo.addItem(tr(source), source)
        combo.setItemData(combo.count()-1, source, 257)


def error_text(error):
    """Localize known errors; arbitrary library prose stays in technical logging."""
    import logging
    message = str(error)
    if _language == 'en': return message
    if message in _catalog or message.startswith(('No observed dataset for ', 'Expected Zarr array: ')):
        return tr(message)
    logging.getLogger('aurora.desktop').warning('%s', message)
    return tr('Operation failed. Review the input and try again.')
