#!/usr/bin/env python3
"""Define la rejilla de area equivalente (EPSG:6933) de una region (Mexico) y su region.geojson.

Uso: python scripts/grid_nacional.py --project ID --name mexico --scale 5000
Escribe config/region_<name>.geojson y grid_<name>.json. No exporta datos.
"""
import argparse, json, math

import numpy as np
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform as warp_transform, transform_geom

CRS = "EPSG:6933"
NODATA = -9999.0


def build_grid_from_bounds(lon0, lat0, lon1, lat1, scale, crs=CRS):
    """EPSG:6933 es cilindrica: x depende solo de lon e y solo de lat, asi que
    las esquinas de la caja lon/lat dan la extension exacta."""
    projected = warp_transform("EPSG:4326", crs, [lon0, lon1], [lat0, lat1])
    xs, ys = projected[:2]
    x0 = math.floor(min(xs) / scale) * scale
    x1 = math.ceil(max(xs) / scale) * scale
    y0 = math.floor(min(ys) / scale) * scale
    y1 = math.ceil(max(ys) / scale) * scale
    return {"crs": crs, "transform": [scale, 0, x0, 0, -scale, y1],
            "width": int((x1 - x0) / scale), "height": int((y1 - y0) / scale),
            "bounds": [x0, y0, x1, y1], "nodata": NODATA, "scale_m": scale}


def memory_mb(h, w, n_months=300, bytes_per_px=5):
    return n_months * h * w * bytes_per_px / 1e6  # float32 + bool, sin compresion


def regional_pixels(geom_wgs84, grid):
    g = transform_geom("EPSG:4326", grid["crs"], geom_wgs84)
    m = rasterize([(g, 1)], out_shape=(grid["height"], grid["width"]),
                  transform=Affine(*grid["transform"]), fill=0, dtype="uint8")
    if m is None:
        raise ValueError("Rasterization did not return a regional mask")
    return int(m.sum())  # centro de pixel (all_touched=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--name", default="mexico")
    p.add_argument("--country", default="Mexico", help="ADM0_NAME en FAO GAUL")
    p.add_argument("--scale", type=int, default=5000)
    p.add_argument("--simplify", type=int, default=1000, help="metros, para que getInfo no sea enorme")
    a = p.parse_args()

    import ee
    ee.Initialize(project=a.project)
    fc = (ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level1")
          .filter(ee.Filter.eq("ADM0_NAME", a.country)))
    print("Estados/unidades:", fc.size().getInfo())
    geom = fc.geometry(maxError=100).simplify(a.simplify)
    gj = geom.getInfo()
    ring = geom.bounds().coordinates().get(0).getInfo()
    if not isinstance(ring, list) or not ring:
        raise ValueError("Earth Engine returned no boundary coordinates")
    lons = [c[0] for c in ring]; lats = [c[1] for c in ring]
    grid = build_grid_from_bounds(min(lons), min(lats), max(lons), max(lats), a.scale)
    grid["n_regional_pixels"] = regional_pixels(gj, grid)
    grid["bbox_lonlat"] = [min(lons), min(lats), max(lons), max(lats)]

    out_region = f"config/region_{a.name}.geojson"
    json.dump({"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "properties": {"name": a.name, "source": "FAO/GAUL_SIMPLIFIED_500m/2015/level1",
                       "filter": f"ADM0_NAME={a.country}", "simplify_m": a.simplify},
        "geometry": gj}]}, open(out_region, "w"))
    json.dump(grid, open(f"grid_{a.name}.json", "w"), indent=2)
    print("Rejilla:", {k: grid[k] for k in ("crs", "transform", "width", "height", "bounds")})
    print("Pixeles regionales (centro de pixel):", grid["n_regional_pixels"])
    print("Memoria aprox. por variable, 300 meses sin compresion: %.0f MB"
          % memory_mb(grid["height"], grid["width"]))
    print("Escrito:", out_region, f"grid_{a.name}.json")


if __name__ == "__main__":
    main()
