"""
A short tour of atomecon. Run it with:

    python demo.py

Nothing here needs lab equipment. Atom economy comes from the balanced
equation alone; the lab numbers further down are made up so the
experimental metrics have something to chew on.
"""

from atomecon import Reaction, ReactionLog, analyze


def rule(title):
    print()
    print("=" * 68)
    print(title)
    print("=" * 68)


rule("1. The one-liner")
print("Give it formulas, get a balanced equation and a full report.")
print()
analyze(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")


rule("2. Balancing, done for you")
print("No coefficients needed. This is Gaussian elimination over exact")
print("fractions, solving for the smallest whole numbers.")
print()
for reactants, products, target in [
    (["N2", "H2"], ["NH3"], "NH3"),
    (["Fe", "O2"], ["Fe2O3"], "Fe2O3"),
    (["C2H5OH", "O2"], ["CO2", "H2O"], "CO2"),
]:
    rxn = Reaction.auto(reactants, products, desired_product=target)
    print(f"  {rxn.equation():<32} atom economy {rxn.atom_economy():5.1f}%")


rule("3. Why atom economy is not percent yield")
aspirin = Reaction(
    reactants={"C7H6O3": 1, "C4H6O3": 1},
    products={"C9H8O4": 1, "C2H4O2": 1},
    desired_product="C9H8O4",
)
print("Aspirin synthesis, with 5 g of each reactant and 4.2 g isolated.")
print()
masses = {"C7H6O3": 5.0, "C4H6O3": 5.0}
print(f"  Atom economy    {aspirin.atom_economy():.1f}%   (fixed by the equation)")
print(f"  Percent yield   {aspirin.percent_yield(masses, 4.2):.1f}%   (depends on the run)")
print(f"  Limiting        {aspirin.limiting_reactant(masses)}")
print()
print("The first number is the same for everyone who ever runs this")
print("reaction. The second is about you.")


rule("4. The floor nobody can get under")
print("E-factor counts grams of waste per gram of product. It cannot go")
print("below what the equation permits, and that limit follows directly")
print("from atom economy:  floor = 100 / atom economy - 1")
print()
print(f"  Measured E-factor  {aspirin.e_factor(masses, 4.2):.2f}")
print(f"  Best possible      {aspirin.e_factor_floor():.2f}")
print(f"  Avoidable waste    {aspirin.excess_e_factor(masses, 4.2):.2f}")
print()
print("The grade scores the avoidable part, not the forced part.")
print(f"  Green grade        {aspirin.green_grade(masses, 4.2)}")


rule("5. Show your working")
print(aspirin.explain_atom_economy())


rule("6. Comparing routes")
print("Route choice beats technique. Here is the evidence.")
print()
log = ReactionLog()
log.add("Aspirin synthesis", aspirin, reactant_masses_g=masses, actual_yield_g=4.2)
log.add("Haber process", Reaction.auto(["N2", "H2"], ["NH3"], desired_product="NH3"))
log.add(
    "Methane combustion",
    Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2"),
    reactant_masses_g={"CH4": 16.043, "O2": 63.996},
    actual_yield_g=44.0,
)
print(log.comparison_table())


rule("7. Impossible numbers are refused")
print("Conservation of mass is checked. You cannot isolate more product")
print("than the total mass you put in.")
print()
combustion = Reaction.auto(["CH4", "O2"], ["CO2", "H2O"], desired_product="CO2")
try:
    combustion.e_factor({"CH4": 1.0, "O2": 2.0}, actual_yield_g=40.0)
except ValueError as error:
    print(f"  ValueError: {error}")


rule("8. Formula checking")
print("A parity check on total valence. It can prove a formula impossible;")
print("it cannot prove one real.")
print()
from atomecon import is_formula_plausible, parse_formula, molar_mass

for formula in ["C8H18", "C8H23", "Fe2O3"]:
    print(f"  {formula:<8} plausible: {is_formula_plausible(formula)}")
print()
print(f"  parse_formula('Fe3(Fe(CN)6)2') -> {parse_formula('Fe3(Fe(CN)6)2')}")
print(f"  molar_mass('C6H12O6')          -> {molar_mass('C6H12O6')}")

print()
print("Full documentation: https://github.com/JvenDeepak0203/atomecon")
print("Try it in a browser:  https://atomecon.streamlit.app/")
print()
