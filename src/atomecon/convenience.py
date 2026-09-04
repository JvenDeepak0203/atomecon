"""
One-call convenience function for the common case: you just have
formulas (no coefficients) and, optionally, real lab masses, and you
want the full picture without creating objects and calling several
methods yourself.
"""

from typing import Dict, List, Optional

from .reaction import Reaction


def analyze(
    reactants: List[str],
    products: List[str],
    desired_product: str,
    reactant_masses_g: Optional[Dict[str, float]] = None,
    actual_yield_g: Optional[float] = None,
) -> Reaction:
    """
    Auto-balance the equation, build the Reaction, print a full summary
    table, and return the Reaction object in case you want to do more
    with it afterward.
    """
    rxn = Reaction.auto(reactants, products, desired_product)
    print(rxn.summary_table(reactant_masses_g, actual_yield_g))
    return rxn
