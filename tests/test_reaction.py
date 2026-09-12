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


def test_equation_method_returns_plain_arrow_string():
    from atomecon import Reaction
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    assert rxn.equation() == "2H2 + O2 -> 2H2O"
    assert "<Reaction" not in rxn.equation()


def test_yield_exceeding_reactant_mass_is_rejected():
    """The bug found in the web app: 3 g in, 40 g out is impossible."""
    rxn = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
    masses = {"CH4": 1.0, "O2": 2.0}

    with pytest.raises(ValueError, match="conservation of mass"):
        rxn.e_factor(masses, actual_yield_g=40.0)

    with pytest.raises(ValueError, match="conservation of mass"):
        rxn.percent_yield(masses, actual_yield_g=40.0)


def test_impossible_yield_cannot_earn_a_green_grade():
    rxn = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
    with pytest.raises(ValueError):
        rxn.green_grade({"CH4": 1.0, "O2": 2.0}, actual_yield_g=40.0)


def test_e_factor_never_negative_for_valid_input():
    rxn = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
    masses = {"CH4": 1.0, "O2": 2.0}
    assert rxn.e_factor(masses, actual_yield_g=1.0) >= 0


def test_yield_exactly_equal_to_input_mass_is_allowed():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    assert rxn.e_factor({"H2": 4.0, "O2": 32.0}, actual_yield_g=36.0) == pytest.approx(0.0, abs=0.01)


def test_limiting_reactant_identifies_the_scarce_one():
    rxn = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
    assert rxn.limiting_reactant({"CH4": 1.0, "O2": 2.0}) == "O2"
    assert rxn.limiting_reactant({"CH4": 0.01, "O2": 100.0}) == "CH4"


def _methane():
    return Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")


def test_e_factor_floor_follows_from_atom_economy():
    rxn = _methane()
    expected = 100.0 / rxn.atom_economy() - 1.0
    assert rxn.e_factor_floor() == pytest.approx(expected, abs=1e-9)


def test_perfect_atom_economy_means_zero_floor():
    rxn = Reaction.auto(["N2", "H2"], ["NH3"], desired_product="NH3")
    assert rxn.atom_economy() == pytest.approx(100.0, abs=0.01)
    assert rxn.e_factor_floor() == pytest.approx(0.0, abs=1e-9)


def test_a_flawless_run_has_no_avoidable_waste():
    """Exact stoichiometry at 100% yield: all remaining waste is forced."""
    rxn = _methane()
    masses = {"CH4": 16.043, "O2": 63.996}
    perfect = rxn.theoretical_yield_g(masses)
    assert rxn.excess_e_factor(masses, perfect) == pytest.approx(0.0, abs=0.01)
    # ...but the raw E-factor is still well above zero, and that is the point.
    assert rxn.e_factor(masses, perfect) > 0.8


def test_perfect_technique_is_no_longer_invisible():
    """A flawless run of a mediocre route must outscore a sloppy one."""
    rxn = _methane()
    masses = {"CH4": 16.043, "O2": 63.996}
    perfect_grade = rxn.green_grade(masses, rxn.theoretical_yield_g(masses))
    sloppy_grade = rxn.green_grade({"CH4": 60.6, "O2": 58.1}, 38.8)
    assert perfect_grade.startswith("B")
    assert sloppy_grade.startswith("C")


def test_grade_reports_the_floor_so_the_number_is_interpretable():
    rxn = _methane()
    text = rxn.green_grade({"CH4": 60.6, "O2": 58.1}, 38.8)
    assert "best possible" in text


def test_pretty_equation_uses_a_real_arrow_and_subscripts():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    assert rxn.pretty_equation() == "2H\u2082 + O\u2082 \u2192 2H\u2082O"


def test_pretty_equation_keeps_coefficients_full_size():
    """The leading 2 multiplies the molecule; it is not an atom count."""
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    assert rxn.pretty_equation().startswith("2H")


def test_plain_equation_is_unchanged_for_machines_and_monospace():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    assert rxn.equation() == "2H2 + O2 -> 2H2O"
