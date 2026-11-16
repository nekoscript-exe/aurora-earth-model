"""Portability fixtures are arbitrary test bytes, never satellite observations."""
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import pytest
from aurora.jobs import fingerprint, fresh
from aurora.portability import CONTENT_SCHEME, content_fingerprint, load_manifest, sha256, contained
from aurora.distribution import verify_package, zip_demo, safe_path
from aurora.hardware import select_device


@pytest.fixture
def store(tmp_path):
    path=tmp_path/'original';path.mkdir()
    (path/'cube.bin').write_bytes(b'EXPLICIT MATHEMATICAL STORAGE TEST')
    (path/'cube_metadata.json').write_text(json.dumps({'source':'UNIT TEST ONLY','storage':{'path':'cube.bin'}}))
    return path


def test_content_identity_survives_copy_move_and_timestamp_loss(store,tmp_path):
    expected=content_fingerprint(store)
    target=tmp_path/'independent copy ñ';shutil.copytree(store,target)
    for p in target.iterdir():os.utime(p,ns=(123456789,123456789))
    assert content_fingerprint(target)['fingerprint']==expected['fingerprint']
    assert fingerprint(target)['fingerprint']!=fingerprint(store)['fingerprint']
    assert fresh({'inputs':[dict(expected,directory=str(target))]})


def test_content_identity_detects_change_with_preserved_stat(store):
    expected=content_fingerprint(store);path=store/'cube.bin';stat=path.stat()
    path.write_bytes(b'X'+path.read_bytes()[1:]);os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    assert not fresh({'inputs':[expected]})


def test_relocation_sidecar_keeps_historical_manifest_bytes(store,tmp_path):
    root=tmp_path/'package';root.mkdir();(root/'config').mkdir()
    target=root/'data';shutil.copytree(store,target)
    result=root/'result';result.mkdir();manifest=result/'manifest.json'
    manifest.write_text(json.dumps({'inputs':[{'directory':'/absent/original/machine','fingerprint':'old'}],'status':'complete','rmse':2.83}))
    before=manifest.read_bytes();source=content_fingerprint(target)
    overlay={'results':{'result/manifest.json':{'manifest_sha256':sha256(manifest),'inputs':[dict(source,directory='data')]}}}
    (root/'config/portable_provenance.json').write_text(json.dumps(overlay))
    loaded=load_manifest(manifest,root)
    assert fresh(loaded) and loaded['rmse']==2.83 and manifest.read_bytes()==before
    assert loaded['original_inputs'][0]['directory']=='/absent/original/machine'
    manifest.write_bytes(before+b' ')
    with pytest.raises(ValueError,match='manifest changed'):load_manifest(manifest,root)


@pytest.mark.parametrize('name',['../escape','/absolute','C:/Windows/file','C:\\Windows\\file','dir/../../escape'])
def test_distribution_paths_reject_traversal_and_windows_drives(tmp_path,name):
    for function in (contained,safe_path):
        with pytest.raises(ValueError):function(tmp_path,name)


def test_unknown_fingerprint_scheme_is_not_silently_accepted(store):
    assert not fresh({'inputs':[dict(content_fingerprint(store),scheme='unrecognized')]})


def test_archive_is_deterministic_and_integrity_rejects_tampering(tmp_path):
    root=tmp_path/'demo';root.mkdir();(root/'payload.txt').write_text('Explicit distribution unit-test bytes')
    manifest={'scientific_scope':'EXPLICIT UNIT TEST, NOT OBSERVATIONS','files':{'payload.txt':{'bytes':(root/'payload.txt').stat().st_size,'sha256':sha256(root/'payload.txt')}}}
    (root/'distribution-manifest.json').write_text(json.dumps(manifest))
    zip_demo(root,tmp_path/'a.zip');os.utime(root/'payload.txt',(100,100));zip_demo(root,tmp_path/'b.zip')
    assert sha256(tmp_path/'a.zip')==sha256(tmp_path/'b.zip') and verify_package(root)['ok']
    (root/'payload.txt').write_text('Changed')
    assert not verify_package(root)['ok']


def test_forced_cpu_does_not_probe_cuda(monkeypatch):
    import torch
    def fail():raise AssertionError('CUDA must not be probed')
    monkeypatch.setattr(torch.cuda,'is_available',fail)
    assert select_device('cpu').type=='cpu'


def test_auto_falls_back_but_explicit_cuda_reports_failure(monkeypatch):
    import torch
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    assert select_device('auto').type=='cpu'
    with pytest.raises(RuntimeError,match='Explicit CUDA'):select_device('cuda')
    with pytest.raises(ValueError):select_device('not-a-device')


def test_installer_never_mutates_an_existing_environment(tmp_path):
    from scripts.install import install
    prefix=tmp_path/'.venv';prefix.mkdir();sentinel=prefix/'unchanged';sentinel.write_text('keep')
    with pytest.raises(FileExistsError):install(tmp_path,prefix)
    assert sentinel.read_text()=='keep'


def test_cpu_profile_and_platform_locks_are_separate():
    root=Path(__file__).resolve().parents[1]
    cpu=(root/'requirements/locks/linux-cpu-hashed.txt').read_text().lower()
    assert 'torch==2.14.1+cpu' in cpu and 'xgboost-cpu==' in cpu
    assert not any(token in cpu for token in ('nvidia-','cuda-','triton=='))
    assert '--hash=sha256:' in cpu
    assert 'not been executed' in (root/'requirements/locks/windows-cpu-hashed.txt').read_text()


def test_new_jobs_use_content_and_relative_locations_without_rewriting(store,tmp_path):
    from aurora.jobs import Job
    root=tmp_path/'project';(root/'config').mkdir(parents=True)
    (root/'config/datasets.json').write_text('{"datasets":[]}')
    shutil.copytree(store,root/'data')
    job=Job(root/'outputs/job',[root/'data'],'unit-test','not-observations',{},allow_synthetic=True)
    job.finish()
    assert job.manifest['inputs'][0]['scheme']==CONTENT_SCHEME
    assert job.manifest['input_locations']==['data']
    moved=tmp_path/'moved project';shutil.copytree(root,moved)
    for path in (moved/'data').iterdir():os.utime(path,(0,0))
    result=load_manifest(moved/'outputs/job/manifest.json')
    assert fresh(result) and result['inputs'][0]['directory']==str((moved/'data').resolve())
