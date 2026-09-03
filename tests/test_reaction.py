import pytest

from atomecon import Reaction


def test_rejects_empty_reactants():
    with pytest.raises(ValueError):
        Reaction(reactants={}, products={"H2O": 1}, desired_product="H2O")


def test_rejects_desired_product_not_in_products():
    with pytest.raises(ValueError):
        Reaction(
            reactants={"H2": 2, "O2": 1},
            products={"H2O": 2},
            desired_product="CO2",
        )


def test_detects_unbalanced_equation():
    with pytest.raises(ValueError):
        Reaction(
            reactants={"H2": 2},
            products={"H2O": 2},
            desired_product="H2O",
        )


def test_allows_unbalanced_when_explicitly_requested():
    rxn = Reaction(
        reactants={"H2": 2},
        products={"H2O": 2},
        desired_product="H2O",
        allow_unbalanced=True,
    )
    assert rxn.is_balanced is False


def test_atom_economy_full_incorporation():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    assert rxn.atom_economy() == pytest.approx(100.0, abs=0.01)


def test_atom_economy_partial_incorporation():
    rxn = Reaction(
        reactants={"C7H6O3": 1, "C4H6O3": 1},
        products={"C9H8O4": 1, "C2H4O2": 1},
        desired_product="C9H8O4",
    )
    ae = rxn.atom_economy()
    assert 70 < ae < 80


def test_theoretical_yield_and_percent_yield():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    theoretical = rxn.theoretical_yield_g({"H2": 4.0, "O2": 100.0})
    assert theoretical == pytest.approx(35.74, abs=0.1)

    pct = rxn.percent_yield({"H2": 4.0, "O2": 100.0}, actual_yield_g=30.0)
    assert pct == pytest.approx(30.0 / theoretical * 100, abs=0.01)


def test_e_factor_zero_waste_case():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    e_fac = rxn.e_factor({"H2": 4.0, "O2": 32.0}, actual_yield_g=36.0)
    assert e_fac == pytest.approx(0.0, abs=0.01)


def test_e_factor_missing_reactant_mass_raises():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    with pytest.raises(ValueError):
        rxn.e_factor({"H2": 4.0}, actual_yield_g=30.0)


def test_explain_atom_economy_contains_key_numbers():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    text = rxn.explain_atom_economy()
    assert "Step 1" in text
    assert "Step 4" in text
    assert "100.0%" in text


def test_green_grade_is_a_for_clean_reaction():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    grade_text = rxn.green_grade({"H2": 4.0, "O2": 32.0}, actual_yield_g=36.0)
    assert grade_text.startswith("A")


def test_green_grade_contains_both_metrics():
    rxn = Reaction(
        reactants={"C7H6O3": 1, "C4H6O3": 1},
        products={"C9H8O4": 1, "C2H4O2": 1},
        desired_product="C9H8O4",
    )
    grade_text = rxn.green_grade({"C7H6O3": 5.0, "C4H6O3": 5.0}, actual_yield_g=4.2)
    assert "Atom economy" in grade_text
    assert "E-factor" in grade_text


def test_summary_table_has_aligned_columns():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    table = rxn.summary_table({"H2": 4.0, "O2": 32.0}, actual_yield_g=36.0)
    lines = table.split("\n")

    first_length = len(lines[0])
    for line in lines:
        assert len(line) == first_length

    assert "Metric" in lines[0]
    assert "Value" in lines[0]
    assert "Green grade" in table


def test_summary_table_without_lab_data_omits_experimental_rows():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    table = rxn.summary_table()
    assert "Atom economy" in table
    assert "E-factor" not in table


def test_summary_contains_atom_economy():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    text = rxn.summary()
    assert "Atom economy" in text
    assert "%" in text
