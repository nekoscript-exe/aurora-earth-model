"""Export complete scientific results without overwriting existing files."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.exports import export_bundle
from aurora.jobs import Cancelled
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--result', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try: export_bundle(a.result, a.output, lambda done, total, phase: print(json.dumps({'event': 'progress', 'done': done, 'total': total, 'phase': phase}), flush=True))
    except Cancelled: sys.exit(2)
