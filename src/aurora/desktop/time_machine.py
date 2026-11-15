"""AURORA — Historical satellite playback."""

import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT
)


class TimeMachine(QWidget):

    DATASETS = {
        ("queretaro", "ndvi"): "queretaro",
        ("queretaro", "lst"): "queretaro_lst",
        ("mexico", "ndvi"): "mexico",
        ("mexico", "lst"): "mexico_lst"
    }

    def __init__(self, root, parent=None):
        super().__init__(parent)

        self.root = root
        self.values = None
        self.dates = None
        self.region_mask = None

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
        self.region.addItem("Queretaro", "queretaro")
        self.region.addItem("Mexico", "mexico")

        self.variable = QComboBox()
        self.variable.addItem("Vegetation — NDVI", "ndvi")
        self.variable.addItem("Temperature — LST", "lst")

        load = QPushButton("Load satellite imagery")
        load.clicked.connect(self.load_dataset)

        controls.addWidget(self.region)
        controls.addWidget(self.variable, 1)
        controls.addWidget(load)

        layout.addLayout(controls)

        self.figure = Figure(facecolor="#080e17")
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.toolbar = NavigationToolbar2QT(
            self.canvas, self
        )

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

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

        self.region.currentIndexChanged.connect(
            self.reset_dataset
        )

        self.variable.currentIndexChanged.connect(
            self.reset_dataset
        )

        self.load_dataset()

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

        self.pause()
        self.values = None
        self.set_controls(False)

        self.figure.clear()
        self.canvas.draw()

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

    def step(self, amount):

        if self.values is None:
            return

        index = (
            self.slider.value() + amount
        ) % len(self.dates)

        self.slider.setValue(index)

    def advance(self):

        self.step(1)

    def load_dataset(self):

        self.reset_dataset()

        key = (
            self.region.currentData(),
            self.variable.currentData()
        )

        path = (
            self.root / "data/processed" /
            self.DATASETS[key] / "cube.npz"
        )

        if not path.is_file():

            self.details.setText(
                "Historical dataset unavailable."
            )

            return

        try:
            with np.load(path, allow_pickle=False) as data:

                self.values = data["X"][..., 0].copy()

                valid = data["valid"][..., 0]

                self.values[~valid] = np.nan

                self.dates = data["dates"].astype(
                    "datetime64[M]"
                )

                self.region_mask = data["region_mask"]

                self.values[:, ~self.region_mask] = np.nan

                self.variable_name = str(
                    data["channels"][0]
                )

            self.figure.clear()
            self.ax = self.figure.add_subplot(111)

            if self.variable_name == "NDVI":

                cmap = "RdYlGn"
                lower, upper = -0.2, 1.0
                self.unit = "NDVI"

            else:

                cmap = "turbo"
                lower, upper = -10, 70
                self.unit = "°C"

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

            self.set_controls(True)
            self.render(0)

            self.toolbar.update()

        except Exception as exc:

            self.reset_dataset()
            self.details.setText(str(exc))

    def render(self, index):

        if self.values is None:
            return

        frame = self.values[index]

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

        coverage = (
            finite.size /
            max(int(self.region_mask.sum()), 1)
        )

        mean = (
            f"{finite.mean():.4f} {self.unit}"
            if finite.size else "N/A"
        )

        self.details.setText(
            f"Valid pixels: {finite.size:,}  |  "
            f"Coverage: {coverage:.2%}  |  "
            f"Regional mean: {mean}\n"
            "Historical satellite observations. "
            "Fixed color scale. Missing data is not zero."
        )

        self.canvas.draw_idle()
