"""Reproduce retrospective forecasts from saved AURORA multivariable weights."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.models.forecasting import forecast_saved
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'run', 'output'): p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); forecast_saved(a.dataset, a.run, a.output)
