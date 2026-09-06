"""
atomecon - lightweight green chemistry metrics from plain chemical formulas.

No RDKit, no SMILES - just formulas and molar masses.
"""

from .formula import parse_formula, molar_mass
from .reaction import Reaction
from .reaction_log import ReactionLog
from .balance import balance_equation
from .convenience import analyze
from .valence import is_formula_plausible, explain_formula_plausibility

__all__ = [
    "parse_formula",
    "molar_mass",
    "Reaction",
    "ReactionLog",
    "balance_equation",
    "analyze",
    "is_formula_plausible",
    "explain_formula_plausibility",
]
__version__ = "0.1.0"
