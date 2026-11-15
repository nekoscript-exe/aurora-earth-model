"""Pure coordinate and cube validation helpers for the desktop explorer.

Raster transforms describe pixel *edges*. Sampling uses the containing pixel,
never interpolation; all coordinates passed to GDAL are longitude, latitude.
"""

import json
from dataclasses import dataclass

import numpy as np
from affine import Affine
from rasterio.crs import CRS
from rasterio.warp import transform, reproject, Resampling

from aurora.variables import get_variable


def _project_points(crs, lon, lat):
    """Keep valid points when GDAL rejects another point's projection domain."""
    try:
        x, y = transform('EPSG:4326', crs, lon, lat)
        return np.asarray(x), np.asarray(y)
    except Exception as exc:
        # Rasterio exposes GDAL domain failures as private exception classes.
        # Do not mask configuration errors or other failures.
        if not any(message in str(exc) for message in (
                'outside of projection domain', 'Reprojection failed')):
            raise
        if len(lon) == 1:
            return np.array([np.nan]), np.array([np.nan])
        mid = len(lon)//2
        left = _project_points(crs, lon[:mid], lat[:mid])
        right = _project_points(crs, lon[mid:], lat[mid:])
        return tuple(np.concatenate(parts) for parts in zip(left, right))


def orthographic_inverse(x, y, longitude, latitude):
    """Screen coordinates (east, north), in sphere radii, to WGS84 degrees."""
    x, y = np.broadcast_arrays(x, y)
    visible = x*x + y*y <= 1
    z = np.sqrt(np.maximum(0, 1-x*x-y*y))
    lat0 = np.radians(latitude)
    lat = np.degrees(np.arcsin(np.clip(
        y*np.cos(lat0) + z*np.sin(lat0), -1, 1)))
    lon = longitude + np.degrees(np.arctan2(
        x, z*np.cos(lat0)-y*np.sin(lat0)))
    return (lon+180) % 360-180, lat, visible


def orthographic_forward(lon, lat, longitude, latitude):
    """WGS84 degrees to screen east/north and front-hemisphere visibility."""
    delta = np.radians(np.asarray(lon)-longitude)
    phi, phi0 = np.radians(lat), np.radians(latitude)
    x = np.cos(phi)*np.sin(delta)
    y = np.sin(phi)*np.cos(phi0)-np.cos(phi)*np.sin(phi0)*np.cos(delta)
    z = np.sin(phi)*np.sin(phi0)+np.cos(phi)*np.cos(phi0)*np.cos(delta)
    return x, y, z >= 0


@dataclass(frozen=True)
class RasterGrid:
    crs: CRS
    affine: Affine
    height: int
    width: int

    def orthographic_mapping(self, width, height, longitude, latitude, zoom):
        """Project integer pixel IDs with GDAL's exact nearest neighbour warp.

        Only geometry is warped. Values and masks are sampled afterwards, so
        missing observations cannot be filled by a neighbouring valid pixel.
        The spherical target matches the globe's analytic screen projection.
        """
        radius = 6371000.0
        scale = min(width, height)*.41*zoom
        pixel_size = radius/scale
        target = Affine(pixel_size, 0, -width/2*pixel_size,
                        0, -pixel_size, height/2*pixel_size)
        crs = CRS.from_string(
            f'+proj=ortho +lat_0={latitude} +lon_0={longitude} '
            f'+R={radius} +units=m')
        ids = np.arange(self.height*self.width, dtype=np.int32).reshape(
            self.height, self.width)
        destination = np.full((height, width), -1, dtype=np.int32)
        reproject(ids, destination, src_transform=self.affine, src_crs=self.crs,
                  dst_transform=target, dst_crs=crs, src_nodata=-1,
                  dst_nodata=-1, resampling=Resampling.nearest, tolerance=0.0)
        # GDAL's warp extent may include limb pixels: enforce our pixel centres.
        yy, xx = np.ogrid[:height, :width]
        visible = ((xx+.5-width/2)**2+(height/2-yy-.5)**2) <= scale*scale
        positions = np.flatnonzero((destination >= 0) & visible)
        source = destination.ravel()[positions]
        return positions, source//self.width, source % self.width

    @classmethod
    def from_metadata(cls, metadata, shape):
        grid = metadata['grid']
        coefficients = grid['transform']
        if len(coefficients) not in (6, 9):
            raise ValueError('Expected six affine coefficients (or homogeneous nine)')
        if len(coefficients) == 9 and list(coefficients[6:]) != [0, 0, 1]:
            raise ValueError('Invalid homogeneous affine transform')
        affine = Affine(*coefficients[:6])
        if not np.isfinite(coefficients).all() or affine.is_degenerate:
            raise ValueError('Non-finite or singular grid transform')
        if tuple(shape) != (grid['height'], grid['width']) or min(shape) <= 0:
            raise ValueError('Raster dimensions disagree with grid metadata')
        return cls(CRS.from_user_input(grid['crs']), affine, *shape)

    def mapping(self, lon, lat, visible):
        """Return flat destination positions and source row/column indices.

        Test membership in native pixel space rather than a longitude bounding
        box, which fails across the date line and for rotated/projected grids.
        """
        lon, lat, visible = np.broadcast_arrays(lon, lat, visible)
        positions = np.flatnonzero(visible & np.isfinite(lon) & np.isfinite(lat)
                                   & (np.abs(lat) <= 90))
        if not positions.size:
            return positions, positions, positions
        x, y = _project_points(self.crs, lon.ravel()[positions],
                               lat.ravel()[positions])
        finite = np.isfinite(x) & np.isfinite(y)
        positions, x, y = positions[finite], x[finite], y[finite]
        inv = ~self.affine
        chosen = np.zeros(positions.size, dtype=bool)
        result = []
        # Accommodate geographic rasters using 0..360 or crossing +/-180.
        for shift in ([0, 360, -360] if self.crs == CRS.from_epsg(4326) else [0]):
            col = inv.a*(x+shift)+inv.b*y+inv.c
            row = inv.d*(x+shift)+inv.e*y+inv.f
            inside = (~chosen & np.isfinite(col) & np.isfinite(row)
                      & (col >= 0) & (col < self.width)
                      & (row >= 0) & (row < self.height))
            result.append((positions[inside], np.floor(row[inside]).astype(int),
                           np.floor(col[inside]).astype(int)))
            chosen |= inside
        return tuple(np.concatenate(parts) for parts in zip(*result))


def load_observations(directory, variable):
    """Load observed values only, checking the documented cube contract."""
    spec = get_variable(variable)
    metadata = json.loads((directory/'cube_metadata.json').read_text())
    if (metadata.get('dataset') != 'satellite'
            or metadata.get('source') != spec.source
            or metadata.get('variable', '').lower() != variable.lower()
            or metadata.get('unit') != spec.unit):
        raise ValueError('Satellite source, variable or units disagree with selection')
    with np.load(directory/'cube.npz', allow_pickle=False) as data:
        declared = metadata.get('shape', [len(data['dates']), metadata['grid']['height'], metadata['grid']['width'], 1])
        if np.prod(declared, dtype='float64')*8 > 256*1024**2:
            raise MemoryError('Eager scientific analysis exceeds budget; use CubeReader.blocks')
        raw, valid, mask = data['X'], data['valid'], data['region_mask']
        if raw.ndim != 4 or raw.shape[-1] != 1 or raw.shape[0] == 0:
            raise ValueError('Expected nonempty [time, height, width, 1] cube')
        if (valid.shape != raw.shape or mask.shape != raw.shape[1:3]
                or valid.dtype != bool or mask.dtype != bool or not mask.any()):
            raise ValueError('Invalid observation or regional mask')
        if [str(c).lower() for c in data['channels']] != [variable.lower()]:
            raise ValueError('Cube channel disagrees with selection')
        grid = RasterGrid.from_metadata(metadata, raw.shape[1:3])
        dates = data['dates'].astype('datetime64[D]')
        if (dates.shape != (raw.shape[0],) or np.isnat(dates).any()
                or np.any(np.diff(dates) <= np.timedelta64(0, 'D'))):
            raise ValueError('Expected strictly increasing observation dates')
        if 'shape' in metadata and list(raw.shape) != metadata['shape']:
            raise ValueError('Cube shape disagrees with metadata')
        values = raw[..., 0].astype(np.float32, copy=True)
        observed = valid[..., 0] & mask & np.isfinite(values)
        nodata = metadata['grid'].get('nodata')
        if nodata is not None:
            observed &= values != nodata
        values[~observed] = np.nan
        if np.any((values < spec.minimum-0.0001) | (values > spec.maximum+0.0001)):
            raise ValueError('Observation values outside documented physical range')
        return values, dates, mask.copy(), metadata, grid


def export_raster(path, values, grid, unit, product="model estimate; not an observation"):
    import rasterio
    from affine import Affine
    with rasterio.open(path, 'w', driver='GTiff', height=grid['height'], width=grid['width'],
                       count=1, dtype='float32', crs=grid['crs'],
                       transform=Affine(*grid['transform'][:6]), nodata=-9999,
                       compress='deflate') as dst:
        dst.write(np.where(np.isfinite(values), values, -9999).astype('float32'), 1)
        dst.update_tags(unit=unit, product=product)


