"""AURORA geospatial forecasting inference."""

import argparse
import json
import sys

from pathlib import Path
from time import perf_counter

import numpy as np
import rasterio
import torch
import xgboost as xgb

from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.models.features import monthly_features
from aurora.models.convlstm import AuroraConvLSTM


def predict_xgboost(history, dates, model_path, eligible):

    model = xgb.XGBRegressor()
    model.load_model(model_path)
    model.set_params(device="cpu")

    features = monthly_features(
        history, dates, len(history)
    )

    prediction = np.full(
        eligible.shape, np.nan, dtype=np.float32
    )

    prediction[eligible] = model.predict(
        features[eligible]
    )

    return prediction


def predict_convlstm(
    history, model_path, eligible, patch_size=32, device=None
):

    from aurora.hardware import select_device
    device = select_device(device)

    model = AuroraConvLSTM().to(device)

    model.load_state_dict(
        torch.load(
            model_path,
            map_location=device,
            weights_only=True
        )
    )

    model.eval()

    history = history[..., 0]

    _, height, width = history.shape

    prediction = np.full(
        (height, width), np.nan, dtype=np.float32
    )

    with torch.inference_mode():

        for y in range(0, height, patch_size):
            for x in range(0, width, patch_size):

                mask = eligible[
                    y:y+patch_size,
                    x:x+patch_size
                ]

                if not mask.any():
                    continue

                patch = history[
                    :,
                    y:y+patch_size,
                    x:x+patch_size
                ]

                _, h, w = patch.shape

                inputs = np.zeros(
                    (1, 12, 2, patch_size, patch_size),
                    dtype=np.float32
                )

                inputs[0, :, 0, :h, :w] = np.nan_to_num(
                    patch, nan=0.0
                )

                inputs[0, :, 1, :h, :w] = np.isfinite(
                    patch
                )

                tensor = torch.from_numpy(inputs).to(device)

                values = model(tensor).cpu().numpy()

                prediction[
                    y:y+h, x:x+w
                ] = values[0, 0, :h, :w]

    prediction[~eligible] = np.nan

    return prediction


def write_geotiff(path, prediction, grid):

    nodata = -9999.0

    values = np.where(
        np.isfinite(prediction),
        prediction,
        nodata
    ).astype(np.float32)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=grid["height"],
        width=grid["width"],
        count=1,
        dtype="float32",
        crs=grid["crs"],
        transform=Affine(*grid["transform"][:6]),
        nodata=nodata,
        compress="deflate"
    ) as dst:

        dst.write(values, 1)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--cube", required=True)
    parser.add_argument("--metadata")
    parser.add_argument("--model", required=True)

    parser.add_argument(
        "--engine",
        choices=["xgboost", "convlstm"],
        required=True
    )

    parser.add_argument("--output", required=True)
    parser.add_argument("--min-history", type=int, default=9)

    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default=None)
    args = parser.parse_args()

    if not 1 <= args.min_history <= 12:
        raise ValueError("min-history must be between 1 and 12")

    start = perf_counter()

    with np.load(args.cube, allow_pickle=False) as data:

        if "channels" in data and str(data["channels"][0]).lower() != "ndvi":
            raise ValueError("Legacy NDVI command: use train_multivariable.py / forecast_saved.py for LST")
        X = data["X"]
        dates = data["dates"].astype("datetime64[M]")

        region = (
            data["region_mask"]
            if "region_mask" in data
            else np.ones(X.shape[1:3], dtype=bool)
        )

    if len(dates) < 12:
        raise ValueError("At least 12 months required")

    if not np.all(np.diff(dates).astype(int) == 1):
        raise ValueError("Invalid monthly calendar")

    history = X[-12:]

    future = dates[-1] + np.timedelta64(1, "M")

    calendar = np.concatenate([
        dates[-12:],
        np.array([future])
    ])

    count = np.isfinite(history[..., 0]).sum(axis=0)

    eligible = region & (count >= args.min_history)

    if not eligible.any():
        raise ValueError("No eligible prediction pixels")

    if args.engine == "xgboost":

        prediction = predict_xgboost(
            history, calendar, args.model, eligible
        )

    else:

        prediction = predict_convlstm(
            history, args.model, eligible, device=args.device
        )

    if not np.isfinite(prediction[eligible]).all():
        raise ValueError("Invalid model predictions")

    prediction = np.clip(prediction, -0.2, 1.0)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        output / "forecast.npz",
        prediction=prediction,
        coverage=count / 12,
        valid=eligible,
        date=np.array(str(future))
    )

    if args.metadata:

        with open(args.metadata) as f:
            metadata = json.load(f)

        grid = metadata["grid"]

        if prediction.shape != (
            grid["height"], grid["width"]
        ):
            raise ValueError("Incompatible grid")

        write_geotiff(
            output / "forecast_ndvi.tif",
            prediction,
            grid
        )

    report = {
        "engine": args.engine,
        "cube": args.cube,
        "model": args.model,
        "forecast_date": str(future),
        "history_start": str(dates[-12]),
        "history_end": str(dates[-1]),
        "minimum_history": args.min_history,
        "regional_pixels": int(region.sum()),
        "predicted_pixels": int(eligible.sum()),
        "prediction_coverage": float(
            eligible.sum() / region.sum()
        ),
        "minimum_ndvi": float(np.nanmin(prediction)),
        "maximum_ndvi": float(np.nanmax(prediction)),
        "mean_ndvi": float(np.nanmean(prediction)),
        "seconds": perf_counter() - start
    }

    with open(output / "forecast_metadata.json", "w") as f:
        json.dump(report, f, indent=4)

    print("=" * 60)
    print("AURORA | SATELLITE FORECAST")
    print(json.dumps(report, indent=4))
    print("=" * 60)


if __name__ == "__main__":
    main()
