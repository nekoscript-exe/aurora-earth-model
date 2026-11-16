"""Paired observation laboratory; analysis runs outside the UI process."""
from aurora.portability import load_manifest

from .i18n import error_text, localized_label, localized_button, add_choices, tr
import json
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QProgressBar
from aurora.jobs import ResultRegistry, fresh, request_cancel
from matplotlib.figure import Figure
from .canvas import FigureCanvasQTAgg
from .toolbar import NavigationToolbar2QT
from .temporal import TemporalSelector
from .dataset_controls import populate_regions


class MultivariateLaboratory(QWidget):
    def __init__(self, root, parent=None):
        super().__init__(parent); self.root = root; self.output = None
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.finished.connect(self.finished)
        self.process.readyReadStandardOutput.connect(self.read_progress)
        self._progress_text = ""; self._error_log = ""
        self.process.errorOccurred.connect(lambda _: self.info.setText(error_text(self.process.errorString())))
        layout = QVBoxLayout(self)
        title = localized_label('Multivariate Laboratory · NDVI × LST')
        title.setStyleSheet('font-size:24px;font-weight:bold;color:#69d9bd;'); layout.addWidget(title)
        row = QHBoxLayout(); self.region = QComboBox(); self.registry = populate_regions(self.region, root, paired=True)
        self.x_variable = QComboBox(); self.y_variable = QComboBox()
        row.addWidget(self.x_variable); row.addWidget(self.y_variable)
        self.view = QComboBox(); add_choices(self.view, ['Overview', 'Pearson raw', 'Spearman anomaly', 'Lag profiles', 'Coverage sensitivity'])
        self.run_button = localized_button('Run paired analysis'); self.run_button.clicked.connect(self.run)
        for widget in (self.region, self.view, self.run_button): row.addWidget(widget)
        self.setup_toggle = localized_button('Investigation setup'); self.setup_toggle.setCheckable(True)
        self.setup_toggle.hide(); row.addWidget(self.setup_toggle)
        layout.addLayout(row)
        self.progress = QProgressBar(); layout.addWidget(self.progress)
        self.cancel_button = localized_button('Cancel paired analysis'); self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_analysis); layout.addWidget(self.cancel_button)
        self.period = TemporalSelector()
        layout.addWidget(self.period.create_toggle()); layout.addWidget(self.period)
        self.figure = Figure(facecolor='#080e17'); self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self)); layout.addWidget(self.canvas, 1)
        self.info = localized_label('Coincident observations only · Association does not establish causation.')
        self.info.setWordWrap(True); layout.addWidget(self.info)
        self.view.currentIndexChanged.connect(self.render_results)
        self.region.currentIndexChanged.connect(self.configure_region)
        self.x_variable.currentIndexChanged.connect(self.configure_pair)
        self.y_variable.currentIndexChanged.connect(self.configure_pair)
        self.configure_region()
        self.render_results()

    def refresh_catalog(self):
        old = self.region.currentData(); self.region.blockSignals(True)
        self.registry = populate_regions(self.region, self.root, paired=True)
        index = self.region.findData(old); self.region.setCurrentIndex(index if index >= 0 else 0)
        self.region.blockSignals(False); self.configure_region()

    def configure_region(self, *_):
        variables = sorted({r.variable for r in self.registry.records if r.region == self.region.currentData()})
        for combo, preferred in ((self.x_variable, 'ndvi'), (self.y_variable, 'lst')):
            old = combo.currentData(); combo.blockSignals(True); combo.clear()
            for variable in variables: combo.addItem(tr(variable.upper()), variable)
            index = combo.findData(old if old in variables else preferred)
            combo.setCurrentIndex(index if index >= 0 else min(0 if combo is self.x_variable else 1, len(variables)-1))
            combo.blockSignals(False)
        self.configure_pair()

    def configure_pair(self, *_):
        try:
            record = self.registry.find(self.region.currentData(), self.x_variable.currentData())
            other = self.registry.find(self.region.currentData(), self.y_variable.currentData())
            self.period.set_dates(np.intersect1d(record.dates, other.dates))
            candidates = [r for r in ResultRegistry(self.root).available(self.region.currentData(), kind='multivariate')
                          if r.get('variables') == [record.variable, other.variable]]
            self.output = candidates[0]['directory'] if candidates else None
            # Preserve historical AURORA 5 analyses, visibly identified as unaudited legacy products.
            if self.output is None and [record.variable, other.variable] == ['ndvi', 'lst']:
                legacy = []
                for path in (self.root/'outputs/aurora5/multivariate').glob('*/report.json'):
                    data = json.loads(path.read_text())
                    if data.get('datasets', {}).get('ndvi') == record.identifier: legacy.append(path)
                if legacy: self.output = max(legacy, key=lambda p: p.stat().st_mtime_ns).parent
            self.run_button.setEnabled(record.variable != other.variable)
        except FileNotFoundError:
            self.period.set_dates([]); self.output = None; self.run_button.setEnabled(False)
        self.render_results()

    def run(self):
        try: start, end = self.period.interval()
        except ValueError as exc: self.info.setText(error_text(exc)); return
        self.output = self.root/'outputs/aurora5/multivariate'/f'{self.region.currentData()}_{datetime.now():%Y%m%d_%H%M%S_%f}'
        self.run_button.setEnabled(False); self.cancel_button.setEnabled(True)
        self.region.setEnabled(False); self.x_variable.setEnabled(False); self.y_variable.setEnabled(False)
        self._progress_text = ''; self._error_log = ''; self.info.setText(tr('Computing native blocks, paired climatologies and global FDR…'))
        self.process.start(sys.executable, [str(self.root/'scripts/paired_job.py'),
            '--x', str(self.registry.find(self.region.currentData(), self.x_variable.currentData()).directory), '--y', str(self.registry.find(self.region.currentData(), self.y_variable.currentData()).directory),
            '--output', str(self.output), '--start', start, '--end', end, '--region', self.region.currentData(), '--memory-mib', '64'])

    def finished(self, code, status):
        self.run_button.setEnabled(True); self.cancel_button.setEnabled(False)
        self.region.setEnabled(True); self.x_variable.setEnabled(True); self.y_variable.setEnabled(True)
        if code:
            self.info.setText(tr('Cancelled') if code == 2 else error_text((self._error_log+bytes(self.process.readAllStandardOutput().data()).decode(errors='replace'))[-1500:])); return
        self.render_results()

    def style_plot(self, ax):
        ax.set_facecolor('#080e17'); ax.tick_params(colors='#bacbd8', labelsize=9)
        ax.title.set_color('#e7edf5'); ax.xaxis.label.set_color('#bacbd8'); ax.yaxis.label.set_color('#bacbd8')
        for spine in ax.spines.values(): spine.set_color('#405568')

    def render_results(self, *_):
        self.figure.clear()
        if self.output is None or not (self.output/'report.json').exists():
            ax = self.figure.add_subplot(111); ax.text(.5, .5, tr('Run an analysis with aligned real datasets'), ha='center', color='#8da5ba')
            self.style_plot(ax); self.canvas.draw(); return
        report = json.loads((self.output/'report.json').read_text())
        manifest = self.output/'manifest.json'
        if manifest.exists() and (load_manifest(manifest).get('status') != 'complete' or not fresh(load_manifest(manifest))):
            self.info.setText(tr('Incomplete or stale result; run a fresh analysis.')); self.canvas.draw(); return
        self.report = report
        with np.load(self.output/'analysis.npz', allow_pickle=False) as data:
            mode = self.view.currentData()
            if mode == 'Overview':
                axes = self.figure.subplots(2, 2); self.draw_map(axes[0, 0], data, 'anomaly_0_pearson', 'Anomaly Pearson r')
                self.scatter(axes[0, 1], data); self.series(axes[1, 0], data); self.lags(axes[1, 1], report)
            else:
                ax = self.figure.add_subplot(111)
                if mode == 'Pearson raw': self.draw_map(ax, data, 'raw_0_pearson', 'Observed NDVI–LST Pearson r')
                elif mode == 'Spearman anomaly': self.draw_map(ax, data, 'anomaly_0_spearman', 'Monthly anomaly Spearman ρ')
                elif mode == 'Lag profiles': self.lags(ax, report)
                else:
                    sensitivity = report['coverage_sensitivity']; keys = list(sensitivity)
                    ax.plot(list(map(float, keys)), [sensitivity[k]['anomaly']['pearson'] for k in keys], 'o-', color='#69d9bd')
                    ax.set_xlabel(tr('Minimum paired regional coverage')); ax.set_ylabel(tr('Anomaly Pearson r')); ax.set_title(tr('Coverage sensitivity'))
        for ax in self.figure.axes: self.style_plot(ax)
        self.info.setText(tr(f"{report['period'][0]} — {report['period'][1]} · {report['paired_observations']:,} coincident observations · {report.get('variables', ['ndvi', 'lst'])}\n"
                          f"Climatology: {report['climatology']['period']} · ≥8 pairs per calendar month. Positive lag: X(t) vs Y(t+lag).\n"
                          +('Native blocks, area weighting and global FDR. ' if manifest.exists() else 'Historical legacy result: source freshness not independently established. ')+
                          'AR1/BH are diagnostics. Association is not causation.'))
        self.figure.tight_layout(h_pad=2.5, w_pad=3, pad=1.2); self.canvas.draw()

    def draw_map(self, ax, data, key, title):
        image = ax.imshow(data[key], cmap='coolwarm', vmin=-1, vmax=1, interpolation='nearest')
        ax.set_title(tr(title)); ax.set_xticks([]); ax.set_yticks([])
        self.figure.colorbar(image, ax=ax, shrink=.75)

    def scatter(self, ax, data):
        ok = data['coverage'] >= .7
        ax.scatter(data['raw_x' if 'raw_x' in data else 'raw_ndvi'][ok], data['raw_y' if 'raw_y' in data else 'raw_lst'][ok], s=9, color='#69d9bd', alpha=.6)
        ax.set_xlabel(tr('Regional '+self.report.get('variables', ['ndvi', 'lst'])[0])); ax.set_ylabel(tr('Regional '+self.report.get('variables', ['ndvi', 'lst'])[1]+' · '+self.report.get('units', ['1', 'degC'])[1])); ax.set_title(tr('Paired monthly regional means'))

    def series(self, ax, data):
        dates = data['dates'].astype('datetime64[M]')
        ax.plot(dates, data['anomaly_x' if 'anomaly_x' in data else 'anomaly_ndvi'], color='#69d9bd'); ax.set_ylabel(tr(self.report.get('variables', ['ndvi', 'lst'])[0]+' anomaly'))
        right = ax.twinx(); right.plot(dates, data['anomaly_y' if 'anomaly_y' in data else 'anomaly_lst'], color='#efbd76', alpha=.65)
        right.set_ylabel(tr(self.report.get('variables', ['ndvi', 'lst'])[1]+' anomaly · '+self.report.get('units', ['1', 'degC'])[1])); ax.set_title(tr('Observed monthly anomalies'))

    def lags(self, ax, report):
        rows = report['lag_profiles']
        for field, color in [('pearson', '#69d9bd'), ('spearman', '#b99de8')]:
            ax.plot([r['lag_months'] for r in rows], [r[field] for r in rows], 'o-', color=color, label=tr(field))
        ax.set_xlabel(tr('Y lag (months)')); ax.set_ylabel(tr('Anomaly correlation')); ax.set_title(tr('Exploratory lag profile'))
        ax.legend(facecolor='#101b29', labelcolor='#bacbd8', fontsize=8, loc='upper left')

    def cancel_analysis(self):
        if self.output is not None:
            request_cancel(self.output); self.cancel_button.setEnabled(False)
            self.info.setText(tr('Cancellation requested; partial products will not be published.'))

    def read_progress(self):
        self._progress_text += bytes(self.process.readAllStandardOutput().data()).decode(errors='replace')
        lines = self._progress_text.split('\n'); self._progress_text = lines.pop()
        for line in lines:
            try:
                data = json.loads(line)
                if data.get('event') == 'progress':
                    self.progress.setRange(0, 1000); self.progress.setValue(int(1000*data['done']/max(data['total'], 1)))
                    self.info.setText(tr(f"{data['phase']} · {data['done']}/{data['total']}"))
            except ValueError: self._error_log = (self._error_log+'\n'+line)[-2000:]
