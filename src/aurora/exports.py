"""Scientific export bundles: portable outputs and atomic completion metadata."""
from aurora.portability import load_manifest
import json
import os
from pathlib import Path
from aurora.jobs import fresh, atomic_json, Cancelled


def export_bundle(result, output, progress=lambda *args: None):
    result, output = Path(result), Path(output)
    manifest = load_manifest(result/'manifest.json')
    if manifest.get('status') != 'complete' or not fresh(manifest): raise ValueError('Only complete, fresh scientific results can be exported')
    if output.with_suffix('.cancel').exists(): raise Cancelled('Export cancelled before start')
    output.mkdir(parents=True, exist_ok=False)
    files = [p for pattern in ('*.csv', '*.json', '*.tif', '*.png') for p in result.glob(pattern) if p.name != 'manifest.json']
    total = sum(p.stat().st_size for p in files); done = 0
    try:
        for source in files:
            with source.open('rb') as src, (output/(source.name+'.partial')).open('wb') as dst:
                while True:
                    if (output/'CANCEL').exists() or output.with_suffix('.cancel').exists(): raise Cancelled('Export cancelled')
                    block = src.read(1024*1024)
                    if not block: break
                    dst.write(block); done += len(block); progress(done, total, 'export-bundle')
            os.replace(output/(source.name+'.partial'), output/source.name)
        if not fresh(manifest): raise RuntimeError('Source changed during export')
        atomic_json(output/'manifest.json', dict(manifest, exported_from=str(result.resolve())))
        atomic_json(output/'export_status.json', {'status': 'complete', 'files': [p.name for p in files]+['manifest.json']})
    except BaseException as exc:
        atomic_json(output/'export_status.json', {'status': 'cancelled' if isinstance(exc, Cancelled) else 'failed', 'error': str(exc)})
        raise
