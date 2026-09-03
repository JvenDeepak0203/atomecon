"""
atomecon - lightweight green chemistry metrics from plain chemical formulas.

No RDKit, no SMILES - just formulas and molar masses.
"""

from .formula import parse_formula, molar_mass
from .reaction import Reaction
from .reaction_log import ReactionLog

__all__ = ["parse_formula", "molar_mass", "Reaction", "ReactionLog"]
__version__ = "0.1.0"
