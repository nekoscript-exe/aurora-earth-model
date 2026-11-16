"""Content identities and relocation overlays; historical scientific files stay immutable."""
import hashlib
import json
from pathlib import Path, PureWindowsPath

CONTENT_SCHEME = 'metadata-storage-sha256-v1'


def sha256(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def contained(root, relative):
    root = Path(root).resolve()
    if PureWindowsPath(relative).drive or Path(relative).is_absolute() or '..' in Path(relative).parts or '\\' in str(relative):
        raise ValueError('Expected a portable relative POSIX path')
    path = (root/relative).resolve()
    if not path.is_relative_to(root): raise ValueError('Path outside distribution')
    return path


def content_fingerprint(directory):
    directory = Path(directory).resolve()
    meta = directory/'cube_metadata.json'; metadata = json.loads(meta.read_text())
    storage = metadata.get('storage', {'path': 'cube.npz'})
    source = contained(directory, storage['path'])
    if not source.exists(): raise FileNotFoundError(source)
    files = [source] if source.is_file() else sorted(p for p in source.rglob('*') if p.is_file())
    digest = hashlib.sha256(meta.read_bytes())
    for path in files:
        if path.is_symlink(): raise ValueError('Symlink storage is not portable')
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(bytes.fromhex(sha256(path)))
    return {'directory': str(directory), 'fingerprint': digest.hexdigest(), 'scheme': CONTENT_SCHEME}


def load_manifest(path, root=None):
    """Relocate only with a manifest-bound, content-verified explicit sidecar."""
    path = Path(path).resolve(); data = json.loads(path.read_text())
    candidates = [Path(root).resolve()] if root is not None else path.parents
    if 'input_locations' in data:
        for candidate in candidates:
            if not (candidate/'config/datasets.json').is_file(): continue
            if len(data['input_locations']) != len(data['inputs']): raise ValueError('Incomplete relative input references')
            relocated = []
            for location, original in zip(data['input_locations'], data['inputs']):
                current = content_fingerprint(contained(candidate, location))
                if original.get('scheme') != CONTENT_SCHEME or current['fingerprint'] != original['fingerprint']:
                    raise ValueError('Relocated observations changed')
                relocated.append(current)
            return dict(data, original_inputs=data['inputs'], inputs=relocated)
        raise ValueError('Relative scientific result requires its dataset registry root')
    for candidate in candidates:
        sidecar = candidate/'config/portable_provenance.json'
        if not sidecar.exists(): continue
        records = json.loads(sidecar.read_text())['results']
        key = path.relative_to(candidate).as_posix()
        if key not in records: return data  # New local results retain ordinary freshness semantics.
        binding = records[key]
        if binding['manifest_sha256'] != sha256(path): raise ValueError('Historical result manifest changed')
        sources = []
        for source in binding['inputs']:
            directory = contained(candidate, source['directory'])
            current = content_fingerprint(directory)
            if current['fingerprint'] != source['fingerprint']: raise ValueError('Relocated observations changed')
            sources.append(current)
        if len(sources) != len(data['inputs']): raise ValueError('Incomplete relocation binding')
        return dict(data, original_inputs=data['inputs'], inputs=sources,
                    relocation={'scheme': CONTENT_SCHEME, 'historical_manifest_sha256': binding['manifest_sha256']})
    return data
