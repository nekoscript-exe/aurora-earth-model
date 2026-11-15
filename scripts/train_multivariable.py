"""Train/evaluate isolated multivariable experiments; never overwrite a run."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.models.forecasting import run_forecast
if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--variable', choices=['ndvi', 'lst'], required=True)
    p.add_argument('--epochs', type=int, default=12)
    p.add_argument('--patience', type=int, default=3)
    p.add_argument('--trees', type=int, default=500)
    a = p.parse_args()
    run_forecast(a.dataset, a.output, a.variable, a.epochs, a.patience, a.trees)
