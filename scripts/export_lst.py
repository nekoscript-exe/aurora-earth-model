#!/usr/bin/env python3
"""Exporta LST diurna mensual MODIS (MOD11A2 v061) a TIFF Float32 en grados Celsius.

PROPUESTA pendiente de acuerdo con Ian: el filtro de QC y la regla de agregacion
mensual son argumentos. Reutiliza la rejilla y las utilidades de export_ndvi.py.
"""
import argparse
import json
import os
import time

import ee

from export_ndvi import NODATA, build_grid, download, finalize, months

COLLECTION = "MODIS/061/MOD11A2"
BAND, QC_BAND = "LST_Day_1km", "QC_Day"
SCALE_FACTOR = 0.02
KELVIN_OFFSET = 273.15
DN_MIN, DN_MAX = 7500, 65535  # rango del catalogo para LST_Day_1km


def qc_mask(qc, max_lst_error):
    ok = qc.bitwiseAnd(3).eq(0)  # bits 0-1 == 0: pixel producido, buena calidad
    if max_lst_error is not None:
        err = qc.rightShift(6).bitwiseAnd(3)  # bits 6-7: error de LST
        ok = ok.And(err.lte(max_lst_error))
    return ok


def prep(max_lst_error):
    def _f(img):
        dn = img.select(BAND)
        ok = (qc_mask(img.select(QC_BAND), max_lst_error)
              .And(dn.gte(DN_MIN)).And(dn.lte(DN_MAX)))
        return dn.updateMask(ok).multiply(SCALE_FACTOR).subtract(KELVIN_OFFSET).toFloat()
    return _f


def month_collection(ic, y, m, assign):
    start = ee.Date.fromYMD(y, m, 1)
    end = start.advance(1, "month")
    if assign == "start":  # compuestos cuya fecha de inicio cae en el mes
        return ic.filterDate(start, end)
    # overlap: compuestos cuyo periodo [time_start, time_end) se traslapa con el mes
    return ic.filter(ee.Filter.And(
        ee.Filter.lt("system:time_start", end.millis()),
        ee.Filter.gt("system:time_end", start.millis())))


def build_image(ic, region, grid, y, m, assign, reducer, max_lst_error):
    month_ic = month_collection(ic, y, m, assign).filterBounds(region)
    n = month_ic.size().getInfo()
    if n == 0:
        return None, 0
    proj = month_ic.first().select(BAND).projection()
    stack = month_ic.map(prep(max_lst_error))
    red = stack.median() if reducer == "median" else stack.mean()
    img = (red.setDefaultProjection(proj)
           .reproject(crs=grid["crs"], crsTransform=grid["transform"])
           .clip(region).unmask(NODATA).toFloat())
    return img, n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--start", required=True, help="YYYY-MM")
    p.add_argument("--end", required=True, help="YYYY-MM")
    p.add_argument("--region", default="config/region.geojson")
    p.add_argument("--scale", type=int, default=1000)
    p.add_argument("--out", default="data/raw_lst")
    p.add_argument("--prefix", default="lst_day")
    p.add_argument("--assign", choices=["start", "overlap"], default="start")
    p.add_argument("--reducer", choices=["median", "mean"], default="median")
    p.add_argument("--max-lst-error", type=int, choices=[0, 1, 2, 3], default=None,
                   help="maximo valor permitido de bits 6-7 de QC_Day (opcional)")
    a = p.parse_args()

    ee.Initialize(project=a.project)
    os.makedirs(a.out, exist_ok=True)
    grid = build_grid(a.region, a.scale)
    print("Rejilla:", grid)
    region = ee.Geometry(json.load(open(a.region))["features"][0]["geometry"])
    ic = ee.ImageCollection(COLLECTION)

    params = {"collection": COLLECTION, "band": BAND, "qc_band": QC_BAND,
              "assign": a.assign, "reducer": a.reducer,
              "max_lst_error": a.max_lst_error, "unit": "C",
              "conversion": "DN*0.02-273.15", "scale_m": a.scale,
              "exported_on": time.strftime("%Y-%m-%d")}
    json.dump(params, open(os.path.join(a.out, "export_params.json"), "w"), indent=2)

    for y, m in months(a.start, a.end):
        out = os.path.join(a.out, f"{a.prefix}_{y}_{m:02d}.tif")
        if os.path.exists(out):
            print(f"{y}-{m:02d}: ya existe, se omite")
            continue
        img, n = build_image(ic, region, grid, y, m, a.assign, a.reducer, a.max_lst_error)
        if img is None:
            print(f"{y}-{m:02d}: SIN OBSERVACIONES (ausencia registrada, no se crea archivo)")
            continue
        frac = finalize(download(img, grid, f"{a.prefix}_{y}_{m:02d}"), out, grid)
        print(f"{y}-{m:02d}: guardado {out} ({n} compuestos; validos/total rejilla: {frac:.2f})")
        time.sleep(1)


if __name__ == "__main__":
    main()