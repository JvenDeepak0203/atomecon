"""
Parsing of plain-text chemical formulas (e.g. "C2H5OH", "Ca(OH)2")
into element counts, and molar mass calculation from those formulas.

No SMILES, no structural chemistry, no external dependencies -
just what's needed for stoichiometry-level calculations.
"""

from typing import Dict

from .elements import ATOMIC_MASSES


def parse_formula(formula: str) -> Dict[str, int]:
    """
    Parse a chemical formula into a dict of {element_symbol: count}.

    Supports nested parentheses and multipliers, e.g.:
        "H2O"        -> {"H": 2, "O": 1}
        "C2H5OH"     -> {"C": 2, "H": 6, "O": 1}
        "Ca(OH)2"    -> {"Ca": 1, "O": 2, "H": 2}
        "Al2(SO4)3"  -> {"Al": 2, "S": 3, "O": 12}

    Raises ValueError on empty input, unknown element symbols, or
    unbalanced parentheses.
    """
    formula = formula.strip()
    if not formula:
        raise ValueError("Formula cannot be empty.")

    invisible_characters = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u00a0"]
    for invisible_char in invisible_characters:
        formula = formula.replace(invisible_char, "")

    if not formula:
        raise ValueError("Formula cannot be empty.")

    stack = [dict()]
    # Coordination compounds are conventionally written with square
    # brackets - K3[Fe(CN)6] - and nested groups sometimes use curly ones,
    # so all three are accepted. The opener is remembered so a mismatched
    # pair is caught rather than silently treated as a group.
    opening_brackets = {"(": ")", "[": "]", "{": "}"}
    closing_brackets = {")": "(", "]": "[", "}": "{"}
    bracket_stack = []
    i = 0
    n = len(formula)

    while i < n:
        char = formula[i]

        if char in opening_brackets:
            stack.append({})
            bracket_stack.append(char)
            i += 1

        elif char in closing_brackets:
            i += 1
            start = i
            while i < n and formula[i].isdigit():
                i += 1
            multiplier = int(formula[start:i]) if i > start else 1

            if len(stack) < 2:
                raise ValueError(f"Unbalanced brackets in formula '{formula}'.")

            expected_opener = closing_brackets[char]
            if bracket_stack[-1] != expected_opener:
                raise ValueError(
                    f"Mismatched brackets in formula '{formula}': "
                    f"'{bracket_stack[-1]}' is closed by '{char}'."
                )
            bracket_stack.pop()

            group = stack.pop()
            for element, count in group.items():
                stack[-1][element] = stack[-1].get(element, 0) + count * multiplier

        elif char.isupper():
            start = i
            i += 1
            while i < n and formula[i].islower():
                i += 1
            element = formula[start:i]

            start_count = i
            while i < n and formula[i].isdigit():
                i += 1
            count = int(formula[start_count:i]) if i > start_count else 1

            if element not in ATOMIC_MASSES:
                raise ValueError(
                    f"Unknown element symbol '{element}' in formula '{formula}'."
                )

            stack[-1][element] = stack[-1].get(element, 0) + count

        else:
            raise ValueError(
                f"Unexpected character {char!r} (Unicode code point "
                f"U+{ord(char):04X}) in formula '{formula}'. If this "
                "character looks blank or invisible, it may have been "
                "accidentally pasted in - try retyping the formula."
            )

    if len(stack) != 1:
        raise ValueError(f"Unbalanced brackets in formula '{formula}'.")

    return stack[0]


def molar_mass(formula: str) -> float:
    """
    Compute the molar mass (g/mol) of a chemical formula string.

    Example:
        molar_mass("H2O") -> 18.015
    """
    counts = parse_formula(formula)
    return sum(ATOMIC_MASSES[element] * count for element, count in counts.items())


_SUBSCRIPT_DIGITS = {
    "0": "\u2080", "1": "\u2081", "2": "\u2082", "3": "\u2083", "4": "\u2084",
    "5": "\u2085", "6": "\u2086", "7": "\u2087", "8": "\u2088", "9": "\u2089",
}


def to_subscripts(formula: str) -> str:
    """Render a formula with proper subscript digits: H2O -> H\u2082O.

    Display only - the result will NOT parse back through parse_formula().
    Keep plain ASCII for anything that needs to line up in a monospace
    table, since subscript glyphs are not fixed width in every font.
    """
    out = ""
    for char in formula:
        if char in _SUBSCRIPT_DIGITS:
            out = out + _SUBSCRIPT_DIGITS[char]
        else:
            out = out + char
    return out
