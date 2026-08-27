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
        # missing an O2 on the reactant side
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
    # Ca(OH)2 + CO2 -> CaCO3 + H2O ; all reactant atoms end up somewhere -
    # here check the 100%-combustion-style case where product IS everything:
    # 2H2 + O2 -> 2H2O, desired product H2O, all reactant mass becomes H2O
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    assert rxn.atom_economy() == pytest.approx(100.0, abs=0.01)


def test_atom_economy_partial_incorporation():
    # Aspirin synthesis: C7H6O3 + C4H6O3 -> C9H8O4 + C2H4O2
    # desired product is aspirin (C9H8O4); acetic acid is a byproduct
    rxn = Reaction(
        reactants={"C7H6O3": 1, "C4H6O3": 1},
        products={"C9H8O4": 1, "C2H4O2": 1},
        desired_product="C9H8O4",
    )
    ae = rxn.atom_economy()
    assert 70 < ae < 80  # known to be roughly 74-75%


def test_theoretical_yield_and_percent_yield():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    # 4 g H2 (~2 mol) is limiting vs plenty of O2
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
    # if isolated mass equals total input mass, waste is 0
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


def test_summary_contains_atom_economy():
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    text = rxn.summary()
    assert "Atom economy" in text
    assert "%" in text
