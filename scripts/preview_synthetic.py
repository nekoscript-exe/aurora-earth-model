from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

with np.load(ROOT / "data/synthetic/cube.npz") as data:
    X = data["X"]
    dates = data["dates"]
    slope = data["true_slope"]

plt.style.use("dark_background")

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

cmap = plt.colormaps["RdYlGn"].copy()
cmap.set_bad("#353535")

for ax, index in zip(axes.flat[:3], [0, 144, 288]):
    image = ax.imshow(
        X[index, :, :, 0],
        cmap=cmap,
        vmin=0,
        vmax=1
    )

    ax.set_title(f"NDVI sintético | {dates[index]}")
    ax.axis("off")

    fig.colorbar(image, ax=ax, shrink=0.8)

image = axes[1, 1].imshow(
    slope,
    cmap="RdBu",
    vmin=-0.008,
    vmax=0.008
)

axes[1, 1].set_title("Pendiente verdadera")
axes[1, 1].axis("off")

fig.colorbar(
    image,
    ax=axes[1, 1],
    shrink=0.8,
    label="NDVI/año"
)

fig.suptitle(
    "AURORA | Synthetic Earth Observation",
    fontsize=20,
    fontweight="bold"
)

fig.tight_layout()

output = ROOT / "docs/evidence/model"
output.mkdir(parents=True, exist_ok=True)

fig.savefig(
    output / "synthetic_preview.png",
    dpi=200,
    bbox_inches="tight"
)

plt.close(fig)
