import argparse
import ee
from rasterio.crs import CRS

parser = argparse.ArgumentParser()
parser.add_argument("--start", type=int, required=True)
parser.add_argument("--end", type=int, required=True)
args = parser.parse_args()

assert 2001 <= args.start <= args.end <= 2025

ee.Initialize(project="aurora-earth-model-2026")

CRS = CRS.from_epsg(6933).to_wkt(version="WKT1_GDAL")
TRANSFORM = [50000, 0, -17350000, 0, -50000, 7300000]

REGION = ee.Geometry.Rectangle(
    [-17350000, -6050000, 17350000, 7300000],
    proj=CRS,
    geodesic=False
)

SOURCE = ee.ImageCollection("MODIS/061/MOD13C1")
projection = ee.Image(SOURCE.first()).select("NDVI").projection()

def prepare(image):
    value = image.select("NDVI")

    return value.updateMask(
        image.select("SummaryQA").eq(0)
        .And(value.gte(-0.2))
        .And(value.lte(1))
    )

def monthly(year, month):
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")

    value = SOURCE.filterDate(start, end).map(
        prepare
    ).median().setDefaultProjection(projection)

    stack = ee.Image.cat([
        value.unmask(0).rename("v"),
        value.mask().unmask(0).rename("w")
    ]).setDefaultProjection(projection)

    agg = stack.reduceResolution(
        reducer=ee.Reducer.sum(),
        maxPixels=4096
    ).reproject(
        crs=CRS,
        crsTransform=TRANSFORM
    )

    weights = agg.select("w")

    return agg.select("v").divide(weights).updateMask(
        weights.gte(0.10)
    ).rename(f"NDVI_{year}_{month:02d}")

existing = {
    t.config.get("description")
    for t in ee.batch.Task.list()
    if t.state in ["READY", "RUNNING", "COMPLETED"]
}

for year in range(args.start, args.end + 1):
    description = f"AURORA_GLOBAL_NDVI_V5_{year}_ANNUAL"

    if description in existing:
        print("OMITIDO:", description)
        continue

    expected = [
        f"{year}-{month:02d}"
        for month in range(1, 13)
    ]

    dates = SOURCE.filterDate(
        f"{year}-01-01", f"{year+1}-01-01"
    ).aggregate_array("system:time_start").map(
        lambda t: ee.Date(t).format("YYYY-MM")
    ).getInfo()

    missing = set(expected) - set(dates)

    if missing:
        print("MESES FALTANTES:", sorted(missing))
        continue

    image = ee.Image.cat([
        monthly(year, month)
        for month in range(1, 13)
    ]).unmask(-9999).toFloat()

    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder="AURORA_GLOBAL_NDVI_HISTORY",
        fileNamePrefix=f"ndvi_global_{year}",
        region=REGION,
        crs=CRS,
        crsTransform=TRANSFORM,
        maxPixels=10000000,
        fileFormat="GeoTIFF",
        formatOptions={
            "cloudOptimized": True,
            "noData": -9999
        }
    )

    task.start()
    print("INICIADO:", year, task.id, flush=True)
