"""CPU reproduction of all four saved models; never modifies reference products."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter
ROOT = Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import torch
from predict import predict_xgboost, predict_convlstm
from aurora.models.forecasting import forecast_saved
from aurora.hardware import hardware_report


def validate(root, require_cpu_build=False, threads=4):
    root=Path(root);torch.set_num_threads(threads)
    if require_cpu_build:
        assert torch.version.cuda is None, 'Validation must use the independent CPU-only wheel'
        assert not any(d.metadata['Name'].lower().startswith(('nvidia-','cuda-','triton')) for d in importlib.metadata.distributions())
    report={'hardware':hardware_report('cpu'),'threads':threads,'models':{},'scope':'Retrospective January 2026 estimates; not new satellite observations'}
    with np.load(root/'data/processed/queretaro/cube.npz',allow_pickle=False) as cube:
        history=cube['X'][-12:].copy();dates=cube['dates'].astype('datetime64[M]')[-12:];region=cube['region_mask'].copy()
    calendar=np.r_[dates,dates[-1]+np.timedelta64(1,'M')]
    eligible=region & (np.isfinite(history[...,0]).sum(axis=0)>=9)
    def compare(variable,engine,actual,reference,seconds):
        # Archived CUDA convolutions used TF32 (control reproduces them exactly).
        # Require strict 1e-6 for XGBoost; allow the TF32 precision envelope only
        # for ConvLSTM. A separate cross-environment CPU check uses 1e-6.
        tolerance=1e-6 if engine=='xgboost' else (1e-3 if variable=='ndvi' else 1e-2)
        with np.load(reference,allow_pickle=False) as data:
            expected=data['prediction'];valid=data['valid']
            assert str(data['date'])[:7]=='2026-01'
            np.testing.assert_array_equal(np.isfinite(actual),valid)
            np.testing.assert_array_equal(np.isfinite(expected),valid)
            within_tolerance = bool(np.allclose(actual,expected,rtol=0,atol=tolerance,equal_nan=True))
        diff=np.asarray(actual[valid],dtype='float64')-expected[valid]
        report['models'][f'{variable}/{engine}']={'device':'cpu','unit':'1' if variable=='ndvi' else 'degC',
            'date':'2026-01','observations_created':False,'mask_exact':True,'pixels':int(valid.sum()),
            'max_absolute_difference':float(np.abs(diff).max()),'rmse_difference':float(np.sqrt(np.mean(diff**2))),
            'absolute_tolerance':tolerance,'relative_tolerance':0,'within_tolerance':within_tolerance,'seconds':seconds}
        cache = os.environ.get('AURORA_VALIDATION_ARRAYS')
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
            np.save(Path(cache)/f'{variable}_{engine}.npy', actual)
    run=root/'outputs/queretaro'
    for engine in ('xgboost','convlstm'):
        start=perf_counter()
        values=(predict_xgboost(history,calendar,run/'xgboost/model.ubj',eligible) if engine=='xgboost'
                else predict_convlstm(history,run/'convlstm/best_model.pt',eligible,device='cpu'))
        values=np.clip(values,-.2,1.)
        compare('ndvi',engine,values,run/f'forecast/{engine}/forecast.npz',perf_counter()-start)
    with tempfile.TemporaryDirectory(prefix='aurora-cpu-inference-') as temporary:
        output=Path(temporary)/'verification-only';start=perf_counter()
        run=root/'outputs/aurora5/queretaro_lst'
        forecast_saved(root/'data/processed/queretaro_lst',run,output,device='cpu')
        elapsed=perf_counter()-start
        for engine in ('xgboost','convlstm'):
            with np.load(output/f'{engine}.npz',allow_pickle=False) as data:values=data['prediction'].copy()
            compare('lst',engine,values,run/f'forecast/{engine}/forecast.npz',elapsed)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path)
    p.add_argument('--require-cpu-build',action='store_true');p.add_argument('--threads',type=int,default=4);a=p.parse_args()
    result=validate(a.root,a.require_cpu_build,a.threads);text=json.dumps(result,indent=2)
    if a.output:a.output.write_text(text)
    print(text)
    sys.exit(0 if all(model['within_tolerance'] for model in result['models'].values()) else 1)
