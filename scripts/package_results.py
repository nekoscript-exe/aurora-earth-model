"""AURORA scientific results delivery."""

import argparse
import hashlib
import json
import zipfile

from pathlib import Path


REQUIRED = [
    "trend_slope.tif",
    "trend_sen.tif",
    "trend_p.tif",
    "trend_q.tif",
    "trend_change.tif",
    "trend_n.tif",
    "trend_significant.tif",
    "trend_lag1.tif",
    "trend_hac_q.tif",
    "coverage.tif",
    "metrics.json",
    "run_metadata.json",
    "monthly_series.csv",
    "annual_series.csv",
    "regional_trend.json"
]


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--region", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    root = Path("outputs") / args.region
    history = root / "history"

    files = []

    for name in REQUIRED:

        path = history / name

        if not path.is_file():
            raise FileNotFoundError(path)

        files.append(path)

    metadata = json.loads(
        (history / "metrics.json").read_text()
    )

    if (
        metadata["dataset"] != "satellite"
        or metadata["months"] != 300
    ):
        raise ValueError(
            "Expected complete real satellite results"
        )

    optional = [
        root / "final_benchmark.json",
        root / "xgboost/metrics.json",
        root / "convlstm/metrics.json"
    ]

    for engine in ["xgboost", "convlstm"]:

        directory = root / "forecast" / engine

        optional.extend([
            directory / "forecast_ndvi.tif",
            directory / "forecast_metadata.json"
        ])

    files.extend(
        path for path in optional
        if path.is_file()
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = []

    with zipfile.ZipFile(
        output, "w",
        compression=zipfile.ZIP_DEFLATED
    ) as archive:

        for path in files:

            name = path.relative_to(root).as_posix()
            content = path.read_bytes()

            archive.writestr(name, content)

            manifest.append({
                "path": name,
                "bytes": len(content),
                "sha256": hashlib.sha256(
                    content
                ).hexdigest()
            })

        archive.writestr(
            "package_manifest.json",
            json.dumps({
                "region": args.region,
                "dataset": metadata["dataset"],
                "files": manifest
            }, indent=4)
        )

    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None

    print("=" * 60)
    print("AURORA | SCIENTIFIC DELIVERY")
    print("Region:", args.region)
    print("Results:", len(files))
    print("Package:", output)
    print("Integrity: PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
