#!/usr/bin/env python3
"""Genera grid_lst.json y manifest_lst.csv a partir de los TIFF de data/raw_lst."""
import csv, glob, json, os

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom

PREFIX = "lst_day"
files = sorted(glob.glob(f"data/raw_lst/{PREFIX}_*.tif"))
if not files:
    raise SystemExit("No hay TIFF en data/raw_lst")

with rasterio.open(files[0]) as s0:
    grid = {"crs": s0.crs.to_string(), "transform": list(s0.transform)[:6],
            "width": s0.width, "height": s0.height, "nodata": s0.nodata}
    ref = (s0.crs, s0.transform, s0.shape)
    reg = json.load(open("config/region.geojson"))["features"][0]["geometry"]
    g = transform_geom("EPSG:4326", s0.crs.to_string(), reg)
    inside = rasterize([(g, 1)], out_shape=s0.shape, transform=s0.transform,
                       fill=0, dtype="uint8")
    if inside is None:
        raise ValueError("Rasterization did not return a regional mask")
    inside = inside.astype(bool)
json.dump(grid, open("grid_lst.json", "w"), indent=2)

rows = []
for f in files:
    with rasterio.open(f) as s:
        assert (s.crs, s.transform, s.shape) == ref, f"Rejilla distinta: {f}"
        a = s.read(1, masked=True)
    valid = ~np.ma.getmaskarray(a)
    vf = round(float((valid & inside).sum() / inside.sum()), 4)
    y, m = os.path.basename(f)[len(PREFIX) + 1:-4].split("_")
    rows.append([f"{y}-{m}-01", f.replace(os.sep, "/"), PREFIX, "C", "EPSG:32614",
                 1000, vf, "MODIS/061/MOD11A2"])
    print(f"{os.path.basename(f)}: validos(region)={vf:.4f} "
          f"min={a.min():.1f} max={a.max():.1f} media={a.mean():.1f}")

with open("manifest_lst.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "path", "variable", "unit", "crs", "scale_m",
                "valid_fraction", "source_id"])
    w.writerows(rows)
print(f"manifest_lst.csv: {len(rows)} filas | grid_lst.json escrito")
