#!/usr/bin/env python3
"""Exporta NDVI mensual MODIS (MOD13Q1 v061) a TIFF Float32 en rejilla fija."""
import argparse, io, json, math, os, time, zipfile

import ee
import numpy as np
import rasterio
import requests
from rasterio.transform import Affine
from rasterio.warp import transform as warp_transform

COLLECTION = "MODIS/061/MOD13Q1"
CRS = "EPSG:32614"
NODATA = -9999.0
SCALE_FACTOR = 0.0001
RAW_MIN, RAW_MAX = -2000, 10000  # rango válido NDVI crudo: VERIFICAR en el catálogo


def flatten(c):
    if isinstance(c[0], (int, float)):
        yield c
    else:
        for x in c:
            yield from flatten(x)


def build_grid(region_path, scale):
    gj = json.load(open(region_path))
    pts = list(flatten(gj["features"][0]["geometry"]["coordinates"]))
    xs, ys = warp_transform("EPSG:4326", CRS, [p[0] for p in pts], [p[1] for p in pts])
    x0 = math.floor(min(xs) / scale) * scale
    x1 = math.ceil(max(xs) / scale) * scale
    y0 = math.floor(min(ys) / scale) * scale
    y1 = math.ceil(max(ys) / scale) * scale
    return {"crs": CRS, "transform": [scale, 0, x0, 0, -scale, y1],
            "width": int((x1 - x0) / scale), "height": int((y1 - y0) / scale),
            "bounds": [x0, y0, x1, y1], "nodata": NODATA}


def months(start, end):
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def build_image(ic, region, grid, y, m):
    start = ee.Date.fromYMD(y, m, 1)
    month_ic = ic.filterDate(start, start.advance(1, "month")).filterBounds(region)
    if month_ic.size().getInfo() == 0:
        return None
    proj = month_ic.first().select("NDVI").projection()

    def prep(img):
        qa, ndvi = img.select("SummaryQA"), img.select("NDVI")
        ok = qa.eq(0).And(ndvi.gte(RAW_MIN)).And(ndvi.lte(RAW_MAX))  # QA antes de escalar
        return ndvi.updateMask(ok).multiply(SCALE_FACTOR).toFloat()

    monthly = month_ic.map(prep).median().setDefaultProjection(proj)
    return (monthly.reduceResolution(ee.Reducer.mean(), maxPixels=1024)
            .reproject(crs=CRS, crsTransform=grid["transform"])
            .clip(region).unmask(NODATA).toFloat())


def download(img, grid, name):
    x0, y0, x1, y1 = grid["bounds"]
    rect = ee.Geometry.Rectangle([x0, y0, x1, y1], proj=CRS, geodesic=False)
    url = img.getDownloadURL({"name": name, "crs": CRS,
                              "crs_transform": grid["transform"],
                              "region": rect, "format": "GEO_TIFF"})
    data = requests.get(url, timeout=300).content
    if data[:2] == b"PK":  # a veces llega en zip
        z = zipfile.ZipFile(io.BytesIO(data))
        data = z.read(z.namelist()[0])
    return data


def finalize(raw_bytes, out_path, grid):
    with rasterio.open(io.BytesIO(raw_bytes)) as src:
        arr = src.read(1).astype("float32")
    if arr.shape != (grid["height"], grid["width"]):
        raise ValueError(f"Forma {arr.shape} distinta a la rejilla")
    arr[~np.isfinite(arr)] = NODATA
    t = grid["transform"]
    profile = dict(driver="GTiff", dtype="float32", count=1, nodata=NODATA,
                   width=grid["width"], height=grid["height"], crs=CRS,
                   transform=Affine(t[0], t[1], t[2], t[3], t[4], t[5]),
                   compress="deflate")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
    return float((arr != NODATA).mean())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--start", required=True, help="YYYY-MM")
    p.add_argument("--end", required=True, help="YYYY-MM")
    p.add_argument("--region", default="config/region.geojson")
    p.add_argument("--scale", type=int, default=1000)
    p.add_argument("--out", default="data/raw")
    a = p.parse_args()

    ee.Initialize(project=a.project)
    os.makedirs(a.out, exist_ok=True)
    grid = build_grid(a.region, a.scale)
    print("Rejilla:", grid)
    gj = json.load(open(a.region))
    region = ee.Geometry(gj["features"][0]["geometry"])
    ic = ee.ImageCollection(COLLECTION)

    for y, m in months(a.start, a.end):
        out = os.path.join(a.out, f"ndvi_{y}_{m:02d}.tif")
        if os.path.exists(out):
            print(f"{y}-{m:02d}: ya existe, se omite")
            continue
        img = build_image(ic, region, grid, y, m)
        if img is None:
            print(f"{y}-{m:02d}: SIN OBSERVACIONES (ausencia registrada, no se crea archivo)")
            continue
        frac = finalize(download(img, grid, f"ndvi_{y}_{m:02d}"), out, grid)
        print(f"{y}-{m:02d}: guardado {out} (válidos/total rejilla: {frac:.2f})")
        time.sleep(1)


if __name__ == "__main__":
    main()