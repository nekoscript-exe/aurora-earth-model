"""Discover trained AND held-out-evaluated predictive runs, without extrapolating coverage."""
import hashlib
import json
import numpy as np
from pathlib import Path
from aurora.jobs import fingerprint


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


class ModelRegistry:
    def __init__(self, root, datasets):
        self.models = []; self.errors = {}
        root = Path(root)
        preservation_path = root/'docs/evidence/aurora5/ndvi_preservation.json'
        preserved = json.loads(preservation_path.read_text()) if preservation_path.exists() else {}
        artifact_path = root/'docs/evidence/aurora5/artifact_manifest.json'
        audit = json.loads(artifact_path.read_text()).get('files', {}) if artifact_path.exists() else {}
        paths = set((root/'outputs').glob('*/final_benchmark.json'))
        paths.update((root/'outputs/aurora5').glob('*/final_benchmark.json'))
        config = root/'config/datasets.json'
        if config.exists():
            for location in json.loads(config.read_text()).get('model_roots', []): paths.update((root/location).glob('*/final_benchmark.json'))
        for benchmark in sorted(paths):
            folder = benchmark.parent
            try:
                result = json.loads(benchmark.read_text()); metrics_path = folder/'metrics.json'
                report = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
                if not all(name in result['results'] for name in ('xgboost', 'convlstm')): continue
                period = result['period']
                if any(not np.isfinite(result['results'][name][metric]) or result['results'][name][metric] < 0
                       for name in ('xgboost', 'convlstm') for metric in ('mae', 'rmse')): continue
                if len({r['observations'] for r in result['results'].values()}) != 1: continue
                if not len(period) == 2 or any(result['results'][name]['observations'] <= 0 for name in ('xgboost', 'convlstm')): continue
                if report and 'test' not in report.get('evaluations', {}): continue
                if not report and result.get('evaluation') != 'held_out_test': continue
                weights = [folder/'xgboost/model.ubj', folder/'convlstm/best_model.pt']
                if not all(path.exists() for path in weights): continue
                for record in datasets.records:
                    # Hashing runs in a background catalog refresh; source size does not affect UI responsiveness.
                    source = record.directory/'cube.npz'
                    if not source.exists(): continue  # A trained run must explicitly bind to its input format.
                    expected = report.get('cube_sha256')
                    legacy = False
                    if not expected:
                        if not result.get('cube'): continue
                        if (root/result['cube']).resolve() != source.resolve(): continue
                        expected = audit.get(str(source.relative_to(root)), {}).get('sha256')
                        legacy = True
                        if not expected or not all(preserved.get(str(path.relative_to(root))) == sha(path) for path in [benchmark]+weights): continue
                    elif record.variable != report.get('variable'): continue
                    if expected != sha(source): continue
                    if report:
                        if report.get('unit') != record.metadata['unit']: continue
                        digests = report.get('model_sha256', {})
                        if not all((digests.get(str(path.relative_to(folder))) or audit.get(str(path.relative_to(root)), {}).get('sha256')) == sha(path)
                                   for path in weights): continue
                    self.models.append({'region': record.region, 'variable': record.variable, 'directory': folder,
                        'source': fingerprint(record.directory), 'unit': record.metadata['unit'],
                        'legacy': legacy, 'period': period, 'benchmark': result, 'artifacts': artifact_stamp(folder)})
            except (OSError, ValueError, KeyError, TypeError) as exc: self.errors[str(folder)] = str(exc)

    def find(self, region, variable):
        for model in self.models:
            if model['region'] == region and model['variable'] == variable:
                if fingerprint(model['source']['directory'])['fingerprint'] != model['source']['fingerprint']: continue
                if artifact_stamp(model['directory']) != model['artifacts']: continue
                return model
        raise FileNotFoundError('No current trained and held-out-evaluated models for this region/variable')


def artifact_stamp(folder):
    paths = [p for pattern in ('*.json', 'xgboost/*', 'convlstm/*', 'forecast/*/*.json', 'forecast/*/*.tif')
             for p in Path(folder).glob(pattern) if p.is_file()]
    digest = hashlib.sha256()
    for path in sorted(paths):
        stat = path.stat(); digest.update(f'{path}:{stat.st_size}:{stat.st_mtime_ns}'.encode())
    return digest.hexdigest()
