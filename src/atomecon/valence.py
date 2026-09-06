"""
A heuristic, partial check for whether a chemical formula could
plausibly represent a real molecule - NOT a full chemical validity
checker like RDKit (which uses actual molecular structure and bonding
rules). This uses one real, well-known shortcut instead.

THE IDEA (valence parity / the "handshake lemma"):
Every bond in a molecule connects exactly two atoms. That means the
total valence (bonding capacity) used across the whole molecule must
always add up to an EVEN number - every bond "uses up" exactly 2 units
of valence, one from each atom it connects, regardless of how those
bonds are arranged. If a formula's total valence adds up to an odd
number, no valid molecule could have that formula - no arrangement of
bonds could ever balance it.

Example: C8H23
  carbon has 4 bonds each, hydrogen has 1 bond each
  8 x 4 + 23 x 1 = 32 + 23 = 55 (odd) -> impossible
Example: C8H18 (real octane)
  8 x 4 + 18 x 1 = 32 + 18 = 50 (even) -> passes

IMPORTANT LIMITATIONS (read before trusting this too much):
- This can only ever RULE OUT impossible formulas - passing this check
  does not prove a formula is real, only that it isn't obviously broken.
- Many elements (iron, sulfur, phosphorus, nitrogen, and most transition
  metals) have VARIABLE valence in real chemistry, so we deliberately
  refuse to guess for them. If a formula contains ANY element without a
  reliable fixed valence, this check is skipped entirely and the formula
  is treated as "unverifiable" rather than risking a wrong answer.
"""

from typing import Tuple

from .formula import parse_formula

FIXED_VALENCE = {
    "H": 1,
    "F": 1,
    "Cl": 1,
    "Br": 1,
    "I": 1,
    "Li": 1,
    "Na": 1,
    "K": 1,
    "O": 2,
    "Be": 2,
    "Mg": 2,
    "Ca": 2,
    "Al": 3,
    "C": 4,
}


def is_formula_plausible(formula: str) -> bool:
    can_verify, total_valence = _total_known_valence(formula)
    if not can_verify:
        return True
    return total_valence % 2 == 0


def explain_formula_plausibility(formula: str) -> str:
    counts = parse_formula(formula)

    lines = []
    lines.append(f"Plausibility check for {formula}:")
    lines.append("")

    unknown_elements = []
    known_total = 0
    for element, count in counts.items():
        if element in FIXED_VALENCE:
            valence = FIXED_VALENCE[element]
            contribution = valence * count
            known_total = known_total + contribution
            lines.append(
                f"  {element}: valence {valence} x {count} = {contribution}"
            )
        else:
            unknown_elements.append(element)
            lines.append(f"  {element}: valence not reliably known - skipped")

    lines.append("")

    if unknown_elements:
        lines.append(
            f"Cannot verify: {', '.join(unknown_elements)} "
            "have variable valence in real chemistry, so no firm "
            "conclusion can be drawn. Treated as plausible."
        )
    else:
        lines.append(f"Total valence = {known_total}")
        if known_total % 2 == 0:
            lines.append(f"{known_total} is even -> passes (a valid molecule could exist)")
        else:
            lines.append(
                f"{known_total} is odd -> IMPOSSIBLE - no valid molecule "
                "can have this formula"
            )

    text = ""
    for i, line in enumerate(lines):
        if i > 0:
            text = text + "\n"
        text = text + line
    return text


def _total_known_valence(formula: str) -> Tuple[bool, int]:
    counts = parse_formula(formula)

    total = 0
    for element, count in counts.items():
        if element not in FIXED_VALENCE:
            return False, 0
        total = total + FIXED_VALENCE[element] * count

    return True, total
