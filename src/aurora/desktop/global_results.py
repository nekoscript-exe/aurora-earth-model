"""Functional integration of complete, fresh scientific job products."""

from .i18n import tr
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .window import AuroraWindow
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window
from affine import Affine
from PySide6.QtCore import QProcess, QFileSystemWatcher, QTimer
from PySide6.QtWidgets import QFileDialog, QLabel, QComboBox, QPushButton, QDialog, QVBoxLayout
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from aurora.jobs import ResultRegistry, fresh, request_cancel
from aurora.catalog import CubeReader, populate_regions, populate_variables
from .tasks import ReaderJobs


class GlobalResultsMixin:
    def setup_global_controls(self, panel):
        self = cast("AuroraWindow", self)
        self.result_selector = QComboBox(); self.result_selector.setToolTip('Completed results; stale results cannot be presented as current')
        self.result_selector.currentIndexChanged.connect(self.select_global_result)
        self.refresh_button = QPushButton(tr('Refresh datasets / results')); self.refresh_button.clicked.connect(self.refresh_catalogs)
        self.cancel_button = QPushButton(tr('Cancel operation')); self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.export_button = QPushButton('Export CSV / JSON / GeoTIFF / PNG'); self.export_button.clicked.connect(self.export_global_result)
        for widget in (self.refresh_button, QLabel(tr('Available scientific results')), self.result_selector, self.export_button, self.cancel_button): panel.addWidget(widget)
        self.io_jobs = ReaderJobs(self, self.main_io_result, lambda error: self.pixel_info.setText(error))
        self._progress_buffer = ''; self.export_process = QProcess(self)
        self.export_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.export_process.readyReadStandardOutput.connect(self.read_export_progress)
        self.export_process.finished.connect(self.export_finished)

    def region_changed_global(self, *_):
        self = cast("AuroraWindow", self)
        populate_variables(self.variable, self.registry, self.region.currentData())
        self.current_history = None; self.check_dataset()

    def refresh_catalogs(self):
        self = cast("AuroraWindow", self)
        processes = (self.process, self.export_process, self.multivariate_lab.process, self.ai_lab.export_process)
        if any(process.state() != QProcess.ProcessState.NotRunning for process in processes):
            self.status.setText('Catalog refresh deferred until active scientific/export jobs finish')
            if hasattr(self, 'catalog_refresh_timer'): self.catalog_refresh_timer.start(1000)
            return
        pages = [self, self.planetary_explorer, self.time_machine]
        for page in pages:
            old = page.region.currentData(); page.region.blockSignals(True)
            page.registry = populate_regions(page.region, self.root_path if page is self else page.root)
            index = page.region.findData(old); page.region.setCurrentIndex(index if index >= 0 else 0)
            page.region.blockSignals(False)
            populate_variables(page.variable, page.registry, page.region.currentData())
            if page is not self: page.reset() if hasattr(page, 'reset') else page.reset_dataset()
        self.check_dataset(); self.multivariate_lab.refresh_catalog()
        self.ai_lab.refresh_catalog()
        if hasattr(self, 'dataset_watcher'): self.update_watch_paths()

    def refresh_global_results(self):
        self = cast("AuroraWindow", self)
        if not hasattr(self, 'result_selector') or getattr(self, '_closing', False): return
        self.io_jobs.cancel_all()
        self.io_jobs.start('results', lambda check: ResultRegistry(self.root_path))

    def apply_result_catalog(self, catalog):
        self = cast("AuroraWindow", self)
        self.result_selector.blockSignals(True); self.result_selector.clear()
        region, variable = self.region.currentData(), self.variable.currentData()
        for record in catalog.available(region, variable, 'statistics'):
            label = f"{record['region']} · {variable} · {' — '.join(record['period'])} · {record['inputs'][0]['directory'].split('/')[-1]}"
            self.result_selector.addItem(label, record)
        stale = sum(r['status'] == 'complete' and r['stale'] and r['region'] == region and r.get('variable') == variable for r in catalog.results)
        self.result_selector.blockSignals(False)
        if self.result_selector.count(): self.select_global_result()
        else:
            self.export_button.setEnabled(False); self.current_history = None
            self.summary.setPlainText(f'No fresh completed results for {region}/{variable}. Stale results excluded: {stale}. Run a scientific investigation.')
            self.map_figure.clear(); self.map_canvas.draw_idle(); self.series_figure.clear(); self.series_canvas.draw_idle()

    def select_global_result(self, *_):
        self = cast("AuroraWindow", self)
        record = self.result_selector.currentData()
        if record is None: return
        if not fresh(record):
            self.export_button.setEnabled(False); self.summary.setPlainText('Result is stale: source changed. Recompute before presenting current results.'); return
        self.output_path = Path(record['directory']); self.load_global_result(record)
        self.export_button.setEnabled(True)

    def load_global_result(self, record):
        self = cast("AuroraWindow", self)
        self.current_history = Path(record['directory']); self.current_metrics = record
        self.summary.setPlainText(json.dumps({k: v for k, v in record.items() if k != 'directory'}, indent=2, default=str))
        from .window import MAP_LAYERS
        selected = self.layer_selector.currentText(); self.layer_selector.blockSignals(True); self.layer_selector.clear()
        for label, file in MAP_LAYERS.items():
            if (self.current_history/file).exists(): self.layer_selector.addItem(label)
        index = self.layer_selector.findText(selected); self.layer_selector.setCurrentIndex(index if index >= 0 else 0)
        self.layer_selector.blockSignals(False)
        self.draw_global_map(); self.draw_global_series()

    def draw_global_map(self):
        self = cast("AuroraWindow", self)
        from .window import MAP_LAYERS
        history = self.current_history

        if history is None:
            return

        filename = MAP_LAYERS.get(self.layer_selector.currentText())

        if filename is None:
            return

        path = history / filename

        if not path.is_file():
            return
        with rasterio.open(path) as src:
            factor = max(1, int(np.ceil(max(src.height, src.width)/768)))
            height, width = max(1, src.height//factor), max(1, src.width//factor)
            values = src.read(1, out_shape=(height, width), masked=True, resampling=Resampling.nearest)
            affine = src.transform @ Affine.scale(src.width/width, src.height/height)
            yy, xx = np.meshgrid(np.arange(height+1), np.arange(width+1), indexing='ij')
            east = affine.a*xx+affine.b*yy+affine.c; north = affine.d*xx+affine.e*yy+affine.f
            unit = src.tags().get('unit', '1'); crs = src.crs
        self.map_figure.set_size_inches(max(self.map_canvas.width(), 320)/self.map_figure.dpi, max(self.map_canvas.height(), 200)/self.map_figure.dpi, forward=False)
        self.map_figure.clear(); ax = self.map_figure.add_subplot(111)
        image = ax.pcolormesh(east, north, values, shading='flat', cmap='viridis')
        ax.set_aspect('equal')
        period = ' — '.join(self.current_metrics['period'])
        ax.set_title(f"{self.current_metrics['region']} · {self.current_metrics['variable']} · {self.layer_selector.currentText()}\n{period}"); ax.set_xlabel(f'Native x · {crs}'); ax.set_ylabel('Native y')
        self.map_figure.colorbar(image, ax=ax, label=unit)
        self.style_axes(ax); self.map_figure.tight_layout(); self.map_canvas.draw_idle()
        self.map_toolbar.update()

    def draw_global_series(self):
        self = cast("AuroraWindow", self)
        history = self.current_history

        if history is None:
            return

        data = pd.read_csv(history/'monthly_series.csv', parse_dates=['date'])
        self.series_figure.clear(); ax = self.series_figure.add_subplot(111)
        ax.plot(data['date'], data['mean'], color='#69d9bd')
        ax.set_title(f"Area-weighted monthly observations · {self.current_metrics['region']}\n{' — '.join(self.current_metrics['period'])} · no gap filling"); ax.set_ylabel(self.current_metrics['unit'])
        self.style_axes(ax); self.series_figure.tight_layout(); self.series_canvas.draw_idle()

    def cancel_operation(self):
        self = cast("AuroraWindow", self)
        if self.export_process.state() != QProcess.ProcessState.NotRunning:
            request_cancel(self._export_directory); self.status.setText('Cancelling export…')
        elif self.process.state() != QProcess.ProcessState.NotRunning and self.output_path:
            request_cancel(self.output_path); self.status.setText('Cancelling at a safe block boundary…')
        self.cancel_button.setEnabled(False)

    def parse_progress(self, text):
        self = cast("AuroraWindow", self)
        self._progress_buffer += text
        lines = self._progress_buffer.split('\n'); self._progress_buffer = lines.pop()
        for line in lines:
            try:
                data = json.loads(line)
                if data.get('event') == 'progress':
                    self.progress.setRange(0, 1000); self.progress.setValue(int(1000*data['done']/max(data['total'], 1)))
                    self.status.setText(f"{data['phase']} · {data['done']}/{data['total']}")
            except (ValueError, KeyError): pass

    def export_global_result(self):
        self = cast("AuroraWindow", self)
        record = self.result_selector.currentData()
        if record is None or not fresh(record): return
        directory = QFileDialog.getExistingDirectory(self, 'Export scientific bundle into a new subdirectory')
        if not directory: return
        self._export_directory = Path(directory)/f'aurora_export_{datetime.now():%Y%m%d_%H%M%S_%f}'
        import sys
        self.export_button.setEnabled(False); self.run_button.setEnabled(False); self.cancel_button.setEnabled(True)
        self.export_process.start(sys.executable, [str(self.root_path/'scripts/export_result.py'), '--result', str(record['directory']), '--output', str(self._export_directory)])

    def read_export_progress(self):
        self = cast("AuroraWindow", self)
        text = bytes(self.export_process.readAllStandardOutput().data()).decode(errors='replace'); self.parse_progress(text)

    def export_finished(self, code, *_):
        self = cast("AuroraWindow", self)
        self.cancel_button.setEnabled(False); self.export_button.setEnabled(True); self.check_dataset()
        self.status.setText('Export complete' if code == 0 else 'Export cancelled or failed; partial export not published')

    def inspect_global_pixel(self, event):
        self = cast("AuroraWindow", self)
        if event.xdata is None or event.ydata is None: return
        history = self.current_history

        if history is None:
            return

        with rasterio.open(history/'coverage.tif') as src:
            row, col = src.index(event.xdata, event.ydata)
            if not (0 <= row < src.height and 0 <= col < src.width): return
            coverage = src.read(1, window=Window.from_slices((row, row+1), (col, col+1)), masked=True)[0, 0]
            if np.ma.is_masked(coverage): self.pixel_info.setText('Outside the observed regional footprint'); return
        self.pixel_info.setText(f'Native row {row}, column {col}; observation coverage {coverage:.2%}. Area-weighted regional summaries are separate.')
        if event.dblclick:
            if not fresh(self.current_metrics):
                self.pixel_info.setText('Source changed; recompute results.'); return
            directory = self.current_metrics['inputs'][0]['directory']; unit = self.current_metrics['unit']
            def read(check):
                with CubeReader(directory, check=check) as reader:
                    values = reader.read_series(slice(None), slice(row, row+1), slice(col, col+1)).ravel()
                    return row, col, reader.dates.copy(), values, unit
            self.io_jobs.start('pixel', read)

    def main_io_result(self, kind, payload):
            self = cast("AuroraWindow", self)
            if kind == 'results':
                self.apply_result_catalog(payload); return
            row, col, dates, values, unit = payload
            dialog = QDialog(self); dialog.setWindowTitle('Native pixel observations'); layout = QVBoxLayout(dialog)
            figure = Figure(); canvas = FigureCanvasQTAgg(figure); layout.addWidget(canvas)
            axis = figure.add_subplot(111); axis.plot(dates, values); axis.set_ylabel(unit)
            axis.set_title(f'Observed pixel {row},{col} · gaps preserved'); figure.autofmt_xdate(); canvas.draw()
            dialog.resize(800, 450); dialog.show(); self._pixel_dialog = dialog

    def start_dataset_watch(self):
        self = cast("AuroraWindow", self)
        self.dataset_watcher = QFileSystemWatcher(self)
        self.catalog_refresh_timer = QTimer(self); self.catalog_refresh_timer.setSingleShot(True)
        self.catalog_refresh_timer.timeout.connect(self.apply_catalog_change)
        self.dataset_watcher.directoryChanged.connect(self.queue_catalog_change)
        self.dataset_watcher.fileChanged.connect(self.queue_catalog_change)
        self.update_watch_paths()

    def queue_catalog_change(self, *_):
        self = cast("AuroraWindow", self)
        self.catalog_refresh_timer.start(500)

    def apply_catalog_change(self):
        self = cast("AuroraWindow", self)
        if getattr(self, '_closing', False): return
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.catalog_refresh_timer.start(1000); return
        self.refresh_catalogs()

    def update_watch_paths(self):
        self = cast("AuroraWindow", self)
        candidates = {self.root_path/'data/processed', self.root_path/'config'}
        processed = self.root_path/'data/processed'
        if processed.exists(): candidates.update(p for p in processed.iterdir() if p.is_dir())
        for record in self.registry.records:
            candidates.add(record.directory); candidates.add(record.directory/'cube_metadata.json')
            storage = record.metadata.get('storage', {'path': 'cube.npz'})
            candidates.add(record.directory/storage['path'])
        desired = {str(p) for p in candidates if p.exists()}
        current = set(self.dataset_watcher.directories()+self.dataset_watcher.files())
        if current-desired: self.dataset_watcher.removePaths(sorted(current-desired))
        if desired-current: self.dataset_watcher.addPaths(sorted(desired-current))
