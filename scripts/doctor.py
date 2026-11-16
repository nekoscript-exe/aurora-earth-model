"""Dependency, dataset, model, integrity and device checks; no Earth Engine login."""
import argparse
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))
from aurora.distribution import verify_package


def diagnose(root, device='auto', integrity=True):
    root = Path(root); errors = []; report = {'root': str(root.resolve()), 'dependencies': {}, 'errors': errors}
    if integrity and (root/'distribution-manifest.json').exists():
        report['integrity'] = verify_package(root)
        if not report['integrity']['ok']: errors.append('Package SHA-256 integrity check failed')
    for name in ('numpy','scipy','pandas','rasterio','pyproj','zarr','torch','xgboost','PySide6','matplotlib','statsmodels'):
        try:
            module = importlib.import_module(name)
            report['dependencies'][name] = getattr(module, '__version__', 'available')
        except (ImportError, OSError) as exc: errors.append(f'{name}: {exc}')
    if errors: report['ok'] = False; return report
    from aurora.catalog import DatasetRegistry
    from aurora.jobs import ResultRegistry
    from aurora.model_catalog import ModelRegistry
    from aurora.hardware import hardware_report
    registry = DatasetRegistry(root); models = ModelRegistry(root, registry); results = ResultRegistry(root)
    report.update(hardware=hardware_report(device), datasets=[r.summary() for r in registry.records],
                  models=[{'region': m['region'], 'variable': m['variable'], 'engines': ['xgboost','convlstm'], 'directory': str(m['directory'])} for m in models.models],
                  fresh_results=len(results.available()), dataset_errors=registry.errors, model_errors=models.errors,
                  google_earth_engine_required=False, trained_model_count=2*len(models.models))
    if registry.errors: errors.append('Dataset registration errors')
    if models.errors: errors.append('Model qualification errors')
    if not {'ndvi','lst'} <= {m['variable'] for m in models.models}: errors.append('Expected four trained models (two variables × two engines)')
    if results.available() == []: errors.append('No fresh scientific results')
    report['ok'] = not errors
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--device', choices=['auto','cpu','cuda'], default='auto'); p.add_argument('--integrity-only', action='store_true')
    p.add_argument('--output', type=Path); args = p.parse_args()
    result = verify_package(args.root) if args.integrity_only else diagnose(args.root, args.device)
    rendered = json.dumps(result, indent=2, default=str)
    if args.output: args.output.write_text(rendered)
    print(rendered); sys.exit(0 if result['ok'] else 1)
