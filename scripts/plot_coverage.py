"""AURORA satellite coverage visualization."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter


def plot_coverage(csv_path, output_path):

    df = pd.read_csv(csv_path)

    df["date"] = pd.to_datetime(df["date"])

    df["valid_fraction"] = pd.to_numeric(
        df["valid_fraction"], errors="coerce"
    )

    df = df.sort_values("date").dropna(
        subset=["valid_fraction"]
    )

    if df.empty:
        raise ValueError("No valid coverage data")

    coverage = df["valid_fraction"]
    mean = coverage.mean()
    threshold = 0.70

    low = df[coverage < threshold]
    worst = df.loc[coverage.idxmin()]

    fig, ax = plt.subplots(figsize=(15, 6))

    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8fafc")

    ax.plot(
        df["date"],
        coverage,
        color="#2563a6",
        linewidth=1.3,
        alpha=0.9,
        label="Monthly coverage"
    )

    ax.scatter(
        low["date"],
        low["valid_fraction"],
        color="#dc554f",
        s=28,
        zorder=5,
        label=f"Below 70% ({len(low)} months)"
    )

    ax.axhline(
        threshold,
        color="#dc554f",
        linestyle="--",
        linewidth=1.3,
        label="70% review threshold"
    )

    ax.axhline(
        mean,
        color="#26936c",
        linestyle=":",
        linewidth=1.6,
        label=f"Mean coverage: {mean:.2%}"
    )

    ax.axhspan(
        0, threshold,
        color="#dc554f",
        alpha=0.045
    )

    ax.annotate(
        f"{worst['date']:%b %Y}\n"
        f"{worst['valid_fraction']:.2%}",
        xy=(
            worst["date"],
            worst["valid_fraction"]
        ),
        xytext=(-65, -25),
        textcoords="offset points",
        arrowprops={
            "arrowstyle": "->",
            "color": "#dc554f"
        },
        color="#b93630",
        fontsize=10,
        fontweight="bold"
    )

    ax.xaxis.set_major_locator(
        mdates.YearLocator(2)
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%Y")
    )

    ax.yaxis.set_major_formatter(
        PercentFormatter(1.0)
    )

    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Year")
    ax.set_ylabel("Valid regional coverage")

    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.25
    )

    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle(
        "AURORA | Satellite Data Quality",
        fontsize=22,
        fontweight="bold"
    )

    ax.set_title(
        f"MODIS NDVI · Monthly coverage · "
        f"{df['date'].min():%Y}–{df['date'].max():%Y}",
        fontsize=12,
        color="#64748b",
        pad=15
    )

    ax.legend(
        loc="lower left",
        ncol=2,
        frameon=False,
        fontsize=10
    )

    fig.text(
        0.5, 0.015,
        f"Source: MODIS/061/MOD13Q1 | "
        f"{len(df)} monthly records | AURORA",
        ha="center",
        fontsize=9,
        color="#64748b"
    )

    fig.tight_layout(rect=[0, 0.045, 1, 0.93])

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print("Monthly records:", len(df))
    print("Mean coverage:", f"{mean:.2%}")
    print("Low coverage months:", len(low))
    print("Output:", output_path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        default="docs/evidence/data/qa_report.csv"
    )

    parser.add_argument(
        "--output",
        default="docs/evidence/data/qa_coverage.png"
    )

    args = parser.parse_args()

    plot_coverage(args.csv, args.output)
