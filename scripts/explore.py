"""AURORA scientific investigation CLI, backed by bounded native-grid jobs."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))
from aurora.catalog import DatasetRegistry, variable_spec
from aurora.temporal import parse_month as monthly, select_interval
from aurora.block_engine import run_statistics
from aurora.model_catalog import ModelRegistry


def parse_month(value):
    try: return monthly(value)
    except ValueError as exc: raise argparse.ArgumentTypeError(str(exc)) from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variable', default='ndvi'); parser.add_argument('--region', default='queretaro')
    parser.add_argument('--start', type=parse_month); parser.add_argument('--end', type=parse_month)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--memory-mib', type=int, default=64); parser.add_argument('--block-size', type=int, default=32)
    args = parser.parse_args(); registry = DatasetRegistry(ROOT)
    try: record = registry.find(args.region, args.variable.lower())
    except FileNotFoundError as exc: parser.error(str(exc))
    spec = variable_spec(record.metadata)
    start, end = str(args.start if args.start is not None else record.dates[0]), str(args.end if args.end is not None else record.dates[-1])
    try: select_interval(record.dates, start, end)
    except ValueError as exc: parser.error(str(exc))
    trained = False
    try: ModelRegistry(ROOT, registry).find(record.region, record.variable); trained = True
    except FileNotFoundError: pass
    report = {'region': record.region, 'dataset': record.identifier, 'variable': record.variable,
              'source': record.metadata['source'], 'unit': spec.unit, 'period': [start, end],
              'dataset_available': True, 'prediction_supported': trained,
              'storage': record.metadata.get('storage', {'format': 'npz', 'path': 'cube.npz'})}
    print(json.dumps(report, indent=2), flush=True)
    if not args.run:
        print('INVESTIGATION CONFIGURATION: READY'); return 0
    output = ROOT/'outputs/global_engine'/f'{record.identifier}_{start}_{end}_{datetime.now():%Y%m%d_%H%M%S_%f}'
    result = run_statistics(record.directory, output, start, end, record.region, args.memory_mib, args.block_size)
    print(json.dumps({'status': 'complete', 'results': str(output), 'eligibility': result['eligibility']}, indent=2))
    return 0


if __name__ == '__main__': sys.exit(main())
