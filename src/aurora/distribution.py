"""Allowlisted, deterministic demo assembly and SHA-256 integrity (stdlib only)."""
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import zipfile


def sha256(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_path(root, name):
    if Path(name).is_absolute() or PureWindowsPath(name).drive or '..' in Path(name).parts or '\\' in name:
        raise ValueError('Unsafe package path')
    path = (Path(root)/name).resolve()
    if not path.is_relative_to(Path(root).resolve()): raise ValueError('Package path escapes root')
    return path


def verify_package(root):
    root = Path(root); manifest = json.loads((root/'distribution-manifest.json').read_text())
    errors = []
    for name, entry in manifest['files'].items():
        try:
            path = safe_path(root, name)
            if path.is_symlink() or not path.is_file() or path.stat().st_size != entry['bytes'] or sha256(path) != entry['sha256']:
                errors.append(name)
        except (OSError, ValueError): errors.append(name)
    return {'ok': not errors, 'verified_files': len(manifest['files']), 'errors': errors,
            'scope': manifest['scientific_scope']}


def build_demo(root, destination, wheelhouse=None):
    # Lazy imports let installers verify integrity before scientific dependencies exist.
    from aurora.portability import content_fingerprint, load_manifest
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination.exists(): raise FileExistsError('Distribution destination already exists')
    destination.mkdir(parents=True)
    source_dirs = ['src', 'scripts', 'tests', 'assets', 'requirements', 'installers']
    files = {root/'README.md', root/'pyrightconfig.json', root/'config/dataset_targets.json'}
    for name in source_dirs:
        files.update(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and 'synthetic' not in p.name.lower())
    files.update((root/'docs').glob('*.md'))
    for name in ['ndvi_preservation.json', 'artifact_manifest.json']:
        files.add(root/'docs/evidence/aurora5'/name)
    data_dirs = ['data/processed/queretaro', 'data/processed/queretaro_lst',
                 'outputs/global_engine/stores/queretaro_ndvi_zarr', 'outputs/global_engine/stores/queretaro_lst_zarr',
                 'outputs/queretaro', 'outputs/aurora5/queretaro_lst',
                 'outputs/aurora5/lst_reloaded', 'outputs/aurora5/storage/queretaro_lst',
                 'outputs/investigations/queretaro_lst_2025-02_2025-10',
                 'outputs/global_engine/queretaro_ndvi_final', 'outputs/global_engine/queretaro_lst_final',
                 'outputs/global_engine/queretaro_paired_final']
    for name in data_dirs:
        directory = root/name
        if not directory.is_dir(): raise FileNotFoundError(directory)
        files.update(p for p in directory.rglob('*') if p.is_file())
    banned = ('.env', '.git', '.aws', '.venv', 'credentials', 'service-account', 'synthetic', 'integration_test')
    expected = json.loads((root/'docs/evidence/aurora5/ndvi_preservation.json').read_text())
    for name, entry in json.loads((root/'docs/evidence/aurora5/artifact_manifest.json').read_text())['files'].items():
        if name.startswith(('outputs/', 'data/')): expected[name] = entry['sha256']
    product_audit = root/'docs/evidence/global_engine/product_manifest.json'
    if product_audit.exists():
        for entry in json.loads(product_audit.read_text())['files']: expected[entry['path']] = entry['sha256']
    for name, digest in expected.items():
        if root/name in files and sha256(root/name) != digest: raise ValueError(f'Scientific artifact differs from historical audit: {name}')
    for source in sorted(files):
        relative = source.relative_to(root)
        if source.is_symlink() or any(token in relative.as_posix().lower() for token in banned):
            raise ValueError(f'Excluded file in distribution: {relative}')
        target = destination/relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)  # Intentionally do not rely on timestamps surviving transfer.
    for name in ['data/processed/queretaro', 'data/processed/queretaro_lst']:
        m = json.loads((destination/name/'cube_metadata.json').read_text())
        if m['dataset'] != 'satellite' or m['variable'].lower() not in ('ndvi', 'lst'):
            raise ValueError('Demo requires the real observed Querétaro datasets')
    overlay = {'schema': 'aurora-relocation-v1', 'results': {}}
    for name in ['queretaro_ndvi_final', 'queretaro_lst_final', 'queretaro_paired_final']:
        relative = f'outputs/global_engine/{name}/manifest.json'
        record = load_manifest(root/relative, root)
        if record['status'] != 'complete' or record['observation_kind'] != 'satellite': raise ValueError('Unqualified scientific result')
        inputs = []
        for original in record['inputs']:
            origin = Path(original['directory']).resolve()
            rel = origin.relative_to(root).as_posix()
            current = content_fingerprint(origin)
            # The sidecar binds byte-identical content, not a guessed relocated path.
            if content_fingerprint(destination/rel)['fingerprint'] != current['fingerprint']: raise ValueError('Copy changed scientific observations')
            inputs.append(dict(current, directory=rel))
        overlay['results'][relative] = {'manifest_sha256': sha256(root/relative), 'inputs': inputs}
    (destination/'config/portable_provenance.json').write_text(json.dumps(overlay, indent=2))
    config = {'datasets': []}
    for variable in ('ndvi', 'lst'):
        rel = f'outputs/global_engine/stores/queretaro_{variable}_zarr'
        identity = content_fingerprint(destination/rel)
        config['datasets'].append({'id': f'queretaro_{variable}_zarr', 'region_id': 'queretaro', 'priority': 10,
                                  'path': rel, 'input': dict(identity, directory=rel)})
    (destination/'config/datasets.json').write_text(json.dumps(config, indent=2))
    if wheelhouse is not None:
        source = Path(wheelhouse)
        if not source.is_dir(): raise FileNotFoundError(source)
        for wheel in sorted(source.glob('*.whl')):
            target = destination/'wheelhouse'/wheel.name; target.parent.mkdir(exist_ok=True)
            shutil.copyfile(wheel, target)
    notice = ('AURORA project license: not selected by this distribution workflow.\n'
              'This is a local validation/handoff artifact; no project license is granted here.\n'
              'Third-party packages retain their own licenses (included inside wheels/installations).\n'
              'Geography attribution: assets/desktop/geography/README.md. MODIS sources remain in cube metadata.\n'
              'Windows installer recipes are untested on Windows. Scientific scope: Querétaro only.\n')
    (destination/'DISTRIBUTION_NOTICE.txt').write_text(notice)
    entries = {p.relative_to(destination).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha256(p)}
               for p in sorted(destination.rglob('*')) if p.is_file()}
    commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    manifest = {'schema': 'aurora-distribution-v1', 'source_commit': commit.stdout.strip() if commit.returncode == 0 else 'unversioned copy',
                'scientific_scope': 'Real Querétaro NDVI/LST, monthly 2001-01 to 2025-12; no complete Mexico/global observations',
                'models': ['queretaro/ndvi/xgboost', 'queretaro/ndvi/convlstm', 'queretaro/lst/xgboost', 'queretaro/lst/convlstm'],
                'license_status': 'not selected', 'windows_status': 'recipes only; not tested on Windows', 'files': entries}
    (destination/'distribution-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def zip_demo(directory, archive):
    directory, archive = Path(directory), Path(archive)
    if archive.exists(): raise FileExistsError(archive)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(directory.rglob('*')):
            if not path.is_file(): continue
            info = zipfile.ZipInfo(path.relative_to(directory).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3; info.external_attr = (0o100644 << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            with output.open(info, 'w') as target, path.open('rb') as source:
                shutil.copyfileobj(source, target, length=1024*1024)
    archive.with_suffix(archive.suffix+'.sha256').write_text(f'{sha256(archive)}  {archive.name}\n')
