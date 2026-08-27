import pytest

from atomecon import parse_formula, molar_mass


def test_simple_formula():
    assert parse_formula("H2O") == {"H": 2, "O": 1}


def test_formula_with_implicit_one():
    assert parse_formula("NaCl") == {"Na": 1, "Cl": 1}


def test_formula_no_digits_after_element():
    assert parse_formula("CO") == {"C": 1, "O": 1}


def test_condensed_organic_formula():
    # ethanol written the way a beginner course teaches it
    assert parse_formula("C2H5OH") == {"C": 2, "H": 6, "O": 1}


def test_parentheses_with_multiplier():
    assert parse_formula("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}


def test_nested_parentheses():
    assert parse_formula("Al2(SO4)3") == {"Al": 2, "S": 3, "O": 12}


def test_empty_formula_raises():
    with pytest.raises(ValueError):
        parse_formula("")


def test_unknown_element_raises():
    with pytest.raises(ValueError):
        parse_formula("Xx2O")


def test_unbalanced_parentheses_raises():
    with pytest.raises(ValueError):
        parse_formula("Ca(OH2")


def test_molar_mass_water():
    assert molar_mass("H2O") == pytest.approx(18.015, abs=0.01)


def test_molar_mass_glucose():
    assert molar_mass("C6H12O6") == pytest.approx(180.156, abs=0.01)
