"""Private, content-bound extraction of the fixed NPZ cube members."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from filelock import FileLock, Timeout

MEMBERS = ('X', 'valid', 'region_mask', 'dates', 'channels')


def digest(path, check):
    result = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            check()
            result.update(block)
    return result.hexdigest()


def private_directory(path):
    """Reject precreated aliases and directories writable by another account."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('NPZ cache directory must not be a symbolic link')
    if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ValueError('NPZ cache directory must be owned by the current user with mode 0700')
    # Walk from the filesystem root: an owned 0700 ancestor already prevents
    # other accounts reaching group-writable descendants (e.g. pytest fixtures).
    if os.name == 'posix':
        for parent in reversed(path.parents):
            info = parent.stat()
            if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
                raise ValueError('NPZ cache parent is writable by other accounts')
            if info.st_uid == os.getuid() and not info.st_mode & 0o077:
                break


def extract_npz(path, cache, limit, check):
    base = Path(cache or os.environ.get('AURORA_CACHE_DIR') or
                Path.home() / '.cache' / 'aurora')
    root = base / 'aurora-arrays-v2'
    private_directory(root)
    before = path.stat()
    source_hash = digest(path, check)
    target = root / source_hash
    private_directory(target)
    if (target / '.lock').is_symlink():
        raise ValueError('NPZ cache lock must not be a symbolic link')
    lock = FileLock(str(target / '.lock'))
    while True:
        check()
        try:
            lock.acquire(timeout=.1)
            break
        except Timeout:
            continue
    try:
        manifest = target / 'manifest.json'
        files = [target / f'{name}.npy' for name in MEMBERS]
        if manifest.is_symlink() or any(file.is_symlink() for file in files):
            raise ValueError('NPZ cache members must not be symbolic links')
        if manifest.exists():
            saved = json.loads(manifest.read_text())
            hashes = {file.name: digest(file, check) for file in files}
            if saved != {'source_sha256': source_hash, 'members': hashes}:
                raise ValueError('NPZ cache integrity check failed')
        else:
            with zipfile.ZipFile(path) as archive:
                needed = sum(archive.getinfo(f'{name}.npy').file_size for name in MEMBERS)
                used = sum(file.stat().st_size for file in root.glob('*/*.npy'))
                if needed + used > limit or needed > shutil.disk_usage(target).free:
                    raise MemoryError('NPZ cache disk budget exhausted; convert to chunked Zarr or use another cache location')
                hashes = {}
                for name, destination in zip(MEMBERS, files):
                    temporary = None
                    try:
                        with archive.open(f'{name}.npy') as source, tempfile.NamedTemporaryFile(dir=target, delete=False) as out:
                            temporary = Path(out.name)
                            value = hashlib.sha256()
                            while block := source.read(1024 * 1024):
                                check()
                                value.update(block)
                                out.write(block)
                        check()
                        os.replace(temporary, destination)
                        hashes[destination.name] = value.hexdigest()
                    finally:
                        if temporary is not None:
                            temporary.unlink(missing_ok=True)
                with tempfile.NamedTemporaryFile(mode='w', dir=target, delete=False) as out:
                    temporary = Path(out.name)
                    json.dump({'source_sha256': source_hash, 'members': hashes}, out)
                try:
                    os.replace(temporary, manifest)
                finally:
                    temporary.unlink(missing_ok=True)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('NPZ input changed during cache preparation')
    finally:
        lock.release()
    return target
