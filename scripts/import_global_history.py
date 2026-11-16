"""Import annual global satellite GeoTIFFs into AURORA packages."""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.variables import get_product

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--variable", choices=["ndvi", "lst", "precip"], required=True)
parser.add_argument("--source", required=True)
parser.add_argument("--allow-partial", action="store_true")
args = parser.parse_args()

spec = get_product(args.variable, args.source)

grid = {
    "crs": "EPSG:6933",
    "transform": [50000, 0, -17350000, 0, -50000, 7300000],
    "width": 694,
    "height": 267,
    "nodata": -9999.0,
}

affine = Affine(*grid["transform"])
shape = (grid["height"], grid["width"])

region_path = ROOT / "assets/desktop/geography/land_50m.geojson"
region_bytes = region_path.read_bytes()
region = json.loads(region_bytes)

geometries = [
    transform_geom("EPSG:4326", grid["crs"], f["geometry"])
    for f in region["features"]
]

inside = geometry_mask(
    geometries,
    out_shape=shape,
    transform=affine,
    invert=True,
    all_touched=False,
)

land_pixels = int(inside.sum())
assert land_pixels > 0

prefix = f"{args.variable}_global_"
files = sorted(args.input.glob(f"{prefix}*.tif"))

if not files:
    raise ValueError("No annual files found")

years = [int(p.stem.removeprefix(prefix)) for p in files]

if len(years) != len(set(years)):
    raise ValueError("Duplicate years")

expected = set(range(2001, 2026))

if not set(years) <= expected:
    raise ValueError("Unexpected years")

missing = sorted(expected - set(years))

if missing and not args.allow_partial:
    raise ValueError(f"Missing years: {missing}")

# Refuse to overwrite a previous import.
args.output.mkdir(parents=True, exist_ok=False)
raw_dir = args.output / "data/raw"
raw_dir.mkdir(parents=True)

records = []
annual_sources = []

for path, year in zip(files, years):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    month_count = (
        9 if args.variable == "precip" and year == 2025 else 12
    )

    if month_count != 12 and not args.allow_partial:
        raise ValueError("Partial year requires --allow-partial")

    with rasterio.open(path) as src:
        if (
            src.count != month_count
            or src.crs.to_epsg() != 6933
            or src.shape != shape
            or src.transform != affine
            or src.nodata != -9999
            or any(d != "float32" for d in src.dtypes)
        ):
            raise ValueError(f"Incompatible raster: {path}")

        for month in range(1, month_count + 1):
            date = f"{year}-{month:02d}-01"
            label = f"{args.variable}_{year}_{month:02d}"
            description = src.descriptions[month - 1]

            if description and description.lower() != label:
                raise ValueError(f"Unexpected band name: {description}")

            array = src.read(month, masked=True)
            values = array.data

            observed = (
                ~np.ma.getmaskarray(array)
                & np.isfinite(values)
            )

            if not observed.any():
                raise ValueError(f"Empty month: {date}")

            if np.any(
                (values[observed] < spec.minimum - 0.0001)
                | (values[observed] > spec.maximum + 0.0001)
            ):
                raise ValueError(f"Invalid physical range: {date}")

            valid = observed & inside
            coverage = float(valid.sum() / land_pixels)

            destination = raw_dir / f"{label}.tif"

            with rasterio.open(
                destination,
                "w",
                driver="GTiff",
                height=shape[0],
                width=shape[1],
                count=1,
                dtype="float32",
                crs=grid["crs"],
                transform=affine,
                nodata=-9999,
                compress="deflate",
            ) as dst:
                dst.write(
                    np.where(observed, values, -9999)
                    .astype("float32"),
                    1
                )
                dst.set_band_description(1, label)

            records.append({
                "date": date,
                "path": destination.relative_to(args.output).as_posix(),
                "variable": args.variable,
                "unit": spec.unit,
                "crs": grid["crs"],
                "scale_m": 50000,
                "valid_fraction": coverage,
                "source_id": args.source,
            })

            print(
                f"{date} | Land coverage: {coverage:.2%} | "
                f"Valid land cells: {valid.sum():,}"
            )

    annual_sources.append({
        "file": path.name,
        "sha256": digest,
        "year": year,
    })

with (args.output / "manifest.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)

(args.output / "grid.json").write_text(
    json.dumps(grid, indent=2)
)

(args.output / "region.geojson").write_bytes(region_bytes)

metadata = {
    "variable": args.variable,
    "source": args.source,
    "received_months": len(records),
    "expected_months": 300,
    "missing_years": missing,
    "missing_months": sorted(
        {f"{y}-{m:02d}-01"
         for y in range(2001, 2026)
         for m in range(1, 13)}
        - {row["date"] for row in records}
    ),
    "calendar_complete": len(records) == 300,
    "land_pixels": land_pixels,
    "land_mask_sha256": hashlib.sha256(region_bytes).hexdigest(),
    "land_mask_method": "Natural Earth 1:50m; pixel-center inclusion",
    "domain": "EPSG:6933 restricted export grid; not full polar coverage",
    "annual_sources": annual_sources,
    "gap_filling": False,
    "import_complete": True,
}

(args.output / "import_metadata.json").write_text(
    json.dumps(metadata, indent=2)
)

print("\n=== IMPORT COMPLETED ===")
print("Received months:", len(records))
print("Land pixels:", land_pixels)
print("Missing years:", missing)
print("Package:", args.output)
