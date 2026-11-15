"""Cancelable bounded paired-variable analysis; synthetic validation is explicit."""
import argparse
from pathlib import Path
import signal
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.block_multivariate import run_pair_statistics
from aurora.jobs import Cancelled
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--x', type=Path, required=True); p.add_argument('--y', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--region')
    p.add_argument('--start'); p.add_argument('--end'); p.add_argument('--baseline-start'); p.add_argument('--baseline-end')
    p.add_argument('--memory-mib', type=int, default=64); p.add_argument('--block-size', type=int, default=32)
    p.add_argument('--allow-synthetic', action='store_true')
    a = p.parse_args()
    def interrupt(*_): raise Cancelled('Signal cancellation')
    signal.signal(signal.SIGINT, interrupt); signal.signal(signal.SIGTERM, interrupt)
    try:
        run_pair_statistics(a.x, a.y, a.output, a.start, a.end, a.region, a.memory_mib, a.block_size,
                            a.baseline_start, a.baseline_end, allow_synthetic=a.allow_synthetic)
    except Cancelled: sys.exit(2)
