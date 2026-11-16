#!/usr/bin/env python3
"""Valida un paquete de una variable (grid.json, manifest.csv, region.geojson y TIFF).

Uso: python scripts/validar_paquete.py RUTA_DEL_PAQUETE [--start 2001-01] [--end 2025-12]
"""
import argparse, csv, json, sys
from pathlib import Path

import numpy as np
import rasterio as rio
from affine import Affine
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom


def months(start, end):
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    while (y, m) <= (ey, em):
        yield f"{y}-{m:02d}-01"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--start", default="2001-01")
    ap.add_argument("--end", default="2025-12")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    g = json.loads((root / "grid.json").read_text())
    rows = list(csv.DictReader((root / "manifest.csv").open()))
    A = Affine(*g["transform"][:6])
    crs = rio.crs.CRS.from_string(g["crs"])
    shape = (g["height"], g["width"])
    geo = json.loads((root / "region.geojson").read_text())
    mask = geometry_mask([transform_geom("EPSG:4326", crs, f["geometry"]) for f in geo["features"]],
                         shape, A, invert=True, all_touched=False)
    assert mask.any(), "la region no toca la rejilla"
    expected = set(months(a.start, a.end))
    seen, issues = set(), []

    for r in sorted(rows, key=lambda r: r["date"]):
        d = r["date"]
        if d not in expected:
            issues.append((d, "fecha fuera del calendario")); continue
        if d in seen:
            issues.append((d, "fecha duplicada")); continue
        seen.add(d)
        path = (root / r["path"]).resolve()
        if not path.is_relative_to(root):
            issues.append((d, "ruta fuera del paquete")); continue
        if not path.exists():
            issues.append((d, "archivo no existe")); continue
        with rio.open(path) as f:
            if (f.crs, f.transform, f.shape) != (crs, A, shape):
                issues.append((d, "CRS/affine/dimensiones distintos")); continue
            if f.count != 1 or f.dtypes[0] != "float32":
                issues.append((d, "bandas o dtype")); continue
            if f.nodata != float(g["nodata"]):
                issues.append((d, "nodata distinto")); continue
            z = f.read(1, masked=True)
        finite = ~np.ma.getmaskarray(z) & np.isfinite(z.data)
        ok = finite & mask
        v = z.data[ok]
        cov = ok.sum() / mask.sum()
        outside = int((finite & ~mask).sum())
        if abs(cov - float(r["valid_fraction"])) > .001:
            issues.append((d, "cobertura declarada distinta de la calculada"))
        if outside:
            issues.append((d, f"{outside} celdas validas fuera de la region"))
        var = r["variable"].lower()
        if not v.size:
            issues.append((d, "vacio"))
        elif var == "ndvi" and (v.min() < -.2001 or v.max() > 1.0001):
            issues.append((d, "rango NDVI"))
        elif var.startswith("lst") and (v.min() < -90 or v.max() > 80):
            issues.append((d, "revisar rango LST"))
        print(d, len(v), round(float(cov), 6),
              float(v.min()) if v.size else None, float(v.max()) if v.size else None)

    missing = sorted(expected - seen)
    print("Missing:", missing)
    print("Issues:", issues)
    print("Months:", len(seen), "/", len(expected))
    sys.exit(1 if (missing or issues) else 0)


if __name__ == "__main__":
    main()
