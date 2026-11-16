"""Merge validated Mexican satellite observations without gap filling."""

from pathlib import Path
import csv
import json
import re
import shutil

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom
from affine import Affine

base = Path.home() / "Proyectos/aurora-earth-model/data/incoming"

package = base / "mexico_yatz/AURORA_Mexico_Ian"
original = package / "mexico"
incoming = base / "mexico_completion"
output = base / "mexico_integrated"

output.mkdir(parents=True, exist_ok=True)

region_path = package / "config/region_mexico.geojson"
region = json.loads(region_path.read_text())

transform = Affine(
    5000, 0, -11425000,
    0, -5000, 3960000
)

shape = (426, 612)
crs = "EPSG:6933"
nodata = -9999.0

geometry = transform_geom(
    "EPSG:4326",
    crs,
    region["features"][0]["geometry"]
)

mask = rasterize(
    [(geometry, 1)],
    out_shape=shape,
    transform=transform,
    all_touched=False
).astype(bool)

assert mask.sum() == 78737

shutil.copy2(region_path, output / "region.geojson")
shutil.copy2(
    package / "grid_mexico.json",
    output / "grid_mexico.json"
)

calendar = {
    f"{year}_{month:02d}"
    for year in range(2001, 2026)
    for month in range(1, 13)
}


def validate_header(src):
    assert src.crs.to_epsg() == 6933
    assert src.transform == transform
    assert src.shape == shape
    assert src.nodata == nodata
    assert all(d == "float32" for d in src.dtypes)


def validate_values(array, lower, upper):
    valid = mask & np.isfinite(array) & (array != nodata)

    assert valid.any()
    assert (array[valid] >= lower - 1e-6).all()
    assert (array[valid] <= upper + 1e-6).all()

    return valid


for variable, prefix, lower, upper in (
    ("ndvi", "ndvi", -0.2, 1.0),
    ("lst", "lst_day", -90.0, 80.0)
):
    target = output / variable
    target.mkdir(exist_ok=True)

    rows = {}

    # Preserve original observations.
    for path in sorted((original / variable).glob("*.tif")):
        match = re.fullmatch(
            rf"{prefix}_(\d{{4}}_\d{{2}})\.tif",
            path.name
        )

        assert match, path.name
        date = match.group(1)

        assert date in calendar
        assert date not in rows

        with rasterio.open(path) as src:
            validate_header(src)
            assert src.count == 1

            array = src.read(1)
            valid = validate_values(array, lower, upper)

            assert not (
                ~mask & np.isfinite(array) & (array != nodata)
            ).any()

        destination = target / path.name

        if not destination.exists():
            shutil.copy2(path, destination)

        rows[date] = {
            "date": date.replace("_", "-"),
            "file": path.name,
            "origin": "original",
            "source_file": path.name,
            "source_band": 1,
            "valid_cells": int(valid.sum()),
            "coverage": float(valid.sum() / mask.sum())
        }

    # Integrate complementary acquisitions.
    for path in sorted(incoming.glob(f"{variable}_mexico_*.tif")):
        with rasterio.open(path) as src:
            validate_header(src)

            for band, description in enumerate(
                src.descriptions, start=1
            ):
                match = re.fullmatch(
                    rf"{variable}_(\d{{4}}_\d{{2}})",
                    description or ""
                )

                assert match, description
                date = match.group(1)
                assert date in calendar

                array = src.read(band)
                valid = validate_values(array, lower, upper)

                array = np.where(
                    valid, array, nodata
                ).astype("float32")

                if date in rows:
                    # Only the validated control may overlap.
                    assert date == "2001_01", date

                    with rasterio.open(
                        target / rows[date]["file"]
                    ) as ref:
                        reference = ref.read(1)

                    np.testing.assert_array_equal(
                        reference, array
                    )

                    print(variable, date, "CONTROL OK")
                    continue

                filename = f"{prefix}_{date}.tif"
                destination = target / filename

                profile = src.profile.copy()
                profile.update(
                    driver="GTiff",
                    count=1,
                    dtype="float32",
                    nodata=nodata,
                    compress="deflate"
                )

                if not destination.exists():
                    with rasterio.open(
                        destination, "w", **profile
                    ) as dst:
                        dst.write(array, 1)
                        dst.set_band_description(1, description)
                else:
                    with rasterio.open(destination) as dst:
                        validate_header(dst)
                        np.testing.assert_array_equal(
                            dst.read(1), array
                        )

                rows[date] = {
                    "date": date.replace("_", "-"),
                    "file": filename,
                    "origin": "complementary",
                    "source_file": path.name,
                    "source_band": band,
                    "valid_cells": int(valid.sum()),
                    "coverage": float(valid.sum() / mask.sum())
                }

                print(variable, date, "OK")

    missing = sorted(calendar - set(rows))

    with (output / f"manifest_{variable}.csv").open(
        "w", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=list(next(iter(rows.values())))
        )
        writer.writeheader()
        writer.writerows(rows[d] for d in sorted(rows))

    print("\n========", variable.upper(), "========")
    print("Months:", len(rows), "/ 300")
    print("Missing:", missing)
    print("Valid observations:",
          sum(r["valid_cells"] for r in rows.values()))
    print("Mean coverage:",
          np.mean([r["coverage"] for r in rows.values()]))
    print("COMPLETE:", not missing)

print("\nOutput:", output)
