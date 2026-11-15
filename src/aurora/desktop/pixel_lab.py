"""Individual satellite pixel investigation."""

from typing import cast
from aurora.scientific_types import LinearRegressionResult

import numpy as np

from scipy.stats import linregress, t

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt import NavigationToolbar2QT


def open_pixel_lab(parent, cube, row, col, lat, lon):

    with np.load(cube, allow_pickle=False) as data:

        dates = data["dates"].astype("datetime64[D]")
        values = data["X"][:, row, col, 0].copy()
        valid = data["valid"][:, row, col, 0]
        variable = str(data["channels"][0])

    values[~valid] = np.nan

    unit = "NDVI" if variable == "NDVI" else "°C"

    year_index = dates.astype("datetime64[Y]")
    years = []
    annual = []

    for year in np.unique(year_index):

        observations = values[year_index == year]

        if np.isfinite(observations).sum() >= 9:
            years.append(int(str(year)))
            annual.append(np.nanmean(observations))

    years = np.asarray(years, dtype=float)
    annual = np.asarray(annual, dtype=float)

    dialog = QDialog(parent)
    dialog.setWindowTitle("AURORA — Pixel Laboratory")
    dialog.resize(1050, 740)

    layout = QVBoxLayout(dialog)

    title = QLabel(f"{variable} / Individual pixel investigation")

    title.setStyleSheet(
        "font-size:24px;font-weight:bold;color:#69d9bd;"
    )

    layout.addWidget(title)

    layout.addWidget(QLabel(
        f"Latitude: {lat:.5f}° | Longitude: {lon:.5f}°"
        f" | Pixel [{row}, {col}]"
    ))

    figure = Figure(facecolor="#080e17")
    canvas = FigureCanvasQTAgg(figure)

    toolbar = NavigationToolbar2QT(canvas, dialog)

    layout.addWidget(toolbar)
    layout.addWidget(canvas, 1)

    monthly, yearly = figure.subplots(2, 1)

    monthly.plot(
        dates, values,
        color="#69d9bd",
        linewidth=0.9
    )

    monthly.set_title("Monthly satellite observations")
    monthly.set_ylabel(unit)

    yearly.plot(
        years, annual,
        "o-", color="#8db7ec",
        markersize=4,
        linewidth=1,
        label="Annual composites"
    )

    yearly.set_title("Annual linear regression")
    yearly.set_ylabel(unit)
    yearly.set_xlabel("Year")

    summary = "Insufficient data for regression."

    if len(years) >= 15:

        result = cast(LinearRegressionResult, linregress(years, annual))

        fitted = result.intercept + result.slope * years

        residuals = annual - fitted
        n = len(years)

        variance = np.sum(residuals ** 2) / (n - 2)

        sxx = np.sum((years - years.mean()) ** 2)

        confidence = t.ppf(0.975, n - 2)

        margin = confidence * np.sqrt(
            variance * (
                1 / n +
                (years - years.mean()) ** 2 / sxx
            )
        )

        yearly.plot(
            years, fitted,
            color="#efbd76",
            linewidth=2,
            label="OLS trend"
        )

        yearly.fill_between(
            years,
            fitted - margin,
            fitted + margin,
            color="#efbd76",
            alpha=0.18,
            label="Nominal 95% confidence band"
        )

        summary = (
            f"Annual slope: {result.slope:+.6f} {unit}/year"
            f" | p = {result.pvalue:.6f}"
            f" | R² = {result.rvalue ** 2:.4f}"
            f" | Valid years: {n}"
        )

    for ax in (monthly, yearly):

        parent.style_axes(ax)
        ax.grid(alpha=0.12)

    yearly.legend(
        facecolor="#14202d",
        labelcolor="#e7edf5",
        fontsize=9
    )

    info = QLabel(summary)
    info.setWordWrap(True)
    info.setStyleSheet(
        "background:#14202d;color:#69d9bd;"
        "padding:15px;border-radius:8px;"
    )

    layout.addWidget(info)

    warning = QLabel(
        "Nominal OLS inference. Temporal dependence "
        "may affect statistical significance. "
        "The confidence band is not a prediction interval."
    )

    warning.setWordWrap(True)
    warning.setStyleSheet("color:#8da5ba;")

    layout.addWidget(warning)

    figure.tight_layout()
    canvas.draw()

    dialog.exec()
