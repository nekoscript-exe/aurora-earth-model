import importlib.util
import pathlib

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "validate_data", ROOT / "scripts" / "validate_data.py")
vd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vd)

H, W = 4, 5
TRANSFORM = [1000.0, 0.0, 335000.0, 0.0, -1000.0, 2387000.0]
NODATA = -9999.0


@pytest.fixture
def grid():
    return {"crs": "EPSG:32614", "transform": TRANSFORM,
            "width": W, "height": H, "nodata": NODATA}


@pytest.fixture
def inside():
    return np.ones((H, W), dtype=bool)


def write_tif(path, arr, transform=TRANSFORM, nodata=NODATA, dtype="float32"):
    arr = np.asarray(arr, dtype=dtype)
    with rasterio.open(
        path, "w", driver="GTiff", dtype=dtype, count=1,
        height=arr.shape[0], width=arr.shape[1], crs="EPSG:32614",
        transform=Affine(*transform), nodata=nodata,
    ) as dst:
        dst.write(arr, 1)
    return str(path)


def good_array():
    return np.full((H, W), 0.5, dtype="float32")


def test_detects_duplicates():
    assert vd.find_duplicates(["2001-01-01", "2001-02-01", "2001-01-01"]) == ["2001-01-01"]
    assert vd.find_duplicates(["2001-01-01", "2001-02-01"]) == []


def test_detects_missing_months():
    dates = ["2001-01-01", "2001-02-01", "2001-04-01"]
    assert vd.find_missing_months(dates) == ["2001-03"]


def test_missing_months_with_expected_range():
    dates = ["2001-02-01", "2001-03-01"]
    assert vd.find_missing_months(dates, "2001-01", "2001-04") == ["2001-01", "2001-04"]


def test_valid_raster_passes(tmp_path, grid, inside):
    issues, stats = vd.check_raster(write_tif(tmp_path / "a.tif", good_array()), grid, inside)
    assert issues == []
    assert stats["valid_fraction"] == 1.0


def test_valid_fraction_counts_nodata(tmp_path, grid, inside):
    arr = good_array()
    arr[:2, :] = NODATA  # mitad de las filas sin dato
    issues, stats = vd.check_raster(write_tif(tmp_path / "a.tif", arr), grid, inside)
    assert issues == []
    assert stats["valid_fraction"] == 0.5


def test_different_shape_is_flagged(tmp_path, grid, inside):
    path = write_tif(tmp_path / "a.tif", np.full((H - 1, W), 0.5))
    issues, _ = vd.check_raster(path, grid, inside)
    assert any("forma" in i for i in issues)


def test_different_transform_is_flagged(tmp_path, grid, inside):
    shifted = [1000.0, 0.0, 336000.0, 0.0, -1000.0, 2387000.0]
    path = write_tif(tmp_path / "a.tif", good_array(), transform=shifted)
    issues, _ = vd.check_raster(path, grid, inside)
    assert "transformada distinta" in issues


def test_wrong_nodata_is_flagged(tmp_path, grid, inside):
    path = write_tif(tmp_path / "a.tif", good_array(), nodata=-1.0)
    issues, _ = vd.check_raster(path, grid, inside)
    assert any("nodata" in i for i in issues)


def test_out_of_range_is_flagged(tmp_path, grid, inside):
    arr = good_array()
    arr[0, 0] = 5.0  # NDVI imposible
    issues, _ = vd.check_raster(write_tif(tmp_path / "a.tif", arr), grid, inside)
    assert "valores fuera de rango" in issues


def test_wrong_dtype_is_flagged(tmp_path, grid, inside):
    path = write_tif(tmp_path / "a.tif", good_array(), dtype="float64")
    issues, _ = vd.check_raster(path, grid, inside)
    assert any("dtype" in i for i in issues)


def test_missing_file_is_flagged(tmp_path, grid, inside):
    issues, _ = vd.check_raster(str(tmp_path / "no_existe.tif"), grid, inside)
    assert issues == ["archivo no existe"]