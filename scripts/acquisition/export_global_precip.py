"""Export monthly GPM IMERG V07 precipitation to AURORA."""

import argparse
import ee
from rasterio.crs import CRS

parser = argparse.ArgumentParser()
parser.add_argument("--start", type=int, required=True)
parser.add_argument("--end", type=int, required=True)
args = parser.parse_args()

assert 2001 <= args.start <= args.end <= 2025

ee.Initialize(project="aurora-earth-model-2026")

SOURCE = "NASA/GPM_L3/IMERG_MONTHLY_V07"
NODATA = -9999

crs = CRS.from_epsg(6933).to_wkt(version="WKT1_GDAL")

transform = [
    50000, 0, -17350000,
    0, -50000, 7300000
]

region = ee.Geometry.Rectangle(
    [-17350000, -6050000, 17350000, 7300000],
    proj=crs,
    geodesic=False
)

source = ee.ImageCollection(SOURCE)


def monthly(year, month):
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")

    image = ee.Image(
        source.filterDate(start, end).first()
    )

    raw = image.select("precipitation")

    # Zero precipitation is valid.
    value = raw.updateMask(raw.gte(0))

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

    return (
        agg.select("v")
        .divide(weights)
        .updateMask(weights.gte(0.90))
        .rename(f"precip_{year}_{month:02d}")
    )


existing = {
    task.get("description")
    for task in ee.data.getTaskList()
    if task.get("state") in (
        "READY", "RUNNING", "COMPLETED"
    )
}

for year in range(args.start, args.end + 1):

    description = f"AURORA_GLOBAL_PRECIP_V1_{year}_ANNUAL"

    if description in existing:
        print("OMITIDO:", description)
        continue

    dates = source.filterDate(
        f"{year}-01-01",
        f"{year+1}-01-01"
    ).aggregate_array("system:time_start").map(
        lambda t: ee.Date(t).format("YYYY-MM")
    ).getInfo()

    months = range(1, 10 if year == 2025 else 13)

    expected = [
        f"{year}-{month:02d}"
        for month in months
    ]

    if sorted(dates) != expected:
        raise ValueError(
            f"Invalid calendar: {year}: {dates}"
        )

    image = ee.Image.cat([
        monthly(year, month)
        for month in months
    ]).unmask(NODATA).toFloat()

    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder="AURORA_GLOBAL_PRECIP_HISTORY",
        fileNamePrefix=f"precip_global_{year}",
        region=region,
        crs=crs,
        crsTransform=transform,
        maxPixels=10000000,
        fileFormat="GeoTIFF",
        formatOptions={
            "cloudOptimized": True,
            "noData": NODATA
        }
    )

    task.start()

    print(
        "INICIADO:", year,
        "Months:", len(expected),
        "Task:", task.id,
        flush=True
    )
