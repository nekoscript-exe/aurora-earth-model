"""AURORA Earth science variable registry."""

from dataclasses import dataclass, replace


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
    "precip": VariableSpec(
        identifier="PRECIP",
        name="Precipitation rate",
        source="NASA/GPM_L3/IMERG_MONTHLY_V07",
        band="precipitation",
        unit="mm/h",
        slope_unit="mm/h/year",
        minimum=0.0,
        maximum=1000.0,
        scale_factor=1.0,
        offset=0.0,
        description="Monthly mean precipitation rate.",
        prediction_supported=False
    ),


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


# Alternative satellite products in physical units.
PRODUCTS = {
    ("ndvi", "MODIS/061/MOD13C1"): replace(
        VARIABLES["ndvi"],
        source="MODIS/061/MOD13C1",
        band="NDVI",
        scale_factor=1.0,
        offset=0.0,
        prediction_supported=False
    ),
    ("lst", "MODIS/061/MOD21C3"): replace(
        VARIABLES["lst"],
        source="MODIS/061/MOD21C3",
        band="LST_Day",
        minimum=-90.0,
        maximum=80.0,
        scale_factor=1.0,
        offset=-273.15,
        prediction_supported=False
    )
}


def get_product(identifier, source):
    """Resolve a variable and its exact satellite product."""
    spec = get_variable(identifier)

    if source == spec.source:
        return spec

    key = (identifier.strip().lower(), source)

    if key not in PRODUCTS:
        raise ValueError(
            f"Unsupported satellite product: {identifier}/{source}"
        )

    return PRODUCTS[key]
