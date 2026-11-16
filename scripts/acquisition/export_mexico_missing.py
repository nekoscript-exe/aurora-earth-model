"""Complete missing Mexico observations using the repository methodology.

Inputs are explicit data paths; importing this module never submits remote jobs.
"""
import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sys

import ee

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from export_grid import month_value, aggregate, ee_crs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--grid', type=Path, required=True)
    parser.add_argument('--missing-ndvi', type=Path, required=True)
    parser.add_argument('--missing-lst', type=Path, required=True)
    args = parser.parse_args()
    grid = json.loads(args.grid.read_text())
    calendars = {'ndvi': args.missing_ndvi, 'lst': args.missing_lst}
    # Validate all supplied calendars before initialization or export submission.
    for path in calendars.values():
        for date in path.read_text().split():
            datetime.strptime(date, '%Y-%m')
    ee.Initialize(project=args.project)

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

        calendar = calendars[variable].read_text().split()

        grouped = defaultdict(list)

        for date in calendar:
            parsed = datetime.strptime(date, "%Y-%m")
            year, month = parsed.year, parsed.month
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


if __name__ == '__main__':
    main()
