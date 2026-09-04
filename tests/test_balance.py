import pytest

from atomecon import balance_equation, Reaction, analyze


def test_balances_water():
    reactants, products = balance_equation(["H2", "O2"], ["H2O"])
    assert reactants == {"H2": 2, "O2": 1}
    assert products == {"H2O": 2}


def test_balances_methane_combustion():
    reactants, products = balance_equation(["CH4", "O2"], ["CO2", "H2O"])
    assert reactants == {"CH4": 1, "O2": 2}
    assert products == {"CO2": 1, "H2O": 2}


def test_balances_ammonia_synthesis():
    reactants, products = balance_equation(["N2", "H2"], ["NH3"])
    assert reactants == {"N2": 1, "H2": 3}
    assert products == {"NH3": 2}


def test_balances_iron_rusting():
    reactants, products = balance_equation(["Fe", "O2"], ["Fe2O3"])
    assert reactants == {"Fe": 4, "O2": 3}
    assert products == {"Fe2O3": 2}


def test_balances_aluminum_oxidation():
    reactants, products = balance_equation(["Al", "O2"], ["Al2O3"])
    assert reactants == {"Al": 4, "O2": 3}
    assert products == {"Al2O3": 2}


def test_reaction_auto_produces_working_reaction():
    rxn = Reaction.auto(["H2", "O2"], ["H2O"], desired_product="H2O")
    assert rxn.is_balanced is True
    assert rxn.atom_economy() == pytest.approx(100.0, abs=0.01)


def test_ambiguous_equation_raises_clear_error():
    with pytest.raises(ValueError):
        balance_equation(
            ["C7H6O3", "C4H6O3"], ["C9H8O4", "C2H4O2"]
        )


def test_analyze_prints_and_returns_reaction(capsys):
    rxn = analyze(["H2", "O2"], ["H2O"], desired_product="H2O")
    captured = capsys.readouterr()
    assert "Atom economy" in captured.out
    assert rxn.is_balanced is True


def test_analyze_with_lab_data_shows_grade(capsys):
    analyze(
        ["H2", "O2"], ["H2O"], desired_product="H2O",
        reactant_masses_g={"H2": 4.0, "O2": 32.0}, actual_yield_g=36.0,
    )
    captured = capsys.readouterr()
    assert "Green grade" in captured.out
