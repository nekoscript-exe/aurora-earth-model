"""Reproducible paired-observation NDVI/LST analysis."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.multivariate import run_analysis
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ndvi', type=Path, required=True); p.add_argument('--lst', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--start', default='2001-01'); p.add_argument('--end', default='2025-12')
    a = p.parse_args()
    print(json.dumps(run_analysis(a.ndvi, a.lst, a.output, a.start, a.end), indent=2))
