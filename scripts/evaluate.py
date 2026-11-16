"""AURORA final forecasting benchmark."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import xgboost as xgb

from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.models.baseline import (
    temporal_split,
    fit_climatology,
    predict_baselines,
    regression_metrics
)

from aurora.models.features import build_tabular_dataset
from aurora.models.convlstm import AuroraConvLSTM
from aurora.models.dataset import SatellitePatchDataset

from train_deep import run_epoch


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--cube", required=True)
    parser.add_argument("--xgb", required=True)
    parser.add_argument("--deep", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    with np.load(args.cube, allow_pickle=False) as data:
        X = data["X"]
        dates = data["dates"].astype("datetime64[M]")

    if not np.all(np.diff(dates).astype(int) == 1):
        raise ValueError("Invalid monthly calendar")

    splits = temporal_split(dates)

    if not all(len(v) for v in splits.values()):
        raise ValueError("Incomplete temporal split")

    indices = splits["test"]

    climate = fit_climatology(
        X, dates, splits["train"]
    )

    actual = X[indices]

    baselines = predict_baselines(
        X, dates, indices, climate
    )

    common = np.isfinite(actual)

    for prediction in baselines.values():
        common &= np.isfinite(prediction)

    results = {
        name: regression_metrics(
            actual, prediction, common
        )
        for name, prediction in baselines.items()
    }

    print("Evaluating XGBoost...", flush=True)

    features, targets = build_tabular_dataset(
        X, dates, indices, common
    )

    model = xgb.XGBRegressor()
    model.load_model(args.xgb)
    model.set_params(device="cpu")

    predicted = model.predict(features)

    assert len(predicted) == common.sum()
    assert np.isfinite(predicted).all()

    results["xgboost"] = regression_metrics(
        targets, predicted
    )

    print("Evaluating ConvLSTM...", flush=True)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    deep = AuroraConvLSTM().to(device)

    deep.load_state_dict(
        torch.load(
            args.deep,
            map_location=device,
            weights_only=True
        )
    )

    dataset = SatellitePatchDataset(
        X, indices, patch_size=32, masks=common
    )

    loader = DataLoader(
        dataset,
        batch_size=16,
        shuffle=False
    )

    amp = (
        device.type == "cuda"
        and torch.cuda.is_bf16_supported()
    )

    results["convlstm"] = run_epoch(
        deep, loader, device, amp
    )

    for metrics in results.values():
        assert metrics["observations"] == int(common.sum())

    ranking = sorted(
        results,
        key=lambda name: results[name]["rmse"]
    )

    report = {
        "cube": args.cube,
        "evaluation": "held_out_test",
        "period": [
            str(dates[indices[0]]),
            str(dates[indices[-1]])
        ],
        "months": len(indices),
        "comparable_observations": int(common.sum()),
        "observed_targets": int(np.isfinite(actual).sum()),
        "results": results,
        "ranking_by_rmse": ranking,
        "best_model": ranking[0]
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        json.dump(report, f, indent=4)

    print("=" * 60)
    print("AURORA | FINAL FORECAST BENCHMARK")
    print("=" * 60)
    print(json.dumps(report, indent=4))
    print("=" * 60)


if __name__ == "__main__":
    main()
