"""Compatibility imports; geospatial logic now belongs to the shared core."""
from aurora.geospatial import (
    RasterGrid, orthographic_inverse, orthographic_forward, load_observations,
)
__all__ = ["RasterGrid", "orthographic_inverse", "orthographic_forward", "load_observations"]
