"""Non-destructive Python 3.14.4 installer; creates an independent environment."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import venv
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'src'))
from aurora.distribution import verify_package


def install(root, prefix, profile='cpu', wheelhouse=None):
    root, prefix = Path(root).resolve(), Path(prefix).resolve()
    if sys.version_info[:3] != (3,14,4): raise RuntimeError('Use Python 3.14.4; other Python versions have not been validated')
    if prefix.exists(): raise FileExistsError('Refusing to modify an existing environment')
    if prefix == root/'.venv': raise ValueError('The development .venv must remain untouched')
    if profile not in ('cpu','nvidia'): raise ValueError('Unknown dependency profile')
    if (root/'distribution-manifest.json').exists():
        check = verify_package(root)
        if not check['ok']: raise ValueError('Package integrity failed before installation')
    system = platform.system().lower()
    if system not in ('linux','windows'): raise RuntimeError('Only Linux and unvalidated Windows recipes are provided')
    if system == 'windows': print('NOTICE: Windows recipes have not been functionally tested on Windows.', flush=True)
    if profile == 'nvidia' and system != 'linux': raise RuntimeError('NVIDIA profile supplied only for Linux; Windows GPU is unvalidated')
    python = prefix/('Scripts/python.exe' if system == 'windows' else 'bin/python')
    lock = root/'requirements/locks'/f'{system}-{profile}-hashed.txt'
    if profile == 'cpu':
        if not lock.exists(): raise FileNotFoundError('Hashed CPU wheel lock unavailable for this platform')
        command = [str(python),'-m','pip','install','--require-hashes','--only-binary=:all:','-r',str(lock)]
        if wheelhouse: command += ['--no-index','--find-links',str(Path(wheelhouse).resolve())]
        else: command += ['--extra-index-url','https://download.pytorch.org/whl/cpu']
    else:
        if wheelhouse: raise ValueError('Offline NVIDIA wheels were not supplied/validated')
        command = [str(python),'-m','pip','install','--extra-index-url','https://download.pytorch.org/whl/cu130',
                   '-r',str(root/'requirements/locks/linux-nvidia.txt')]
    if wheelhouse and not Path(wheelhouse).is_dir():
        raise FileNotFoundError('Wheelhouse directory unavailable')
    if profile == 'nvidia' and not (root/'requirements/locks/linux-nvidia.txt').is_file():
        raise FileNotFoundError('NVIDIA lock unavailable')
    bootstrap = root/'requirements/locks/installer-bootstrap.txt'
    if not bootstrap.is_file():
        raise FileNotFoundError('Hashed installer bootstrap lock unavailable')
    venv.EnvBuilder(with_pip=True).create(prefix)
    bootstrap_command = [str(python), '-m', 'pip', '--disable-pip-version-check', 'install',
                         '--require-hashes', '--only-binary=:all:', '-r', str(bootstrap)]
    if wheelhouse:
        bootstrap_command += ['--no-index', '--find-links', str(Path(wheelhouse).resolve())]
    subprocess.run(bootstrap_command, check=True)
    subprocess.run(command, check=True)
    subprocess.run([str(python),'-m','pip','check'], check=True)
    env = dict(os.environ, PYTHONPATH=str(root/'src'), AURORA_DEVICE='cpu' if profile=='cpu' else 'auto')
    subprocess.run([str(python),str(root/'scripts/doctor.py'),'--root',str(root),'--device',env['AURORA_DEVICE']],env=env,check=True)
    print(f'Installed. Run: {python} {root/"scripts/desktop.py"} --device {env["AURORA_DEVICE"]}',flush=True)
    return python


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prefix',type=Path,default=ROOT/'.aurora-venv')
    p.add_argument('--profile',choices=['cpu','nvidia'],default='cpu');p.add_argument('--wheelhouse',type=Path)
    a=p.parse_args();install(ROOT,a.prefix,a.profile,a.wheelhouse)
