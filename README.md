# atomecon

🧪 **[Try it live in your browser](https://atomecon.streamlit.app/)** - no install needed.

Lightweight green chemistry metrics - atom economy, theoretical yield, percent yield, E-factor, and automatic equation balancing - computed from **plain chemical formulas**. No RDKit, no SMILES, no dependencies.

## Who this is for

- Chemistry students taking green chemistry coursework, tired of redoing molar-mass arithmetic by hand for every reaction
- Anyone comparing multiple synthesis routes for the same product, who wants to score them programmatically instead of recalculating each one manually
- Developers who want atom economy and equation balancing without installing RDKit or learning SMILES notation

## Why this exists

Existing chemistry packages either don't cover green chemistry metrics at all, or require RDKit and SMILES notation to calculate even a single metric like atom economy. `atomecon` bundles the standard metrics together, balances equations automatically, takes formulas the way you'd write them in a chemistry class (`"C2H5OH"`, not `"CCO"`), and has zero dependencies.

## Install

```bash
pip install atomecon
```

## Quick start

```python
from atomecon import analyze

analyze(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
```

Balances the equation and prints a report. No coefficients, no separate method calls.

## The three kinds of number

This is the distinction the whole library is built around, and the one students most often blur together.

**Atom economy is about the reaction you chose.** It asks what fraction of the reactant mass ends up in the product you wanted, according to the balanced equation. It needs no lab data, and it is identical for everyone who ever runs that reaction. Better technique cannot improve it. Only a different route can.

**Percent yield is about how you ran it.** It compares what you actually isolated against the most the equation allows, given the masses you started with. It varies run to run.

**E-factor is about waste**, in grams of waste per gram of product.

`atomecon` keeps this explicit in its API: `atom_economy()` takes no arguments, while `percent_yield()` and `e_factor()` require real measured masses.

### The E-factor floor

E-factor and atom economy are not independent, and this trips people up. Even a flawless run discards every atom the equation sends into the other products. So the lowest E-factor a reaction can ever reach is fixed by its atom economy:

```
E-factor floor = 100 / atom economy - 1
```

A reaction at 100% atom economy has a floor of 0. One at 50% has a floor of 1.0: a gram of waste per gram of product, forever, no matter how carefully it is run. Methane combustion at 55% can never get below 0.82.

```python
from atomecon import Reaction

rxn = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")

print(rxn.e_factor_floor())
# 0.819...  the best this equation can ever do

masses = {"CH4": 16.043, "O2": 63.996}
print(rxn.excess_e_factor(masses, actual_yield_g=44.0))
# 0.0  a flawless run: all remaining waste is forced by the equation
```

## Green grade

A single A-F letter for comparing reactions at a glance.

```python
print(rxn.green_grade(masses, actual_yield_g=44.0))
# B  (Atom economy: 55% | E-factor: 0.8, best possible 0.8)
```

It scores two deliberately separate things:

- **Atom economy** scores the route you picked.
- **Avoidable waste** - E-factor above the floor - scores how you ran it.

Grading raw E-factor instead would punish a low-atom-economy reaction twice for the same fact, since its floor is set by its atom economy. Under that older approach a perfect run of methane combustion scored no better than a careless one, because the reaction could never reach the top E-factor band regardless. Grading the avoidable part fixes that: technique becomes visible, while a wasteful route still cannot reach an A.

This is a transparent scoring rule of our own devising, **not a scientific standard**. The bands are module-level constants so you can read them, show them to someone, or disagree with them:

```python
from atomecon.reaction import (
    ATOM_ECONOMY_BANDS,      # [(90, 4), (75, 3), (60, 2), (40, 1)]  at least
    AVOIDABLE_WASTE_BANDS,   # [(0.5, 4), (2, 3), (5, 2), (15, 1)]   at most
    grade_letter,
)

grade_letter(3, 3)   # 'B' - the letter for a given pair of scores
```

Worth knowing where these numbers came from. The atom economy thresholds roughly track real categories of reaction. The waste thresholds echo the shape of Sheldon's published E-factor figures, but those describe *total* waste across industries while these apply to *avoidable* waste, which is a different quantity. Treat them as a starting point, not a derivation.

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

print(rxn.limiting_reactant(masses))                    # C7H6O3 - runs out first
print(rxn.theoretical_yield_g(masses))                  # 6.52 g
print(rxn.percent_yield(masses, actual_yield_g=4.2))    # 64.4
print(rxn.e_factor(masses, actual_yield_g=4.2))         # 1.38
print(rxn.e_factor_floor())                             # 0.33
print(rxn.excess_e_factor(masses, actual_yield_g=4.2))  # 1.05
print(rxn.green_grade(masses, actual_yield_g=4.2))      # B  (...)

print(rxn.summary_table(reactant_masses_g=masses, actual_yield_g=4.2))
```

## Automatic equation balancing

```python
rxn = Reaction.auto(["N2", "H2"], ["NH3"], desired_product="NH3")
print(rxn)
# <Reaction N2 + 3H2 -> 2NH3>
```

Gaussian elimination over exact fractions, solving for the smallest whole-number coefficients.

If you only want the coefficients and not a whole `Reaction`:

```python
from atomecon import balance_equation

reactants, products = balance_equation(["CH4", "O2"], ["CO2", "H2O"])
print(reactants, products)
# {'CH4': 1, 'O2': 2} {'CO2': 1, 'H2O': 2}
```

**When one answer is not enough.** Some equations have more than one valid balancing ratio. This is a genuine mathematical ambiguity, not a bug, so `balance_equation()` and `Reaction.auto()` raise rather than guess. To see the options instead:

```python
from atomecon.balance import possible_balances

for reactants, products in possible_balances(["C", "O2"], ["CO", "CO2"]):
    print(reactants, products)
# {'C': 3, 'O2': 2} {'CO': 2, 'CO2': 1}
# {'C': 4, 'O2': 3} {'CO': 2, 'CO2': 2}
# {'C': 5, 'O2': 3} {'CO': 4, 'CO2': 1}
# ...
```

Returned simplest first, every coefficient a positive whole number, every one atom-balanced. It cannot return *all* of them: when the solution space has more than one dimension there are infinitely many, so this returns the tidiest ones found within a bounded search.

Two different things cause this, and they mean opposite things:

- **Several answers are all correct.** Burning carbon really does give a mix of CO and CO2, and the ratio depends on the air supply. Pick the one matching your conditions.
- **One answer is correct and the rest are artifacts.** The aspirin synthesis is ambiguous only because all four species happen to share H:O = 2:1, which makes the oxygen constraint redundant. `11C7H6O3 + C4H6O3 -> 9C9H8O4` balances perfectly and is nonsense.

Atom counts alone cannot tell these apart, so the choice is yours. It matters: across valid balancings of `C + O2 -> CO + CO2`, atom economy for CO2 ranges from 20.8% to 75.9%.

## Impossible results are refused

A yield heavier than everything you put in violates conservation of mass. Left unchecked it produces negative waste, a negative E-factor, and a flattering grade for a reaction that cannot exist.

```python
rxn = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
rxn.e_factor({"CH4": 1.0, "O2": 2.0}, actual_yield_g=40.0)
# ValueError: actual_yield_g (40.00 g) is greater than the total mass of
# reactants used (3.00 g). That breaks conservation of mass ...
```

`Reaction` also verifies the equation is atom-balanced on construction. Pass `allow_unbalanced=True` to override.

## Learning mode: see the calculation

```python
print(rxn.explain_atom_economy())
```

Prints the molar masses, the coefficients, the totals, and the final division as numbered steps.

For the same numbers as data rather than prose:

```python
parts = rxn.atom_economy_breakdown()
print(parts["total_reactant_mass"])   # 80.039
print(parts["reactants"][0])          # {'formula': 'CH4', 'coefficient': 1, ...}
```

## Comparing reactions

```python
from atomecon import Reaction, ReactionLog

combustion = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")

log = ReactionLog()
log.add(
    "Methane combustion",
    combustion,
    reactant_masses_g={"CH4": 16.043, "O2": 63.996},
    actual_yield_g=44.0,
)
log.add("Haber process", Reaction.auto(["N2", "H2"], ["NH3"], desired_product="NH3"))

print(log.comparison_table())
```

Prints a table sorted by atom economy, greenest first. For the same data as records you can feed into a spreadsheet or a web page:

```python
for record in log.to_records():
    print(record["name"], record["atom_economy"], record["grade_letter"])
```

`ReactionLog` is in-memory only. It resets each time your program runs.

## Display helpers

`equation()` returns plain ASCII, which is what you want for terminals, monospace tables, and anything a machine reads back. For showing to people:

```python
print(rxn.pretty_equation())
# CH₄ + 2O₂ → CO₂ + 2H₂O

from atomecon import to_subscripts
print(to_subscripts("Ca(OH)2"))
# Ca(OH)₂
```

Coefficients stay full size, because they multiply the molecule rather than counting atoms inside it.

## Formula plausibility checking

```python
from atomecon import is_formula_plausible

is_formula_plausible("C8H18")   # True  (real octane)
is_formula_plausible("C8H23")   # False (impossible - odd total valence)
is_formula_plausible("Fe2O3")   # True  (iron has variable valence - not checked)
```

**Important limitation:** this can only rule formulas out as impossible. It cannot prove a formula is real, and it deliberately skips elements with variable valence (iron, sulfur, phosphorus, nitrogen, most transition metals) rather than risk a wrong answer. This is one mathematical shortcut, not a replacement for real molecular validity checking.

To see the reasoning rather than just the verdict:

```python
from atomecon import explain_formula_plausibility

print(explain_formula_plausibility("C8H23"))
```

## Formula syntax

```python
from atomecon import parse_formula, molar_mass

parse_formula("Ca(OH)2")       # {"Ca": 1, "O": 2, "H": 2}
parse_formula("Fe3(Fe(CN)6)2") # {"Fe": 5, "C": 12, "N": 12}
molar_mass("C6H12O6")          # 180.156
```

Round, square and curly brackets all group, so coordination compounds can be
written the conventional way:

```python
parse_formula("K3[Fe(CN)6]")   # {"K": 3, "Fe": 1, "C": 6, "N": 6}
parse_formula("[Cu(NH3)4]SO4") # {"Cu": 1, "N": 4, "H": 12, "S": 1, "O": 4}
molar_mass("K3[Fe(CN)6]")      # 329.247
```

Bracket types must match: `K3(Fe(CN)6]` is rejected rather than quietly
accepted.

## What this library does NOT do

- **Does not verify a formula represents a real molecule** beyond the valence-parity check above. No bonding or structure model like RDKit.
- **Does not verify a reaction is chemically real.** It will happily compute metrics for an atom-balanced but chemically impossible reaction.
- **No charge or ionic support.** Formulas are tracked by atoms only, not electric charge.
- **The green grade is not a standard.** It is a scoring rule of our own.

## Try the demo

`demo.py` ships with the source, not with the wheel, so grab the repository:

```bash
git clone https://github.com/JvenDeepak0203/atomecon
cd atomecon
python demo.py
```

A guided tour: balancing, the yield-versus-atom-economy distinction, the E-factor floor, route comparison, and the conservation-of-mass check.

## Web app

Live at [atomecon.streamlit.app](https://atomecon.streamlit.app/), or run it yourself:

```bash
pip install streamlit
streamlit run app.py
```

What the app adds over the library:

- Worked examples in a dropdown, including a deliberately ambiguous one
- Yield sliders capped at the theoretical maximum, so impossible results cannot be entered, with a selectable mass range from 1 g to 1 kg
- The atom economy calculation laid out step by step, with the arithmetic shown
- A picker for equations with several valid balancings
- Save reactions and compare them side by side, sorted greenest first
- Export the comparison to CSV and load it back later
- A reference diagram for how the grade is worked out

## Running tests

```bash
pip install pytest
pytest
```

## Changelog

**0.1.3**

- Square and curly brackets are now accepted in formulas, so coordination compounds such as `K3[Fe(CN)6]` parse. Mismatched bracket types are rejected.
- New `possible_balances()`, which lists the simple whole-number balancings of an ambiguous equation instead of refusing outright.
- Grading bands exposed as `ATOM_ECONOMY_BANDS`, `AVOIDABLE_WASTE_BANDS` and `grade_letter()`, so the rule can be shown rather than only applied.
- Web app: balance picker, CSV import, selectable mass range, grading reference diagram, Prussian blue and ambiguous-reaction examples, and an unreadable formula now reports an error instead of crashing the page.

**0.1.2**

- Yields exceeding the total reactant mass are now rejected. Previously these produced a negative E-factor and an undeservedly good grade.
- `green_grade()` now scores avoidable waste (E-factor above the floor) rather than raw E-factor, so a low-atom-economy reaction is no longer penalised twice and good technique is visible.
- New: `limiting_reactant()`, `e_factor_floor()`, `excess_e_factor()`, `atom_economy_breakdown()`, `pretty_equation()`, `to_subscripts()`, `ReactionLog.to_records()`.
- `comparison_table()` now uses stable column widths and right-aligned numbers.
- Added `demo.py`, which earlier versions of this README referenced without shipping it.
- Web app: example presets, saved-reaction comparison, CSV export, formatted working.

**0.1.1** - initial public release.

## License

MIT
