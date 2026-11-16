"""Explicit runtime device policy; no training, model or scientific-data changes."""
import os
import platform
import shutil


def select_device(request=None):
    import torch
    policy = request or os.environ.get('AURORA_DEVICE', 'auto')
    if policy not in ('auto', 'cpu', 'cuda'): raise ValueError('Device must be auto, cpu or cuda')
    if policy == 'cpu': return torch.device('cpu')  # Do not probe CUDA when explicitly disabled.
    try:
        if not torch.cuda.is_available(): raise RuntimeError('CUDA unavailable')
        # is_available alone does not establish wheel/driver/architecture compatibility.
        probe = torch.ones(1, device='cuda') + 1
        torch.cuda.synchronize()
        if probe.item() != 2: raise RuntimeError('CUDA execution probe failed')
        return torch.device('cuda')
    except (RuntimeError, AssertionError) as exc:
        if policy == 'cuda': raise RuntimeError(f'Explicit CUDA requested but unavailable: {exc}') from exc
        return torch.device('cpu')


def hardware_report(request=None):
    import torch
    selected = select_device(request)
    return {'system': platform.system(), 'machine': platform.machine(), 'python': platform.python_version(),
            'logical_cpus': os.cpu_count(), 'torch': torch.__version__, 'torch_cuda_build': torch.version.cuda,
            'requested_device': request or os.environ.get('AURORA_DEVICE', 'auto'), 'selected_device': str(selected),
            'gpu': torch.cuda.get_device_name(0) if selected.type == 'cuda' else None,
            'free_disk_bytes': shutil.disk_usage('.').free}
