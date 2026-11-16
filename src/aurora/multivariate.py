"""Paired NDVI/LST research; associations never imply causation."""
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from scipy.stats import rankdata, t as student_t
from aurora.geospatial import load_observations
from aurora.models.baseline import fit_climatology
from aurora.temporal import select_interval
from aurora.trend import fdr_correction
from aurora.geospatial import export_raster


def paired_correlation(a, b, minimum=36):
    """Pairwise complete correlation along time; constants remain undefined."""
    valid = np.isfinite(a) & np.isfinite(b)
    n = valid.sum(axis=0)
    x, y = np.where(valid, a, 0).astype('float64'), np.where(valid, b, 0).astype('float64')
    mx = np.divide(x.sum(axis=0), n, out=np.zeros(n.shape), where=n > 0)
    my = np.divide(y.sum(axis=0), n, out=np.zeros(n.shape), where=n > 0)
    dx, dy = np.where(valid, x-mx, 0), np.where(valid, y-my, 0)
    denominator = np.sqrt((dx*dx).sum(axis=0)*(dy*dy).sum(axis=0))
    r = np.divide((dx*dy).sum(axis=0), denominator,
                  out=np.full(n.shape, np.nan), where=(denominator > 1e-12) & (n >= minimum))
    return np.clip(r, -1, 1), n


def lagged_pairs(a, b, lag):
    """Positive lag: NDVI at t paired with LST at t+lag. No gap compression."""
    if abs(lag) >= len(a):
        raise ValueError('Lag exceeds selected interval')
    if lag > 0: return a[:-lag], b[lag:]
    if lag < 0: return a[-lag:], b[:lag]
    return a, b


def correlation_maps(a, b, minimum=36):
    valid = np.isfinite(a) & np.isfinite(b)
    aa, bb = np.where(valid, a, np.nan), np.where(valid, b, np.nan)
    r, n = paired_correlation(aa, bb, minimum)
    rho, _ = paired_correlation(rankdata(aa, axis=0, nan_policy='omit'),
                                 rankdata(bb, axis=0, nan_policy='omit'), minimum)
    # Diagnostic AR(1) effective sample size; not a universal dependence correction.
    rx, _ = paired_correlation(aa[:-1], aa[1:], 12)
    ry, _ = paired_correlation(bb[:-1], bb[1:], 12)
    product = np.clip(rx*ry, -.99, .99)
    effective = np.minimum(n, np.maximum(3, n*(1-product)/(1+product)))
    def pvalue(count):
        statistic = np.abs(r)*np.sqrt(np.maximum(count-2, 0)/np.maximum(1-r*r, 1e-15))
        return np.where(np.isfinite(r) & (count > 2), 2*student_t.sf(statistic, count-2), np.nan)
    return {'pearson': r, 'spearman': rho, 'pairs': n, 'effective_n_ar1': effective,
            'p_iid_diagnostic': pvalue(n), 'p_ar1_diagnostic': pvalue(effective)}


def paired_anomalies(a, b, dates, baseline_start='2002-01', baseline_end='2018-12', minimum=8):
    idx = np.flatnonzero(select_interval(dates, baseline_start, baseline_end))
    valid = np.isfinite(a) & np.isfinite(b)
    aa, bb = np.where(valid, a, np.nan), np.where(valid, b, np.nan)
    climates = [fit_climatology(v[..., None], dates, idx)[..., 0] for v in (aa, bb)]
    months = dates.astype('datetime64[M]').astype(int) % 12
    count = np.stack([valid[idx[months[idx] == m]].sum(axis=0) for m in range(12)])
    eligible = count[months] >= minimum
    return (np.where(eligible, aa-climates[0][months], np.nan),
            np.where(eligible, bb-climates[1][months], np.nan), count)


def regional_series(a, b, region):
    valid = np.isfinite(a) & np.isfinite(b) & region
    count = valid.sum(axis=(1, 2))
    means = [np.divide(np.where(valid, value, 0).sum(axis=(1, 2)), count,
                       out=np.full(len(a), np.nan), where=count > 0) for value in (a, b)]
    return *means, count/max(int(region.sum()), 1)


def scalar_association(a, b):
    r, n = paired_correlation(a, b, 12)
    good = np.isfinite(a) & np.isfinite(b)
    rho, _ = paired_correlation(rankdata(np.where(good, a, np.nan), nan_policy='omit'),
                                 rankdata(np.where(good, b, np.nan), nan_policy='omit'), 12)
    return {'pearson': float(r) if np.isfinite(r) else None,
            'spearman': float(rho) if np.isfinite(rho) else None, 'months': int(n)}


def block_bootstrap(a, b, replicates=499, block=12):
    rng = np.random.default_rng(42); estimates = []
    for _ in range(replicates):
        starts = rng.integers(0, len(a), size=int(np.ceil(len(a)/block)))
        idx = ((starts[:, None]+np.arange(block)) % len(a)).ravel()[:len(a)]
        r, _ = paired_correlation(a[idx], b[idx], 12)
        if np.isfinite(r): estimates.append(float(r))
    return np.quantile(estimates, [.025, .975]).tolist() if estimates else None


def run_analysis(ndvi_directory, lst_directory, output, start='2001-01', end='2025-12', minimum=36):
    begun = perf_counter(); output = Path(output); output.mkdir(parents=True, exist_ok=False)
    a, dates, region_a, meta_a, ga = load_observations(Path(ndvi_directory), 'ndvi')
    b, dates_b, region_b, _, gb = load_observations(Path(lst_directory), 'lst')
    dates, dates_b = dates.astype('datetime64[M]'), dates_b.astype('datetime64[M]')
    if ga != gb or not np.array_equal(dates, dates_b):
        raise ValueError('Cubes must share CRS, affine, shape and calendar; no implicit resampling')
    if not np.all(np.diff(dates).astype(int) == 1):
        raise ValueError('Consecutive months required for lag analysis')
    region = region_a & region_b
    if not region.any(): raise ValueError('No common region')
    valid = np.isfinite(a) & np.isfinite(b) & region
    a, b = np.where(valid, a, np.nan), np.where(valid, b, np.nan)
    an, bn, climate_count = paired_anomalies(a, b, dates)
    selected = select_interval(dates, start, end)
    a, b, an, bn, dates = a[selected], b[selected], an[selected], bn[selected], dates[selected]
    lags = [lag for lag in (-12, -6, -3, -1, 0, 1, 3, 6, 12) if len(a)-abs(lag) >= minimum]
    if not lags: raise ValueError(f'At least {minimum} months required for correlation maps')
    maps = {}; families = []
    for name, aa, bb in [('raw', a, b), ('anomaly', an, bn)]:
        for lag in lags:
            result = correlation_maps(*lagged_pairs(aa, bb, lag), minimum)
            maps[f'{name}_{lag}'] = result; families.append(result['p_ar1_diagnostic'])
    # One BH family covers BOTH raw/anomaly maps and ALL selected lags.
    q, _ = fdr_correction(np.stack(families))
    arrays = {}
    for i, (key, result) in enumerate(maps.items()):
        result['q_ar1_diagnostic'] = q[i]
        arrays.update({f'{key}_{field}': value for field, value in result.items()})
    raw_x, raw_y, coverage = regional_series(a, b, region)
    anomaly_x, anomaly_y, anomaly_coverage = regional_series(an, bn, region)
    sensitivity = {}
    for threshold in (.5, .7, .9, .95):
        ok = coverage >= threshold; ok_an = anomaly_coverage >= threshold
        sensitivity[str(threshold)] = {'raw': scalar_association(np.where(ok, raw_x, np.nan), np.where(ok, raw_y, np.nan)),
                                      'anomaly': scalar_association(np.where(ok_an, anomaly_x, np.nan), np.where(ok_an, anomaly_y, np.nan))}
    lag_profiles = []
    for lag in range(-12, 13):
        if len(a)-abs(lag) < 12: continue
        # Coverage selection occurs before lag pairing, so both dates qualify.
        xx, yy = np.where(anomaly_coverage >= .7, anomaly_x, np.nan), np.where(anomaly_coverage >= .7, anomaly_y, np.nan)
        lag_profiles.append({'lag_months': lag, **scalar_association(*lagged_pairs(xx, yy, lag))})
    months = dates.astype(int) % 12
    seasonal_sensitivity = {}
    for name, season in [('DJF', [11, 0, 1]), ('MAM', [2, 3, 4]), ('JJA', [5, 6, 7]), ('SON', [8, 9, 10])]:
        ok = np.isin(months, season) & (anomaly_coverage >= .7)
        seasonal_sensitivity[name] = scalar_association(np.where(ok, anomaly_x, np.nan), np.where(ok, anomaly_y, np.nan))
    leave_month_out = []
    for month in range(12):
        ok = (months != month) & (anomaly_coverage >= .7)
        leave_month_out.append({'excluded_calendar_month': month+1,
            **scalar_association(np.where(ok, anomaly_x, np.nan), np.where(ok, anomaly_y, np.nan))})
    stable_region = region & (np.isfinite(a).mean(axis=0) >= .9)
    sx, sy, sc = regional_series(an, bn, stable_region)
    stable_result = scalar_association(np.where(sc >= .7, sx, np.nan), np.where(sc >= .7, sy, np.nan))
    ok = np.isfinite(anomaly_x) & np.isfinite(anomaly_y) & (anomaly_coverage >= .7)
    detrended = {'pearson': None, 'spearman': None, 'months': int(ok.sum())}
    if ok.sum() >= 12:
        time = np.arange(len(a))[ok]
        design = np.column_stack([np.ones(len(time)), time])
        rx = anomaly_x[ok]-design @ np.linalg.lstsq(design, anomaly_x[ok], rcond=None)[0]
        ry = anomaly_y[ok]-design @ np.linalg.lstsq(design, anomaly_y[ok], rcond=None)[0]
        detrended = scalar_association(rx, ry)
    seasonal_coverage = [{'month': m+1, 'paired_coverage': float(coverage[months == m].mean())
                         if (months == m).any() else None} for m in range(12)]
    np.savez_compressed(output/'analysis.npz', **arrays, dates=dates.astype(str),
                        raw_ndvi=raw_x, raw_lst=raw_y, anomaly_ndvi=anomaly_x, anomaly_lst=anomaly_y,
                        coverage=coverage, anomaly_coverage=anomaly_coverage, climate_count=climate_count)
    for name in ('raw', 'anomaly'):
        for field in ('pearson', 'spearman', 'pairs', 'q_ar1_diagnostic'):
            export_raster(output/f'{name}_{field}.tif', maps[f'{name}_0'][field], meta_a['grid'], 'months' if field == 'pairs' else '1',
                          product='paired-observation statistic; not a raw measurement')
    ok = anomaly_coverage >= .7
    report = {'period': [str(dates[0]), str(dates[-1])], 'alignment': 'exact; no resampling',
              'datasets': {'ndvi': Path(ndvi_directory).name, 'lst': Path(lst_directory).name},
              'common_regional_pixels': int(region.sum()), 'paired_observations': int(np.isfinite(a).sum()),
              'climatology': {'period': ['2002-01', '2018-12'], 'minimum_samples_per_calendar_month': 8,
                              'support': 'coincident valid NDVI and LST only'},
              'minimum_pairs_per_map': minimum, 'map_lags': lags,
              'coverage_sensitivity': sensitivity, 'seasonal_coverage': seasonal_coverage,
              'seasonal_anomaly_sensitivity': seasonal_sensitivity, 'leave_one_month_out': leave_month_out,
              'stable_footprint_sensitivity': {'pixels_with_90pct_pairs': int(stable_region.sum()), **stable_result},
              'detrended_regional_anomaly_sensitivity': detrended,
              'lag_profiles': lag_profiles, 'lag_definition': 'positive: NDVI(t) vs LST(t+lag)',
              'regional_anomaly_pearson_ci95_block12': block_bootstrap(np.where(ok, anomaly_x, np.nan), np.where(ok, anomaly_y, np.nan)),
              'bootstrap_replicates': 499, 'seed': 42,
              'pixel_median_anomaly_r': float(np.nanmedian(maps['anomaly_0']['pearson'])),
              'seconds': perf_counter()-begun,
              'limits': ['Association is not causation.', 'AR1 effective sample sizes and BH q maps are diagnostics, not calibrated spatial-temporal causal inference.',
                         'Lag1 uses consecutive calendar pairs; missing months are never compressed.',
                         'BH family covers raw and anomaly Pearson tests at all map lags; spatial dependence remains. Spearman maps have no significance claims.',
                         'Regional means use changing coincident support; coverage thresholds do not remove composition bias.',
                         'Regional bootstrap resamples paired 12-month circular blocks; stationarity is an approximation.',
                         'Equal pixel weighting suits this projected equal-resolution regional grid, not arbitrary global latitude-longitude grids.']}
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    return report
