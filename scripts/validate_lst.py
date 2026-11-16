#!/usr/bin/env python3
"""Valida los TIFF mensuales de LST (grados C) contra grid_lst.json y manifest_lst.csv."""
import argparse, csv, json, os, sys
from collections import Counter

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform_geom

LST_MIN, LST_MAX = -30.0, 80.0  # rango plausible en C (criterio propio, documentar)
MIN_COVERAGE = 0.70
TOL_COVERAGE = 0.001  # diferencia maxima declarada/calculada


def month_range(start, end):
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def find_duplicates(dates):
    return sorted(d for d, c in Counter(dates).items() if c > 1)


def find_missing_months(dates, start, end):
    present = {d[:7] for d in dates}
    return [m for m in month_range(start, end) if m not in present]


def check_raster(path, grid, inside):
    issues, stats = [], {"valid_fraction": "", "min": "", "max": "", "mean": ""}
    if not os.path.exists(path):
        return ["archivo no existe"], stats
    with rasterio.open(path) as s:
        if s.count != 1:
            issues.append(f"bandas={s.count}")
        if s.dtypes[0] != "float32":
            issues.append(f"dtype={s.dtypes[0]}")
        if s.crs is None or s.crs.to_string() != grid["crs"]:
            issues.append(f"crs={s.crs}")
        if (s.height, s.width) != (grid["height"], grid["width"]):
            issues.append(f"forma={(s.height, s.width)}")
        if not np.allclose(list(s.transform)[:6], grid["transform"]):
            issues.append("transformada distinta")
        if s.nodata != grid["nodata"]:
            issues.append(f"nodata={s.nodata}")
        arr = s.read(1).astype("float32")
    arr[(arr == grid["nodata"]) | ~np.isfinite(arr)] = np.nan
    if arr.shape != inside.shape:
        return issues + ["no se puede medir cobertura (forma)"], stats
    valid = ~np.isnan(arr)
    vals = arr[valid]
    if vals.size:
        stats.update(min=round(float(vals.min()), 2), max=round(float(vals.max()), 2),
                     mean=round(float(vals.mean()), 2))
        if vals.min() < LST_MIN or vals.max() > LST_MAX:
            issues.append("valores fuera de rango plausible")
    stats["valid_fraction"] = round(float((valid & inside).sum() / inside.sum()), 4)
    return issues, stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="manifest_lst.csv")
    p.add_argument("--grid", default="grid_lst.json")
    p.add_argument("--region", default="config/region.geojson")
    p.add_argument("--raw", default="data/raw_lst")
    p.add_argument("--start", required=True, help="YYYY-MM esperado")
    p.add_argument("--end", required=True, help="YYYY-MM esperado")
    p.add_argument("--out-csv", default="docs/evidence/data/qa_lst_report.csv")
    a = p.parse_args()

    grid = json.load(open(a.grid))
    geom = json.load(open(a.region))["features"][0]["geometry"]
    geom = transform_geom("EPSG:4326", grid["crs"], geom)
    inside = rasterize([(geom, 1)], out_shape=(grid["height"], grid["width"]),
                       transform=Affine(*grid["transform"]), fill=0,
                       dtype="uint8").astype(bool)
    rows = list(csv.DictReader(open(a.manifest)))
    dates = [r["date"] for r in rows]
    errors = 0

    dups = find_duplicates(dates)
    if dups:
        errors += len(dups)
        print("DUPLICADOS en manifest:", dups)
    missing = find_missing_months(dates, a.start, a.end)
    if missing:
        errors += len(missing)
        print("MESES FALTANTES:", missing)

    listed = {os.path.normpath(r["path"]) for r in rows}
    if os.path.isdir(a.raw):
        for f in sorted(os.listdir(a.raw)):
            if f.endswith(".tif") and os.path.normpath(os.path.join(a.raw, f)) not in listed:
                errors += 1
                print("TIFF fuera del manifest:", f)

    report = []
    for r in rows:
        issues, st = check_raster(r["path"], grid, inside)
        if st["valid_fraction"] != "" and abs(st["valid_fraction"] - float(r["valid_fraction"])) > TOL_COVERAGE:
            issues.append("cobertura declarada distinta de la calculada")
        if issues:
            errors += 1
        review = st["valid_fraction"] != "" and st["valid_fraction"] < MIN_COVERAGE
        report.append({"date": r["date"], "path": r["path"],
                       "status": "ERROR" if issues else ("REVISAR" if review else "OK"),
                       "issues": "; ".join(issues), **st})

    os.makedirs(os.path.dirname(a.out_csv), exist_ok=True)
    cols = ["date", "path", "status", "issues", "valid_fraction", "min", "max", "mean"]
    with open(a.out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(report)

    vf = [x["valid_fraction"] for x in report if x["valid_fraction"] != ""]
    n_rev = sum(x["status"] == "REVISAR" for x in report)
    if vf:
        print(f"cobertura media {np.mean(vf):.4f} | minima {min(vf):.4f}")
    print(f"{len(report)} archivos | errores: {errors} | a revisar (<70%): {n_rev}")
    print("CSV:", a.out_csv)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
