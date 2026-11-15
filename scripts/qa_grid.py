#!/usr/bin/env python3
"""Genera el manifest y valida los TIFF mensuales de una region/variable en una rejilla dada."""
import argparse, csv, glob, json, os, sys
from collections import Counter

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform_geom

VARS = {  # prefijo, unidad, fuente, rango plausible (criterio propio para LST)
    "ndvi": ("ndvi", "1", "MODIS/061/MOD13Q1", -0.2, 1.0),
    "lst": ("lst_day", "C", "MODIS/061/MOD11A2", -30.0, 80.0),
}
MIN_COVERAGE = 0.70


def month_range(start, end):
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def check_file(path, grid, inside, lo, hi):
    issues, st = [], {"valid_fraction": "", "min": "", "max": "", "mean": ""}
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
    if arr.shape != inside.shape:
        return issues + ["no se puede medir cobertura"], st
    arr[(arr == grid["nodata"]) | ~np.isfinite(arr)] = np.nan
    valid = ~np.isnan(arr)
    vals = arr[valid]
    if vals.size:
        st.update(min=round(float(vals.min()), 3), max=round(float(vals.max()), 3),
                  mean=round(float(vals.mean()), 3))
        if vals.min() < lo or vals.max() > hi:
            issues.append("valores fuera de rango")
    if (valid & ~inside).any():
        issues.append("datos fuera de la region")
    st["valid_fraction"] = round(float((valid & inside).sum() / inside.sum()), 4)
    return issues, st


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variable", required=True, choices=list(VARS))
    p.add_argument("--dir", required=True)
    p.add_argument("--grid", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--manifest-out", required=True)
    p.add_argument("--report-out", required=True)
    p.add_argument("--start", help="YYYY-MM (opcional: revisa meses faltantes)")
    p.add_argument("--end", help="YYYY-MM")
    a = p.parse_args()

    prefix, unit, source, lo, hi = VARS[a.variable]
    grid = json.load(open(a.grid))
    geom = transform_geom("EPSG:4326", grid["crs"],
                          json.load(open(a.region))["features"][0]["geometry"])
    inside = rasterize([(geom, 1)], out_shape=(grid["height"], grid["width"]),
                       transform=Affine(*grid["transform"]), fill=0,
                       dtype="uint8").astype(bool)
    files = sorted(glob.glob(os.path.join(a.dir, f"{prefix}_*.tif")))
    if not files:
        raise SystemExit("No hay TIFF en " + a.dir)

    rows, report, errors = [], [], 0
    for f in files:
        y, m = os.path.basename(f)[len(prefix) + 1:-4].split("_")
        issues, st = check_file(f, grid, inside, lo, hi)
        errors += bool(issues)
        review = st["valid_fraction"] != "" and st["valid_fraction"] < MIN_COVERAGE
        path = f.replace(os.sep, "/")
        rows.append([f"{y}-{m}-01", path, prefix, unit, grid["crs"],
                     grid.get("scale_m", ""), st["valid_fraction"], source])
        report.append({"date": f"{y}-{m}-01", "path": path,
                       "status": "ERROR" if issues else ("REVISAR" if review else "OK"),
                       "issues": "; ".join(issues), **st})

    dups = sorted(d for d, c in Counter(r[0] for r in rows).items() if c > 1)
    if dups:
        errors += len(dups)
        print("DUPLICADOS:", dups)
    if a.start and a.end:
        have = {r[0][:7] for r in rows}
        missing = [x for x in month_range(a.start, a.end) if x not in have]
        if missing:
            errors += len(missing)
            print(f"MESES FALTANTES ({len(missing)}):", missing[:12], "..." if len(missing) > 12 else "")

    with open(a.manifest_out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "path", "variable", "unit", "crs", "scale_m",
                    "valid_fraction", "source_id"])
        w.writerows(rows)
    os.makedirs(os.path.dirname(a.report_out) or ".", exist_ok=True)
    cols = ["date", "path", "status", "issues", "valid_fraction", "min", "max", "mean"]
    with open(a.report_out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(report)

    vf = [x["valid_fraction"] for x in report if x["valid_fraction"] != ""]
    n_rev = sum(x["status"] == "REVISAR" for x in report)
    for x in report:
        print(f"{x['date']}: {x['status']} | validos(region)={x['valid_fraction']} "
              f"min={x['min']} max={x['max']} media={x['mean']} {x['issues']}")
    if vf:
        print(f"cobertura media {np.mean(vf):.4f} | minima {min(vf):.4f}")
    print(f"{len(report)} archivos | errores: {errors} | a revisar (<70%): {n_rev}")
    print("manifest:", a.manifest_out, "| QA:", a.report_out)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
