"""Copy exact observed NPZ members to an NPY directory without loading X in RAM."""
import argparse
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.catalog import CubeReader, DatasetRegistry
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); reader = CubeReader(a.dataset)
    a.output.mkdir(parents=True, exist_ok=False); folder = a.output/'cube_arrays'; folder.mkdir()
    if reader.format != 'npz': raise ValueError('This converter expects an existing NPZ')
    for name, value in reader.arrays.items(): shutil.copyfile(Path(value.filename), folder/f'{name}.npy')
    metadata = dict(reader.metadata); metadata['storage'] = {'format': 'npy', 'path': 'cube_arrays'}
    (a.output/'cube_metadata.json').write_text(json.dumps(metadata, indent=2))
    print('Exact arrays copied; original observations unchanged:', a.output)
