import pytest

from atomecon import Reaction, ReactionLog


def test_empty_log_message():
    log = ReactionLog()
    table = log.comparison_table()
    assert "No reactions added yet" in table


def test_len_tracks_number_added():
    log = ReactionLog()
    assert len(log) == 0

    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    log.add("Water", rxn)
    assert len(log) == 1

    log.add("Water again", rxn)
    assert len(log) == 2


def test_comparison_table_sorted_by_atom_economy_descending():
    log = ReactionLog()

    high_ae = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    low_ae = Reaction(
        reactants={"CH4": 1, "O2": 2},
        products={"CO2": 1, "H2O": 2},
        desired_product="CO2",
    )

    log.add("Combustion", low_ae)
    log.add("Water", high_ae)

    table = log.comparison_table()
    lines = table.split("\n")

    first_data_row = lines[2]
    assert "Water" in first_data_row


def test_comparison_table_shows_grade_when_lab_data_given():
    log = ReactionLog()
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    log.add("Water", rxn, reactant_masses_g={"H2": 4.0, "O2": 32.0}, actual_yield_g=36.0)

    table = log.comparison_table()
    assert "no lab data" not in table
    assert "A" in table


def test_comparison_table_columns_aligned():
    log = ReactionLog()
    rxn = Reaction(
        reactants={"H2": 2, "O2": 1},
        products={"H2O": 2},
        desired_product="H2O",
    )
    log.add("Water", rxn)

    table = log.comparison_table()
    lines = table.split("\n")
    first_length = len(lines[0])
    for line in lines:
        assert len(line) == first_length
