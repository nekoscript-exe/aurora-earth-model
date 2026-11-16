"""AURORA - validacion independiente (Sofia).

Parte A (siempre): coherencia interna de outputs/ (conteos, BH, serie regional...).
Parte B: 3 pixeles recalculados con scipy.stats.linregress. Dos formas de darle las series mensuales:
  (a) --manifest + --root : lee los 300 TIFF mensuales (data/raw)
  (b) --pixel-csv         : CSV ligero con columnas date,row,col,ndvi (lo exporta Ian para los 3 pixeles)
Siempre imprime y guarda los 3 pixeles elegidos (pixels_selected.csv) para pedirselos a Ian.

Uso:
    python scripts/validate_independent.py --outputs outputs --dest docs/evidence/science
    python scripts/validate_independent.py --outputs outputs --dest docs/evidence/science \
        --manifest manifest.csv --root .
    python scripts/validate_independent.py --outputs outputs --dest docs/evidence/science \
        --pixel-csv pixel_series.csv
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
TOL_SLOPE = 1e-6  # unidades/año; para LST usar --tol 1e-5 (°C/año)


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


def _closest_to_median(slope, mask):
    med = np.median(slope[mask])
    d = np.where(mask, np.abs(slope - med), np.inf)
    return tuple(int(i) for i in np.unravel_index(np.argmin(d), d.shape))


def pick_pixels(slope, q, n, mode="auto"):
    """Regla documentada, determinista, sobre pixeles con serie completa (n maximo).
    mode='sig'   : aumento significativo / disminucion significativa / sin evidencia.
    mode='nosig' : pendiente negativa / positiva (si existe) / cercana a cero, SIN etiquetar significancia.
    mode='auto'  : 'sig' si hay pixeles con q<0.05; si no, 'nosig'."""
    ok = np.isfinite(slope) & np.isfinite(q) & (n == np.nanmax(n))
    if mode == "auto":
        mode = "sig" if (ok & (q < ALPHA)).any() else "nosig"
    out = {}
    if mode == "sig":
        classes = {
            "aumento significativo": ok & (q < ALPHA) & (slope > 0),
            "disminución significativa": ok & (q < ALPHA) & (slope < 0),
            "sin evidencia significativa": ok & (q >= ALPHA),
        }
        for name, mask in classes.items():
            if mask.any():
                out[name] = _closest_to_median(slope, mask)
    else:
        for name, mask in {"pendiente negativa": ok & (slope < 0),
                           "pendiente positiva": ok & (slope > 0)}.items():
            if mask.any():
                out[name] = _closest_to_median(slope, mask)
        if ok.any():
            d = np.where(ok, np.abs(slope), np.inf)
            out["pendiente cercana a cero"] = tuple(int(i) for i in np.unravel_index(np.argmin(d), d.shape))
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
    nt = n[np.isfinite(n) & ~np.isfinite(slope)]
    add("no probados tienen n<15", "max n < 15", float(nt.max()) if nt.size else "n/a (0 no probados)",
        (nt.max() < MIN_YEARS) if nt.size else True)
    add("aumentos significativos", m["significant_increase"], inc, inc == m["significant_increase"])
    add("disminuciones significativas", m["significant_decrease"], dec,
        dec == m["significant_decrease"])
    add("no significativos", m["not_significant"], ns, ns == m["not_significant"])
    add("trend_significant == (q<0.05)", True,
        bool(np.all((sig[v] == 1) == (q[v] < ALPHA))), np.all((sig[v] == 1) == (q[v] < ALPHA)))
    d = float(np.abs(bh_qvalues(p[v]) - q[v]).max())
    add("q = Benjamini–Hochberg(p) recalculado", "dif. máx < 1e-6", f"{d:.2e}", d < 1e-6)
    sg = v & (q < ALPHA)
    if sg.any():
        add("signo OLS = signo Sen (píxeles con q<0.05)", 1.0,
            float(np.mean(np.sign(slope[sg]) == np.sign(sen[sg]))),
            np.all(np.sign(slope[sg]) == np.sign(sen[sg])))
    else:
        add("signo OLS = signo Sen (todos los probados)", ">= 0.9",
            float(np.mean(np.sign(slope[v]) == np.sign(sen[v]))),
            np.mean(np.sign(slope[v]) == np.sign(sen[v])) >= 0.9)
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
def _load_maps(outputs):
    outputs = Path(outputs)
    slope, ext = read_raster(outputs / "trend_slope.tif")
    p, _ = read_raster(outputs / "trend_p.tif")
    q, _ = read_raster(outputs / "trend_q.tif")
    n, _ = read_raster(outputs / "trend_n.tif")
    return slope, p, q, n, ext


def pixel_center(ext, shape, r, c):
    """Coordenadas (este, norte) del centro del pixel, en la proyeccion del raster."""
    left, right, bottom, top = ext
    return (left + (c + 0.5) * (right - left) / shape[1],
            top - (r + 0.5) * (top - bottom) / shape[0])


def selected_pixels(outputs, mode="auto"):
    slope, p, q, n, ext = _load_maps(outputs)
    rows = []
    for cls, (r, c) in pick_pixels(slope, q, n, mode).items():
        x, y = pixel_center(ext, slope.shape, r, c)
        rows.append({"clase": cls, "fila": r, "columna": c, "este_m": x, "norte_m": y,
                     "pendiente_Ian": float(slope[r, c]), "p_Ian": float(p[r, c]),
                     "q_Ian": float(q[r, c]), "n_años": int(n[r, c])})
    return pd.DataFrame(rows)


def compare_pixel(cls, r, c, dates, values, slope, p, tol=TOL_SLOPE):
    ys, ms = annual_means(dates, values)
    res = regress(ys, ms)
    if res is None:
        return {"clase": cls, "fila": r, "columna": c, "años": len(ys),
                "nota": f"menos de {MIN_YEARS} años válidos"}
    ds = abs(res["slope"] - slope[r, c])
    return {"clase": cls, "fila": r, "columna": c, "años": res["n_years"],
            "pendiente_linregress": res["slope"], "pendiente_Ian": float(slope[r, c]),
            "dif_pendiente": ds, "p_linregress": res["p"], "p_Ian": float(p[r, c]),
            "tolerancia": tol, "dentro_de_tolerancia": bool(ds < tol)}


def check_pixels(outputs, manifest, root, tol=TOL_SLOPE, mode="auto"):
    """Variante (a): lee los TIFF mensuales."""
    slope, p, q, n, _ = _load_maps(outputs)
    picks = pick_pixels(slope, q, n, mode)
    df = pd.read_csv(manifest).sort_values("date")
    dates = df["date"].tolist()
    stack = np.stack([read_raster(Path(root) / rel)[0] for rel in df["path"]])  # [T,H,W]
    return pd.DataFrame([compare_pixel(cls, r, c, dates, stack[:, r, c], slope, p, tol)
                         for cls, (r, c) in picks.items()])


def check_pixels_csv(outputs, pixel_csv, tol=TOL_SLOPE, mode="auto"):
    """Variante (b): CSV largo date,row,col,ndvi (vacio/NaN = faltante)."""
    slope, p, q, n, _ = _load_maps(outputs)
    classes = {v: k for k, v in pick_pixels(slope, q, n, mode).items()}
    df = pd.read_csv(pixel_csv)
    rows = []
    for (r, c), g in df.groupby(["row", "col"]):
        g = g.sort_values("date")
        cls = classes.get((int(r), int(c)), "(píxel no elegido por la regla)")
        rows.append(compare_pixel(cls, int(r), int(c), g["date"].tolist(),
                                  pd.to_numeric(g["ndvi"], errors="coerce").to_numpy(), slope, p, tol))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outputs", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--root", default=".")
    ap.add_argument("--pixel-csv", default=None, help="CSV date,row,col,ndvi de los píxeles elegidos")
    ap.add_argument("--tol", type=float, default=TOL_SLOPE, help="tolerancia de pendiente (LST: 1e-5)")
    ap.add_argument("--pick-mode", default="auto", choices=["auto", "sig", "nosig"],
                    help="nosig: negativa/positiva/cercana a cero, sin etiquetar significancia")
    a = ap.parse_args()
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)

    A = check_outputs(a.outputs)
    A.to_csv(dest / "validation_outputs.csv", index=False)
    print(A.to_string(index=False))
    print(f"\nParte A: {int(A['ok'].sum())}/{len(A)} comprobaciones correctas")

    S = selected_pixels(a.outputs, a.pick_mode)
    S.to_csv(dest / "pixels_selected.csv", index=False)
    print("\nPíxeles elegidos (pedir a Ian sus 300 valores mensuales, formato date,row,col,ndvi):")
    print(S.to_string(index=False))

    B = None
    if a.pixel_csv and Path(a.pixel_csv).exists():
        B = check_pixels_csv(a.outputs, a.pixel_csv, a.tol, a.pick_mode)
    elif a.manifest and Path(a.manifest).exists():
        B = check_pixels(a.outputs, a.manifest, a.root, a.tol, a.pick_mode)
    if B is not None:
        B.to_csv(dest / "validation_pixels.csv", index=False)
        print("\n" + B.to_string(index=False))
    else:
        print("\nParte B omitida: falta --pixel-csv o --manifest con los TIFF mensuales.")


if __name__ == "__main__":
    main()
