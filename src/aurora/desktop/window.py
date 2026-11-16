"""AURORA Desktop — Scientific investigation interface."""

from .i18n import error_text, localized_label, localized_button, add_choices, tr, tr_items, LanguageController, active_language, metadata_text, log_text

import json
import sys

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

from PySide6.QtCore import QProcess, QSettings
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFrame
from .mission_theme import DARK_STYLE, LIGHT_STYLE
from .appearance import refresh_figures
from .report import render_report
from .mission_home import MissionHome
from .ai_lab import AILaboratory
from .time_machine import TimeMachine
from .temporal import TemporalSelector
from .multivariate_lab import MultivariateLaboratory
from .dataset_controls import populate_regions, populate_variables
from .global_results import GlobalResultsMixin
from aurora.jobs import fresh
from .globe import PlanetaryExplorer
from .pixel_lab import open_pixel_lab
from PySide6.QtWidgets import QTextBrowser
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox,
    QPushButton, QPlainTextEdit, QSpinBox,
    QTabWidget, QMessageBox, QProgressBar, QScrollArea
)

from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, FuncFormatter
from .canvas import FigureCanvasQTAgg
from matplotlib.colors import (
    TwoSlopeNorm, ListedColormap, BoundaryNorm
)
from .toolbar import NavigationToolbar2QT

MAP_LAYERS = {
    "OLS trend": "trend_slope.tif",
    "Theil-Sen trend": "trend_sen.tif",
    "Statistical significance": "trend_significant.tif",
    "Estimated change": "trend_change.tif",
    "Satellite coverage": "coverage.tif"
}


ROOT = Path(__file__).resolve().parents[3]

STYLE = """
QWidget {
    background: #101820;
    color: #e5edf5;
    font-size: 13px;
}
QComboBox, QSpinBox, QPlainTextEdit {
    background: #172531;
    border: 1px solid #304352;
    border-radius: 6px;
    padding: 8px;
}
QPushButton {
    background: #267c70;
    border: none;
    border-radius: 6px;
    padding: 12px;
    font-weight: bold;
}
QPushButton:hover {
    background: #329d8c;
}
QPushButton:disabled {
    background: #25333e;
    color: #71828e;
}
QTabBar::tab {
    background: #172531;
    padding: 12px 22px;
}
QTabBar::tab:selected {
    background: #267c70;
}
QProgressBar {
    border: none;
    background: #243340;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background: #53c5ae;
}
"""


class AuroraWindow(QMainWindow, GlobalResultsMixin):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            tr("AURORA — Earth System Intelligence")
        )
        self.resize(1280, 820)
        self.settings = QSettings("AURORA", "Desktop")
        self.appearance = self.settings.value("appearance", "dark")
        self.setStyleSheet(
            LIGHT_STYLE if self.appearance == "light" else DARK_STYLE
        )
        self.setMinimumSize(1000, 680)
        self.setWindowIcon(
            QIcon(str(ROOT / "assets/desktop/logo.svg"))
        )

        self.root_path = ROOT
        self.process = QProcess(self)
        self.output_path = None

        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )

        self.process.readyReadStandardOutput.connect(
            self.read_output
        )

        self.process.finished.connect(
            self.finished
        )

        self.process.errorOccurred.connect(
            self.process_error
        )

        self.build_ui()
        self.stabilize_progress_bars()
        names = ['Home', 'Planetary Explorer', 'Time Machine', 'Predictive intelligence',
                 'Multivariate Laboratory', 'Scientific results', 'Spatial analysis', 'Temporal analysis', 'Execution log']
        for index, name in enumerate(names):
            self.tabs.setTabText(index, name)
        self.language_controller = LanguageController(self)
        self.language_selector.currentIndexChanged.connect(self.change_interface_language)
        self.check_dataset()
        self.start_dataset_watch()

    def stabilize_progress_bars(self):
        for bar in self.findChildren(QProgressBar):
            policy = bar.sizePolicy()
            policy.setRetainSizeWhenHidden(True)
            bar.setSizePolicy(policy)
            bar.setFixedHeight(6)
            bar.setTextVisible(False)

    def change_appearance(self, *_):
        self.appearance = self.theme_selector.currentData()

        self.settings.setValue("appearance", self.appearance)
        self.settings.sync()

        self.setStyleSheet(
            LIGHT_STYLE if self.appearance == "light" else DARK_STYLE
        )
        refresh_figures(self)

    def change_interface_language(self, *_):
        self.language_controller.change(self.language_selector.currentData())

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = localized_label("A U R O R A")
        title.setStyleSheet(
            "font-size: 32px; font-weight: bold;"
            "color: #80d9c7;"
        )

        subtitle = localized_label(
            'EARTH SYSTEM INTELLIGENCE  /  Scientific Investigation Environment'
        )

        title.setObjectName("brand")
        subtitle.setObjectName("subtitle")

        header = QHBoxLayout()

        logo = localized_label()
        logo.setPixmap(
            QPixmap(str(ROOT / "assets/desktop/logo.svg"))
            .scaled(66, 66)
        )

        branding = QVBoxLayout()
        branding.addWidget(title)
        branding.addWidget(subtitle)

        header.addWidget(logo)
        header.addLayout(branding)
        header.addStretch()

        edition = localized_label('RESEARCH EDITION')
        edition.setStyleSheet(
            "color: #69d9bd; font-size: 11px;"
        )
        header.addWidget(localized_label('Language'))
        self.language_selector = QComboBox()
        self.language_selector.setObjectName('interfaceLanguage')
        self.language_selector.addItem('English', 'en')
        self.language_selector.addItem('Español', 'es')
        self.language_selector.setCurrentIndex(self.language_selector.findData(active_language()))
        self.language_selector.setToolTip(tr('Choose the interface language. Applied immediately; saved for the next launch.'))
        header.addWidget(self.language_selector)
        self.theme_selector = QComboBox()
        self.theme_selector.addItem(tr("Dark"), "dark")
        self.theme_selector.addItem(tr("Light"), "light")
        self.theme_selector.setCurrentIndex(
            max(0, self.theme_selector.findData(self.appearance))
        )

        self.theme_selector.currentIndexChanged.connect(
            self.change_appearance
        )

        header.addWidget(self.theme_selector)
        header.addWidget(edition)

        layout.addLayout(header)

        workspace = QHBoxLayout()
        workspace.setSpacing(18)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(290)

        panel = QVBoxLayout(sidebar)
        panel.setContentsMargins(18, 20, 18, 20)
        panel.setSpacing(16)

        heading = localized_label('Investigation setup')
        heading.setStyleSheet(
            "font-size: 19px; font-weight: bold;"
        )
        panel.addWidget(heading)

        description = localized_label(
            'Configure an environmental investigation using historical satellite observations.'
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #8da5ba;")
        panel.addWidget(description)

        controls = QVBoxLayout()

        self.variable = QComboBox()
        self.variable.addItem(
            tr('Vegetation activity — NDVI'), "ndvi"
        )
        self.variable.addItem(
            tr('Land surface temperature — LST'), "lst"
        )

        self.region = QComboBox()
        self.registry = populate_regions(self.region, ROOT)
        populate_variables(self.variable, self.registry, self.region.currentData(), preserve=False)

        self.temporal = TemporalSelector()
        self.start, self.end = self.temporal.start, self.temporal.end

        for label, widget in [
            ("Environmental variable", self.variable),
            ("Region of interest", self.region)
        ]:
            column = QVBoxLayout()
            column.addWidget(localized_label(label))
            column.addWidget(widget)
            controls.addLayout(column)

        panel.addLayout(controls)
        panel.addWidget(self.temporal)

        self.status = localized_label()
        self.status.setWordWrap(True)
        panel.addWidget(self.status)

        self.run_button = localized_button(
            "Run scientific investigation"
        )
        self.run_button.clicked.connect(self.run)
        panel.addWidget(self.run_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        panel.addWidget(self.progress)
        self.setup_global_controls(panel)

        panel.addStretch()

        source = localized_label(
            "SATELLITE OBSERVATIONS\n"
            "NASA Terra / MODIS\n\n"
            "Statistical trend detection\n"
            "Geospatial analysis"
        )
        source.setStyleSheet(
            "color: #8da5ba; font-size: 12px;"
        )
        panel.addWidget(source)

        self.tabs = QTabWidget()

        self.welcome = MissionHome(
            ROOT, self.tabs.setCurrentIndex, self
        )
        self.tabs.addTab(self.welcome, tr('Home'))

        self.planetary_explorer = PlanetaryExplorer(ROOT, self)

        self.tabs.addTab(
            self.planetary_explorer, tr('Planetary Explorer')
        )

        self.time_machine = TimeMachine(ROOT, self)

        self.tabs.addTab(
            self.time_machine, tr("Time Machine")
        )


        self.ai_lab = AILaboratory(ROOT, self)

        self.tabs.addTab(
            self.ai_lab, tr("Predictive intelligence")
        )


        self.multivariate_lab = MultivariateLaboratory(ROOT, self)
        self.tabs.addTab(self.multivariate_lab, tr('Multivariate Laboratory'))

        self.summary = QTextBrowser()
        self.summary.setReadOnly(True)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        self.map_figure = Figure(
            facecolor="#101820"
        )
        self.map_canvas = FigureCanvasQTAgg(
            self.map_figure
        )

        self.series_figure = Figure(
            facecolor="#101820"
        )
        self.series_canvas = FigureCanvasQTAgg(
            self.series_figure
        )

        self.tabs.addTab(
            self.summary, tr("Scientific results")
        )
        self.map_panel = QWidget()
        map_layout = QVBoxLayout(self.map_panel)

        self.layer_selector = QComboBox()
        add_choices(self.layer_selector, list(MAP_LAYERS))

        self.map_toolbar = NavigationToolbar2QT(
            self.map_canvas, self
        )

        map_layout.addWidget(localized_label('Scientific map layer'))
        map_layout.addWidget(self.layer_selector)
        map_layout.addWidget(self.map_toolbar)
        map_layout.addWidget(self.map_canvas, 1)

        self.pixel_info = localized_label(
            "Click to inspect a pixel. Double-click to explore its history."
        )
        self.pixel_info.setWordWrap(True)
        self.pixel_info.setStyleSheet(
            "background:#14202d;"
            "color:#69d9bd;"
            "padding:14px;border-radius:8px;"
        )

        map_layout.addWidget(self.pixel_info)

        self.map_canvas.mpl_connect(
            "button_press_event",
            self.inspect_pixel
        )


        self.layer_selector.currentIndexChanged.connect(
            self.refresh_map
        )

        self.tabs.addTab(
            self.map_panel, tr("Spatial analysis")
        )
        self.tabs.addTab(
            self.series_canvas, tr("Temporal analysis")
        )
        self.tabs.addTab(
            self.log, tr("Execution log")
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True); scroll.setFixedWidth(310)
        scroll.setWidget(sidebar)
        sidebar = scroll
        self.investigation_panel = sidebar
        explorer = self.planetary_explorer
        for page in (explorer, self.multivariate_lab):
            page.setup_toggle.show()
            page.setup_toggle.clicked.connect(lambda checked: sidebar.setVisible(checked))

        def sync_workspace(index):
            for page in (explorer, self.multivariate_lab):
                page.setup_toggle.setChecked(False)

            sidebar.setVisible(index in (2, 5, 6, 7, 8))

            for button in getattr(self, "mission_navigation", []):
                button.setChecked(index in button.property("pageIndexes"))

        self.tabs.currentChanged.connect(sync_workspace)
        workspace.addWidget(sidebar)
        workspace.addWidget(self.tabs, 1)

        self.tabs.tabBar().hide()

        navigation = QHBoxLayout()
        navigation.setSpacing(8)

        self.mission_navigation = []

        for caption, indexes in (
            ("Home", (0,)),
            ("Explore", (1, 2)),
            ("Research", (5, 4, 6, 7, 8)),
            ("Predictive intelligence", (3,)),
        ):
            button = localized_button(caption)
            button.setObjectName("missionNavigation")
            button.setCheckable(True)
            button.setProperty("pageIndexes", indexes)
            button.clicked.connect(
                lambda checked=False, i=indexes[0]:
                    self.tabs.setCurrentIndex(i)
            )
            navigation.addWidget(button, 1)
            self.mission_navigation.append(button)

        layout.addLayout(navigation)

        scientific_navigation = QFrame()
        scientific_navigation.setObjectName("scientificNavigation")
        scientific_row = QHBoxLayout(scientific_navigation)
        scientific_row.setContentsMargins(8, 4, 8, 4)

        exploration_navigation = QFrame()
        exploration_navigation.setObjectName("scientificNavigation")
        exploration_row = QHBoxLayout(exploration_navigation)
        exploration_row.setContentsMargins(8, 4, 8, 4)

        for caption, index in (
            ("Planetary Explorer", 1),
            ("Time Machine", 2),
        ):
            button = localized_button(caption)
            button.clicked.connect(
                lambda checked=False, i=index:
                    self.tabs.setCurrentIndex(i)
            )
            exploration_row.addWidget(button)

        for caption, index in (
            ("Scientific results", 5),
            ("Multivariate Laboratory", 4),
            ("Spatial analysis", 6),
            ("Temporal analysis", 7),
            ("Execution log", 8),
        ):
            button = localized_button(caption)
            button.clicked.connect(
                lambda checked=False, i=index:
                    self.tabs.setCurrentIndex(i)
            )
            scientific_row.addWidget(button)

        self.tabs.currentChanged.connect(
            lambda index: scientific_navigation.setVisible(index >= 4)
        )

        self.tabs.currentChanged.connect(
            lambda index: exploration_navigation.setVisible(
                index in (1, 2)
            )
        )

        exploration_navigation.setVisible(
            self.tabs.currentIndex() in (1, 2)
        )

        layout.addWidget(exploration_navigation)
        layout.addWidget(scientific_navigation)
        layout.addLayout(workspace, 1)

        scientific_navigation.setVisible(
            self.tabs.currentIndex() >= 4
        )
        sync_workspace(self.tabs.currentIndex())

        footer = localized_label(
            "AURORA v5.0  |  "
            "NASA Space Apps Challenge 2026"
        )
        footer.setStyleSheet("color: #718b9d;")
        layout.addWidget(footer)

        self.variable.currentIndexChanged.connect(
            self.check_dataset
        )
        self.region.currentIndexChanged.connect(self.region_changed_global)

    def check_dataset(self):

        key = (
            self.region.currentData(),
            self.variable.currentData()
        )

        try:
            directory = self.registry.find(*key).directory
            available = True
        except FileNotFoundError:
            directory, available = None, False

        if available and getattr(self, "_temporal_dataset", None) != directory:
            self.temporal.set_dates(self.registry.find(*key).dates)
        elif not available:
            self.temporal.set_dates([])
        self._temporal_dataset = directory

        running = self.process.state() != (
            QProcess.ProcessState.NotRunning
        )

        self.run_button.setEnabled(
            available and not running
        )

        self.status.setText(
            tr("Historical dataset available"
            if available else
            "Historical dataset unavailable")
        )

        self.status.setStyleSheet("color: #80d9c7;" if available else "color: #e6b66b;")
        self.refresh_global_results()

    def run(self):

        try:
            start, end = self.temporal.interval()
        except ValueError as exc:
            QMessageBox.warning(self, tr("Invalid investigation"), error_text(exc))
            return

        region = self.region.currentData()
        variable = self.variable.currentData()

        from datetime import datetime
        record = self.registry.find(region, variable)
        self.output_path = ROOT / "outputs/global_engine" / f"{record.identifier}_{datetime.now():%Y%m%d_%H%M%S_%f}"
        self.cancel_button.setEnabled(True); self.export_button.setEnabled(False)
        self._progress_buffer = ''
        self._log_buffer = ''
        self.log.clear()
        self.summary.setHtml(
            tr("<h2>Scientific investigation running...</h2>")
        )
        self.map_figure.clear()
        self.series_figure.clear()
        self.map_canvas.draw()
        self.series_canvas.draw()
        self.tabs.setCurrentWidget(self.log)

        for widget in [
            self.variable, self.region,
            self.temporal, self.run_button
        ]:
            widget.setEnabled(False)

        self.progress.setRange(0, 0)
        self.status.setText(
            tr("Scientific investigation running...")
        )

        self.process.setWorkingDirectory(str(ROOT))

        self.process.start(
            sys.executable,
            [
                "-u",
                str(ROOT / "scripts/scientific_job.py"),
                "--dataset", str(record.directory), "--output", str(self.output_path),
                "--region", region, "--start", start, "--end", end,
                "--memory-mib", "64", "--block-size", "32"
            ]
        )

    def read_output(self):

        text = bytes(self.process.readAllStandardOutput().data()).decode("utf-8", errors="replace")

        self.parse_progress(text)
        self.log.moveCursor(
            self.log.textCursor().MoveOperation.End
        )

        self.append_worker_log(text)
        self.log.ensureCursorVisible()

    def append_worker_log(self, text, final=False):
        self._log_buffer = getattr(self, '_log_buffer', '') + text
        lines = self._log_buffer.splitlines(keepends=True)
        self._log_buffer = ''
        if lines and not lines[-1].endswith('\n') and not final:
            self._log_buffer = lines.pop()
        self.log.insertPlainText(log_text(''.join(lines)))

    def restore_controls(self):

        self.progress.setRange(0, 1)

        for widget in [
            self.variable, self.region,
            self.temporal
        ]:
            widget.setEnabled(True)

        self.check_dataset()

    def process_error(self, error):

        self.log.appendPlainText(
            error_text(self.process.errorString())
        )

        if self.process.state() == (
            QProcess.ProcessState.NotRunning
        ):
            self.restore_controls()
            self.status.setText(tr('Execution error'))

    def finished(self, code, exit_status):

        completed_output = self.output_path
        self.read_output()
        self.append_worker_log("", final=True)
        self.cancel_button.setEnabled(False)
        self.restore_controls()
        self.output_path = completed_output

        if (
            code != 0
            or exit_status != QProcess.ExitStatus.NormalExit
        ):
            self.status.setText(tr(tr('Investigation cancelled') if code == 2 else tr('Investigation failed')))
            return

        try:
            self.load_results()
        except Exception as exc:
            self.log.appendPlainText(error_text(exc))
            self.status.setText(tr('Result loading failed'))
            return

        self.progress.setValue(1)
        self.status.setText(tr('Investigation completed'))
        self.tabs.setCurrentWidget(self.summary)

    def load_results(self):

        if self.output_path is None:
            raise ValueError("No scientific result selected")

        manifest = self.output_path / 'manifest.json'
        if manifest.exists():
            record = json.loads(manifest.read_text())
            if record.get('status') != 'complete' or not fresh(record):
                raise ValueError('Incomplete or stale scientific result')
            record['directory'] = self.output_path
            self.load_global_result(record)
            return
        history = self.output_path / "history"

        if (self.output_path / "descriptive.json").exists():
            data = json.loads((self.output_path / "descriptive.json").read_text())
            self.current_history = None
            self.summary.setPlainText(metadata_text(data))
            self.map_figure.clear(); self.map_canvas.draw()
            self.series_figure.clear()
            ax = self.series_figure.add_subplot(111)
            ax.plot(data["dates"], data["mean"], color="#69d9bd")
            ax.set_title(tr("Monthly observations · descriptive period"))
            ax.set_ylabel(tr(data["unit"])); self.style_axes(ax)
            self.series_canvas.draw()
            return
        metrics = json.loads(
            (history / "metrics.json").read_text()
        )

        regional = json.loads(
            (history / "regional_trend.json").read_text()
        )

        result = {
            "historical_analysis": metrics,
            "regional_analysis": regional
        }

        self.summary.setHtml(
            tr(render_report(metrics, regional))
        )

        self.current_history = history
        self.current_metrics = metrics

        self.draw_map(history, metrics)
        self.draw_series(history, metrics)

    def style_axes(self, ax):

        ax.set_facecolor("#101820")
        ax.tick_params(colors="#bacbd8")
        ax.title.set_color("#e5edf5")
        ax.xaxis.label.set_color("#bacbd8")
        ax.yaxis.label.set_color("#bacbd8")

        for spine in ax.spines.values():
            spine.set_color("#405568")

    def inspect_pixel(self, event):

        if event.button != 1:
            return
        history = self.current_history
        if history is not None and (history/'manifest.json').exists():
            self.inspect_global_pixel(event)
            return

        if self.current_history is None:
            return

        if self.process.state() != QProcess.ProcessState.NotRunning:
            return

        if self.map_toolbar.mode:
            return

        if not self.map_figure.axes:
            return

        if event.inaxes is not self.map_figure.axes[0]:
            return

        if event.xdata is None or event.ydata is None:
            return

        x, y = event.xdata, event.ydata
        history = self.current_history
        if history is None:
            return

        try:
            with rasterio.open(
                history / "trend_slope.tif"
            ) as src:

                row, col = src.index(x, y)

                if not (
                    0 <= row < src.height
                    and 0 <= col < src.width
                ):
                    return

                projected = transform(
                    src.crs, "EPSG:4326", [x], [y]
                )
                lon, lat = projected[0], projected[1]

            values = {}

            for key, filename in [
                ("OLS", "trend_slope.tif"),
                ("Sen", "trend_sen.tif"),
                ("p", "trend_p.tif"),
                ("q", "trend_q.tif"),
                ("change", "trend_change.tif"),
                ("coverage", "coverage.tif"),
                ("years", "trend_n.tif")
            ]:

                with rasterio.open(
                    history / filename
                ) as src:

                    value = next(
                        src.sample([(x, y)], masked=True)
                    )[0]

                    values[key] = (
                        None if np.ma.is_masked(value)
                        else float(value)
                    )

            if values["OLS"] is None:
                self.pixel_info.setText(
                    tr("No evaluated trend at this location.")
                )
                return

            def fmt(key, digits=6):
                value = values[key]
                return (
                    "N/A" if value is None
                    else f"{value:.{digits}f}"
                )

            coverage = values["coverage"]

            coverage_text = (
                "N/A" if coverage is None
                else f"{coverage:.2%}"
            )

            unit = self.current_metrics["slope_unit"]

            self.pixel_info.setText(
                tr(f"PIXEL [{row}, {col}]  |  "
                f"Lat: {lat[0]:.5f}°  "
                f"Lon: {lon[0]:.5f}°\n"
                f"OLS: {fmt('OLS')} {unit}  |  "
                f"Sen: {fmt('Sen')}  |  "
                f"Change: {fmt('change')}\n"
                f"p: {fmt('p')}  |  "
                f"q: {fmt('q')}  |  "
                f"Coverage: {coverage_text}  |  "
                f"Valid years: {fmt('years', 0)}")
            )

            if event.dblclick:
                open_pixel_lab(
                    self,
                    history.parent / "cube.npz",
                    row, col, lat[0], lon[0]
                )

        except Exception as exc:
            self.pixel_info.setText(
                tr("Pixel inspection failed: ")+error_text(exc)
            )

    def refresh_map(self, *_):

        if self.current_history is None:
            return

        if self.process.state() != (
            QProcess.ProcessState.NotRunning
        ):
            return

        if (self.current_history/'manifest.json').exists(): self.draw_global_map()
        else: self.draw_map(self.current_history, self.current_metrics)

    def draw_map(self, history, metrics):

        layer = self.layer_selector.currentData()
        variable = metrics["variable"]

        with rasterio.open(
            history / MAP_LAYERS[layer]
        ) as src:

            data = (
                src.read(1, masked=True)
                .astype("float64")
                .filled(np.nan)
            )

            bounds = src.bounds
            crs = src.crs

        self.map_figure.clear()
        self.map_figure.set_facecolor("#080e17")

        ax = self.map_figure.add_subplot(111)

        extent = (
            bounds.left, bounds.right,
            bounds.bottom, bounds.top
        )

        label = metrics["slope_unit"]
        extend = "neither"

        if layer == "Statistical significance":

            cmap = ListedColormap([
                "#46576a", "#69d9bd"
            ])

            norm = BoundaryNorm(
                [-0.5, 0.5, 1.5], cmap.N
            )

            label = "OLS / BH-FDR nominal significance"

        elif layer == "Satellite coverage":

            data *= 100
            cmap = "viridis"
            norm = None
            label = "Valid observations (%)"

        else:

            finite = data[np.isfinite(data)]

            limit = (
                float(np.percentile(np.abs(finite), 98))
                if finite.size else 1.0
            )

            limit = max(limit, 1e-12)

            cmap = (
                "RdYlGn" if variable == "NDVI"
                else "coolwarm"
            )

            norm = TwoSlopeNorm(
                vmin=-limit, vcenter=0, vmax=limit
            )

            extend = "both"

            if layer == "Estimated change":
                label = (
                    "NDVI" if variable == "NDVI"
                    else "Temperature change (°C)"
                )

        options = {
            "cmap": cmap,
            "norm": norm,
            "extent": extent,
            "origin": "upper",
            "interpolation": "nearest"
        }

        if layer == "Satellite coverage":
            options.update(vmin=0, vmax=100)

        image = ax.imshow(data, **options)

        ax.set_title(
            tr(f"{variable} | {layer}"),
            fontsize=15,
            fontweight="bold",
            pad=18
        )

        ax.set_xlabel(tr(f"Easting — {crs}"))
        ax.set_ylabel(tr("Northing"))

        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(5))

        formatter = FuncFormatter(
            lambda value, _: f"{value / 1000:,.0f}"
        )

        ax.xaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_formatter(formatter)

        ax.set_xlabel(tr(f"Easting (km) — {crs}"))
        ax.set_ylabel(tr("Northing (km)"))


        colorbar = self.map_figure.colorbar(
            image, ax=ax,
            shrink=0.8,
            extend=extend
        )

        colorbar.set_label(
            tr(label), color="#bacbd8"
        )

        if layer == "Statistical significance":
            colorbar.set_ticks([0, 1])
            colorbar.set_ticklabels(tr_items([
                "Not significant", "Significant"
            ]))

        colorbar.ax.tick_params(colors="#bacbd8")

        self.style_axes(ax)
        self.map_figure.tight_layout()
        self.map_canvas.draw()
        self.map_toolbar.update()

    def draw_series(self, history, metrics):

        monthly = pd.read_csv(
            history / "monthly_series.csv",
            parse_dates=["date"]
        )

        self.series_figure.clear()
        ax = self.series_figure.add_subplot(111)

        ax.plot(
            monthly["date"],
            monthly["mean"],
            color="#6bd5bd",
            linewidth=1.2,
            label=tr("Monthly observations")
        )

        ax.set_title(tr("Regional monthly time series"))
        ax.set_ylabel(
            tr("NDVI" if metrics["variable"] == "NDVI"
            else "Temperature (°C)")
        )

        ax.grid(alpha=0.15)

        self.style_axes(ax)
        self.series_figure.tight_layout()
        self.series_canvas.draw()

    def closeEvent(self, event):
        self._closing = True
        for jobs in (self.io_jobs, self.planetary_explorer.reader_jobs, self.time_machine.reader_jobs, self.ai_lab.model_jobs):
            jobs.cancel_all()
        for process in (self.process, self.export_process, self.multivariate_lab.process, self.ai_lab.export_process):
            if process.state() != QProcess.ProcessState.NotRunning:
                process.terminate()
                if not process.waitForFinished(1500): process.kill(); process.waitForFinished(500)
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().waitForDone(1500)
        super().closeEvent(event)
