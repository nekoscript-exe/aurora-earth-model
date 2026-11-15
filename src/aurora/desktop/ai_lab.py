"""AURORA Predictive Intelligence Laboratory."""

from .i18n import error_text, localized_label, localized_button, add_choices, tr

import json
from pathlib import Path

import numpy as np
import rasterio
from aurora.catalog import DatasetRegistry, display_scale
from .dataset_controls import populate_regions
from aurora.model_catalog import ModelRegistry
from aurora.jobs import request_cancel
from .tasks import ReaderJobs

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QFileDialog
)

from matplotlib.figure import Figure
from .canvas import FigureCanvasQTAgg
from .toolbar import NavigationToolbar2QT


class AILaboratory(QWidget):

    def __init__(self, root, parent=None):
        super().__init__(parent)

        self.root = root
        self.model_jobs = ReaderJobs(self, self.models_ready, self.models_error)
        self.model_registry = None
        self.directory = None

        layout = QVBoxLayout(self)

        title = localized_label('Predictive Intelligence')
        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
            "color:#b99de8;"
        )

        layout.addWidget(title)

        self.info = localized_label(
            "Historical predictive experiment"
        )

        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        controls = QHBoxLayout()

        self.region = QComboBox()
        self.registry = DatasetRegistry(root)
        controls.addWidget(self.region)
        self.variable = QComboBox()

        controls.addWidget(self.variable)
        self.view = QComboBox()

        add_choices(self.view, [
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

        refresh = localized_button('Refresh results')
        refresh.clicked.connect(self.render_results)

        controls.addWidget(refresh)
        self.export_button = localized_button('Export'); self.export_button.clicked.connect(self.export_results)
        controls.addWidget(self.export_button)
        self.cancel_export_button = localized_button('Cancel'); self.cancel_export_button.setEnabled(False)
        self.cancel_export_button.clicked.connect(self.cancel_export); controls.addWidget(self.cancel_export_button)
        self.export_process = QProcess(self); self.export_process.finished.connect(self.export_finished)

        layout.addLayout(controls)

        self.figure = Figure(facecolor="#080e17")
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.toolbar = NavigationToolbar2QT(
            self.canvas, self
        )

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        self.details = localized_label()
        self.details.setWordWrap(True)

        self.details.setStyleSheet(
            "background:#14202d;color:#a9c7dd;"
            "padding:14px;border-radius:8px;"
        )

        layout.addWidget(self.details)

        self.region.currentIndexChanged.connect(self.models_region_changed)
        self.variable.currentIndexChanged.connect(self.render_results)
        self.view.currentIndexChanged.connect(self.render_results)

        self.refresh_catalog()
        self.render_results()

    def read_json(self, path):

        return json.loads(path.read_text())

    def style_plot(self, ax):

        ax.set_facecolor("#080e17")
        ax.tick_params(colors="#bacbd8")
        ax.title.set_color("#e7edf5")
        ax.xaxis.label.set_color("#bacbd8")
        ax.yaxis.label.set_color("#bacbd8")

        for spine in ax.spines.values():
            spine.set_color("#405568")

        ax.grid(alpha=0.12)

    def render_results(self, *_):

        variable = self.variable.currentData()
        self.unit = "°C" if variable == "lst" else "NDVI"
        region = self.region.currentData()
        model = None
        if self.model_registry is not None:
            try: model = self.model_registry.find(region, variable)
            except FileNotFoundError: pass
        if model is not None:
            self.directory = model['directory']
            self.unit = model['unit']
            self.scale = display_scale(self.registry.find(region, variable).metadata)
        else: self.directory = self.root/'outputs/NO_TRAINED_EVALUATED_MODELS'
        self.info.setText(tr(f"{str(variable).upper()} / {region} · "+('trained and held-out evaluated' if model else 'No current trained/evaluated models')))
        self.figure.clear()

        ax = self.figure.add_subplot(111)

        mode = self.view.currentData()

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
                tr("Predictive results unavailable"),
                ha="center", va="center",
                transform=ax.transAxes,
                color="#efbd76"
            )

            self.details.setText(error_text(exc))

        self.style_plot(ax)

        self.figure.tight_layout()
        self.canvas.draw()
        self.toolbar.update()

    def draw_benchmark(self, ax, mode):

        if self.directory is None:
            raise ValueError("No evaluated model selected")

        data = self.read_json(
            self.directory / "final_benchmark.json"
        )

        field = {
            "Model benchmark": "rmse",
            "MAE comparison": "mae",
            "R² comparison": "r2"
        }[mode]

        results = data["results"]

        names = [name for name in results if results[name].get(field) is not None and np.isfinite(results[name][field])]
        if not names:
            ax.text(.5, .5, tr(field.upper()+' undefined for this target population'), ha='center', color='#efbd76')
            self.details.setText(tr('Undefined scores are not replaced with zero.')); return

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
            tr(f"Predictive model comparison / {field.upper()}")
        )

        ax.set_xlabel(tr(field.upper() + (f" ({self.unit})" if field != "r2" else "")))

        period = data["period"]

        self.details.setText(
            tr(f"Held-out test: {period[0]} — {period[1]}\n"
            f"Comparable observations: "
            f'{data["comparable_observations"]:,}\n'
            "Rolling one-month-ahead evaluation. "
            "Models compared over common valid targets.")
        )

    def draw_training(self, ax):

        if self.directory is None:
            raise ValueError("No evaluated model selected")

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
            label=tr("Training RMSE")
        )

        ax.plot(
            epochs, validation,
            "o-", color="#b99de8",
            label=tr("Validation RMSE")
        )

        ax.axvline(
            data["best_epoch"],
            color="#efbd76",
            linestyle="--",
            label=tr("Best checkpoint")
        )

        ax.set_xlabel(tr("Epoch"))
        ax.set_ylabel(tr("RMSE"))
        ax.set_title(tr("ConvLSTM learning curves"))

        ax.legend(
            facecolor="#14202d",
            labelcolor="#e7edf5"
        )

        peak = data.get('peak_vram_mib')
        peak_text = f'{peak:.2f} MiB' if peak is not None else 'N/A (CPU)'
        self.details.setText(
            tr(f'Best epoch: {data["best_epoch"]}\n'
            f'Training time: {data["seconds"]:.2f} s\n'
            f'Peak allocated VRAM: '
            f'{peak_text}')
        )

    def draw_importance(self, ax):

        if self.directory is None:
            raise ValueError("No evaluated model selected")

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

        ax.set_title(tr("XGBoost feature importance"))
        ax.set_xlabel(tr("Relative importance (%)"))

        self.details.setText(
            tr("Feature importance describes model behavior. "
            "It does not establish environmental causality.")
        )

    def read_prediction(self, engine):

        if self.directory is None:
            raise ValueError("No evaluated model selected")

        directory = self.directory / "forecast" / engine

        metadata = self.read_json(
            directory / "forecast_metadata.json"
        )

        with rasterio.open(
            directory / f"forecast_{self.variable.currentData()}.tif"
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

            ax.set_title(tr("XGBoost minus ConvLSTM"))

            self.details.setText(
                tr(f'Date: {meta_a["forecast_date"]}\n'
                f"Mean absolute model difference: "
                f"{np.abs(finite).mean():.6f} {self.unit}\n"
                "Model disagreement is not a calibrated "
                "uncertainty estimate.")
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
                cmap=self.scale[2], vmin=self.scale[0], vmax=self.scale[1],
                extent=extent,
                interpolation="nearest"
            )

            ax.set_title(
                tr(f'{mode} / {metadata["forecast_date"]}')
            )

            self.details.setText(
                tr(f'Predicted pixels: '
                f'{metadata["predicted_pixels"]:,}\n'
                f'Spatial coverage: '
                f'{metadata["prediction_coverage"]:.2%}\n'
                f'Mean {self.unit}: {metadata["mean_"+self.variable.currentData()]:.5f}\n'
                "Retrospective forecast from December 2025. "
                "Not yet verified against the actual target month.")
            )

        ax.set_xticks([])
        ax.set_yticks([])

        bar = self.figure.colorbar(
            image, ax=ax, shrink=0.8
        )

        bar.set_label(tr(self.unit), color="#bacbd8")
        bar.ax.tick_params(colors="#bacbd8")

    def refresh_catalog(self):
        self.model_jobs.start('models', lambda check: ModelRegistry(self.root, DatasetRegistry(self.root)))

    def models_ready(self, kind, registry):
        self.model_registry = registry
        current_region, current_variable = self.region.currentData(), self.variable.currentData()
        self.region.blockSignals(True); self.variable.blockSignals(True)
        self.region.clear()
        for region in sorted({model['region'] for model in registry.models}): self.region.addItem(tr(region), region)
        index = self.region.findData(current_region); self.region.setCurrentIndex(index if index >= 0 else 0)
        self.region.blockSignals(False); self.variable.blockSignals(False)
        self.models_region_changed()
        index = self.variable.findData(current_variable)
        if index >= 0: self.variable.setCurrentIndex(index)
        self.render_results()

    def models_region_changed(self, *_):
        current = self.variable.currentData(); self.variable.blockSignals(True); self.variable.clear()
        if self.model_registry:
            for variable in sorted({model['variable'] for model in self.model_registry.models if model['region'] == self.region.currentData()}, key=lambda v: (v != 'ndvi', v != 'lst', v)):
                self.variable.addItem(tr(variable.upper()), variable)
        index = self.variable.findData(current); self.variable.setCurrentIndex(index if index >= 0 else 0)
        self.variable.blockSignals(False); self.render_results()

    def models_error(self, error):
        self.info.setText(tr('Model discovery failed: '+error))

    def export_results(self):
        import sys
        from datetime import datetime
        if not self.model_registry: return
        try: self.model_registry.find(self.region.currentData(), self.variable.currentData())
        except FileNotFoundError as exc: self.details.setText(error_text(exc)); return
        directory = QFileDialog.getExistingDirectory(self, tr('Export evaluated predictive results'))
        if not directory: return
        self.export_directory = Path(directory)/f'aurora_predictive_{datetime.now():%Y%m%d_%H%M%S_%f}'
        self.cancel_export_button.setEnabled(True); self.export_button.setEnabled(False)
        self.details.setText(tr('Exporting scientific formats in background… Cancel is available.'))
        self.export_process.start(sys.executable, [str(self.root/'scripts/export_model_result.py'), '--root', str(self.root),
            '--region', self.region.currentData(), '--variable', self.variable.currentData(), '--output', str(self.export_directory)])

    def cancel_export(self):
        request_cancel(self.export_directory); self.cancel_export_button.setEnabled(False)

    def export_finished(self, code, *_):
        self.cancel_export_button.setEnabled(False); self.export_button.setEnabled(True)
        self.details.setText(tr('Predictive export complete' if code == 0 else 'Predictive export cancelled or failed; partial bundle is not complete'))
