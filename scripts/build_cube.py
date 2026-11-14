"""AURORA Satellite Data Engine."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import rasterio

from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.warp import transform_geom


def build_cube(package, region_path, output, start, end):
    package = Path(package)
    output = Path(output)

    with open(package / "grid.json") as f:
        grid = json.load(f)

    with open(region_path) as f:
        region = json.load(f)

    with open(package / "manifest.csv", newline="") as f:
        records = list(csv.DictReader(f))

    if not records:
        raise ValueError("Empty manifest")

    records.sort(key=lambda row: row["date"])

    crs = rasterio.crs.CRS.from_string(grid["crs"])
    transform = Affine(*grid["transform"][:6])

    height = grid["height"]
    width = grid["width"]

    nodata = float(grid["nodata"])

    geometries = [
        transform_geom(
            "EPSG:4326",
            crs,
            feature["geometry"]
        )
        for feature in region["features"]
    ]

    inside = geometry_mask(
        geometries,
        out_shape=(height, width),
        transform=transform,
        invert=True,
        all_touched=False
    )

    if not inside.any():
        raise ValueError("Empty regional mask")

    dates = np.arange(
        np.datetime64(start, "M"),
        np.datetime64(end, "M") + np.timedelta64(1, "M"),
        dtype="datetime64[M]"
    ).astype("datetime64[D]").astype(str)

    if not len(dates):
        raise ValueError("Invalid date interval")

    indices = {
        date: i for i, date in enumerate(dates)
    }

    X = np.full(
        (len(dates), height, width, 1),
        np.nan,
        dtype=np.float32
    )

    valid = np.zeros(X.shape, dtype=bool)

    seen = set()
    report = []

    for row in records:
        date = row["date"]

        if date in seen:
            raise ValueError(f"Duplicate date: {date}")

        seen.add(date)

        if date not in indices:
            raise ValueError(f"Unexpected date: {date}")

        if row["variable"].lower() != "ndvi":
            raise ValueError("Unexpected variable")

        if row["source_id"] != "MODIS/061/MOD13Q1":
            raise ValueError("Unexpected satellite source")

        path = (package / row["path"]).resolve()

        if not path.is_relative_to(package.resolve()):
            raise ValueError("Invalid raster path")

        with rasterio.open(path) as src:
            if (
                src.crs != crs
                or src.transform != transform
                or src.width != width
                or src.height != height
                or src.count != 1
                or src.dtypes[0] != "float32"
                or src.nodata != nodata
            ):
                raise ValueError(
                    f"Incompatible raster: {path}"
                )

            raster = src.read(1, masked=True)

            raw = raster.data.astype(np.float32)

            observed = (
                ~np.ma.getmaskarray(raster)
                & np.isfinite(raw)
            )

            mask = observed & inside

            if np.any(
                (raw[mask] < -0.200001)
                | (raw[mask] > 1.000001)
            ):
                raise ValueError(
                    f"Invalid NDVI range: {date}"
                )

            index = indices[date]

            X[index, :, :, 0] = np.where(
                mask, raw, np.nan
            )

            valid[index, :, :, 0] = mask

            coverage = float(
                mask.sum() / inside.sum()
            )

            report.append({
                "date": date,
                "coverage": coverage,
                "valid_pixels": int(mask.sum()),
                "excluded_outside": int(
                    (observed & ~inside).sum()
                ),
                "review_required": coverage < 0.70
            })

            print(
                f"{date} | "
                f"Coverage: {coverage:.4%} | "
                f"Valid: {mask.sum()}"
            )

    output.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output / "cube.npz",
        X=X,
        valid=valid,
        dates=dates,
        channels=np.array(["NDVI"]),
        region_mask=inside
    )

    metadata = {
        "dataset": "satellite",
        "source": "MODIS/061/MOD13Q1",
        "shape": list(X.shape),
        "grid": grid,
        "regional_pixels": int(inside.sum()),
        "received_months": len(seen),
        "expected_months": len(dates),
        "missing_months": [
            date for date in dates
            if date not in seen
        ],
        "coverage": report
    }

    with open(output / "cube_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    print("=" * 60)
    print("AURORA | SATELLITE DATA ENGINE")
    print("Cube shape:", X.shape)
    print("Received months:", len(seen))
    print("Expected months:", len(dates))
    print("Valid observations:", valid.sum())
    print("Regional pixels:", inside.sum())
    print("Output:", output / "cube.npz")
    print("SATELLITE DATA ENGINE: COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--package", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", default="2001-01")
    parser.add_argument("--end", default="2025-12")

    args = parser.parse_args()

    build_cube(
        args.package,
        args.region,
        args.output,
        args.start,
        args.end
    )
