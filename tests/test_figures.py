"""Pruebas de scripts/plot_results.py con rasters DIMINUTOS Y SINTETICOS.
Solo prueban el codigo; nunca son evidencia cientifica."""
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import plot_results as pr  # noqa: E402

NODATA = -9999.0


def write_tif(path, arr):
    arr = np.where(np.isfinite(arr), arr, NODATA).astype("float32")
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
        dtype="float32", crs="EPSG:32614", transform=from_origin(300000, 2300000, 1000, 1000),
        nodata=NODATA,
    ) as dst:
        dst.write(arr, 1)


@pytest.fixture
def outputs(tmp_path):
    slope = np.array([[0.01, -0.02, 0.0], [np.nan, 0.005, -0.001], [0.03, 0.0, np.nan]])
    q = np.array([[0.01, 0.01, 0.9], [np.nan, 0.5, 0.2], [0.001, 0.8, np.nan]])
    n = np.array([[20, 20, 18], [np.nan, 17, 16], [25, 15, np.nan]])
    for name, arr in [("slope", slope), ("q", q), ("n", n), ("change", slope * 24)]:
        write_tif(tmp_path / f"trend_{name}.tif", arr)
    return tmp_path


def test_read_raster_converts_nodata_to_nan(outputs):
    arr, extent = pr.read_raster(outputs / "trend_slope.tif")
    assert np.isnan(arr[1, 0]) and np.isnan(arr[2, 2])
    assert arr[0, 0] == pytest.approx(0.01)
    assert len(extent) == 4


def test_categorize_significance():
    slope = np.array([0.01, -0.01, 0.01, np.nan])
    q = np.array([0.01, 0.01, 0.5, 0.01])
    cat = pr.categorize_significance(slope, q)
    assert cat[0] == 2 and cat[1] == 1 and cat[2] == 0 and np.isnan(cat[3])


def test_significance_legend_labels(outputs):
    slope, ext = pr.read_raster(outputs / "trend_slope.tif")
    q, _ = pr.read_raster(outputs / "trend_q.tif")
    fig = pr.make_significance_fig(slope, q, ext)
    texts = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert pr.LABEL_NONE in texts and pr.LABEL_NODATA in texts
    assert pr.LABEL_UP in texts and pr.LABEL_DOWN in texts


def test_constant_series_does_not_crash():
    arr = np.zeros((3, 3))
    fig = pr.make_divergent_fig(arr, None, "t", "l")
    assert fig is not None


def test_all_nodata_does_not_crash():
    arr = np.full((3, 3), np.nan)
    assert pr.make_divergent_fig(arr, None, "t", "l") is not None
    assert pr.make_coverage_fig(arr, None) is not None
    assert pr.categorize_significance(arr, arr).shape == (3, 3)


def test_select_locations():
    slope = np.array([[0.03, -0.02], [0.001, np.nan]])
    q = np.array([[0.001, 0.01], [0.9, np.nan]])
    locs = pr.select_locations(slope, q)
    assert locs == {"Aumento": (0, 0), "Disminución": (0, 1), "Estable": (1, 0)}


def test_select_locations_without_significant():
    slope = np.array([[0.01, 0.02]])
    q = np.array([[0.9, 0.8]])
    assert list(pr.select_locations(slope, q)) == ["Estable"]


def test_annual_means_requires_nine_months():
    dates = [f"2001-{m:02d}-01" for m in range(1, 13)] + [f"2002-{m:02d}-01" for m in range(1, 13)]
    vals = np.ones(24) * 0.5
    vals[12:20] = np.nan  # 2002 queda con 4 meses validos
    years, means = pr.annual_means(dates, vals)
    assert list(years) == [2001, 2002]
    assert means[0] == pytest.approx(0.5) and np.isnan(means[1])


def test_run_all_creates_figures(outputs, tmp_path):
    dest = tmp_path / "figs"
    saved = pr.run_all(outputs, dest, note="DATOS SINTÉTICOS")
    names = {p.name for p in saved}
    assert {"map_slope.png", "map_significance.png", "map_coverage.png", "map_change.png"} <= names
    assert all(p.exists() and p.stat().st_size > 0 for p in saved)


def test_run_all_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        pr.run_all(tmp_path, tmp_path / "figs")


def test_run_all_optional_hac_and_monthly_coverage(outputs, tmp_path):
    q = np.array([[0.01, 0.01, 0.9], [np.nan, 0.5, 0.2], [0.001, 0.8, np.nan]])
    write_tif(outputs / "trend_hac_q.tif", q)
    write_tif(outputs / "coverage.tif", np.full((3, 3), 0.9))
    names = {p.name for p in pr.run_all(outputs, tmp_path / "figs2")}
    assert "map_significance_hac.png" in names and "map_coverage_monthly.png" in names


def test_categorize_region_marks_untested():
    slope = np.array([0.01, np.nan, np.nan])
    q = np.array([0.01, np.nan, np.nan])
    region = np.array([True, True, False])
    cat = pr.categorize_significance(slope, q, region=region)
    assert cat[0] == 2 and cat[1] == 3 and np.isnan(cat[2])


def test_significance_legend_with_region(outputs):
    slope, ext = pr.read_raster(outputs / "trend_slope.tif")
    q, _ = pr.read_raster(outputs / "trend_q.tif")
    n, _ = pr.read_raster(outputs / "trend_n.tif")
    fig = pr.make_significance_fig(slope, q, ext, region=np.isfinite(n))
    texts = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert pr.LABEL_UNTESTED in texts and pr.LABEL_OUTSIDE in texts


def test_regional_figure(tmp_path):
    import json

    import pandas as pd

    dates = pd.date_range("2001-01-01", periods=48, freq="MS").strftime("%Y-%m-%d")
    pd.DataFrame({"date": dates, "mean": np.linspace(0.4, 0.5, 48),
                  "coverage": np.r_[np.full(47, 0.95), 0.5]}).to_csv(tmp_path / "m.csv", index=False)
    pd.DataFrame({"year": [2001, 2002, 2003, 2004], "mean": [0.4, 0.42, 0.45, 0.47],
                  "valid_months": [12] * 4}).to_csv(tmp_path / "a.csv", index=False)
    (tmp_path / "t.json").write_text(json.dumps(
        {"trend": {"slope_per_year": 0.02, "p_value": 0.1, "period": [2001, 2004]}}))
    fig = pr.make_regional_fig(tmp_path / "m.csv", tmp_path / "a.csv", tmp_path / "t.json")
    assert any("OLS" in t.get_text() for t in fig.axes[0].get_legend().get_texts())


def test_configure_english_and_lst_labels():
    try:
        pr.configure(variable="LST", unit="°C", lang="en", warm=True)
        assert pr.LABEL_UP == "Significant increase (q<0.05)"
        fig = pr.make_divergent_fig(np.array([[0.1, -0.1]]), None, pr.T("slope_title"), pr.T("per_year"))
        assert "LST" in fig.axes[0].get_title() and "°C per year" in fig.axes[1].get_ylabel()
    finally:
        pr.configure()  # restaura NDVI/español
    assert pr.LABEL_UP == "Aumento significativo (q<0.05)"
