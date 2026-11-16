import argparse
import ee
from rasterio.crs import CRS

parser = argparse.ArgumentParser()
parser.add_argument("--start", type=int, required=True)
parser.add_argument("--end", type=int, required=True)
args = parser.parse_args()

assert 2001 <= args.start <= args.end <= 2025

ee.Initialize(project="aurora-earth-model-2026")

crs = CRS.from_epsg(6933).to_wkt(version="WKT1_GDAL")
transform = [50000, 0, -17350000, 0, -50000, 7300000]

region = ee.Geometry.Rectangle(
    [-17350000, -6050000, 17350000, 7300000],
    proj=crs,
    geodesic=False
)

# Keep the calendar-aligned July 2001 monthly product.
# Exclude the overlapping asset starting on July 3.
source = ee.ImageCollection("MODIS/061/MOD21C3").filter(
    ee.Filter.neq("system:index", "2001_07_03")
)

def monthly(year, month):
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")

    image = ee.Image(source.filterDate(start, end).first())

    raw = image.select("LST_Day")
    qa = image.select("QC_Day")
    error = image.select("LST_Day_err")
    count = image.select("Count_Day")

    lst = raw.subtract(273.15)

    mask = (
        count.gt(0)
        .And(lst.gte(-90))
        .And(lst.lte(80))
        .And(qa.bitwiseAnd(3).lte(1))
        .And(error.gt(0))
        .And(error.lte(2))
    )

    value = lst.updateMask(mask)

    stack = ee.Image.cat([
        value.unmask(0).rename("v"),
        value.mask().unmask(0).rename("w")
    ]).setDefaultProjection(raw.projection())

    agg = stack.reduceResolution(
        reducer=ee.Reducer.sum(),
        maxPixels=4096
    ).reproject(
        crs=crs,
        crsTransform=transform
    )

    weights = agg.select("w")

    return agg.select("v").divide(weights).updateMask(
        weights.gte(0.10)
    ).rename(f"lst_{year}_{month:02d}")

existing = {
    t.get("description")
    for t in ee.data.getTaskList()
    if t.get("state") in ("READY", "RUNNING", "COMPLETED")
}

for year in range(args.start, args.end + 1):
    description = f"AURORA_GLOBAL_LST_V8_{year}_ANNUAL"

    if description in existing:
        print("OMITIDO:", description)
        continue

    dates = source.filterDate(
        f"{year}-01-01", f"{year+1}-01-01"
    ).aggregate_array("system:time_start").map(
        lambda t: ee.Date(t).format("YYYY-MM")
    ).getInfo()

    expected = [
        f"{year}-{month:02d}"
        for month in range(1, 13)
    ]

    if sorted(dates) != expected:
        print("INVALID CALENDAR:", year, dates)
        continue

    image = ee.Image.cat([
        monthly(year, month)
        for month in range(1, 13)
    ]).unmask(-9999).toFloat()

    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder="AURORA_GLOBAL_LST_HISTORY",
        fileNamePrefix=f"lst_global_{year}",
        region=region,
        crs=crs,
        crsTransform=transform,
        maxPixels=10000000,
        fileFormat="GeoTIFF",
        formatOptions={
            "cloudOptimized": True,
            "noData": -9999
        }
    )

    task.start()
    print("INICIADO:", year, task.id, flush=True)
