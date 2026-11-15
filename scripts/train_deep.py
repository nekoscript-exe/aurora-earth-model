"""AURORA Deep - ConvLSTM training pipeline."""

import argparse
import json
import random
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from torch.utils.data import DataLoader
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.models.convlstm import AuroraConvLSTM
from aurora.models.dataset import SatellitePatchDataset

from aurora.models.baseline import (
    temporal_split,
    fit_climatology,
    predict_baselines,
    regression_metrics
)


def run_epoch(
    model, loader, device, amp, optimizer=None
):
    training = optimizer is not None
    model.train(training)

    squared_error = 0.0
    absolute_error = 0.0
    target_sum = 0.0
    target_square_sum = 0.0
    observations = 0

    progress = tqdm(
        loader,
        desc="Train" if training else "Validation",
        leave=False
    )

    for inputs, target, mask in progress:

        inputs = inputs.to(device, non_blocking=True)
        target = target.to(device, non_blocking=True)
        mask = mask.to(device, non_blocking=True)

        if training:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(training):

            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16,
                enabled=amp
            ):
                prediction = model(inputs)

            p = prediction.float()[mask]
            y = target.float()[mask]

            if y.numel() == 0:
                continue

            error = p - y
            loss = error.square().mean()

            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite loss")

            if training:
                loss.backward()

                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1.0
                )

                optimizer.step()

        with torch.no_grad():
            error = error.detach().double()
            y = y.detach().double()

            squared_error += error.square().sum().item()
            absolute_error += error.abs().sum().item()
            target_sum += y.sum().item()
            target_square_sum += y.square().sum().item()
            observations += y.numel()

        progress.set_postfix(
            rmse=f"{(squared_error / observations)**0.5:.5f}"
        )

    if observations == 0:
        raise ValueError("No valid observations")

    sst = (
        target_square_sum
        - target_sum**2 / observations
    )

    return {
        "observations": observations,
        "mae": absolute_error / observations,
        "rmse": (squared_error / observations)**0.5,
        "r2": 1 - squared_error / sst if sst > 0 else None
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cube",
        default="data/synthetic/cube.npz"
    )

    parser.add_argument(
        "--output",
        default="outputs/synthetic/convlstm"
    )

    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--patch-size", type=int, default=32)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--lr", type=float, default=0.001)

    args = parser.parse_args()

    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    amp = (
        device.type == "cuda"
        and torch.cuda.is_bf16_supported()
    )

    if device.type == "cuda":
        torch.cuda.manual_seed_all(42)
        torch.backends.cudnn.benchmark = True
        torch.cuda.reset_peak_memory_stats()

    start = perf_counter()

    with np.load(args.cube, allow_pickle=False) as data:
        if "channels" in data and str(data["channels"][0]).lower() != "ndvi":
            raise ValueError("Legacy NDVI command: use train_multivariable.py / forecast_saved.py for LST")
        X = data["X"]
        dates = data["dates"].astype("datetime64[M]")

    if not np.all(np.diff(dates).astype(int) == 1):
        raise ValueError("Monthly dates must be consecutive")

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

    for values in baselines.values():
        common &= np.isfinite(values)

    train_data = SatellitePatchDataset(
        X,
        splits["train"],
        patch_size=args.patch_size
    )

    val_data = SatellitePatchDataset(
        X,
        val_indices,
        patch_size=args.patch_size,
        masks=common
    )

    train_loader = DataLoader(
        train_data,
        batch_size=args.batch_size,
        shuffle=True,
        pin_memory=device.type == "cuda",
        num_workers=0
    )

    val_loader = DataLoader(
        val_data,
        batch_size=args.batch_size,
        shuffle=False,
        pin_memory=device.type == "cuda",
        num_workers=0
    )

    model = AuroraConvLSTM().to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=args.lr
    )

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    best_rmse = float("inf")
    best_epoch = 0
    stale = 0
    history = []

    print("=" * 60)
    print("AURORA | DEEP LEARNING ENGINE")
    print("=" * 60)
    print("Device:", device)
    print("BF16 AMP:", amp)
    print("Training patches:", len(train_data))
    print("Validation patches:", len(val_data))
    print("Parameters:", sum(
        p.numel() for p in model.parameters()
    ))
    print("=" * 60)

    for epoch in range(1, args.epochs + 1):

        epoch_start = perf_counter()

        train = run_epoch(
            model,
            train_loader,
            device,
            amp,
            optimizer
        )

        val = run_epoch(
            model,
            val_loader,
            device,
            amp
        )

        assert val["observations"] == common.sum()

        history.append({
            "epoch": epoch,
            "train": train,
            "validation": val,
            "seconds": perf_counter() - epoch_start
        })

        print(
            f"Epoch {epoch:02d}/{args.epochs} | "
            f"Train RMSE: {train['rmse']:.6f} | "
            f"Val RMSE: {val['rmse']:.6f} | "
            f"Val MAE: {val['mae']:.6f}",
            flush=True
        )

        if val["rmse"] < best_rmse:

            best_rmse = val["rmse"]
            best_epoch = epoch
            stale = 0

            torch.save(
                model.state_dict(),
                output / "best_model.pt"
            )

            print("Best checkpoint saved")

        else:
            stale += 1

        if stale >= args.patience:
            print("Early stopping")
            break

    model.load_state_dict(
        torch.load(
            output / "best_model.pt",
            map_location=device,
            weights_only=True
        )
    )

    final = run_epoch(
        model, val_loader, device, amp
    )

    results = {
        name: regression_metrics(
            actual, values, common
        )
        for name, values in baselines.items()
    }

    results["convlstm"] = final

    report = {
        "cube": args.cube,
        "device": str(device),
        "torch_version": str(torch.__version__),
        "amp_bf16": amp,
        "seed": 42,
        "configuration": vars(args),
        "best_epoch": best_epoch,
        "epochs_completed": len(history),
        "training_patches": len(train_data),
        "validation_patches": len(val_data),
        "validation": results,
        "history": history,
        "seconds": perf_counter() - start,
        "peak_vram_mib": (
            torch.cuda.max_memory_allocated() / 1024**2
            if device.type == "cuda" else None
        )
    }

    with open(output / "metrics.json", "w") as f:
        json.dump(report, f, indent=4)

    print("=" * 60)
    print("AURORA | DEEP TRAINING COMPLETE")
    print("Best epoch:", best_epoch)
    print(json.dumps(results, indent=4))
    print("Total seconds:", report["seconds"])
    print("Peak VRAM MiB:", report["peak_vram_mib"])
    print("=" * 60)


if __name__ == "__main__":
    main()
