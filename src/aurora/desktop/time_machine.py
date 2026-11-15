"""AURORA — Historical satellite playback."""

import numpy as np
from .temporal import TemporalSelector
from aurora.temporal import select_interval
from aurora.catalog import ObservationSeries, populate_regions, populate_variables, display_scale
from .tasks import ReaderJobs

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QProgressBar
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT
)


class TimeMachine(QWidget):

    def __init__(self, root, parent=None):
        super().__init__(parent)

        self.root = root
        self.reader_jobs = ReaderJobs(self, self.read_ready, self.read_error)
        self.values = None
        self.dates = None
        self.region_mask = None

        self.redraw_timer = QTimer(self); self.redraw_timer.setSingleShot(True)
        self.redraw_timer.timeout.connect(self.draw_visible)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)

        layout = QVBoxLayout(self)

        title = QLabel("Earth Time Machine")
        title.setStyleSheet(
            "font-size:27px;font-weight:bold;"
            "color:#69d9bd;"
        )

        layout.addWidget(title)

        layout.addWidget(QLabel(
            "Explore historical satellite observations."
        ))

        controls = QHBoxLayout()

        self.region = QComboBox()
        self.registry = populate_regions(self.region, root)

        self.variable = QComboBox()
        self.variable.addItem("Vegetation — NDVI", "ndvi")
        self.variable.addItem("Temperature — LST", "lst")

        populate_variables(self.variable, self.registry, self.region.currentData(), preserve=False)

        load = QPushButton("Load satellite imagery")
        load.clicked.connect(lambda _: self.load_dataset(asynchronous=True))

        controls.addWidget(self.region)
        controls.addWidget(self.variable, 1)
        controls.addWidget(load)

        layout.addLayout(controls)
        self.read_progress = QProgressBar(); self.read_progress.setRange(0, 0); self.read_progress.hide()
        self.cancel_read_button = QPushButton('Cancel loading'); self.cancel_read_button.setEnabled(False)
        self.cancel_read_button.clicked.connect(self.cancel_read)
        layout.addWidget(self.read_progress); layout.addWidget(self.cancel_read_button)


        self.figure = Figure(facecolor="#080e17")
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.toolbar = NavigationToolbar2QT(
            self.canvas, self
        )

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        self.period = TemporalSelector()
        layout.addWidget(self.period.create_toggle())
        layout.addWidget(self.period)
        self.period.changed.connect(self.apply_period)

        self.date_label = QLabel("No dataset loaded")

        self.date_label.setStyleSheet(
            "font-size:25px;font-weight:bold;"
            "color:#69d9bd;"
        )

        layout.addWidget(self.date_label)

        self.slider = QSlider(
            Qt.Orientation.Horizontal
        )

        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self.render)

        layout.addWidget(self.slider)

        playback = QHBoxLayout()

        self.previous = QPushButton("Previous")
        self.play = QPushButton("Play")
        self.next = QPushButton("Next")

        self.previous.clicked.connect(
            lambda: self.step(-1)
        )

        self.play.clicked.connect(
            self.toggle_playback
        )

        self.next.clicked.connect(
            lambda: self.step(1)
        )

        self.speed = QComboBox()

        for label, interval in [
            ("0.5x", 1000),
            ("1x", 500),
            ("2x", 250),
            ("4x", 125),
            ("8x", 63)
        ]:
            self.speed.addItem(label, interval)

        self.speed.setCurrentIndex(1)
        self.speed.currentIndexChanged.connect(
            self.update_speed
        )

        for widget in [
            self.previous, self.play,
            self.next, self.speed
        ]:
            playback.addWidget(widget)

        layout.addLayout(playback)

        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setStyleSheet(
            "background:#14202d;color:#a9c7dd;"
            "padding:14px;border-radius:8px;"
        )

        layout.addWidget(self.details)

        self.region.currentIndexChanged.connect(self.region_changed)

        self.variable.currentIndexChanged.connect(
            self.reset_dataset
        )

        self.load_dataset(asynchronous=True)

    def set_controls(self, enabled):

        for widget in [
            self.slider, self.previous,
            self.next, self.play
        ]:
            widget.setEnabled(enabled)

    def pause(self):

        self.timer.stop()
        self.play.setText("Play")

    def hideEvent(self, event):

        self.pause()
        super().hideEvent(event)

    def reset_dataset(self, *_):

        self.reader_jobs.cancel_all()
        self.set_read_busy(False)
        self.pause()
        self.values = None
        self.dates = None
        self.period.set_dates([])
        self.set_controls(False)

        self.figure.clear()
        if self.isVisible(): self.draw_visible()

        self.date_label.setText(
            "Load selected satellite dataset"
        )

        self.details.setText(
            "Select Load satellite imagery to continue."
        )

    def update_speed(self, *_):

        self.timer.setInterval(
            self.speed.currentData()
        )

    def toggle_playback(self):

        if self.values is None:
            return

        if self.timer.isActive():
            self.pause()
        else:
            self.timer.start(
                self.speed.currentData()
            )
            self.play.setText("Pause")

    def apply_period(self):
        if self.values is None or not len(self.period.dates):
            return
        try:
            selected = select_interval(self.dates, *self.period.interval())
        except ValueError:
            return
        indices = np.flatnonzero(selected)
        self.pause()
        self.slider.setRange(int(indices[0]), int(indices[-1]))
        self.slider.setValue(int(indices[0]))

    def step(self, amount):

        if self.values is None or self.reader_jobs.busy('frame'):
            return

        index = (
            self.slider.value() + amount
        ) % len(self.dates)

        self.slider.setValue(index)

    def advance(self):

        self.step(1)

    def load_dataset(self, asynchronous=False):

        self.reset_dataset()

        key = (
            self.region.currentData(),
            self.variable.currentData()
        )

        try:
            record = self.registry.find(*key)
            if asynchronous:
                self.details.setText('Opening observed data in background…')
                variable = self.variable.currentData()
                def read(check):
                    series = ObservationSeries(record.directory, variable, check=check); series[0]; return series
                self.set_read_busy(True)
                self.reader_jobs.start('dataset', read)
                return
            self.attach_series(ObservationSeries(record.directory, self.variable.currentData()))
        except Exception as exc: self.read_error(str(exc))

    def attach_series(self, series):
            self.values = series
            self.dates = self.values.dates
            self.region_mask = self.values.mask
            self.variable_name = self.values.spec.identifier
            self.ensure_figure_size()
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)

            lower, upper, cmap, _ = display_scale(self.values.reader.metadata)
            self.unit = self.values.spec.unit

            self.image = self.ax.imshow(
                self.values[0],
                cmap=cmap,
                vmin=lower,
                vmax=upper,
                interpolation="nearest"
            )

            self.ax.set_facecolor("#080e17")
            self.ax.set_xticks([])
            self.ax.set_yticks([])

            bar = self.figure.colorbar(
                self.image,
                ax=self.ax,
                shrink=0.8,
                extend="both"
            )

            bar.set_label(self.unit, color="#bacbd8")
            bar.ax.tick_params(colors="#bacbd8")

            self.figure.tight_layout()

            self.slider.blockSignals(True)

            self.slider.setRange(
                0, len(self.dates) - 1
            )

            self.slider.setValue(0)
            self.slider.blockSignals(False)

            self.period.set_dates(self.dates)
            self.set_controls(True)
            self.render(0)

            self.toolbar.update()

    def region_changed(self, *_):
        populate_variables(self.variable, self.registry, self.region.currentData()); self.reset_dataset()

    def read_error(self, message):
        self.reset_dataset(); self.details.setText(message)

    def read_ready(self, kind, value):
        self.set_read_busy(False)
        if kind == 'dataset': self.attach_series(value)
        else: self.apply_frame(*value)

    def render(self, index):

        if self.values is None:
            return

        if self.values.reader.format == 'zarr' or self.region_mask.size > 262144:
            series = self.values
            self.set_read_busy(True)
            self.reader_jobs.start('frame', lambda check: (index, series[index]))
            return
        self.apply_frame(index, self.values[index])

    def apply_frame(self, index, frame):
        self.image.set_data(frame)

        date = str(self.dates[index])

        self.date_label.setText(
            f"{date}  /  {index + 1:03d}"
            f" of {len(self.dates):03d}"
        )

        self.ax.set_title(
            f"{self.variable_name} | "
            f"{self.region.currentText()} | {date}",
            color="#e7edf5",
            fontsize=14,
            pad=15
        )

        finite = frame[np.isfinite(frame)]

        weighted_mean, coverage = self.values.summary(frame)
        mean = f"{weighted_mean:.4f} {self.unit}" if weighted_mean is not None else "N/A"

        self.details.setText(
            f"Valid pixels: {finite.size:,}  |  "
            f"Coverage: {coverage:.2%}  |  "
            f"Area-weighted mean: {mean}\n"
            f"Display stride {self.values.stride}; statistics on displayed samples. "
            "Historical satellite observations. "
            "Fixed color scale. Missing data is not zero."
        )

        if self.isVisible(): self.draw_visible()

    def set_read_busy(self, busy):
        self.read_progress.setVisible(busy); self.cancel_read_button.setEnabled(busy)

    def cancel_read(self):
        self.reset_dataset(); self.details.setText('Read cancelled; no incomplete observation displayed.')

    def ensure_figure_size(self):
        self.figure.set_size_inches(max(self.canvas.width(), 320)/self.figure.dpi,
                                    max(self.canvas.height(), 200)/self.figure.dpi, forward=False)

    def showEvent(self, event):
        super().showEvent(event); self.redraw_timer.start(0)

    def draw_visible(self):
        if not self.isVisible() or self.canvas.width() <= 0 or self.canvas.height() <= 0: return
        self.ensure_figure_size(); self.figure.tight_layout(); self.canvas.draw_idle()
