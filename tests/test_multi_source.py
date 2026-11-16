"""Satellite product identity and compatibility tests."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.variables import get_variable, get_product
from aurora.catalog import variable_spec


@pytest.mark.parametrize("variable,source,unit", [
    ("ndvi", "MODIS/061/MOD13Q1", "1"),
    ("ndvi", "MODIS/061/MOD13C1", "1"),
    ("lst", "MODIS/061/MOD11A2", "degC"),
    ("lst", "MODIS/061/MOD21C3", "degC"),
])
def test_product_identity(variable, source, unit):
    spec = get_product(variable, source)

    assert spec.source == source
    assert spec.unit == unit
    assert spec.identifier.lower() == variable


@pytest.mark.parametrize("variable", ["ndvi", "lst"])
def test_original_product_preserved(variable):
    original = get_variable(variable)

    assert get_product(variable, original.source) == original


@pytest.mark.parametrize("variable,source", [
    ("ndvi", "MODIS/061/MOD13C1"),
    ("lst", "MODIS/061/MOD21C3"),
])
def test_alternative_prediction_disabled(variable, source):
    assert not get_product(variable, source).prediction_supported


@pytest.mark.parametrize("variable,source", [
    ("ndvi", "MODIS/061/MOD21C3"),
    ("lst", "MODIS/061/MOD13C1"),
    ("ndvi", "UNKNOWN"),
])
def test_invalid_product(variable, source):
    with pytest.raises(ValueError):
        get_product(variable, source)


@pytest.mark.parametrize("variable,source,unit", [
    ("NDVI", "MODIS/061/MOD13C1", "1"),
    ("LST", "MODIS/061/MOD21C3", "degC"),
])
def test_catalog_alternative_source(variable, source, unit):
    metadata = {
        "variable": variable,
        "source": source,
        "unit": unit,
    }

    spec = variable_spec(metadata)

    assert spec.source == source
    assert spec.unit == unit


def test_invalid_temperature_units():
    with pytest.raises(ValueError):
        variable_spec({
            "variable": "LST",
            "source": "MODIS/061/MOD21C3",
            "unit": "K",
        })
