"""AURORA - sensibilidad de la serie regional (Sofia, S5).

Uso: python scripts/sensitivity_regional.py --monthly outputs/monthly_series.csv --dest docs/evidence/science
Columnas esperadas: date, mean, coverage. Reproduce la tendencia regional OLS variando:
  (a) el umbral de cobertura mensual (50/60/70/80/90 %), y
  (b) soporte comun: solo los meses del calendario que superan el umbral en TODOS los años.
Reporta todo, sin escoger el resultado mas favorable.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

MIN_MONTHS, MIN_YEARS = 9, 15


def regional_trend(df, thr, months=None):
    d = df[df["coverage"] >= thr]
    if months is not None:
        d = d[d["month"].isin(months)]
    g = d.groupby("year")["mean"].agg(["mean", "count"])
    g = g[g["count"] >= MIN_MONTHS] if months is None else g[g["count"] >= len(months)]
    if len(g) < MIN_YEARS:
        return None
    r = stats.linregress(g.index.values, g["mean"].values)
    h = stats.t.ppf(0.975, len(g) - 2) * r.stderr
    return {"años": len(g), "pendiente": r.slope, "p": r.pvalue, "R2": r.rvalue**2,
            "IC95_inf": r.slope - h, "IC95_sup": r.slope + h}


def run(monthly):
    df = pd.read_csv(monthly)
    df["year"] = df["date"].str[:4].astype(int)
    df["month"] = df["date"].str[5:7].astype(int)
    rows = []
    for thr in (0.5, 0.6, 0.7, 0.8, 0.9):
        r = regional_trend(df, thr)
        rows.append({"variante": f"cobertura ≥ {int(thr*100)} %", **(r or {"años": 0})})
    # soporte comun: meses del calendario que pasan el umbral en todos los años
    for thr in (0.5, 0.7):
        ok = df.groupby("month")["coverage"].min()
        months = sorted(ok[ok >= thr].index)
        r = regional_trend(df, 0.0, months) if months else None
        rows.append({"variante": f"mismos meses (cobertura ≥ {int(thr*100)} % en todos los años): {months}",
                     **(r or {"años": 0})})
    cov = df.groupby("month")["coverage"].agg(["min", "mean"]).round(3)
    low = df[df["coverage"] < 0.7].groupby("month").size().rename("meses_<70%")
    return pd.DataFrame(rows), cov.join(low).fillna(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--monthly", required=True)
    ap.add_argument("--dest", required=True)
    a = ap.parse_args()
    t, cov = run(a.monthly)
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    t.to_csv(dest / "sensitivity_regional.csv", index=False)
    cov.to_csv(dest / "coverage_by_calendar_month.csv")
    pd.set_option("display.width", 200, "display.max_colwidth", 90)
    print(t.to_string(index=False)); print(); print(cov.to_string())


if __name__ == "__main__":
    main()
