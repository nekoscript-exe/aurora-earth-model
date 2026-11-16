"""Cooperative jobs, provenance and atomic publication of scientific results."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone


class Cancelled(RuntimeError):
    pass


def atomic_json(path, value):
    path = Path(path); temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False, default=str))
    os.replace(temporary, path)


def fingerprint(directory):
    """Metadata plus storage stat fingerprint; no read of the complete observations."""
    directory = Path(directory).resolve()
    meta = directory/'cube_metadata.json'; m = json.loads(meta.read_text())
    storage = m.get('storage', {'path': 'cube.npz'})
    source = (directory/storage['path']).resolve()
    if not source.is_relative_to(directory): raise ValueError('Storage outside dataset')
    files = [source] if source.is_file() else sorted(p for p in source.rglob('*') if p.is_file())
    digest = hashlib.sha256(meta.read_bytes())
    for file in files:
        stat = file.stat()
        digest.update(f'{file.relative_to(directory)}:{stat.st_size}:{stat.st_mtime_ns}'.encode())
    return {'directory': str(directory), 'fingerprint': digest.hexdigest(), 'scheme': 'metadata-sha256+storage-size-mtime_ns'}


def fresh(manifest):
    try:
        return all(fingerprint(source['directory'])['fingerprint'] == source['fingerprint']
                   for source in manifest['inputs'])
    except (OSError, ValueError, KeyError): return False


class Job:
    def __init__(self, output, inputs, kind, region, parameters, allow_synthetic=False):
        self.output = Path(output); self.output.mkdir(parents=True, exist_ok=False)
        self.cancel_path = self.output/'CANCEL'
        self.manifest = {'schema': 'aurora-scientific-result-v1', 'status': 'running',
                         'created_utc': datetime.now(timezone.utc).isoformat(),
                         'kind': kind, 'region': region, 'parameters': parameters,
                         'observation_kind': 'synthetic_test' if allow_synthetic else 'satellite',
                         'inputs': [fingerprint(p) for p in inputs]}
        self.save()

    def save(self): atomic_json(self.output/'manifest.json', self.manifest)

    def check(self):
        if self.cancel_path.exists() or self.output.with_suffix('.cancel').exists(): raise Cancelled('Cancellation requested; incomplete results are not published')

    def progress(self, done, total, phase):
        self.check()
        print(json.dumps({'event': 'progress', 'done': done, 'total': total, 'phase': phase}), flush=True)

    def finish(self, **data):
        self.check()
        if not fresh(self.manifest): raise RuntimeError('Inputs changed during processing; result not published')
        self.manifest.update(data, status='complete'); self.save()

    def fail(self, exception):
        self.manifest.update(status='cancelled' if isinstance(exception, Cancelled) else 'failed', error=str(exception))
        self.save()


class ResultRegistry:
    def __init__(self, root):
        self.results = []
        root = Path(root)
        roots = [
            'outputs/global_engine',
            'outputs/global_engine/jobs',
            'outputs/aurora5/multivariate',
        ]
        config = root/'config/datasets.json'
        if config.exists(): roots += json.loads(config.read_text()).get('result_roots', [])
        paths = set()
        for location in roots: paths.update((root/location).glob('*/manifest.json'))
        for path in paths:
            try:
                data = json.loads(path.read_text())
                if data.get('schema') != 'aurora-scientific-result-v1' or data.get('observation_kind') != 'satellite': continue
                data = dict(data, directory=path.parent, stale=not fresh(data))
                self.results.append(data)
            except (OSError, ValueError): continue
        self.results.sort(key=lambda r: r.get('created_utc', ''), reverse=True)

    def available(self, region=None, variable=None, kind=None):
        return [r for r in self.results if r['status'] == 'complete' and not r['stale']
                and (region is None or r['region'] == region)
                and (variable is None or r.get('variable') == variable)
                and (kind is None or r['kind'] == kind)]


def request_cancel(output):
    flag = Path(output).with_suffix('.cancel')
    flag.parent.mkdir(parents=True, exist_ok=True); flag.touch()
