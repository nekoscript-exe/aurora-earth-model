"""Prepare Mexican historical observations for the AURORA cube engine."""

from pathlib import Path
import csv
import json
import shutil
import numpy as np

root = Path(__file__).resolve().parents[2]

source = Path.home() / (
    "Proyectos/aurora-earth-model/"
    "data/incoming/mexico_integrated"
)

grid = {
    "crs": "EPSG:6933",
    "transform": [
        5000, 0, -11425000,
        0, -5000, 3960000
    ],
    "width": 612,
    "height": 426,
    "nodata": -9999.0
}

for variable, product, unit in (
    ("ndvi", "MODIS/061/MOD13Q1", "1"),
    ("lst", "MODIS/061/MOD11A2", "degC")
):
    output = root / "data/incoming" / f"mexico_{variable}"
    target = output / "data" / variable

    target.mkdir(parents=True, exist_ok=True)

    shutil.copy2(
        source / "region.geojson",
        output / "region.geojson"
    )

    (output / "grid.json").write_text(
        json.dumps(grid, indent=4)
    )

    with (source / f"manifest_{variable}.csv").open() as f:
        records = list(csv.DictReader(f))

    rows = []
    seen = set()

    for record in records:
        date = record["date"] + "-01"

        assert date not in seen
        seen.add(date)

        coverage = float(record["coverage"])

        assert np.isfinite(coverage)
        assert 0 <= coverage <= 1

        original = source / variable / record["file"]
        destination = target / original.name

        assert original.is_file(), original

        shutil.copy2(original, destination)

        rows.append({
            "date": date,
            "variable": variable,
            "source_id": product,
            "unit": unit,
            "path": destination.relative_to(output).as_posix(),
            "valid_fraction": coverage,
            "origin": record["origin"],
            "source_file": record["source_file"],
            "source_band": record["source_band"]
        })

    with (output / "manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=list(rows[0])
        )
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: r["date"]))

    print("\nVARIABLE:", variable.upper())
    print("Source:", product)
    print("Unit:", unit)
    print("Months:", len(rows))
    print("Package:", output)

print("\nMEXICO PACKAGING: COMPLETED")
