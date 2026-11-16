"""Convert real NPZ/NPY observations without changing raw values or masks."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.storage import to_zarr
from aurora.jobs import Cancelled, atomic_json
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    def check():
        if (a.output/'CANCEL').exists(): raise Cancelled('Conversion cancelled; no dataset metadata published')
    try:
        to_zarr(a.dataset, a.output, progress=lambda done, total, phase: print(f'{phase}: {done}/{total}', flush=True), check=check)
        atomic_json(a.output/'conversion_status.json', {'status': 'complete', 'source': str(a.dataset)})
    except BaseException as exc:
        if a.output.exists() and not (a.output/'cube_metadata.json').exists():
            atomic_json(a.output/'conversion_status.json', {'status': 'cancelled' if isinstance(exc, Cancelled) else 'failed', 'error': str(exc)})
        raise
