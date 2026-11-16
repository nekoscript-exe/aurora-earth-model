"""Ellipsoidal surface area of native raster cells, in m²; no observation resampling."""
import numpy as np
from pyproj import CRS, Transformer, Geod


def cell_areas(grid, rows=slice(None), cols=slice(None), check=lambda: None, mask=None):
    yy = np.arange(*rows.indices(grid.height)); xx = np.arange(*cols.indices(grid.width))
    crs = CRS.from_user_input(grid.crs); a = grid.affine
    if crs.is_geographic and a.b == 0 and a.d == 0:
        north = a.f+a.e*yy; south = north+a.e
        if np.max(np.abs(np.r_[north, south]), initial=0) > 90+1e-9 or abs(a.a) > 180:
            raise ValueError('Geographic cell latitude or longitude width invalid')
        ellipsoid = crs.ellipsoid
        if ellipsoid is None:
            raise ValueError('CRS has no reference ellipsoid')
        radius = ellipsoid.semi_major_metre
        flattening = 1/ellipsoid.inverse_flattening if ellipsoid.inverse_flattening else 0
        e2 = flattening*(2-flattening); e = np.sqrt(e2)
        def primitive(lat):
            u = np.sin(np.radians(lat))
            if e < 1e-15: return u
            return u/(2*(1-e2*u*u))+np.arctanh(e*u)/(2*e)
        stripe = np.abs(primitive(north)-primitive(south))*radius**2*(1-e2)*np.radians(abs(a.a))
        return np.broadcast_to(stripe[:, None], (len(yy), len(xx))).copy(), 'exact ellipsoidal latitude/longitude cell integral'
    method = crs.coordinate_operation.method_name.lower() if crs.coordinate_operation else ''
    if crs.is_projected and ('equal area' in method or 'equal earth' in method):
        factors = [axis.unit_conversion_factor for axis in crs.axis_info[:2]]
        return np.full((len(yy), len(xx)), abs(a.determinant)*np.prod(factors)), 'native equal-area projection determinant'
    # Dense projected/geographic cell edges are mapped to their geodetic CRS.
    geodetic = crs.geodetic_crs
    if geodetic is None:
        raise ValueError('CRS has no geodetic reference system')
    transformer = Transformer.from_crs(crs, geodetic, always_xy=True)
    geod = geodetic.get_geod()
    if geod is None:
        raise ValueError('Unable to initialize geodesic calculations')
    area = np.zeros((len(yy), len(xx)))
    t = np.arange(8)/8
    offsets = np.vstack([np.column_stack([t, t*0]), np.column_stack([t*0+1, t]),
                         np.column_stack([1-t, t*0+1]), np.column_stack([t*0, 1-t])])
    for r, y in enumerate(yy):
        check()
        for c, x in enumerate(xx):
            if mask is not None and not mask[r, c]: continue
            px = a.a*(x+offsets[:, 0])+a.b*(y+offsets[:, 1])+a.c
            py = a.d*(x+offsets[:, 0])+a.e*(y+offsets[:, 1])+a.f
            lon, lat = transformer.transform(px, py)
            value = abs(geod.polygon_area_perimeter(lon, lat)[0])
            if not np.isfinite(value) or value <= 0: raise ValueError('Invalid geodesic cell area')
            area[r, c] = value
    return area, 'ellipsoidal geodesic polygon with 8 segments per cell edge (approximation)'
