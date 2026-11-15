"""AURORA Explorer — Earth System Intelligence."""

import argparse
import json
import re
import subprocess
import sys

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.variables import VARIABLES, get_variable


DATASETS = {
    ("queretaro", "ndvi"): "queretaro",
    ("queretaro", "lst"): "queretaro_lst",
    ("mexico", "ndvi"): "mexico",
    ("mexico", "lst"): "mexico_lst"
}


def parse_month(value):

    if not re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", value
    ):
        raise argparse.ArgumentTypeError(
            "Expected YYYY-MM"
        )

    return np.datetime64(value, "M")


def run_script(script, *args):

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / script),
            *map(str, args)
        ],
        cwd=ROOT,
        check=True
    )


def main():

    parser = argparse.ArgumentParser(
        description="AURORA Earth System Intelligence"
    )

    parser.add_argument(
        "--variable",
        choices=list(VARIABLES),
        default="ndvi"
    )

    parser.add_argument(
        "--region",
        choices=["queretaro", "mexico"],
        default="queretaro"
    )

    parser.add_argument(
        "--start",
        type=parse_month,
        default="2001-01"
    )

    parser.add_argument(
        "--end",
        type=parse_month,
        default="2025-12"
    )

    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the scientific investigation"
    )

    args = parser.parse_args()

    if args.start > args.end:
        parser.error("Start must precede end")

    spec = get_variable(args.variable)

    dataset = DATASETS[
        (args.region, args.variable)
    ]

    directory = ROOT / "data/processed" / dataset

    cube = directory / "cube.npz"
    metadata = directory / "cube_metadata.json"

    available = (
        cube.is_file() and metadata.is_file()
    )

    report = {
        "region": args.region,
        "variable": spec.identifier,
        "description": spec.description,
        "source": spec.source,
        "unit": spec.unit,
        "period": [
            str(args.start),
            str(args.end)
        ],
        "dataset_available": available,
        "prediction_supported":
            spec.prediction_supported
    }

    print("=" * 60)
    print("AURORA | EARTH SYSTEM INTELLIGENCE")
    print(json.dumps(report, indent=4), flush=True)

    if not available:
        print("Historical dataset unavailable.")
        return 1 if args.run else 0

    if not args.run:
        print("INVESTIGATION CONFIGURATION: READY")
        return 0

    with np.load(cube, allow_pickle=False) as data:

        dates = data["dates"].astype(
            "datetime64[M]"
        )

        if (
            args.start < dates[0]
            or args.end > dates[-1]
        ):
            parser.error(
                "Requested period exceeds dataset"
            )

        selected = (
            (dates >= args.start)
            & (dates <= args.end)
        )

        years, counts = np.unique(
            dates[selected].astype("datetime64[Y]"),
            return_counts=True
        )

        if (counts >= 9).sum() < 15:
            parser.error(
                "At least 15 calendar years with "
                "nine selected months are required"
            )

        X = data["X"][selected]
        valid = data["valid"][selected]
        region = data["region_mask"]
        channels = data["channels"]

        selected_dates = data["dates"][selected]

    if str(channels[0]) != spec.identifier:
        raise ValueError("Unexpected cube variable")

    name = (
        f"{args.region}_{args.variable}_"
        f"{args.start}_{args.end}"
    )

    output = ROOT / "outputs/investigations" / name
    output.mkdir(parents=True, exist_ok=True)

    subset = output / "cube.npz"
    subset_metadata = output / "cube_metadata.json"

    np.savez_compressed(
        subset,
        X=X,
        valid=valid,
        region_mask=region,
        channels=channels,
        dates=selected_dates
    )

    meta = json.loads(metadata.read_text())

    meta["shape"] = list(X.shape)
    meta["expected_months"] = len(selected_dates)

    selected_set = set(map(str, selected_dates))

    meta["coverage"] = [
        row for row in meta["coverage"]
        if row["date"] in selected_set
    ]

    meta["missing_months"] = [
        date for date in meta["missing_months"]
        if date in selected_set
    ]

    meta["received_months"] = (
        len(selected_dates)
        - len(meta["missing_months"])
    )

    subset_metadata.write_text(
        json.dumps(meta, indent=4)
    )

    run_script(
        "analyze_history.py",
        "--cube", subset,
        "--metadata", subset_metadata,
        "--output", output / "history"
    )

    run_script(
        "regional_series.py",
        "--cube", subset,
        "--output", output / "history"
    )

    report["results"] = str(output)
    report["status"] = "completed"

    (output / "investigation.json").write_text(
        json.dumps(report, indent=4)
    )

    print("=" * 60)
    print("INVESTIGATION COMPLETED")
    print("Results:", output)
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
