
"""Generate synthetic data for AURORA Core."""

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "src"))

from aurora.synthetic import generate_synthetic_cube


def main():
    output = ROOT / "data" / "synthetic"
    output.mkdir(parents=True, exist_ok=True)

    dataset = generate_synthetic_cube()

    path = output / "cube.npz"

    np.savez_compressed(path, **dataset)

    print("=" * 55)
    print("AURORA - SYNTHETIC ENGINE")
    print("=" * 55)
    print("Dataset:", path)
    print("Shape:", dataset["X"].shape)
    print("Observations:", dataset["X"].size)
    print("Valid fraction:", dataset["valid"].mean())
    print("Mean NDVI:", np.nanmean(dataset["X"]))
    print("First date:", dataset["dates"][0])
    print("Last date:", dataset["dates"][-1])
    print("Size (MB):", round(path.stat().st_size / 1024**2, 2))
    print("SYNTHETIC ENGINE: COMPLETED")
    print("=" * 55)


if __name__ == "__main__":
    main()
