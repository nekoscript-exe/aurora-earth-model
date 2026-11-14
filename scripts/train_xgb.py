"""AURORA XGBoost GPU training pipeline."""

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.models.baseline import (
    temporal_split,
    fit_climatology,
    predict_baselines,
    regression_metrics
)

from aurora.models.features import (
    FEATURE_NAMES,
    build_tabular_dataset
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cube",
        default="data/synthetic/cube.npz"
    )

    parser.add_argument(
        "--output",
        default="outputs/synthetic/xgboost"
    )

    parser.add_argument(
        "--device",
        default="cuda"
    )

    args = parser.parse_args()

    start = perf_counter()

    with np.load(args.cube, allow_pickle=False) as data:
        X = data["X"]
        dates = data["dates"].astype("datetime64[M]")

    if not np.all(np.diff(dates).astype(int) == 1):
        raise ValueError("Monthly calendar must be consecutive")

    splits = temporal_split(dates)

    if any(len(v) == 0 for v in splits.values()):
        raise ValueError("Insufficient historical data")

    climate = fit_climatology(
        X, dates, splits["train"]
    )

    val_indices = splits["validation"]
    actual = X[val_indices]

    baselines = predict_baselines(
        X, dates, val_indices, climate
    )

    common = np.isfinite(actual)

    for prediction in baselines.values():
        common &= np.isfinite(prediction)

    print("Building training dataset...", flush=True)

    X_train, y_train = build_tabular_dataset(
        X, dates, splits["train"]
    )

    print("Building validation dataset...", flush=True)

    X_val, y_val = build_tabular_dataset(
        X, dates, val_indices, common
    )

    print("Train shape:", X_train.shape)
    print("Validation shape:", X_val.shape)
    print("Device:", args.device)
    print("Starting training...", flush=True)

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        eval_metric="rmse",
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.9,
        tree_method="hist",
        device=args.device,
        early_stopping_rounds=25,
        random_state=42,
        max_bin=256
    )

    train_start = perf_counter()

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=25
    )

    train_seconds = perf_counter() - train_start

    prediction = model.predict(X_val)

    assert len(prediction) == common.sum()

    if not np.isfinite(prediction).all():
        raise ValueError("Non-finite predictions")

    config = json.loads(
        model.get_booster().save_config()
    )

    actual_device = config["learner"][
        "generic_param"
    ]["device"]

    results = {
        name: regression_metrics(
            actual, values, common
        )
        for name, values in baselines.items()
    }

    results["xgboost"] = regression_metrics(
        y_val, prediction
    )

    report = {
        "cube": args.cube,
        "device": actual_device,
        "xgboost_version": xgb.__version__,
        "features": FEATURE_NAMES,
        "training_observations": int(len(y_train)),
        "validation_observations": int(len(y_val)),
        "best_iteration": int(model.best_iteration),
        "training_seconds": train_seconds,
        "total_seconds": perf_counter() - start,
        "validation": results,
        "feature_importance": {
            name: float(score)
            for name, score in zip(
                FEATURE_NAMES,
                model.feature_importances_
            )
        }
    }

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    model.save_model(output / "model.ubj")

    np.savez_compressed(
        output / "validation_predictions.npz",
        actual=y_val,
        predicted=prediction,
        mask=common,
        dates=str(dates[val_indices[0]])
              if len(val_indices) == 1
              else dates[val_indices].astype(str)
    )

    with open(output / "metrics.json", "w") as f:
        json.dump(report, f, indent=4)

    print("=" * 60)
    print("AURORA | XGBOOST TRAINING COMPLETE")
    print("=" * 60)
    print(json.dumps(report, indent=4))
    print("=" * 60)


if __name__ == "__main__":
    main()
