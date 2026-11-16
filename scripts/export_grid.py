#!/usr/bin/env python3
"""Exporta NDVI o LST mensual MODIS a una rejilla arbitraria (p. ej. Mexico, EPSG:6933, 5 km).

Agregacion espacial: media de los pixeles validos (suma de valores / suma de pesos validos),
en uno o dos pasos segun la razon de agregacion. La mascara regional se aplica localmente
por centro de pixel. Reutiliza months() de export_ndvi.py.
"""
import argparse, io, json, os, time, zipfile

import ee
import numpy as np
import rasterio
import requests
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform_geom

from export_ndvi import months

NODATA = -9999.0
STEP_M = 5000       # escala intermedia si la razon de agregacion es muy grande
MAX_RATIO = 32      # 32 x 32 = 1024 pixeles nativos por pixel de salida (limite maxPixels)
MIN_NATIVE = 0.5    # minimo de area valida (en pixeles nativos) para reportar una celda

VARS = {
    "ndvi": {"coll": "MODIS/061/MOD13Q1", "band": "NDVI", "qc": "SummaryQA",
             "native": 250, "prefix": "ndvi"},
    "lst": {"coll": "MODIS/061/MOD11A2", "band": "LST_Day_1km", "qc": "QC_Day",
            "native": 1000, "prefix": "lst_day"},
}


def ee_crs(grid):
    """Earth Engine no reconoce EPSG:6933 por codigo: se le pasa como WKT."""
    return CRS.from_string(grid["crs"]).to_wkt(version="WKT1_GDAL")


def prep(var):
    cfg = VARS[var]

    def _f(img):
        raw, qc = img.select(cfg["band"]), img.select(cfg["qc"])
        if var == "ndvi":
            ok = qc.eq(0).And(raw.gte(-2000)).And(raw.lte(10000))  # QA antes de escalar
            val = raw.multiply(0.0001)
        else:
            ok = qc.bitwiseAnd(3).eq(0).And(raw.gte(7500)).And(raw.lte(65535))
            val = raw.multiply(0.02).subtract(273.15)  # kelvin a C
        return val.updateMask(ok).toFloat().rename("v")
    return _f


def month_value(var, y, m, bounds_geom):
    cfg = VARS[var]
    start = ee.Date.fromYMD(y, m, 1)
    ic = (ee.ImageCollection(cfg["coll"]).filterDate(start, start.advance(1, "month"))
          .filterBounds(bounds_geom))
    n = ic.size().getInfo()
    if n == 0:
        return None, None, 0
    proj = ic.first().select(cfg["band"]).projection()
    return ic.map(prep(var)).median().setDefaultProjection(proj), proj, n


def aggregate(v, proj, var, grid, min_cover):
    native, target = VARS[var]["native"], grid["scale_m"]
    crs = ee_crs(grid)
    stack = ee.Image.cat([v.unmask(0), v.mask().rename("w")]).setDefaultProjection(proj)
    if target / native > MAX_RATIO:
        if target % STEP_M:
            raise SystemExit(f"scale_m {target} debe ser multiplo de {STEP_M}")
        stack = (stack.reduceResolution(ee.Reducer.sum(), maxPixels=1024)
                 .reproject(crs=crs, scale=STEP_M))
    stack = (stack.reduceResolution(ee.Reducer.sum(), maxPixels=1024)
             .reproject(crs=crs, crsTransform=grid["transform"]))
    vs, ws = stack.select("v"), stack.select("w")
    wmin = max(min_cover * (target / native) ** 2, MIN_NATIVE)
    return vs.divide(ws).updateMask(ws.gte(wmin)).unmask(NODATA).toFloat()


def _fetch(url):
    resp = requests.get(url, timeout=600)
    data = resp.content
    if resp.status_code != 200 or data[:2] not in (b"II", b"MM", b"PK"):
        raise RuntimeError(f"La descarga no es un TIFF (HTTP {resp.status_code}): {data[:600]!r}")
    if data[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(data))
        data = z.read(z.namelist()[0])
    return data


def tile_windows(width, height, nx, ny):
    """Ventanas (c0, c1, r0, r1) que cubren la rejilla sin traslapes."""
    xs = np.linspace(0, width, nx + 1).astype(int)
    ys = np.linspace(0, height, ny + 1).astype(int)
    return [(int(xs[i]), int(xs[i + 1]), int(ys[j]), int(ys[j + 1]))
            for j in range(ny) for i in range(nx)]


def download(img, grid, name, tiles=(4, 3)):
    """Descarga por teselas (columnas x filas) y las ensambla en un arreglo completo.
    Evita 'Reprojection output too large' al pedir la rejilla entera de una vez."""
    t, scale = grid["transform"], grid["scale_m"]
    ox, oy = t[2], t[5]
    out = np.full((grid["height"], grid["width"]), NODATA, dtype="float32")
    for c0, c1, r0, r1 in tile_windows(grid["width"], grid["height"], *tiles):
        tx0, tx1 = ox + c0 * scale, ox + c1 * scale
        ty1, ty0 = oy - r0 * scale, oy - r1 * scale
        rect = ee.Geometry.Rectangle([tx0, ty0, tx1, ty1], proj=ee_crs(grid), geodesic=False)
        url = img.getDownloadURL({"name": name, "crs": ee_crs(grid),
                                  "crs_transform": [scale, 0, tx0, 0, -scale, ty1],
                                  "region": rect, "format": "GEO_TIFF"})
        with rasterio.open(io.BytesIO(_fetch(url))) as src:
            arr = src.read(1).astype("float32")
        if arr.shape != (r1 - r0, c1 - c0):
            raise ValueError(f"Tesela {arr.shape} distinta de {(r1 - r0, c1 - c0)}")
        out[r0:r1, c0:c1] = arr
    return out


def finalize(arr, out_path, grid, inside):
    arr = arr.astype("float32")
    if arr.shape != (grid["height"], grid["width"]):
        raise ValueError(f"Forma {arr.shape} distinta a la rejilla")
    arr[~np.isfinite(arr)] = NODATA
    arr[~inside] = NODATA  # mascara regional por centro de pixel
    t = grid["transform"]
    profile = dict(driver="GTiff", dtype="float32", count=1, nodata=NODATA,
                   width=grid["width"], height=grid["height"], crs=grid["crs"],
                   transform=Affine(*t), compress="deflate")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
    return float(((arr != NODATA) & inside).sum() / inside.sum())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--variable", required=True, choices=["ndvi", "lst"])
    p.add_argument("--grid", required=True, help="p. ej. grid_mexico.json")
    p.add_argument("--region", required=True, help="p. ej. config/region_mexico.geojson")
    p.add_argument("--out", required=True, help="p. ej. data/mexico/ndvi")
    p.add_argument("--months", nargs="+", help="lista YYYY-MM (alternativa a start/end)")
    p.add_argument("--start", help="YYYY-MM")
    p.add_argument("--end", help="YYYY-MM")
    p.add_argument("--tiles", default="4x3", help="teselas de descarga COLUMNASxFILAS, p. ej. 4x3 o 6x4")
    p.add_argument("--min-cover", type=float, default=0.0,
                   help="fraccion minima de area valida por celda (0-1); piso fijo de 0.5 pixeles nativos")
    a = p.parse_args()
    if not a.months and not (a.start and a.end):
        p.error("indica --months o --start y --end")

    tiles = tuple(int(s) for s in a.tiles.lower().split("x"))
    ee.Initialize(project=a.project)
    os.makedirs(a.out, exist_ok=True)
    grid = json.load(open(a.grid))
    geom = json.load(open(a.region))["features"][0]["geometry"]
    g = transform_geom("EPSG:4326", grid["crs"], geom)
    inside = rasterize([(g, 1)], out_shape=(grid["height"], grid["width"]),
                       transform=Affine(*grid["transform"]), fill=0,
                       dtype="uint8").astype(bool)
    print("Rejilla:", {k: grid[k] for k in ("crs", "transform", "width", "height", "scale_m")},
          "| pixeles regionales:", int(inside.sum()))
    x0, y0, x1, y1 = grid["bounds"]
    bounds_geom = ee.Geometry.Rectangle([x0, y0, x1, y1], proj=ee_crs(grid), geodesic=False)

    cfg = VARS[a.variable]
    json.dump({"variable": a.variable, "collection": cfg["coll"], "grid_file": a.grid,
               "crs": grid["crs"], "scale_m": grid["scale_m"],
               "aggregation": "media de pixeles validos (suma valores / suma pesos validos), 1 o 2 pasos",
               "min_cover": a.min_cover, "min_native_pixels": MIN_NATIVE, "download_tiles": a.tiles,
               "mask": "centro de pixel, local", "month_rule": "compuestos por fecha de inicio, mediana",
               "exported_on": time.strftime("%Y-%m-%d")},
              open(os.path.join(a.out, "export_params.json"), "w"), indent=2)

    ym = ([(int(s[:4]), int(s[5:7])) for s in a.months] if a.months
          else list(months(a.start, a.end)))
    for y, m in ym:
        out = os.path.join(a.out, f"{cfg['prefix']}_{y}_{m:02d}.tif")
        if os.path.exists(out):
            print(f"{y}-{m:02d}: ya existe, se omite")
            continue
        v, proj, n = month_value(a.variable, y, m, bounds_geom)
        if v is None:
            print(f"{y}-{m:02d}: SIN OBSERVACIONES (ausencia registrada, no se crea archivo)")
            continue
        img = aggregate(v, proj, a.variable, grid, a.min_cover)
        frac = finalize(download(img, grid, f"{cfg['prefix']}_{y}_{m:02d}", tiles), out, grid, inside)
        print(f"{y}-{m:02d}: guardado {out} ({n} imagenes; validos/region: {frac:.2f})")
        time.sleep(1)


if __name__ == "__main__":
    main()
