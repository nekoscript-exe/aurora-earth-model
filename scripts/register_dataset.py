"""Register an observed dataset via configuration, without changing source code or data."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.catalog import CubeReader, variable_spec
from aurora.jobs import atomic_json, fingerprint
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True); p.add_argument('--id', required=True)
    p.add_argument('--region', required=True); p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--priority', type=int, default=0, help='Explicit selection preference within a region/variable')
    p.add_argument('--validate-all', action='store_true', help='Check all observed values in bounded windows')
    a = p.parse_args()
    reader = CubeReader(a.dataset)
    if reader.metadata.get('dataset') != 'satellite': raise ValueError('Only observed satellite products can enter the production registry')
    spec = variable_spec(reader.metadata)
    if [str(c).lower() for c in reader.arrays['channels'][:]] != [reader.metadata['variable'].lower()]: raise ValueError('Channel mismatch')
    if a.validate_all:
        import numpy as np
        for key, block in reader.blocks(months=12, rows=64, cols=64):
            if np.any((block < spec.minimum-.0001) | (block > spec.maximum+.0001)): raise ValueError(f'Physical range violation at {key}')
    config = a.root/'config/datasets.json'; config.parent.mkdir(parents=True, exist_ok=True)
    content = json.loads(config.read_text()) if config.exists() else {'datasets': []}
    if any(entry['id'] == a.id for entry in content['datasets']): raise ValueError('Registration id already exists')
    dataset_path = a.dataset.resolve()
    root_path = a.root.resolve()
    identity = fingerprint(dataset_path)

    if dataset_path.is_relative_to(root_path):
        stored_path = dataset_path.relative_to(root_path).as_posix()
        identity['directory'] = stored_path
    else:
        stored_path = str(dataset_path)

    content['datasets'].append({'id': a.id, 'region_id': a.region, 'priority': a.priority, 'path': stored_path,
        'input': identity, 'validation': 'all physical values checked' if a.validate_all else 'headers, masks, identity and calendar',
        'coverage_validation': 'no national/global completeness claim; use supplied footprint and coverage'})
    atomic_json(config, content); reader.close()
    print(f'Registered {a.id}; refresh the dataset catalog in the desktop application.')
