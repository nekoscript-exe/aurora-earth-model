"""AURORA Predictive Intelligence Laboratory."""

import json

import numpy as np
import rasterio

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg, NavigationToolbar2QT
)


class AILaboratory(QWidget):

    def __init__(self, root, parent=None):
        super().__init__(parent)

        self.root = root
        self.directory = root / "outputs/queretaro"

        layout = QVBoxLayout(self)

        title = QLabel("Predictive Intelligence")
        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
            "color:#b99de8;"
        )

        layout.addWidget(title)

        self.info = QLabel(
            "NDVI / Queretaro / Historical predictive experiment"
        )

        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        controls = QHBoxLayout()

        self.view = QComboBox()

        self.view.addItems([
            "Model benchmark",
            "MAE comparison",
            "R² comparison",
            "XGBoost prediction",
            "ConvLSTM prediction",
            "Prediction difference",
            "ConvLSTM training history",
            "XGBoost feature importance"
        ])

        controls.addWidget(self.view, 1)

        refresh = QPushButton("Refresh results")
        refresh.clicked.connect(self.render)

        controls.addWidget(refresh)

        layout.addLayout(controls)

        self.figure = Figure(facecolor="#080e17")
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.toolbar = NavigationToolbar2QT(
            self.canvas, self
        )

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        self.details = QLabel()
        self.details.setWordWrap(True)

        self.details.setStyleSheet(
            "background:#14202d;color:#a9c7dd;"
            "padding:14px;border-radius:8px;"
        )

        layout.addWidget(self.details)

        self.view.currentIndexChanged.connect(self.render)

        self.render()

    def read_json(self, path):

        return json.loads(path.read_text())

    def style(self, ax):

        ax.set_facecolor("#080e17")
        ax.tick_params(colors="#bacbd8")
        ax.title.set_color("#e7edf5")
        ax.xaxis.label.set_color("#bacbd8")
        ax.yaxis.label.set_color("#bacbd8")

        for spine in ax.spines.values():
            spine.set_color("#405568")

        ax.grid(alpha=0.12)

    def render(self, *_):

        self.figure.clear()

        ax = self.figure.add_subplot(111)

        mode = self.view.currentText()

        try:

            if mode in [
                "Model benchmark",
                "MAE comparison",
                "R² comparison"
            ]:
                self.draw_benchmark(ax, mode)

            elif mode == "ConvLSTM training history":
                self.draw_training(ax)

            elif mode == "XGBoost feature importance":
                self.draw_importance(ax)

            else:
                self.draw_prediction(ax, mode)

        except Exception as exc:

            ax.clear()

            ax.text(
                0.5, 0.5,
                "Predictive results unavailable",
                ha="center", va="center",
                transform=ax.transAxes,
                color="#efbd76"
            )

            self.details.setText(str(exc))

        self.style(ax)

        self.figure.tight_layout()
        self.canvas.draw()
        self.toolbar.update()

    def draw_benchmark(self, ax, mode):

        data = self.read_json(
            self.directory / "final_benchmark.json"
        )

        field = {
            "Model benchmark": "rmse",
            "MAE comparison": "mae",
            "R² comparison": "r2"
        }[mode]

        results = data["results"]

        names = list(results)

        names.sort(
            key=lambda name: results[name][field],
            reverse=(field == "r2")
        )

        values = [
            results[name][field] for name in names
        ]

        labels = {
            "xgboost": "XGBoost",
            "convlstm": "ConvLSTM",
            "climatology": "Climatology",
            "persistence": "Persistence",
            "seasonal": "Seasonal persistence"
        }

        colors = [
            "#69d9bd" if name == "xgboost"
            else "#b99de8" if name == "convlstm"
            else "#536a80"
            for name in names
        ]

        bars = ax.barh(
            [labels.get(n, n) for n in names],
            values,
            color=colors
        )

        ax.bar_label(
            bars,
            fmt="%.5f",
            padding=5,
            color="#e7edf5"
        )

        ax.invert_yaxis()
        ax.margins(x=0.2)

        ax.set_title(
            f"Predictive model comparison / {field.upper()}"
        )

        ax.set_xlabel(field.upper())

        period = data["period"]

        self.details.setText(
            f"Held-out test: {period[0]} — {period[1]}\n"
            f"Comparable observations: "
            f'{data["comparable_observations"]:,}\n'
            "Rolling one-month-ahead evaluation. "
            "Models compared over common valid targets."
        )

    def draw_training(self, ax):

        data = self.read_json(
            self.directory / "convlstm/metrics.json"
        )

        history = data["history"]

        epochs = [row["epoch"] for row in history]

        train = [
            row["train"]["rmse"] for row in history
        ]

        validation = [
            row["validation"]["rmse"] for row in history
        ]

        ax.plot(
            epochs, train,
            "o-", color="#69d9bd",
            label="Training RMSE"
        )

        ax.plot(
            epochs, validation,
            "o-", color="#b99de8",
            label="Validation RMSE"
        )

        ax.axvline(
            data["best_epoch"],
            color="#efbd76",
            linestyle="--",
            label="Best checkpoint"
        )

        ax.set_xlabel("Epoch")
        ax.set_ylabel("RMSE")
        ax.set_title("ConvLSTM learning curves")

        ax.legend(
            facecolor="#14202d",
            labelcolor="#e7edf5"
        )

        self.details.setText(
            f'Best epoch: {data["best_epoch"]}\n'
            f'Training time: {data["seconds"]:.2f} s\n'
            f'Peak allocated VRAM: '
            f'{data["peak_vram_mib"]:.2f} MiB'
        )

    def draw_importance(self, ax):

        data = self.read_json(
            self.directory / "xgboost/metrics.json"
        )

        items = sorted(
            data["feature_importance"].items(),
            key=lambda item: item[1]
        )

        ax.barh(
            [name for name, _ in items],
            [value * 100 for _, value in items],
            color="#69d9bd"
        )

        ax.set_title("XGBoost feature importance")
        ax.set_xlabel("Relative importance (%)")

        self.details.setText(
            "Feature importance describes model behavior. "
            "It does not establish environmental causality."
        )

    def read_prediction(self, engine):

        directory = self.directory / "forecast" / engine

        metadata = self.read_json(
            directory / "forecast_metadata.json"
        )

        with rasterio.open(
            directory / "forecast_ndvi.tif"
        ) as src:

            values = (
                src.read(1, masked=True)
                .astype("float64")
                .filled(np.nan)
            )

            bounds = src.bounds

            extent = (
                bounds.left, bounds.right,
                bounds.bottom, bounds.top
            )

            grid = (
                src.crs, src.transform, src.shape
            )

        return values, extent, grid, metadata

    def draw_prediction(self, ax, mode):

        if mode == "Prediction difference":

            a, extent, grid_a, meta_a = (
                self.read_prediction("xgboost")
            )

            b, _, grid_b, meta_b = (
                self.read_prediction("convlstm")
            )

            if grid_a != grid_b:
                raise ValueError("Prediction grids differ")

            if meta_a["forecast_date"] != meta_b["forecast_date"]:
                raise ValueError("Prediction dates differ")

            difference = a - b

            finite = difference[np.isfinite(difference)]

            if not finite.size:
                raise ValueError("No comparable predictions")

            limit = max(
                float(np.max(np.abs(finite))),
                1e-6
            )

            image = ax.imshow(
                difference,
                cmap="coolwarm",
                vmin=-limit,
                vmax=limit,
                extent=extent
            )

            ax.set_title("XGBoost minus ConvLSTM")

            self.details.setText(
                f'Date: {meta_a["forecast_date"]}\n'
                f"Mean absolute model difference: "
                f"{np.abs(finite).mean():.6f} NDVI\n"
                "Model disagreement is not a calibrated "
                "uncertainty estimate."
            )

        else:

            engine = (
                "xgboost" if mode == "XGBoost prediction"
                else "convlstm"
            )

            values, extent, _, metadata = (
                self.read_prediction(engine)
            )

            image = ax.imshow(
                values,
                cmap="RdYlGn",
                vmin=-0.2, vmax=1,
                extent=extent,
                interpolation="nearest"
            )

            ax.set_title(
                f'{mode} / {metadata["forecast_date"]}'
            )

            self.details.setText(
                f'Predicted pixels: '
                f'{metadata["predicted_pixels"]:,}\n'
                f'Spatial coverage: '
                f'{metadata["prediction_coverage"]:.2%}\n'
                f'Mean NDVI: {metadata["mean_ndvi"]:.5f}\n'
                "Retrospective forecast from December 2025. "
                "Not yet verified against the actual target month."
            )

        ax.set_xticks([])
        ax.set_yticks([])

        bar = self.figure.colorbar(
            image, ax=ax, shrink=0.8
        )

        bar.set_label("NDVI", color="#bacbd8")
        bar.ax.tick_params(colors="#bacbd8")
