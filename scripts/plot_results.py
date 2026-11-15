"""AURORA - figuras cientificas

Uso:
    python scripts/plot_results.py --outputs outputs --dest docs/evidence/science
    python scripts/plot_results.py --outputs outputs --dest figs --manifest manifest.csv --root .

Lee los GeoTIFF de outputs/ (trend_slope, trend_p, trend_q, trend_change, trend_n)
y genera mapas PNG. Respeta nodata. No inventa datos: si falta un archivo, avisa.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap, TwoSlopeNorm
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from rasterio.plot import plotting_extent

REGION = "Querétaro"
PERIOD = "2001–2025"
SOURCE = "MODIS/061/MOD13Q1 (NDVI)"
NODATA = -9999.0
Q_THRESHOLD = 0.05
MIN_MONTHS = 9

LABEL_NONE = "Sin evidencia significativa"
LABEL_DOWN = "Disminución significativa (q<0.05)"
LABEL_UP = "Aumento significativo (q<0.05)"
LABEL_NODATA = "Sin datos"
LABEL_OUTSIDE = "Fuera de la región"
LABEL_UNTESTED = "En la región, no probado (datos insuficientes)"


# ---------- lectura ----------
def read_raster(path):
    """Devuelve (array float64 con NaN en nodata, extent para imshow)."""
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float64")
        nodata = src.nodata if src.nodata is not None else NODATA
        extent = plotting_extent(src)
    arr[~np.isfinite(arr)] = np.nan
    arr[arr == nodata] = np.nan
    return arr, extent


# ---------- utilidades ----------
def _title(base, note=""):
    t = f"{base}\n{REGION} · {PERIOD} · {SOURCE}"
    return f"{t}\n{note}" if note else t


def save_fig(fig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def _legend_below(ax, handles):
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=2, fontsize=8, frameon=False)


def _sym_limit(arr):
    m = np.nanmax(np.abs(arr)) if np.isfinite(arr).any() else np.nan
    return m if np.isfinite(m) and m > 0 else 1e-9


def _map_axes():
    fig, ax = plt.subplots(figsize=(7, 6))
    km = FuncFormatter(lambda v, _: f"{v / 1000:.0f}")
    ax.xaxis.set_major_formatter(km)
    ax.yaxis.set_major_formatter(km)
    ax.set_xlabel("Este (km, UTM 14N)")
    ax.set_ylabel("Norte (km, UTM 14N)")
    return fig, ax


# ---------- mapas ----------
def make_divergent_fig(arr, extent, title, cbar_label, note=""):
    """Mapa divergente centrado en cero (pendiente o cambio estimado)."""
    lim = _sym_limit(arr)
    cmap = plt.get_cmap("BrBG").copy()
    cmap.set_bad("#9e9e9e")
    fig, ax = _map_axes()
    im = ax.imshow(arr, cmap=cmap, norm=TwoSlopeNorm(vcenter=0, vmin=-lim, vmax=lim),
                   extent=extent)
    fig.colorbar(im, ax=ax, label=cbar_label, shrink=0.8)
    _legend_below(ax, [Patch(color="#9e9e9e", label=LABEL_NODATA)])
    ax.set_title(_title(title, note), fontsize=10)
    return fig


def categorize_significance(slope, q, threshold=Q_THRESHOLD, region=None):
    """NaN=fuera/sin datos, 0=sin evidencia, 1=disminuye, 2=aumenta.
    Si se da `region` (bool), 3 = dentro de la region pero no probado."""
    cat = np.full(slope.shape, np.nan)
    valid = np.isfinite(slope) & np.isfinite(q)
    sig = valid & (q < threshold)
    cat[valid] = 0
    cat[sig & (slope < 0)] = 1
    cat[sig & (slope > 0)] = 2
    if region is not None:
        cat[region & ~valid] = 3
    return cat


def make_significance_fig(slope, q, extent, note="",
                          title="Significancia de la tendencia (q de Benjamini–Hochberg)",
                          region=None):
    cat = categorize_significance(slope, q, region=region)
    colors = ["#fff7bc", "#8c510a", "#1a9850"]
    labels = [LABEL_NONE, LABEL_DOWN, LABEL_UP]
    if region is None:
        bad, bad_label, vmax = "#9e9e9e", LABEL_NODATA, 2.5
    else:
        colors.append("#9e9e9e")
        labels.append(LABEL_UNTESTED)
        bad, bad_label, vmax = "#ffffff", LABEL_OUTSIDE, 3.5
    cmap = ListedColormap(colors)
    cmap.set_bad(bad)
    fig, ax = _map_axes()
    ax.imshow(cat, cmap=cmap, vmin=-0.5, vmax=vmax, interpolation="nearest", extent=extent)
    handles = [Patch(color=c, label=l) for c, l in zip(colors, labels)]
    handles.append(Patch(facecolor=bad, edgecolor="#555555", label=bad_label))
    _legend_below(ax, handles)
    ax.set_title(_title(title, note), fontsize=10)
    return fig


def make_coverage_fig(n, extent, note="", label="Años válidos por píxel (n)",
                      title="Cobertura de datos"):
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#9e9e9e")
    fig, ax = _map_axes()
    im = ax.imshow(n, cmap=cmap, extent=extent)
    fig.colorbar(im, ax=ax, label=label, shrink=0.8)
    _legend_below(ax, [Patch(color="#9e9e9e", label=LABEL_NODATA)])
    ax.set_title(_title(title, note), fontsize=10)
    return fig


# ---------- series ----------
def select_locations(slope, q, threshold=Q_THRESHOLD):
    """Elige (fila, col) de: aumento, disminucion y estable, si existen."""
    valid = np.isfinite(slope) & np.isfinite(q)
    sig = valid & (q < threshold)

    def pick(score, mask):
        if not mask.any():
            return None
        s = np.where(mask, score, -np.inf)
        r, c = np.unravel_index(np.argmax(s), s.shape)
        return int(r), int(c)

    out = {
        "Aumento": pick(slope, sig & (slope > 0)),
        "Disminución": pick(-slope, sig & (slope < 0)),
        "Estable": pick(-np.abs(slope), valid & ~sig),
    }
    return {k: v for k, v in out.items() if v is not None}


def annual_means(dates, values, min_months=MIN_MONTHS):
    """Medias anuales; anio con menos de min_months validos -> NaN."""
    years = np.array([int(str(d)[:4]) for d in dates])
    values = np.asarray(values, dtype="float64")
    uniq = np.unique(years)
    means = np.full(len(uniq), np.nan)
    for i, y in enumerate(uniq):
        v = values[years == y]
        v = v[np.isfinite(v)]
        if len(v) >= min_months:
            means[i] = v.mean()
    return uniq, means


def load_pixel_series(manifest_path, root, locations):
    """Lee cada TIFF del manifest y extrae los pixeles elegidos."""
    import pandas as pd

    df = pd.read_csv(manifest_path).sort_values("date")
    dates = df["date"].tolist()
    series = {k: [] for k in locations}
    for rel in df["path"]:
        arr, _ = read_raster(Path(root) / rel)
        for k, (r, c) in locations.items():
            series[k].append(arr[r, c])
    return dates, {k: np.array(v) for k, v in series.items()}


def make_series_fig(dates, series, locations, note=""):
    fig, axes = plt.subplots(len(series), 1, figsize=(8, 2.6 * len(series)),
                             sharex=True, squeeze=False)
    x = np.array([np.datetime64(str(d)[:10]) for d in dates])
    for ax, (label, vals) in zip(axes[:, 0], series.items()):
        ax.plot(x, vals, color="#bdbdbd", lw=0.8, label="NDVI mensual")
        years, means = annual_means(dates, vals)
        xm = np.array([np.datetime64(f"{y}-07-01") for y in years])
        ax.plot(xm, means, "o-", color="#08519c", ms=3, label="Media anual (≥9 meses)")
        r, c = locations[label]
        ax.set_title(f"{label} (fila {r}, columna {c})", fontsize=9)
        ax.set_ylabel("NDVI")
        ax.legend(fontsize=7, loc="upper left")
    axes[-1, 0].set_xlabel("Fecha")
    fig.suptitle(_title("Series de tiempo en píxeles seleccionados", note), fontsize=10)
    fig.tight_layout()
    return fig


# ---------- serie regional (CSV de Ian) ----------
def make_regional_fig(monthly_csv, annual_csv, trend_json, note=""):
    """Serie regional: media mensual, media anual y recta OLS (de regional_trend.json)."""
    import json

    import pandas as pd

    mo = pd.read_csv(monthly_csv)
    an = pd.read_csv(annual_csv)
    tr = json.load(open(trend_json, encoding="utf-8"))["trend"]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.array([np.datetime64(str(d)[:10]) for d in mo["date"]])
    low = mo["coverage"].to_numpy() < 0.7
    ax.plot(x, mo["mean"], color="#bdbdbd", lw=0.8, label="Media regional mensual")
    ax.scatter(x[low], mo["mean"].to_numpy()[low], s=14, facecolors="none",
               edgecolors="#d95f02", label="Mes con cobertura < 70 % (excluido)")
    xa = np.array([np.datetime64(f"{int(y)}-07-01") for y in an["year"]])
    ax.plot(xa, an["mean"], "o", color="#08519c", ms=4, label="Media anual regional")
    y0, y1 = int(tr["period"][0]), int(tr["period"][1])
    mean_y, mean_v = an["year"].mean(), an["mean"].mean()
    fit = lambda y: mean_v + tr["slope_per_year"] * (y - mean_y)  # noqa: E731
    ax.plot([np.datetime64(f"{y0}-07-01"), np.datetime64(f"{y1}-07-01")],
            [fit(y0), fit(y1)], color="#b2182b", lw=2,
            label=f"OLS: {tr['slope_per_year']:+.5f} NDVI/año (p={tr['p_value']:.3f})")
    ax.set_ylabel("NDVI")
    ax.set_xlabel("Fecha")
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title(_title("Serie regional de NDVI", note), fontsize=10)
    fig.tight_layout()
    return fig


# ---------- orquestador ----------
REQUIRED = ["trend_slope.tif", "trend_q.tif", "trend_change.tif", "trend_n.tif"]


def run_all(outputs, dest, manifest=None, root=".", note=""):
    outputs, dest = Path(outputs), Path(dest)
    missing = [f for f in REQUIRED if not (outputs / f).exists()]
    if missing:
        raise FileNotFoundError(f"Faltan en {outputs}: {', '.join(missing)}")

    slope, ext = read_raster(outputs / "trend_slope.tif")
    q, _ = read_raster(outputs / "trend_q.tif")
    change, _ = read_raster(outputs / "trend_change.tif")
    n, _ = read_raster(outputs / "trend_n.tif")

    saved = [
        save_fig(make_divergent_fig(slope, ext, "Pendiente de NDVI", "NDVI por año", note),
                 dest / "map_slope.png"),
        save_fig(make_significance_fig(slope, q, ext, note, region=np.isfinite(n)),
                 dest / "map_significance.png"),
        save_fig(make_coverage_fig(n, ext, note), dest / "map_coverage.png"),
        save_fig(make_divergent_fig(change, ext, "Cambio estimado en el período",
                                    "Cambio de NDVI en el período", note),
                 dest / "map_change.png"),
    ]

    # Opcionales (si Ian los entrega): sensibilidad HAC y cobertura mensual
    hac = outputs / "trend_hac_q.tif"
    if hac.exists():
        qh, _ = read_raster(hac)
        saved.append(save_fig(
            make_significance_fig(slope, qh, ext, note,
                                  title="Sensibilidad: significancia con errores HAC (q)",
                                  region=np.isfinite(n)),
            dest / "map_significance_hac.png"))
    cov = outputs / "coverage.tif"
    if cov.exists():
        c, _ = read_raster(cov)
        saved.append(save_fig(
            make_coverage_fig(c, ext, note, label="Fracción de meses válidos",
                              title="Cobertura temporal mensual"),
            dest / "map_coverage_monthly.png"))

    mcsv, acsv, tjson = (outputs / "monthly_series.csv", outputs / "annual_series.csv",
                         outputs / "regional_trend.json")
    if mcsv.exists() and acsv.exists() and tjson.exists():
        saved.append(save_fig(make_regional_fig(mcsv, acsv, tjson, note),
                              dest / "series_regional.png"))

    if manifest and Path(manifest).exists():
        locs = select_locations(slope, q)
        if locs:
            dates, series = load_pixel_series(manifest, root, locs)
            saved.append(save_fig(make_series_fig(dates, series, locs, note),
                                  dest / "series_locations.png"))
    return saved


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outputs", required=True, help="carpeta con trend_*.tif")
    p.add_argument("--dest", required=True, help="carpeta destino de las figuras")
    p.add_argument("--manifest", default=None, help="manifest.csv (para las series)")
    p.add_argument("--root", default=".", help="raiz para rutas relativas del manifest")
    p.add_argument("--note", default="", help="texto extra en titulos (ej. DATOS SINTÉTICOS)")
    a = p.parse_args()
    for f in run_all(a.outputs, a.dest, a.manifest, a.root, a.note):
        print("OK", f)


if __name__ == "__main__":
    main()
