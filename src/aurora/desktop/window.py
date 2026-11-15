"""AURORA Desktop — Scientific investigation interface."""

import json
import sys

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox,
    QPushButton, QPlainTextEdit, QSpinBox,
    QTabWidget, QMessageBox, QProgressBar
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import TwoSlopeNorm


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
        self.setStyleSheet(STYLE)

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

        layout.addWidget(title)
        layout.addWidget(subtitle)

        controls = QHBoxLayout()

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

        layout.addLayout(controls)

        self.status = QLabel()
        layout.addWidget(self.status)

        self.run_button = QPushButton(
            "Run scientific investigation"
        )
        self.run_button.clicked.connect(self.run)
        layout.addWidget(self.run_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.tabs = QTabWidget()

        self.summary = QPlainTextEdit()
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
        self.tabs.addTab(
            self.map_canvas, "Spatial trends"
        )
        self.tabs.addTab(
            self.series_canvas, "Temporal analysis"
        )
        self.tabs.addTab(
            self.log, "Execution log"
        )

        layout.addWidget(self.tabs, 1)

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
        self.summary.clear()
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

        self.summary.setPlainText(
            json.dumps(result, indent=4)
        )

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

    def draw_map(self, history, metrics):

        with rasterio.open(
            history / "trend_slope.tif"
        ) as src:

            data = (
                src.read(1, masked=True)
                .astype("float64")
                .filled(np.nan)
            )
            bounds = src.bounds
            crs = src.crs

        finite = data[np.isfinite(data)]

        limit = (
            float(np.percentile(np.abs(finite), 98))
            if finite.size else 1.0
        )
        limit = max(limit, 1e-12)

        self.map_figure.clear()
        ax = self.map_figure.add_subplot(111)

        cmap = (
            "RdYlGn"
            if metrics["variable"] == "NDVI"
            else "coolwarm"
        )

        image = ax.imshow(
            data,
            cmap=cmap,
            norm=TwoSlopeNorm(
                vmin=-limit,
                vcenter=0,
                vmax=limit
            ),
            extent=(
                bounds.left, bounds.right,
                bounds.bottom, bounds.top
            ),
            origin="upper"
        )

        ax.set_title(
            f'{metrics["variable"]} | Spatial trend'
        )
        ax.set_xlabel(f"Easting — {crs}")
        ax.set_ylabel("Northing")

        colorbar = self.map_figure.colorbar(
            image, ax=ax, shrink=0.8, extend="both"
        )

        colorbar.set_label(
            metrics["slope_unit"],
            color="#bacbd8"
        )
        colorbar.ax.tick_params(colors="#bacbd8")

        self.style_axes(ax)
        self.map_figure.tight_layout()
        self.map_canvas.draw()

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
