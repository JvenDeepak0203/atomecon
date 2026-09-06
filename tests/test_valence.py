import pytest

from atomecon import is_formula_plausible, explain_formula_plausibility


def test_real_octane_is_plausible():
    assert is_formula_plausible("C8H18") is True


def test_impossible_formula_is_rejected():
    assert is_formula_plausible("C8H23") is False


def test_water_is_plausible():
    assert is_formula_plausible("H2O") is True


def test_table_salt_is_plausible():
    assert is_formula_plausible("NaCl") is True


def test_carbon_dioxide_is_plausible():
    assert is_formula_plausible("CO2") is True


def test_ammonia_not_wrongly_rejected():
    assert is_formula_plausible("NH3") is True


def test_iron_oxide_not_wrongly_rejected():
    assert is_formula_plausible("Fe2O3") is True


def test_explain_shows_impossible_verdict():
    text = explain_formula_plausibility("C8H23")
    assert "IMPOSSIBLE" in text
    assert "55" in text


def test_explain_shows_unverifiable_for_unknown_elements():
    text = explain_formula_plausibility("NH3")
    assert "Cannot verify" in text
    assert "N" in text
