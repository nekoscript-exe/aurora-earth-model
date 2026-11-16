#!/usr/bin/env python3
"""Arma el paquete de entrega de Mexico (una carpeta por variable + evidence/) sin tocar los originales.

Copia los TIFF, normaliza manifest/grid/region/export_params y genera el QA, los meses
faltantes, el registro de exportaciones y un reporte de validacion con cifras reales.
"""
import argparse, csv, hashlib, json, shutil, time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import Affine
from rasterio.warp import transform_geom

VARS = {
    "ndvi": dict(prefix="ndvi", unit="1", source="MODIS/061/MOD13Q1", data_dir="data/raw", lo=-0.2, hi=1.0),
    "lst": dict(prefix="lst_day", unit="C", source="MODIS/061/MOD11A2", data_dir="data/raw_lst", lo=-90.0, hi=80.0),
}
MIN_COVERAGE = 0.70


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def month_list(start, end):
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def region_mask(region_path, grid):
    geo = json.loads(Path(region_path).read_text())
    geoms = [transform_geom("EPSG:4326", grid["crs"], f["geometry"]) for f in geo["features"]]
    mask = geometry_mask(geoms, (grid["height"], grid["width"]), Affine(*grid["transform"][:6]),
                         invert=True, all_touched=False)
    assert mask.any(), "la region no toca la rejilla"
    return mask


def process(var, src, out, grid, mask, region_path, start, end):
    cfg = VARS[var]
    root = out / f"mexico_{var}"
    data = root / cfg["data_dir"]
    data.mkdir(parents=True, exist_ok=True)
    manifest, qa, missing, tasks, alerts = [], [], [], [], []
    scale = grid.get("scale_m", "")
    for y, m in month_list(start, end):
        date = f"{y}-{m:02d}-01"
        name = f"{cfg['prefix']}_{y}_{m:02d}.tif"
        s = Path(src) / name
        if not s.exists():
            missing.append([date, var, "archivo ausente en " + str(src)])
            tasks.append([date, var, "getDownloadURL interactivo (teselas)", "missing", name, 0])
            continue
        d = data / name
        shutil.copy2(s, d)
        with rasterio.open(d) as f:
            z = f.read(1, masked=True)
            bad = (f.crs.to_string(), tuple(f.transform)[:6], f.shape) != \
                  (grid["crs"], tuple(Affine(*grid["transform"][:6]))[:6], (grid["height"], grid["width"]))
        finite = ~np.ma.getmaskarray(z) & np.isfinite(z.data)
        ok = finite & mask
        v = z.data[ok]
        cov = float(ok.sum() / mask.sum())
        rng_alert = bool(v.size and (v.min() < cfg["lo"] - 1e-4 or v.max() > cfg["hi"] + 1e-4))
        review = cov < MIN_COVERAGE or rng_alert or bad or not v.size
        if bad:
            alerts.append((date, "rejilla distinta"))
        if rng_alert:
            alerts.append((date, "valores fuera de rango"))
        rel = d.relative_to(root).as_posix()
        manifest.append([date, rel, cfg["prefix"], cfg["unit"], grid["crs"], scale,
                         round(cov, 4), cfg["source"]])
        qa.append([date, var, int(ok.sum()), int(mask.sum()), round(cov, 6),
                   float(v.min()) if v.size else "", float(v.max()) if v.size else "",
                   float(v.mean()) if v.size else "", float(v.std()) if v.size else "",
                   bool(review), sha256(d), int((finite & ~mask).sum())])
        tasks.append([date, var, "getDownloadURL interactivo (teselas)", "downloaded", name, d.stat().st_size])

    with open(root / "manifest.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "path", "variable", "unit", "crs", "scale_m", "valid_fraction", "source_id"])
        w.writerows(manifest)
    shutil.copy2(grid["_grid_path"], root / "grid.json")
    shutil.copy2(region_path, root / "region.geojson")
    p = Path(src) / "export_params.json"
    if p.exists():
        shutil.copy2(p, root / "export_params.json")
    return root, qa, missing, tasks, alerts


def write_csv(path, header, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src-ndvi", default="data/mexico/ndvi")
    p.add_argument("--src-lst", default="data/mexico/lst")
    p.add_argument("--grid", default="grid_mexico.json")
    p.add_argument("--region", default="config/region_mexico.geojson")
    p.add_argument("--out", required=True, help="carpeta de entrega, fuera del repositorio")
    p.add_argument("--start", default="2001-01")
    p.add_argument("--end", default="2025-12")
    a = p.parse_args()

    out = Path(a.out).expanduser()
    (out / "evidence").mkdir(parents=True, exist_ok=True)
    grid = json.loads(Path(a.grid).read_text())
    grid["_grid_path"] = a.grid
    mask = region_mask(a.region, grid)
    qa_cols = ["date", "variable", "valid_pixels", "regional_pixels", "coverage", "min", "max",
               "mean", "std", "review_required", "sha256", "valid_outside_region"]
    all_missing, all_tasks, lines = [], [], []
    n_expected = len(list(month_list(a.start, a.end)))
    for var, src in (("ndvi", a.src_ndvi), ("lst", a.src_lst)):
        root, qa, missing, tasks, alerts = process(var, src, out, grid, mask, a.region, a.start, a.end)
        write_csv(out / "evidence" / f"qa_mexico_{var}.csv", qa_cols, qa)
        all_missing += missing
        all_tasks += tasks
        covs = [r[4] for r in qa]
        low = [(r[0][:7], r[4]) for r in qa if r[4] < MIN_COVERAGE]
        outside = sum(r[11] for r in qa)
        lines += [f"## {var.upper()}", f"- Archivos presentes: {len(qa)} / {n_expected}",
                  f"- Meses faltantes: {len(missing)}",
                  f"- Cobertura regional media: {np.mean(covs):.4f}; minima: {min(covs):.4f}" if covs else "- Sin archivos",
                  f"- Meses con cobertura < 70 % (revision, no rechazo): {len(low)}"
                  + (": " + ", ".join(f"{d} ({c:.2f})" for d, c in low) if low else ""),
                  f"- Alertas de rango/rejilla: {alerts if alerts else 'ninguna'}",
                  f"- Celdas validas fuera de la region (suma): {outside}", ""]
    write_csv(out / "evidence" / "missing_months.csv", ["date", "variable", "reason"], all_missing)
    write_csv(out / "evidence" / "export_tasks.csv",
              ["date", "variable", "method", "status", "file", "size_bytes"], all_tasks)
    report = ["# Reporte de validacion, Mexico (5 km, EPSG:6933)", "",
              f"Generado: {time.strftime('%Y-%m-%d %H:%M')} | rango: {a.start} a {a.end} | rejilla: "
              f"{grid['height']} x {grid['width']}, {int(mask.sum())} celdas regionales", ""] + lines + [
              "## Notas y limitaciones",
              "- Validacion interna de integridad (calendario, rejilla, dtype, nodata, rango, cobertura); "
              "no sustituye una validacion independiente del producto original.",
              "- Los faltantes no se imputaron. Las exportaciones fueron descargas interactivas por teselas; "
              "no hay IDs de tareas de Earth Engine (ver export_tasks.csv).",
              "- Cobertura = celdas validas dentro de la mascara regional (centro de pixel) / celdas de la mascara.",
              "- Fuentes: NDVI MODIS/061/MOD13Q1 (SummaryQA == 0); LST MODIS/061/MOD11A2 (QC_Day bits 0-1 = 0, en C). "
              "Parametros en export_params.json de cada variable.", ""]
    (out / "evidence" / "validation_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print("Paquete en:", out)


if __name__ == "__main__":
    main()
