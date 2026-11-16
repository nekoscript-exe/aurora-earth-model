"""Earth science registry tests."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aurora.variables import get_variable


def test_ndvi_registry():

    spec = get_variable("ndvi")

    assert spec.unit == "1"
    assert spec.minimum == -0.2
    assert spec.maximum == 1.0
    assert spec.prediction_supported


def test_lst_registry():

    spec = get_variable("lst")

    assert spec.unit == "degC"
    assert spec.slope_unit == "degC/year"
    assert spec.prediction_supported


def test_lst_conversion():

    spec = get_variable("lst")

    temperature = (
        15000 * spec.scale_factor
        + spec.offset
    )

    assert temperature == pytest.approx(26.85)


def test_case_insensitive():

    assert get_variable("NDVI") == get_variable("ndvi")


def test_unknown_variable():

    with pytest.raises(ValueError):
        get_variable("unknown")
