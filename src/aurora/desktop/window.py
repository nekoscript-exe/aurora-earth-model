"""AURORA Desktop — Scientific investigation interface."""

import json
import sys

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

from PySide6.QtCore import QProcess
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFrame
from .theme import STYLE as AURORA_STYLE
from .report import render_report
from .welcome import WelcomePage
from .pixel_lab import open_pixel_lab
from PySide6.QtWidgets import QTextBrowser
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox,
    QPushButton, QPlainTextEdit, QSpinBox,
    QTabWidget, QMessageBox, QProgressBar
)

from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator, FuncFormatter
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import (
    TwoSlopeNorm, ListedColormap, BoundaryNorm
)
from matplotlib.backends.backend_qtagg import (
    NavigationToolbar2QT
)

MAP_LAYERS = {
    "OLS trend": "trend_slope.tif",
    "Theil-Sen trend": "trend_sen.tif",
    "Statistical significance": "trend_significant.tif",
    "Estimated change": "trend_change.tif",
    "Satellite coverage": "coverage.tif"
}


ROOT = Path(__file__).resolve().parents[3]

DATASETS = {
    ("queretaro", "ndvi"): "queretaro",
    ("queretaro", "lst"): "queretaro_lst",
    ("mexico", "ndvi"): "mexico",
    ("mexico", "lst"): "mexico_lst"
}

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


class AuroraWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "AURORA — Earth System Intelligence"
        )
        self.resize(1280, 820)
        self.setStyleSheet(AURORA_STYLE)
        self.setMinimumSize(1000, 680)
        self.setWindowIcon(
            QIcon(str(ROOT / "assets/desktop/logo.svg"))
        )

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
        self.check_dataset()

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("A U R O R A")
        title.setStyleSheet(
            "font-size: 32px; font-weight: bold;"
            "color: #80d9c7;"
        )

        subtitle = QLabel(
            "EARTH SYSTEM INTELLIGENCE  /  "
            "Scientific Investigation Environment"
        )

        title.setObjectName("brand")
        subtitle.setObjectName("subtitle")

        header = QHBoxLayout()

        logo = QLabel()
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

        edition = QLabel("RESEARCH EDITION")
        edition.setStyleSheet(
            "color: #69d9bd; font-size: 11px;"
        )
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

        heading = QLabel("Investigation setup")
        heading.setStyleSheet(
            "font-size: 19px; font-weight: bold;"
        )
        panel.addWidget(heading)

        description = QLabel(
            "Configure an environmental investigation "
            "using historical satellite observations."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #8da5ba;")
        panel.addWidget(description)

        controls = QVBoxLayout()

        self.variable = QComboBox()
        self.variable.addItem(
            "Vegetation activity — NDVI", "ndvi"
        )
        self.variable.addItem(
            "Land surface temperature — LST", "lst"
        )

        self.region = QComboBox()
        self.region.addItem("Queretaro", "queretaro")
        self.region.addItem("Mexico", "mexico")

        self.start = QSpinBox()
        self.start.setRange(2001, 2025)
        self.start.setValue(2001)

        self.end = QSpinBox()
        self.end.setRange(2001, 2025)
        self.end.setValue(2025)

        for label, widget in [
            ("Environmental variable", self.variable),
            ("Region of interest", self.region),
            ("Start year", self.start),
            ("End year", self.end)
        ]:
            column = QVBoxLayout()
            column.addWidget(QLabel(label))
            column.addWidget(widget)
            controls.addLayout(column)

        panel.addLayout(controls)

        self.status = QLabel()
        self.status.setWordWrap(True)
        panel.addWidget(self.status)

        self.run_button = QPushButton(
            "Run scientific investigation"
        )
        self.run_button.clicked.connect(self.run)
        panel.addWidget(self.run_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        panel.addWidget(self.progress)

        panel.addStretch()

        source = QLabel(
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

        self.welcome = WelcomePage(self.run_button.click)
        self.tabs.addTab(self.welcome, "Home")

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
            self.summary, "Scientific results"
        )
        self.map_panel = QWidget()
        map_layout = QVBoxLayout(self.map_panel)

        self.layer_selector = QComboBox()
        self.layer_selector.addItems(list(MAP_LAYERS))

        self.map_toolbar = NavigationToolbar2QT(
            self.map_canvas, self
        )

        map_layout.addWidget(QLabel("Scientific map layer"))
        map_layout.addWidget(self.layer_selector)
        map_layout.addWidget(self.map_toolbar)
        map_layout.addWidget(self.map_canvas, 1)

        self.pixel_info = QLabel(
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
            self.map_panel, "Spatial analysis"
        )
        self.tabs.addTab(
            self.series_canvas, "Temporal analysis"
        )
        self.tabs.addTab(
            self.log, "Execution log"
        )

        workspace.addWidget(sidebar)
        workspace.addWidget(self.tabs, 1)

        layout.addLayout(workspace, 1)

        footer = QLabel(
            "AURORA v4.0  |  "
            "NASA Space Apps Challenge 2026"
        )
        footer.setStyleSheet("color: #718b9d;")
        layout.addWidget(footer)

        self.variable.currentIndexChanged.connect(
            self.check_dataset
        )
        self.region.currentIndexChanged.connect(
            self.check_dataset
        )

    def check_dataset(self):

        key = (
            self.region.currentData(),
            self.variable.currentData()
        )

        directory = (
            ROOT / "data/processed" / DATASETS[key]
        )

        available = (
            (directory / "cube.npz").is_file()
            and
            (directory / "cube_metadata.json").is_file()
        )

        running = self.process.state() != (
            QProcess.ProcessState.NotRunning
        )

        self.run_button.setEnabled(
            available and not running
        )

        self.status.setText(
            "Historical dataset available"
            if available else
            "Historical dataset unavailable"
        )

        self.status.setStyleSheet(
            "color: #80d9c7;"
            if available else
            "color: #e6b66b;"
        )

    def run(self):

        start = self.start.value()
        end = self.end.value()

        if end - start + 1 < 15:
            QMessageBox.warning(
                self,
                "Invalid investigation",
                "Select at least 15 calendar years."
            )
            return

        region = self.region.currentData()
        variable = self.variable.currentData()

        self.output_path = (
            ROOT / "outputs/investigations" /
            f"{region}_{variable}_{start}-01_{end}-12"
        )

        self.log.clear()
        self.summary.setHtml(
            "<h2>Scientific investigation running...</h2>"
        )
        self.map_figure.clear()
        self.series_figure.clear()
        self.map_canvas.draw()
        self.series_canvas.draw()
        self.tabs.setCurrentWidget(self.log)

        for widget in [
            self.variable, self.region,
            self.start, self.end, self.run_button
        ]:
            widget.setEnabled(False)

        self.progress.setRange(0, 0)
        self.status.setText(
            "Scientific investigation running..."
        )

        self.process.setWorkingDirectory(str(ROOT))

        self.process.start(
            sys.executable,
            [
                "-u",
                str(ROOT / "scripts/explore.py"),
                "--variable", variable,
                "--region", region,
                "--start", f"{start}-01",
                "--end", f"{end}-12",
                "--run"
            ]
        )

    def read_output(self):

        text = bytes(
            self.process.readAllStandardOutput()
        ).decode("utf-8", errors="replace")

        self.log.moveCursor(
            self.log.textCursor().MoveOperation.End
        )

        self.log.insertPlainText(text)
        self.log.ensureCursorVisible()

    def restore_controls(self):

        self.progress.setRange(0, 1)

        for widget in [
            self.variable, self.region,
            self.start, self.end
        ]:
            widget.setEnabled(True)

        self.check_dataset()

    def process_error(self, error):

        self.log.appendPlainText(
            self.process.errorString()
        )

        if self.process.state() == (
            QProcess.ProcessState.NotRunning
        ):
            self.restore_controls()
            self.status.setText("Execution error")

    def finished(self, code, exit_status):

        self.read_output()
        self.restore_controls()

        if (
            code != 0
            or exit_status != QProcess.ExitStatus.NormalExit
        ):
            self.status.setText("Investigation failed")
            return

        try:
            self.load_results()
        except Exception as exc:
            self.log.appendPlainText(str(exc))
            self.status.setText("Result loading failed")
            return

        self.progress.setValue(1)
        self.status.setText("Investigation completed")
        self.tabs.setCurrentWidget(self.summary)

    def load_results(self):

        history = self.output_path / "history"

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
            render_report(metrics, regional)
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

        if not hasattr(self, "current_history"):
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

                lon, lat = transform(
                    src.crs, "EPSG:4326", [x], [y]
                )

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
                    "No evaluated trend at this location."
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
                f"PIXEL [{row}, {col}]  |  "
                f"Lat: {lat[0]:.5f}°  "
                f"Lon: {lon[0]:.5f}°\n"
                f"OLS: {fmt('OLS')} {unit}  |  "
                f"Sen: {fmt('Sen')}  |  "
                f"Change: {fmt('change')}\n"
                f"p: {fmt('p')}  |  "
                f"q: {fmt('q')}  |  "
                f"Coverage: {coverage_text}  |  "
                f"Valid years: {fmt('years', 0)}"
            )

            if event.dblclick:
                open_pixel_lab(
                    self,
                    history.parent / "cube.npz",
                    row, col, lat[0], lon[0]
                )

        except Exception as exc:
            self.pixel_info.setText(
                f"Pixel inspection failed: {exc}"
            )

    def refresh_map(self, *_):

        if not hasattr(self, "current_history"):
            return

        if self.process.state() != (
            QProcess.ProcessState.NotRunning
        ):
            return

        self.draw_map(
            self.current_history,
            self.current_metrics
        )

    def draw_map(self, history, metrics):

        layer = self.layer_selector.currentText()
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
            f"{variable} | {layer}",
            fontsize=15,
            fontweight="bold",
            pad=18
        )

        ax.set_xlabel(f"Easting — {crs}")
        ax.set_ylabel("Northing")

        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(5))

        formatter = FuncFormatter(
            lambda value, _: f"{value / 1000:,.0f}"
        )

        ax.xaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_formatter(formatter)

        ax.set_xlabel(f"Easting (km) — {crs}")
        ax.set_ylabel("Northing (km)")


        colorbar = self.map_figure.colorbar(
            image, ax=ax,
            shrink=0.8,
            extend=extend
        )

        colorbar.set_label(
            label, color="#bacbd8"
        )

        if layer == "Statistical significance":
            colorbar.set_ticks([0, 1])
            colorbar.set_ticklabels([
                "Not significant", "Significant"
            ])

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
            label="Monthly observations"
        )

        ax.set_title("Regional monthly time series")
        ax.set_ylabel(
            "NDVI" if metrics["variable"] == "NDVI"
            else "Temperature (°C)"
        )

        ax.grid(alpha=0.15)

        self.style_axes(ax)
        self.series_figure.tight_layout()
        self.series_canvas.draw()
