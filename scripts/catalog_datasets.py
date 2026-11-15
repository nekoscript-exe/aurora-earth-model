"""Report only available observed datasets; planned regions have no data entries."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))
from aurora.catalog import DatasetRegistry
if __name__ == '__main__':
    registry = DatasetRegistry(ROOT)
    print(json.dumps({'datasets': [r.summary() for r in registry.records], 'errors': registry.errors}, indent=2))
