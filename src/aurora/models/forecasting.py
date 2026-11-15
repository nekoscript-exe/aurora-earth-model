"""Multivariable one-month forecasting. Legacy NDVI artifacts remain untouched."""
import hashlib
import json
import random
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
import xgboost as xgb
from torch.utils.data import DataLoader

from aurora.geospatial import load_observations, export_raster
from aurora.models.baseline import temporal_split, fit_climatology, predict_baselines, regression_metrics
from aurora.models.features import monthly_features, build_tabular_dataset, FEATURE_NAMES
from aurora.models.dataset import SatellitePatchDataset
from aurora.models.convlstm import AuroraConvLSTM


def training_normalization(X, indices):
    values = X[indices]
    values = values[np.isfinite(values)].astype('float64')
    if not values.size:
        raise ValueError('Empty training observations')
    return {'mean': float(values.mean()), 'std': max(float(values.std()), 1e-6)}


def common_mask(actual, predictions, history_eligible):
    mask = np.isfinite(actual) & history_eligible
    for value in predictions.values():
        mask &= np.isfinite(value)
    if not mask.any():
        raise ValueError('No common observed targets')
    return mask


def neural_predictions(model, X, indices, device, patch_size=32, batch_size=16):
    """Inference never requires or manufactures target observations."""
    h, w = X.shape[1:3]
    output = np.full((len(indices), h, w, 1), np.nan, dtype='float32')
    model.eval()
    tensors, locations = [], []
    def flush():
        if not tensors:
            return
        with torch.inference_mode():
            result = model(torch.from_numpy(np.stack(tensors)).to(device)).float().cpu().numpy()
        for values, (pos, y, x, hh, ww) in zip(result, locations):
            output[pos, y:y+hh, x:x+ww, 0] = values[0, :hh, :ww]
        tensors.clear(); locations.clear()
    for pos, t in enumerate(indices):
        if t < 12 or t > len(X):
            raise ValueError('Need preceding 12 observed calendar months')
        for y in range(0, h, patch_size):
            for x in range(0, w, patch_size):
                history = X[t-12:t, y:y+patch_size, x:x+patch_size, 0]
                if not np.isfinite(history).any():
                    continue
                _, hh, ww = history.shape
                inputs = np.zeros((12, 2, patch_size, patch_size), dtype='float32')
                inputs[:, 0, :hh, :ww] = np.nan_to_num(history, nan=0.0)
                inputs[:, 1, :hh, :ww] = np.isfinite(history)
                tensors.append(inputs); locations.append((pos, y, x, hh, ww))
                if len(tensors) == batch_size:
                    flush()
    flush()
    return output


def run_forecast(directory, output, variable='lst', epochs=12, patience=3,
                 trees=500, batch_size=16, patch_size=32, min_history=9):
    # A new run directory is required: historical products can never be overwritten.
    if epochs < 1 or patience < 1 or trees < 1 or not 1 <= min_history <= 12:
        raise ValueError('Invalid training configuration')
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    start = perf_counter()
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    torch.set_num_threads(min(8, torch.get_num_threads()))
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cuda':
        torch.cuda.manual_seed_all(42); torch.cuda.reset_peak_memory_stats()
    values, dates, region, metadata, _ = load_observations(Path(directory), variable)
    dates = dates.astype('datetime64[M]'); X = values[..., None]
    if not np.all(np.diff(dates).astype(int) == 1):
        raise ValueError('Consecutive monthly calendar required')
    split = temporal_split(dates)
    if not all(len(indices) for indices in split.values()):
        raise ValueError('Required train/validation/test periods unavailable')
    norm = training_normalization(X, split['train'])
    normalized = ((X-norm['mean'])/norm['std']).astype('float32')
    climate = fit_climatology(X, dates, split['train'])
    np.savez_compressed(output/'climatology_model.npz', climatology=climate, training_dates=dates[split['train']].astype(str))
    eligible = {name: np.stack([(np.isfinite(X[t-12:t]).sum(axis=0) >= min_history)
                               & region[..., None] for t in indices]) for name, indices in split.items()}
    validation_baselines = predict_baselines(X, dates, split['validation'], climate)
    validation_mask = common_mask(X[split['validation']], validation_baselines, eligible['validation'])
    train_mask = eligible['train'] & np.isfinite(X[split['train']])
    print('Building tabular features', flush=True)
    F, y = build_tabular_dataset(X, dates, split['train'], train_mask)
    Fv, yv = build_tabular_dataset(X, dates, split['validation'], validation_mask)
    model = xgb.XGBRegressor(objective='reg:squarederror', eval_metric='rmse',
                            n_estimators=trees, max_depth=6, learning_rate=.05,
                            subsample=.85, colsample_bytree=.9, tree_method='hist',
                            device=str(device), early_stopping_rounds=25, random_state=42)
    t = perf_counter(); model.fit(F, y, eval_set=[(Fv, yv)], verbose=50)
    xgb_seconds = perf_counter()-t
    (output/'xgboost').mkdir(); model.save_model(output/'xgboost/model.ubj')
    actual_xgb_device = json.loads(model.get_booster().save_config())['learner']['generic_param']['device']
    importance = dict(zip(FEATURE_NAMES, map(float, model.feature_importances_)))
    del F, y, Fv, yv
    # CPU prediction avoids host/device mismatch copies for small per-frame maps.
    model.set_params(device='cpu')
    train_data = SatellitePatchDataset(normalized, split['train'], patch_size, masks=train_mask)
    val_data = SatellitePatchDataset(normalized, split['validation'], patch_size, masks=validation_mask)
    loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False, num_workers=0)
    deep = AuroraConvLSTM(output_activation='linear').to(device)
    optimizer = torch.optim.Adam(deep.parameters(), lr=.001)
    # Existing masked trainer reused; metrics are transformed back to physical units.
    import importlib.util
    spec = importlib.util.spec_from_file_location('aurora_legacy_trainer', Path(__file__).resolve().parents[3]/'scripts/train_deep.py')
    if spec is None or spec.loader is None:
        raise ImportError('Unable to load AURORA trainer')
    trainer = importlib.util.module_from_spec(spec); spec.loader.exec_module(trainer)
    amp = device.type == 'cuda' and torch.cuda.is_bf16_supported()
    history, best, stale, best_epoch = [], float('inf'), 0, 0
    (output/'convlstm').mkdir(); t = perf_counter()
    for epoch in range(1, epochs+1):
        tr = trainer.run_epoch(deep, loader, device, amp, optimizer)
        va = trainer.run_epoch(deep, val_loader, device, amp)
        for metrics in (tr, va):
            metrics['mae'] *= norm['std']; metrics['rmse'] *= norm['std']
        history.append({'epoch': epoch, 'train': tr, 'validation': va})
        print(f'Epoch {epoch}: train RMSE={tr["rmse"]:.4f}; validation={va["rmse"]:.4f}', flush=True)
        if va['rmse'] < best:
            best, stale, best_epoch = va['rmse'], 0, epoch
            torch.save(deep.state_dict(), output/'convlstm/best_model.pt')
        else:
            stale += 1
        if stale >= patience:
            break
    deep_seconds = perf_counter()-t
    deep.load_state_dict(torch.load(output/'convlstm/best_model.pt', map_location=device, weights_only=True))
    def predictions(indices):
        result = predict_baselines(X, dates, indices, climate)
        maps = []
        for index in indices:
            features = monthly_features(X, dates, index)
            ok = region & (features[..., 8] > 0)
            prediction = np.full(region.shape, np.nan, dtype='float32')
            prediction[ok] = model.predict(features[ok]); maps.append(prediction)
        result['xgboost'] = np.stack(maps)[..., None]
        result['convlstm'] = neural_predictions(deep, normalized, indices, device, patch_size, batch_size)*norm['std']+norm['mean']
        return result
    evaluations = {}
    for name in ('validation', 'test'):
        idx = split[name]; predicted = predictions(idx)
        mask = common_mask(X[idx], predicted, eligible[name])
        results = {engine: regression_metrics(X[idx], prediction, mask) for engine, prediction in predicted.items()}
        evaluations[name] = {'period': [str(dates[idx[0]]), str(dates[idx[-1]])],
                             'comparable_observations': int(mask.sum()),
                             'observed_targets': int(np.isfinite(X[idx]).sum()), 'results': results}
        np.savez_compressed(output/f'{name}_predictions.npz', actual=X[idx], mask=mask,
                            dates=dates[idx].astype(str), **predicted)
    # January 2026 (or the next month of an explicitly different input calendar).
    future = dates[-1]+np.timedelta64(1, 'M')
    calendar = np.r_[dates, future]
    features = monthly_features(X, calendar, len(X))
    count = np.isfinite(X[-12:, ..., 0]).sum(axis=0)
    ok = region & (count >= min_history)
    future_predictions = {'persistence': X[-1, ..., 0], 'seasonal': X[-12, ..., 0],
                          'climatology': climate[int(future.astype(int)) % 12, ..., 0]}
    p = np.full(region.shape, np.nan, dtype='float32'); p[ok] = model.predict(features[ok])
    future_predictions['xgboost'] = p
    future_predictions['convlstm'] = neural_predictions(deep, normalized, [len(X)], device, patch_size, batch_size)[0, ..., 0]*norm['std']+norm['mean']
    unit = metadata['unit']
    for engine, prediction in future_predictions.items():
        prediction = np.where(ok, prediction, np.nan)
        folder = output/'forecast'/engine; folder.mkdir(parents=True)
        np.savez_compressed(folder/'forecast.npz', prediction=prediction, valid=np.isfinite(prediction), date=str(future), coverage=count/12)
        export_raster(folder/f'forecast_{variable}.tif', prediction, metadata['grid'], unit)
        report = {'forecast_date': str(future), 'predicted_pixels': int(np.isfinite(prediction).sum()),
                  'prediction_coverage': float(np.isfinite(prediction).sum()/region.sum()),
                  f'mean_{variable}': float(np.nanmean(prediction)), 'unit': unit,
                  'interpretation': 'retrospective one-month model estimate, no target observation available'}
        (folder/'forecast_metadata.json').write_text(json.dumps(report, indent=2))
    report = {'variable': variable, 'unit': unit, 'mae_rmse_unit': unit,
              'cube_sha256': hashlib.sha256((Path(directory)/'cube.npz').read_bytes()).hexdigest(),
              'splits': {name: [str(dates[idx[0]]), str(dates[idx[-1]])] for name, idx in split.items()},
              'normalization_train_only': norm, 'minimum_history': min_history,
              'output_activation': 'linear', 'history_months': 12, 'horizon_months': 1,
              'evaluation_protocol': 'rolling one-month ahead; observed preceding months',
              'model_sha256': {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (output/'xgboost/model.ubj', output/'convlstm/best_model.pt')},
              'seed': 42, 'device': str(device), 'xgboost_device': actual_xgb_device,
              'gpu': torch.cuda.get_device_name(0) if device.type == 'cuda' else None,
              'torch_version': str(torch.__version__), 'xgboost_version': xgb.__version__,
              'best_epoch': best_epoch, 'xgboost_best_iteration': int(model.best_iteration),
              'configuration': {'epochs': epochs, 'patience': patience, 'trees': trees, 'patch_size': patch_size, 'batch_size': batch_size},
              'xgboost_seconds': xgb_seconds, 'convlstm_seconds': deep_seconds,
              'total_seconds': perf_counter()-start,
              'peak_vram_mib': torch.cuda.max_memory_allocated()/1024**2 if device.type == 'cuda' else None,
              'evaluations': evaluations, 'forecast_date': str(future)}
    (output/'metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    (output/'normalization.json').write_text(json.dumps(norm, indent=2))
    (output/'final_benchmark.json').write_text(json.dumps(evaluations['test'], indent=2))
    (output/'convlstm/metrics.json').write_text(json.dumps({'history': history, 'best_epoch': best_epoch,
        'seconds': deep_seconds, 'peak_vram_mib': report['peak_vram_mib']}, indent=2))
    (output/'xgboost/metrics.json').write_text(json.dumps({'feature_importance': importance}, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    return report


def forecast_saved(directory, run, output):
    """Reproduce next-month estimates from exported weights without retraining."""
    run, output = Path(run), Path(output)
    report = json.loads((run/'metrics.json').read_text())
    variable = report['variable']; norm = report['normalization_train_only']
    if hashlib.sha256((Path(directory)/'cube.npz').read_bytes()).hexdigest() != report['cube_sha256']:
        raise ValueError('Reproduction requires the exact training input cube')
    values, dates, region, metadata, _ = load_observations(Path(directory), variable)
    X = values[..., None]; dates = dates.astype('datetime64[M]')
    with np.load(run/'climatology_model.npz', allow_pickle=False) as climate_model:
        climate = climate_model['climatology']
    model = xgb.XGBRegressor(); model.load_model(run/'xgboost/model.ubj'); model.set_params(device='cpu')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    deep = AuroraConvLSTM('linear').to(device)
    deep.load_state_dict(torch.load(run/'convlstm/best_model.pt', map_location=device, weights_only=True))
    normalized = ((X-norm['mean'])/norm['std']).astype('float32')
    future = dates[-1]+np.timedelta64(1, 'M')
    count = np.isfinite(values[-12:]).sum(axis=0)
    eligible = region & (count >= report['minimum_history'])
    features = monthly_features(X, np.r_[dates, future], len(X))
    prediction = np.full(region.shape, np.nan, dtype='float32')
    prediction[eligible] = model.predict(features[eligible])
    config = report['configuration']
    results = {'xgboost': prediction,
               'convlstm': neural_predictions(deep, normalized, [len(X)], device, config['patch_size'], config['batch_size'])[0, ..., 0]*norm['std']+norm['mean'],
               'persistence': values[-1], 'seasonal': values[-12],
               'climatology': climate[int(future.astype(int)) % 12, ..., 0]}
    output.mkdir(parents=True, exist_ok=False)
    for engine, values in results.items():
        prediction = np.where(eligible, values, np.nan)
        export_raster(output/f'{engine}_{variable}.tif', prediction, metadata['grid'], metadata['unit'])
        np.savez_compressed(output/f'{engine}.npz', prediction=prediction, date=str(future))
    (output/'metadata.json').write_text(json.dumps({'source_run': str(run), 'date': str(future),
        'variable': variable, 'unit': metadata['unit'], 'product': 'retrospective model estimate'}, indent=2))
