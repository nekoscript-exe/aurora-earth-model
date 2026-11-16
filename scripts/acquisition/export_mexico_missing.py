"""Complete missing Mexico observations using reference methodology."""

import sys
import json
from pathlib import Path
from collections import defaultdict

import ee

REFERENCE = Path("/tmp/aurora-mexico-reference")

sys.path.insert(0, str(REFERENCE / "scripts"))

from export_grid import month_value, aggregate, ee_crs

ee.Initialize(project="aurora-earth-model-2026")

grid = json.loads(
    (REFERENCE / "grid_mexico.json").read_text()
)

crs = ee_crs(grid)

region = ee.Geometry.Rectangle(
    grid["bounds"],
    proj=crs,
    geodesic=False
)

existing = {
    t.get("description")
    for t in ee.data.getTaskList()
    if t.get("state") in (
        "READY", "RUNNING", "COMPLETED"
    )
}

for variable in ("ndvi", "lst"):

    calendar = Path(
        f"/tmp/aurora_mexico_{variable}_missing.txt"
    ).read_text().split()

    grouped = defaultdict(list)

    for date in calendar:
        year, month = map(int, date.split("-"))
        grouped[year].append(month)

    # Existing observation for independent comparison.
    grouped[2001].append(1)

    for year, months in sorted(grouped.items()):

        description = (
            f"AURORA_MEXICO_{variable.upper()}_V1_{year}"
        )

        if description in existing:
            print("OMITIDO:", description)
            continue

        bands = []

        for month in sorted(set(months)):

            value, projection, count = month_value(
                variable, year, month, region
            )

            if value is None:
                raise RuntimeError(
                    f"No observations: {variable} {year}-{month:02d}"
                )

            image = aggregate(
                value,
                projection,
                variable,
                grid,
                0.0
            )

            bands.append(
                image.rename(
                    f"{variable}_{year}_{month:02d}"
                )
            )

        annual = ee.Image.cat(bands).unmask(-9999).toFloat()

        task = ee.batch.Export.image.toDrive(
            image=annual,
            description=description,
            folder="AURORA_MEXICO_MISSING",
            fileNamePrefix=f"{variable}_mexico_{year}",
            region=region,
            crs=crs,
            crsTransform=grid["transform"],
            maxPixels=10000000,
            fileFormat="GeoTIFF",
            formatOptions={
                "cloudOptimized": True,
                "noData": -9999
            }
        )

        task.start()

        print(
            "INICIADO:", description,
            "| Months:", sorted(set(months)),
            "| Task:", task.id,
            flush=True
        )
