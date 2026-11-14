"""AURORA satellite cube inspection."""

import argparse
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("--cube", required=True)
parser.add_argument("--output", required=True)

args = parser.parse_args()

with np.load(args.cube, allow_pickle=False) as data:
    X = data["X"]
    dates = data["dates"]
    region = data["region_mask"]

indices = [0, len(dates) // 2, len(dates) - 1]

plt.style.use("dark_background")

fig, axes = plt.subplots(
    2, 2, figsize=(13, 12)
)

cmap = plt.colormaps["RdYlGn"].copy()
cmap.set_bad("#202020")

for ax, index in zip(axes.flat[:3], indices):
    values = X[index, :, :, 0]

    image = ax.imshow(
        values,
        cmap=cmap,
        vmin=-0.2,
        vmax=1.0,
        interpolation="nearest"
    )

    ax.set_title(
        f"NDVI | {dates[index]}"
    )

    ax.axis("off")

    fig.colorbar(
        image, ax=ax, shrink=0.8
    )

coverage = np.isfinite(
    X[..., 0]
).mean(axis=0)

coverage = np.where(
    region, coverage, np.nan
)

image = axes[1, 1].imshow(
    coverage,
    cmap="viridis",
    vmin=0,
    vmax=1,
    interpolation="nearest"
)

axes[1, 1].set_title("Cobertura temporal")
axes[1, 1].axis("off")

fig.colorbar(
    image, ax=axes[1, 1], shrink=0.8
)

fig.suptitle(
    "AURORA | Real Earth Observation\n"
    "Queretaro - MODIS MOD13Q1",
    fontsize=20,
    fontweight="bold"
)

fig.tight_layout()

output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)

fig.savefig(
    output,
    dpi=200,
    bbox_inches="tight"
)

plt.close(fig)

print("Preview saved:", output)
