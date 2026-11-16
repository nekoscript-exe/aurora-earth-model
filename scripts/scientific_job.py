"""Cancelable native-grid scientific jobs; complete manifests publish results."""
import argparse
import json
from pathlib import Path
import signal
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.block_engine import run_statistics
from aurora.jobs import Cancelled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--region'); parser.add_argument('--start'); parser.add_argument('--end')
    parser.add_argument('--memory-mib', type=int, default=64)
    parser.add_argument('--block-size', type=int, default=32)
    parser.add_argument('--allow-synthetic', action='store_true', help='Explicit infrastructure validation only')
    parser.add_argument('--no-hac', action='store_true'); parser.add_argument('--no-sen', action='store_true')
    args = parser.parse_args()
    def interrupt(*_): raise Cancelled('Interrupted by signal')
    signal.signal(signal.SIGINT, interrupt); signal.signal(signal.SIGTERM, interrupt)
    try:
        result = run_statistics(args.dataset, args.output, args.start, args.end, args.region,
            args.memory_mib, args.block_size, args.allow_synthetic, not args.no_hac, not args.no_sen)
        print(json.dumps({'event': 'complete', 'seconds': result['seconds']}), flush=True)
        return 0
    except Cancelled as exc:
        print(json.dumps({'event': 'cancelled', 'message': str(exc)}), flush=True); return 2
    except Exception as exc:
        print(json.dumps({'event': 'failed', 'message': str(exc)}), file=sys.stderr, flush=True); return 1


if __name__ == '__main__': sys.exit(main())
