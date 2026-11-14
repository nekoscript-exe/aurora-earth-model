#!/usr/bin/env python3
"""Valida los TIFF mensuales de NDVI contra el contrato de datos."""
import argparse, csv, json, os, sys
from collections import Counter

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform_geom

NDVI_MIN, NDVI_MAX = -0.2, 1.0  # rango físico: VERIFICAR contra el catálogo
MIN_COVERAGE = 0.70


def load_grid(path):
    g = json.load(open(path))
    g["affine"] = Affine(*g["transform"])
    return g


def region_mask(region_path, grid):
    geom = json.load(open(region_path))["features"][0]["geometry"]
    geom = transform_geom("EPSG:4326", grid["crs"], geom)
    return rasterize([(geom, 1)], out_shape=(grid["height"], grid["width"]),
                     transform=grid["affine"], fill=0, dtype="uint8").astype(bool)


def find_duplicates(dates):
    return sorted(d for d, c in Counter(dates).items() if c > 1)


def _month_range(start, end):
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def find_missing_months(dates, start=None, end=None):
    present = sorted({d[:7] for d in dates})
    if not present:
        return []
    return [m for m in _month_range(start or present[0], end or present[-1])
            if m not in present]


def check_raster(path, grid, inside):
    """Devuelve (lista de problemas, estadísticas)."""
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
        arr = s.read(1).astype("float32")  # a float antes de poner NaN
    arr[(arr == grid["nodata"]) | ~np.isfinite(arr)] = np.nan
    if arr.shape != inside.shape:
        return issues + ["no se puede medir cobertura (forma)"], stats
    valid = ~np.isnan(arr)
    vals = arr[valid]
    if vals.size:
        stats.update(min=round(float(vals.min()), 4), max=round(float(vals.max()), 4),
                     mean=round(float(vals.mean()), 4))
        if vals.min() < NDVI_MIN or vals.max() > NDVI_MAX:
            issues.append("valores fuera de rango")
    stats["valid_fraction"] = round(float((valid & inside).sum() / inside.sum()), 4)
    return issues, stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="manifest.csv")
    p.add_argument("--grid", default="grid.json")
    p.add_argument("--region", default="config/region.geojson")
    p.add_argument("--raw", default="data/raw")
    p.add_argument("--start", help="YYYY-MM esperado (opcional)")
    p.add_argument("--end", help="YYYY-MM esperado (opcional)")
    p.add_argument("--out-csv", default="docs/evidence/data/qa_report.csv")
    p.add_argument("--out-fig", default="docs/evidence/data/qa_coverage.png")
    a = p.parse_args()

    grid = load_grid(a.grid)
    inside = region_mask(a.region, grid)
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

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pts = [(x["date"], x["valid_fraction"]) for x in report if x["valid_fraction"] != ""]
    if pts:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot([d for d, _ in pts], [v for _, v in pts], marker="o")
        ax.axhline(MIN_COVERAGE, color="red", ls="--", label="umbral 70%")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("fracción válida (dentro de la región)")
        ax.tick_params(axis="x", rotation=60, labelsize=6)
        ax.legend()
        fig.tight_layout()
        fig.savefig(a.out_fig, dpi=100)

    n_rev = sum(x["status"] == "REVISAR" for x in report)
    print(f"{len(report)} archivos | errores: {errors} | a revisar (<70%): {n_rev}")
    print("CSV:", a.out_csv)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()