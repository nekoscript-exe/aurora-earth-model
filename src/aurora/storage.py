"""Bounded conversion of existing observations to interoperable chunked Zarr v2."""
import json
from pathlib import Path
import numpy as np
from aurora.catalog import CubeReader
from aurora.jobs import Job, atomic_json


def _require_zarr_array(group, name):
    import zarr

    array = group[name]

    if not isinstance(array, zarr.Array):
        raise TypeError(f'Expected Zarr array: {name}')

    return array



def to_zarr(source, output, chunks=(12, 128, 128, 1), progress=None, check=lambda: None):
    import zarr
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    reader = CubeReader(source, check=check)
    if reader.format == 'zarr' and any(np.prod(reader.arrays[name].chunks)*np.dtype(reader.arrays[name].dtype).itemsize > 32*1024**2 for name in ('X', 'valid', 'region_mask')):
        reader.close(); raise MemoryError('Source chunks exceed conversion decode budget; rechunk with an explicit larger-memory workflow')
    group = zarr.open_group(str(output/'cube.zarr'), mode='w', zarr_format=2)
    for name in ('X', 'valid', 'region_mask', 'dates', 'channels'):
        original = reader.arrays[name]
        if name in ('X', 'valid'):
            group.create_array(name, shape=original.shape, chunks=chunks, dtype=original.dtype,
                               fill_value=np.nan if name == 'X' else False)
        elif name == 'region_mask':
            group.create_array(name, shape=original.shape, chunks=chunks[1:3], dtype=bool, fill_value=False)
        else: group.create_array(name, data=np.asarray(original[:]))
    total = int(np.prod([int(np.ceil(reader.shape[i]/chunks[i])) for i in range(3)])); done = 0
    for t in range(0, reader.shape[0], chunks[0]):
        for y in range(0, reader.shape[1], chunks[1]):
            for x in range(0, reader.shape[2], chunks[2]):
                check()
                index = (slice(t, t+chunks[0]), slice(y, y+chunks[1]), slice(x, x+chunks[2]), slice(None))
                # Copy raw values AND validity exactly, including finite NoData.
                _require_zarr_array(group, 'X')[index] = reader.arrays['X'][index]
                _require_zarr_array(group, 'valid')[index] = reader.arrays['valid'][index]
                if t == 0:
                    spatial = index[1:3]
                    _require_zarr_array(group, 'region_mask')[spatial] = reader.arrays['region_mask'][spatial]
                reader.release_pages()
                done += 1
                if progress: progress(done, total, 'convert-zarr')
    check()
    metadata = dict(reader.metadata); metadata['storage'] = {'format': 'zarr', 'path': 'cube.zarr', 'zarr_format': 2, 'chunks': list(chunks)}
    metadata['conversion'] = {'method': 'exact raw array and mask copy, no resampling', 'zarr_version': zarr.__version__}
    atomic_json(output/'cube_metadata.json', metadata)  # Only publish metadata after all chunks complete.
    reader.close()
    return metadata
