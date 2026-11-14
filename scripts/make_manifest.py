#!/usr/bin/env python3
"""Genera grid.json y manifest.csv a partir de los TIFF reales de data/raw."""
import csv, glob, json, os

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom

files = sorted(glob.glob("data/raw/ndvi_*.tif"))
if not files:
    raise SystemExit("No hay TIFF en data/raw")

with rasterio.open(files[0]) as s0:
    grid = {"crs": s0.crs.to_string(), "transform": list(s0.transform)[:6],
            "width": s0.width, "height": s0.height, "nodata": s0.nodata}
    ref = (s0.crs, s0.transform, s0.shape)
    reg = json.load(open("config/region.geojson"))["features"][0]["geometry"]
    g = transform_geom("EPSG:4326", s0.crs.to_string(), reg)
    inside = rasterize([(g, 1)], out_shape=s0.shape, transform=s0.transform,
                       fill=0, dtype="uint8").astype(bool)
json.dump(grid, open("grid.json", "w"), indent=2)

rows = []
for f in files:
    with rasterio.open(f) as s:
        assert (s.crs, s.transform, s.shape) == ref, f"Rejilla distinta: {f}"
        valid = ~np.ma.getmaskarray(s.read(1, masked=True))
    y, m = os.path.basename(f)[5:-4].split("_")
    rows.append([f"{y}-{m}-01", f.replace(os.sep, "/"), "ndvi", "1", "EPSG:32614",
                 1000, round(float((valid & inside).sum() / inside.sum()), 4),
                 "MODIS/061/MOD13Q1"])

with open("manifest.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "path", "variable", "unit", "crs", "scale_m",
                "valid_fraction", "source_id"])
    w.writerows(rows)
print(f"manifest.csv: {len(rows)} filas | grid.json actualizado")