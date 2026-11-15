"""Export only a source-qualified, trained and evaluated predictive run."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.catalog import DatasetRegistry
from aurora.model_catalog import ModelRegistry
from aurora.model_exports import export_model_bundle
from aurora.jobs import Cancelled
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1]); p.add_argument('--region', required=True)
    p.add_argument('--variable', required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        model = ModelRegistry(a.root, DatasetRegistry(a.root)).find(a.region, a.variable)
        export_model_bundle(model, a.output)
    except Cancelled: sys.exit(2)
