"""AURORA Earth science variable registry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VariableSpec:

    identifier: str
    name: str
    source: str
    band: str
    unit: str
    slope_unit: str
    minimum: float
    maximum: float
    scale_factor: float
    offset: float
    description: str
    prediction_supported: bool


VARIABLES = {

    "ndvi": VariableSpec(
        identifier="NDVI",
        name="Normalized Difference Vegetation Index",
        source="MODIS/061/MOD13Q1",
        band="NDVI",
        unit="1",
        slope_unit="NDVI/year",
        minimum=-0.2,
        maximum=1.0,
        scale_factor=0.0001,
        offset=0.0,
        description="Satellite-derived vegetation greenness.",
        prediction_supported=True
    ),

    "lst": VariableSpec(
        identifier="LST",
        name="Daytime Land Surface Temperature",
        source="MODIS/061/MOD11A2",
        band="LST_Day_1km",
        unit="degC",
        slope_unit="degC/year",
        minimum=-123.15,
        maximum=1037.55,
        scale_factor=0.02,
        offset=-273.15,
        description="Daytime temperature of the land surface.",
        prediction_supported=True
    )
}


def get_variable(identifier):

    key = identifier.strip().lower()

    if key not in VARIABLES:
        raise ValueError(
            f"Unsupported Earth science variable: {identifier}"
        )

    return VARIABLES[key]
