# atomecon

🧪 **[Try it live in your browser](https://atomecon.streamlit.app/)** - no install needed.

Lightweight green chemistry metrics - atom economy, theoretical yield, percent yield, E-factor, and automatic equation balancing - computed from **plain chemical formulas**. No RDKit, no SMILES, no heavy dependencies.

## Who this is for

- Chemistry students taking green chemistry coursework, tired of redoing molar-mass arithmetic by hand for every reaction
- Anyone comparing multiple synthesis routes for the same product, who wants to score them programmatically instead of recalculating each one manually
- Developers who want atom economy and equation balancing without installing RDKit or learning SMILES notation

## Why this exists

Existing chemistry packages either don't cover green chemistry metrics at all (they focus on general stoichiometry), or require RDKit and SMILES notation to calculate even a single metric like atom economy. `atomecon` bundles the standard metrics together, balances equations automatically, takes formulas the way you'd write them in a chemistry class (`"C2H5OH"`, not `"CCO"`), and has zero dependencies.

## Try it without installing anything

**[atomecon.streamlit.app](https://atomecon.streamlit.app/)** - type in a reaction's formulas, get it balanced and analyzed instantly in your browser.

## Install

```bash
pip install atomecon
```

## Core concepts

- **Atom economy** is *theoretical* - it only depends on the balanced equation and molar masses. It's always computable, with no lab data.
- **Theoretical yield**, **percent yield**, and **E-factor** are *experimental* - they depend on the real masses of reactants you used and the real mass of product you isolated. These vary run to run.

`atomecon` keeps this distinction explicit: `atom_economy()` takes no arguments beyond the reaction itself, while `e_factor()` and `percent_yield()` require you to supply real measured masses.

## Quick start - the one-line version

```python
from atomecon import analyze

analyze(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
```
Balances the equation automatically and prints a full report - no coefficients, no separate method calls needed.

## Full walkthrough

```python
from atomecon import Reaction

# Aspirin synthesis: salicylic acid + acetic anhydride -> aspirin + acetic acid
rxn = Reaction(
    reactants={"C7H6O3": 1, "C4H6O3": 1},
    products={"C9H8O4": 1, "C2H4O2": 1},
    desired_product="C9H8O4",
)

print(rxn.atom_economy())
# 75.0  (theoretical - no lab data needed)

masses = {"C7H6O3": 5.0, "C4H6O3": 5.0}
print(rxn.theoretical_yield_g(masses))
print(rxn.percent_yield(masses, actual_yield_g=4.2))
print(rxn.e_factor(masses, actual_yield_g=4.2))
print(rxn.green_grade(masses, actual_yield_g=4.2))

print(rxn.summary_table(reactant_masses_g=masses, actual_yield_g=4.2))
```

## Automatic equation balancing

Don't want to work out coefficients yourself? Just give formulas:

```python
from atomecon import Reaction

rxn = Reaction.auto(["N2", "H2"], ["NH3"], desired_product="NH3")
print(rxn)
# <Reaction N2 + 3H2 -> 2NH3>
```

This uses real linear algebra (Gaussian elimination over exact fractions) to solve for the smallest whole-number coefficients - the same process you'd do by hand, automated.

**Known limitation:** a small number of equations have more than one valid balancing ratio (a genuine mathematical ambiguity, not a bug) and will raise a clear error asking you to specify coefficients manually instead of guessing.

## Learning mode: see the calculation, not just the answer

```python
print(rxn.explain_atom_economy())
```

## Green grade: one number to compare reactions at a glance

```python
print(rxn.green_grade(masses, actual_yield_g=4.2))
# B  (Atom economy: 75% | E-factor: 1.4)
```

A simple, transparent scoring rule (not a scientific standard) - combines atom economy and E-factor into a single A-F grade.

## Comparing multiple reactions

```python
from atomecon import Reaction, ReactionLog

log = ReactionLog()
log.add("Aspirin route", rxn, reactant_masses_g=masses, actual_yield_g=4.2)

combustion = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
log.add("Methane combustion", combustion)

print(log.comparison_table())
```
Builds a table sorted by atom economy (greenest first). `ReactionLog` is in-memory only - it resets each time your program runs.

## Formula plausibility checking

```python
from atomecon import is_formula_plausible

is_formula_plausible("C8H18")   # True  (real octane)
is_formula_plausible("C8H23")   # False (impossible - odd total valence)
is_formula_plausible("Fe2O3")   # True  (iron has variable valence - not checked, benefit of the doubt)
```

**Important limitation:** this can only rule out formulas as impossible - it cannot prove a formula is real, and it deliberately skips elements with variable real-world valence (iron, sulfur, phosphorus, nitrogen, most transition metals) rather than risk a wrong answer. This is a long way from full molecular validity checking (which is what RDKit does using real molecular structure) - it's one useful mathematical shortcut, not a replacement for it.

## Formula syntax

```python
from atomecon import parse_formula, molar_mass

parse_formula("Ca(OH)2")       # {"Ca": 1, "O": 2, "H": 2}
parse_formula("Fe3(Fe(CN)6)2") # {"Fe": 5, "C": 12, "N": 12}
molar_mass("C6H12O6")          # 180.156
```

## Reaction balance checking

`Reaction` verifies the equation is atom-balanced on construction and raises a clear error if it isn't. Pass `allow_unbalanced=True` to override.

## What this library does NOT do (known scope limits)

- **Does not verify a formula represents a real molecule** beyond the basic valence-parity check above - no bonding/structure model like RDKit
- **Does not verify a reaction is chemically real** - it will calculate metrics for atom-balanced but chemically implausible reactions
- **No charge/ionic support** - formulas are tracked by atoms only, not electric charge

## Try the demo script

```bash
python demo.py
```

## Web app

Live at [atomecon.streamlit.app](https://atomecon.streamlit.app/), or run it yourself:
```bash
pip install streamlit
streamlit run app.py
```

## Running tests

```bash
pip install pytest
pytest
```

## License

MIT
