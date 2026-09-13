"""
Automatic chemical equation balancing.

Given just the reactant and product formulas (no coefficients), this
works out the smallest whole-number coefficients that balance the
equation - the same thing you'd do by hand in intro chemistry, done
here with linear algebra instead of trial and error.

HOW IT WORKS (high level):
Every element must appear in equal total amounts on both sides. That
gives one equation per element, with the coefficients as the unknowns.
Solving that system of equations (its "null space") gives the ratio of
coefficients; scaling that ratio up to whole numbers gives the answer.

This file is more mathematically advanced than the rest of the library
(it uses exact fractions and row reduction). If you're reading through
line by line, it's fine to treat this as "trusted machinery" - the way
you'd use a library function without re-deriving how it works - rather
than trace every line the way we did with formula.py.
"""

import math
from fractions import Fraction
from typing import Dict, List, Tuple

from .formula import parse_formula


def balance_equation(
    reactant_formulas: List[str], product_formulas: List[str]
) -> Tuple[Dict[str, int], Dict[str, int]]:
    species = reactant_formulas + product_formulas
    num_species = len(species)

    element_counts_per_species = []
    all_elements = []
    for formula in species:
        counts = parse_formula(formula)
        element_counts_per_species.append(counts)
        for element in counts:
            if element not in all_elements:
                all_elements.append(element)

    num_reactants = len(reactant_formulas)

    matrix = []
    for element in all_elements:
        row = []
        for i, counts in enumerate(element_counts_per_species):
            count = counts.get(element, 0)
            if i >= num_reactants:
                count = -count
            row.append(Fraction(count))
        matrix.append(row)

    coefficients = _solve_null_space(matrix, num_species)

    reactant_coeffs = {}
    for i in range(num_reactants):
        reactant_coeffs[reactant_formulas[i]] = coefficients[i]

    product_coeffs = {}
    for i in range(num_reactants, num_species):
        product_index = i - num_reactants
        product_coeffs[product_formulas[product_index]] = coefficients[i]

    return reactant_coeffs, product_coeffs


def _solve_null_space(matrix, num_species):
    num_rows = len(matrix)

    working = []
    for row in matrix:
        working.append(list(row))

    pivot_columns = []
    current_row = 0

    for col in range(num_species):
        pivot_row = None
        for r in range(current_row, num_rows):
            if working[r][col] != 0:
                pivot_row = r
                break

        if pivot_row is None:
            continue

        working[current_row], working[pivot_row] = working[pivot_row], working[current_row]

        pivot_value = working[current_row][col]
        for c in range(num_species):
            working[current_row][c] = working[current_row][c] / pivot_value

        for r in range(num_rows):
            if r != current_row and working[r][col] != 0:
                factor = working[r][col]
                for c in range(num_species):
                    working[r][c] = working[r][c] - factor * working[current_row][c]

        pivot_columns.append(col)
        current_row += 1
        if current_row == num_rows:
            break

    free_columns = []
    for col in range(num_species):
        if col not in pivot_columns:
            free_columns.append(col)

    if len(free_columns) != 1:
        raise ValueError(
            "Could not automatically balance this equation (expected exactly "
            "one degree of freedom, found "
            f"{len(free_columns)}). Try specifying coefficients manually "
            "with Reaction(reactants={...}, products={...})."
        )

    free_col = free_columns[0]

    values = [Fraction(0)] * num_species
    values[free_col] = Fraction(1)

    for i, col in enumerate(pivot_columns):
        values[col] = -working[i][free_col]

    lcm_of_denominators = 1
    for v in values:
        lcm_of_denominators = _lcm(lcm_of_denominators, v.denominator)

    whole_numbers = []
    for v in values:
        whole_numbers.append(int(v * lcm_of_denominators))

    all_non_positive = True
    for w in whole_numbers:
        if w > 0:
            all_non_positive = False
    if all_non_positive:
        whole_numbers = [-w for w in whole_numbers]

    for w in whole_numbers:
        if w <= 0:
            raise ValueError(
                "Could not automatically balance this equation into all "
                "positive coefficients. Try specifying coefficients "
                "manually with Reaction(reactants={...}, products={...})."
            )

    overall_gcd = whole_numbers[0]
    for w in whole_numbers[1:]:
        overall_gcd = math.gcd(overall_gcd, w)

    simplified = []
    for w in whole_numbers:
        simplified.append(w // overall_gcd)

    return simplified


def _lcm(a, b):
    return a * b // math.gcd(a, b)


def possible_balances(
    reactant_formulas: List[str],
    product_formulas: List[str],
    search_range: int = 6,
    max_solutions: int = 12,
) -> List[Tuple[Dict[str, int], Dict[str, int]]]:
    """Find simple whole-number balancings, simplest first.

    When the solution space has more than one dimension there are
    INFINITELY many valid balancings, so this cannot return all of them
    and does not claim to. It returns the ones built from small
    combinations of the solution basis - which is where the chemically
    meaningful answer lives, if there is one.

    Only solutions where every species has a coefficient of 1 or more are
    returned. A zero would mean that species takes no part, which is a
    different equation from the one that was asked about.

    Ordering is by total coefficient size, so the tidiest equation comes
    first. That is a presentation choice, not a chemical judgement: the
    atom counts cannot tell you which balancing is the real reaction.
    """
    species = reactant_formulas + product_formulas
    num_species = len(species)
    num_reactants = len(reactant_formulas)

    element_counts_per_species = []
    all_elements = []
    for formula in species:
        counts = parse_formula(formula)
        element_counts_per_species.append(counts)
        for element in counts:
            if element not in all_elements:
                all_elements.append(element)

    matrix = []
    for element in all_elements:
        row = []
        for i, counts in enumerate(element_counts_per_species):
            count = counts.get(element, 0)
            if i >= num_reactants:
                count = -count
            row.append(Fraction(count))
        matrix.append(row)

    basis = _null_space_basis(matrix, num_species)
    if not basis:
        return []

    candidates = []
    seen = []
    for multipliers in _integer_combinations(len(basis), search_range):
        vector = [Fraction(0)] * num_species
        for weight, basis_vector in zip(multipliers, basis):
            for i in range(num_species):
                vector[i] = vector[i] + weight * basis_vector[i]

        whole = _to_smallest_whole_numbers(vector)
        if whole is None:
            continue
        if whole in seen:
            continue
        seen.append(whole)
        candidates.append(whole)

    candidates.sort(key=lambda v: (sum(v), max(v)))

    results = []
    for coefficients in candidates[:max_solutions]:
        reactant_coeffs = {}
        for i in range(num_reactants):
            reactant_coeffs[reactant_formulas[i]] = coefficients[i]

        product_coeffs = {}
        for i in range(num_reactants, num_species):
            product_coeffs[product_formulas[i - num_reactants]] = coefficients[i]

        results.append((reactant_coeffs, product_coeffs))

    return results


def _null_space_basis(matrix, num_species):
    """Row reduce, then read off one basis vector per free column."""
    working = []
    for row in matrix:
        working.append(list(row))

    pivot_columns = []
    current_row = 0
    for col in range(num_species):
        pivot_row = None
        for r in range(current_row, len(working)):
            if working[r][col] != 0:
                pivot_row = r
                break
        if pivot_row is None:
            continue

        working[current_row], working[pivot_row] = (
            working[pivot_row], working[current_row]
        )

        pivot_value = working[current_row][col]
        working[current_row] = [x / pivot_value for x in working[current_row]]

        for r in range(len(working)):
            if r != current_row and working[r][col] != 0:
                factor = working[r][col]
                working[r] = [
                    a - factor * b for a, b in zip(working[r], working[current_row])
                ]

        pivot_columns.append(col)
        current_row = current_row + 1

    free_columns = []
    for col in range(num_species):
        if col not in pivot_columns:
            free_columns.append(col)

    basis = []
    for free_col in free_columns:
        vector = [Fraction(0)] * num_species
        vector[free_col] = Fraction(1)
        for row_index, pivot_col in enumerate(pivot_columns):
            vector[pivot_col] = -working[row_index][free_col]
        basis.append(vector)

    return basis


def _integer_combinations(count, search_range):
    """Every tuple of `count` integers in [-search_range, search_range]."""
    if count == 0:
        return []

    values = list(range(-search_range, search_range + 1))
    combinations = [[]]
    for _ in range(count):
        extended = []
        for partial in combinations:
            for value in values:
                extended.append(partial + [value])
        combinations = extended

    result = []
    for combination in combinations:
        if any(value != 0 for value in combination):
            result.append(combination)
    return result


def _to_smallest_whole_numbers(vector):
    """Scale to positive whole numbers, or return None if impossible."""
    denominator_lcm = 1
    for value in vector:
        denominator_lcm = _lcm(denominator_lcm, value.denominator)

    scaled = []
    for value in vector:
        scaled.append(int(value * denominator_lcm))

    if all(x < 0 for x in scaled):
        scaled = [-x for x in scaled]

    if any(x <= 0 for x in scaled):
        return None

    divisor = 0
    for x in scaled:
        divisor = math.gcd(divisor, x)
    if divisor > 1:
        scaled = [x // divisor for x in scaled]

    return tuple(scaled)
