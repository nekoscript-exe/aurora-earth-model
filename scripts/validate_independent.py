"""AURORA - validacion independiente (Sofia).

Parte A (siempre): coherencia interna de outputs/ (conteos, BH, serie regional...).
Parte B (si hay manifest + TIFF mensuales): 3 pixeles recalculados con scipy.stats.linregress.

Uso:
    python scripts/validate_independent.py --outputs outputs --dest docs/evidence/science
    python scripts/validate_independent.py --outputs outputs --dest docs/evidence/science \
        --manifest manifest.csv --root .
No corrige nada: solo compara y reporta. Ian decide las correcciones.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from plot_results import read_raster  # mismo directorio (scripts/)

ALPHA = 0.05
MIN_MONTHS = 9
MIN_YEARS = 15
TOL_SLOPE = 1e-6  # NDVI/año (propuesta del plan)


# ---------- funciones puras ----------
def bh_qvalues(p):
    """Benjamini-Hochberg sobre un vector de p."""
    p = np.asarray(p, dtype="float64")
    o = np.argsort(p)
    m = len(p)
    adj = p[o] * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    q = np.empty(m)
    q[o] = np.minimum(adj, 1.0)
    return q


def annual_means(dates, values, min_months=MIN_MONTHS):
    years = np.array([int(str(d)[:4]) for d in dates])
    values = np.asarray(values, dtype="float64")
    ys, ms = [], []
    for y in np.unique(years):
        v = values[years == y]
        v = v[np.isfinite(v)]
        if len(v) >= min_months:
            ys.append(y)
            ms.append(v.mean())
    return np.array(ys), np.array(ms)


def regress(years, means):
    """linregress sobre años reales; None si hay menos de MIN_YEARS años."""
    if len(years) < MIN_YEARS:
        return None
    r = stats.linregress(years, means)
    return {"slope": r.slope, "p": r.pvalue, "n_years": len(years)}


def pick_pixels(slope, q, n):
    """Regla documentada: en cada clase, el pixel con serie completa (n maximo)
    cuya pendiente esta mas cerca de la mediana de la clase."""
    ok = np.isfinite(slope) & np.isfinite(q) & (n == np.nanmax(n))
    classes = {
        "aumento significativo": ok & (q < ALPHA) & (slope > 0),
        "disminución significativa": ok & (q < ALPHA) & (slope < 0),
        "sin evidencia significativa": ok & (q >= ALPHA),
    }
    out = {}
    for name, mask in classes.items():
        if mask.any():
            med = np.median(slope[mask])
            d = np.where(mask, np.abs(slope - med), np.inf)
            out[name] = tuple(int(i) for i in np.unravel_index(np.argmin(d), d.shape))
    return out


# ---------- Parte A ----------
def check_outputs(outputs):
    outputs = Path(outputs)
    g = lambda n: read_raster(outputs / n)[0]  # noqa: E731
    slope, p, q, n = g("trend_slope.tif"), g("trend_p.tif"), g("trend_q.tif"), g("trend_n.tif")
    sen, ch, sig = g("trend_sen.tif"), g("trend_change.tif"), g("trend_significant.tif")
    rows = []

    def add(name, expected, observed, ok):
        rows.append({"comprobacion": name, "esperado": expected, "observado": observed,
                     "ok": bool(ok)})

    m = json.load(open(outputs / "metrics.json", encoding="utf-8"))
    v = np.isfinite(p)
    inc = int(((q < ALPHA) & (slope > 0)).sum())
    dec = int(((q < ALPHA) & (slope < 0)).sum())
    ns = int((q >= ALPHA).sum())
    add("píxeles regionales", m["regional_pixels"], int(np.isfinite(n).sum()),
        np.isfinite(n).sum() == m["regional_pixels"])
    add("píxeles probados", m["tested_pixels"], int(np.isfinite(slope).sum()),
        np.isfinite(slope).sum() == m["tested_pixels"])
    add("no probados (n<15)", m["not_tested"], int((np.isfinite(n) & ~np.isfinite(slope)).sum()),
        (np.isfinite(n) & ~np.isfinite(slope)).sum() == m["not_tested"])
    add("no probados tienen n<15", "max n < 15",
        float(np.nanmax(n[np.isfinite(n) & ~np.isfinite(slope)])),
        np.nanmax(n[np.isfinite(n) & ~np.isfinite(slope)]) < MIN_YEARS)
    add("aumentos significativos", m["significant_increase"], inc, inc == m["significant_increase"])
    add("disminuciones significativas", m["significant_decrease"], dec,
        dec == m["significant_decrease"])
    add("no significativos", m["not_significant"], ns, ns == m["not_significant"])
    add("trend_significant == (q<0.05)", True,
        bool(np.all((sig[v] == 1) == (q[v] < ALPHA))), np.all((sig[v] == 1) == (q[v] < ALPHA)))
    d = float(np.abs(bh_qvalues(p[v]) - q[v]).max())
    add("q = Benjamini–Hochberg(p) recalculado", "dif. máx < 1e-6", f"{d:.2e}", d < 1e-6)
    add("signo OLS = signo Sen (píxeles con q<0.05)", 1.0,
        float(np.mean(np.sign(slope[v & (q < ALPHA)]) == np.sign(sen[v & (q < ALPHA)]))),
        np.all(np.sign(slope[v & (q < ALPHA)]) == np.sign(sen[v & (q < ALPHA)])))
    span = ch[v] / slope[v]
    add("cambio = pendiente × intervalo (años)", "entre 14 y 24",
        f"{np.nanmin(span):.2f}–{np.nanmax(span):.2f}",
        np.nanmin(span) >= MIN_YEARS - 1 - 1e-3 and np.nanmax(span) <= 24 + 1e-3)
    add("pendiente media", m["mean_slope"], float(np.nanmean(slope)),
        abs(np.nanmean(slope) - m["mean_slope"]) < 1e-9)

    # serie regional
    a = pd.read_csv(outputs / "annual_series.csv")
    mo = pd.read_csv(outputs / "monthly_series.csv")
    rt = json.load(open(outputs / "regional_trend.json", encoding="utf-8"))["trend"]
    lr = stats.linregress(a["year"], a["mean"])
    add("regional: pendiente (linregress)", rt["slope_per_year"], lr.slope,
        abs(lr.slope - rt["slope_per_year"]) < 1e-9)
    add("regional: p", rt["p_value"], lr.pvalue, abs(lr.pvalue - rt["p_value"]) < 1e-9)
    add("regional: R²", rt["r_squared"], lr.rvalue**2, abs(lr.rvalue**2 - rt["r_squared"]) < 1e-9)
    h = stats.t.ppf(0.975, len(a) - 2) * lr.stderr
    ci = rt["confidence_interval_95"]
    add("regional: IC 95 %", ci, [lr.slope - h, lr.slope + h],
        abs(lr.slope - h - ci[0]) < 1e-9 and abs(lr.slope + h - ci[1]) < 1e-9)
    mo["year"] = mo["date"].str[:4].astype(int)
    ok = mo[mo["coverage"] >= 0.7].groupby("year")["mean"].agg(["mean", "count"])
    add("regional: media anual = media de meses con cobertura ≥ 0.7", "dif. máx < 1e-9",
        f'{np.abs(ok["mean"].values - a["mean"].values).max():.2e}',
        np.abs(ok["mean"].values - a["mean"].values).max() < 1e-9
        and (ok["count"].values == a["valid_months"].values).all())
    return pd.DataFrame(rows)


# ---------- Parte B ----------
def check_pixels(outputs, manifest, root):
    outputs = Path(outputs)
    slope, _ = read_raster(outputs / "trend_slope.tif")
    p, _ = read_raster(outputs / "trend_p.tif")
    q, _ = read_raster(outputs / "trend_q.tif")
    n, _ = read_raster(outputs / "trend_n.tif")
    picks = pick_pixels(slope, q, n)
    df = pd.read_csv(manifest).sort_values("date")
    dates = df["date"].tolist()
    stack = np.stack([read_raster(Path(root) / rel)[0] for rel in df["path"]])  # [T,H,W]
    rows = []
    for cls, (r, c) in picks.items():
        ys, ms = annual_means(dates, stack[:, r, c])
        res = regress(ys, ms)
        ds = abs(res["slope"] - slope[r, c])
        rows.append({"clase": cls, "fila": r, "columna": c, "años": res["n_years"],
                     "pendiente_linregress": res["slope"], "pendiente_Ian": float(slope[r, c]),
                     "dif_pendiente": ds, "p_linregress": res["p"], "p_Ian": float(p[r, c]),
                     "dentro_de_tolerancia_1e-6": bool(ds < TOL_SLOPE)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outputs", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)

    A = check_outputs(a.outputs)
    A.to_csv(dest / "validation_outputs.csv", index=False)
    print(A.to_string(index=False))
    print(f"\nParte A: {int(A['ok'].sum())}/{len(A)} comprobaciones correctas")

    if a.manifest and Path(a.manifest).exists():
        B = check_pixels(a.outputs, a.manifest, a.root)
        B.to_csv(dest / "validation_pixels.csv", index=False)
        print("\n" + B.to_string(index=False))
    else:
        print("\nParte B omitida: falta --manifest y los TIFF mensuales (data/raw).")


if __name__ == "__main__":
    main()
