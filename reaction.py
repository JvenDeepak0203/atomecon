"""
Core Reaction class for green-chemistry metrics.

Design note on atom economy vs. E-factor / yield:

  - Atom economy is a THEORETICAL property of the balanced equation itself
    (which atoms end up in the desired product vs. the other products).
    It never changes for a given equation - it needs no lab data.

  - E-factor and percent yield are EXPERIMENTAL - they depend on the actual
    masses of reactants you used and the actual mass of product you isolated,
    which vary run to run due to side reactions, losses, and impurities.

This class keeps that distinction explicit in its API: atom_economy() takes
no experimental arguments, while e_factor() and percent_yield() require
real measured masses.

Note: this version deliberately avoids comprehensions / generator expressions
and writes every loop out the long way, for readability while learning.
"""

from typing import Dict, Optional

from .formula import parse_formula, molar_mass


class Reaction:
    def __init__(
        self,
        reactants: Dict[str, int],
        products: Dict[str, int],
        desired_product: str,
        allow_unbalanced: bool = False,
    ):
        """
        reactants / products: dict of {formula: stoichiometric_coefficient}
        desired_product: the formula (must be a key in `products`) whose
                          atom economy / yield you care about.
        allow_unbalanced: if False (default), raises ValueError when the
                          equation's atom counts don't balance on both sides.
        """
        if not reactants:
            raise ValueError("`reactants` cannot be empty.")
        if not products:
            raise ValueError("`products` cannot be empty.")
        if desired_product not in products:
            raise ValueError(
                f"desired_product '{desired_product}' must be a key in `products`."
            )

        # Store exactly what was passed in, so every method can reach it
        # later via self.reactants / self.products / self.desired_product.
        self.reactants = reactants
        self.products = products
        self.desired_product = desired_product

        # Build a dictionary of molar masses for every reactant.
        # Long-form version of what used to be a one-line dict comprehension.
        self._reactant_masses = {}
        for formula in reactants:
            self._reactant_masses[formula] = molar_mass(formula)

        # Same idea, for every product.
        self._product_masses = {}
        for formula in products:
            self._product_masses[formula] = molar_mass(formula)

        self.is_balanced = self._check_balanced()
        if not self.is_balanced and not allow_unbalanced:
            raise ValueError(
                "Reaction is not balanced (atom counts differ between "
                "reactants and products). Pass allow_unbalanced=True to "
                "override, but note that atom economy is not meaningful "
                "for an unbalanced equation."
            )

    # ---------- internal helpers ----------

    def _total_atoms(self, compounds: Dict[str, int]) -> Dict[str, int]:
        """
        Given a dict like {"H2": 2, "O2": 1}, return the total count of
        each individual element across all of them, e.g. {"H": 4, "O": 2}.
        """
        totals: Dict[str, int] = {}

        # Go through each compound on this side of the equation.
        for formula, coeff in compounds.items():
            # Break that formula down into its elements, e.g. "H2" -> {"H": 2}
            element_counts = parse_formula(formula)

            # Add each element's count (scaled by the coefficient) to the running total.
            for element, count in element_counts.items():
                if element not in totals:
                    totals[element] = 0
                totals[element] = totals[element] + count * coeff

        return totals

    def _check_balanced(self) -> bool:
        reactant_totals = self._total_atoms(self.reactants)
        product_totals = self._total_atoms(self.products)
        return reactant_totals == product_totals

    # ---------- theoretical metrics (no lab data needed) ----------

    def atom_economy(self) -> float:
        """
        % of total reactant mass that ends up in the desired product,
        assuming the reaction as written goes to completion.
        Purely theoretical - based only on the balanced equation.
        """
        # mass of the desired product = (molar mass) x (how many the equation makes)
        one_unit_mass = self._product_masses[self.desired_product]
        how_many_made = self.products[self.desired_product]
        desired_mass = one_unit_mass * how_many_made

        # total mass of all reactants combined
        total_reactant_mass = 0
        for formula, coeff in self.reactants.items():
            mass_of_this_reactant = self._reactant_masses[formula] * coeff
            total_reactant_mass = total_reactant_mass + mass_of_this_reactant

        return desired_mass / total_reactant_mass * 100

    def explain_atom_economy(self) -> str:
        """
        Same result as atom_economy(), but returns a step-by-step
        breakdown of the calculation instead of just the final number.
        Meant for learning/teaching, not for use in other code.
        """
        lines = []
        lines.append(f"Atom economy for {self.desired_product}:")
        lines.append("")

        one_unit_mass = self._product_masses[self.desired_product]
        how_many_made = self.products[self.desired_product]
        desired_mass = one_unit_mass * how_many_made

        lines.append(
            f"Step 1: Molar mass of desired product ({self.desired_product}) "
            f"= {one_unit_mass:.2f} g/mol"
        )
        lines.append(
            f"Step 2: Product coefficient = {how_many_made}  ->  "
            f"desired mass = {one_unit_mass:.2f} x {how_many_made} "
            f"= {desired_mass:.2f} g"
        )
        lines.append("")
        lines.append("Step 3: Reactant masses:")

        total_reactant_mass = 0
        for formula, coeff in self.reactants.items():
            one_mass = self._reactant_masses[formula]
            mass_of_this_reactant = one_mass * coeff
            total_reactant_mass = total_reactant_mass + mass_of_this_reactant
            lines.append(
                f"  {formula} (coeff {coeff}): {one_mass:.2f} g/mol x {coeff} "
                f"= {mass_of_this_reactant:.2f} g"
            )

        lines.append(f"  Total reactant mass = {total_reactant_mass:.2f} g")
        lines.append("")

        result = desired_mass / total_reactant_mass * 100
        lines.append(
            f"Step 4: {desired_mass:.2f} / {total_reactant_mass:.2f} x 100 "
            f"= {result:.1f}%"
        )

        text = ""
        for i, line in enumerate(lines):
            if i > 0:
                text = text + "\n"
            text = text + line
        return text

    # ---------- experimental metrics (need real lab data) ----------

    def theoretical_yield_g(self, reactant_masses_g: Dict[str, float]) -> float:
        """
        Given the actual masses (g) of each reactant you used, find the
        limiting reagent and compute the maximum possible mass (g) of the
        desired product the stoichiometry allows.
        """
        self._validate_reactant_masses(reactant_masses_g)

        # For each reactant: how many "equation-units" worth do we actually have?
        # (moles available) / (coefficient in the equation)
        # Whichever reactant gives the SMALLEST ratio is the limiting reagent -
        # it runs out first and caps how much product can form.
        smallest_ratio_so_far = None
        for formula, coeff in self.reactants.items():
            moles_available = reactant_masses_g[formula] / self._reactant_masses[formula]
            ratio = moles_available / coeff

            if smallest_ratio_so_far is None or ratio < smallest_ratio_so_far:
                smallest_ratio_so_far = ratio

        limiting_ratio = smallest_ratio_so_far

        product_moles = limiting_ratio * self.products[self.desired_product]
        return product_moles * self._product_masses[self.desired_product]

    def percent_yield(
        self, reactant_masses_g: Dict[str, float], actual_yield_g: float
    ) -> float:
        """% of the theoretical maximum product mass that was actually obtained."""
        theoretical = self.theoretical_yield_g(reactant_masses_g)
        return actual_yield_g / theoretical * 100

    def e_factor(
        self, reactant_masses_g: Dict[str, float], actual_yield_g: float
    ) -> float:
        """
        Environmental factor: kg (or g) of waste produced per kg (or g) of
        product actually isolated. Lower is greener; 0 is ideal (no waste).

            E-factor = (total input mass - actual product mass) / actual product mass
        """
        self._validate_reactant_masses(reactant_masses_g)
        if actual_yield_g <= 0:
            raise ValueError("actual_yield_g must be positive.")

        # Add up every reactant mass the user actually used.
        total_input_mass = 0
        for mass in reactant_masses_g.values():
            total_input_mass = total_input_mass + mass

        waste = total_input_mass - actual_yield_g
        return waste / actual_yield_g

    def _validate_reactant_masses(self, reactant_masses_g: Dict[str, float]) -> None:
        """Make sure the user supplied a mass for every reactant in the equation."""
        missing = []
        for formula in self.reactants:
            if formula not in reactant_masses_g:
                missing.append(formula)

        if missing:
            raise ValueError(
                f"reactant_masses_g is missing entries for: {sorted(missing)}"
            )

    def green_grade(
        self, reactant_masses_g: Dict[str, float], actual_yield_g: float
    ) -> str:
        """
        Combine atom economy and E-factor into a single A-F letter grade,
        as a quick at-a-glance summary of how "green" this reaction is.

        This is a simple, transparent scoring rule - not a scientific
        standard - meant to make the two numbers easier to interpret together.
        """
        ae = self.atom_economy()
        ef = self.e_factor(reactant_masses_g, actual_yield_g)

        # Atom economy: higher is better.
        if ae >= 90:
            ae_points = 4
        elif ae >= 75:
            ae_points = 3
        elif ae >= 60:
            ae_points = 2
        elif ae >= 40:
            ae_points = 1
        else:
            ae_points = 0

        # E-factor: lower is better (0 = no waste at all).
        if ef <= 0.5:
            ef_points = 4
        elif ef <= 2:
            ef_points = 3
        elif ef <= 5:
            ef_points = 2
        elif ef <= 15:
            ef_points = 1
        else:
            ef_points = 0

        average_points = (ae_points + ef_points) / 2

        if average_points >= 3.5:
            letter = "A"
        elif average_points >= 2.5:
            letter = "B"
        elif average_points >= 1.5:
            letter = "C"
        elif average_points >= 0.5:
            letter = "D"
        else:
            letter = "F"

        return (
            f"{letter}  (Atom economy: {ae:.0f}% | E-factor: {ef:.1f})"
        )

    # ---------- reporting ----------

    def summary(
        self,
        reactant_masses_g: Optional[Dict[str, float]] = None,
        actual_yield_g: Optional[float] = None,
    ) -> str:
        """
        Human-readable report. Always includes atom economy.
        Includes yield / E-factor too if experimental data is supplied.
        """
        lines = [
            f"Reaction: {self._equation_str()}",
            f"Balanced: {self.is_balanced}",
            f"Atom economy ({self.desired_product}): {self.atom_economy():.1f}%",
        ]

        if reactant_masses_g is not None and actual_yield_g is not None:
            theoretical = self.theoretical_yield_g(reactant_masses_g)
            yield_pct = self.percent_yield(reactant_masses_g, actual_yield_g)
            e_fac = self.e_factor(reactant_masses_g, actual_yield_g)
            lines.append(f"Theoretical yield: {theoretical:.2f} g")
            lines.append(
                f"Actual yield: {actual_yield_g:.2f} g ({yield_pct:.1f}% of theoretical)"
            )
            lines.append(f"E-factor: {e_fac:.2f} (g waste per g product)")
        else:
            lines.append(
                "E-factor / yield not shown - pass reactant_masses_g and "
                "actual_yield_g to include them."
            )

        result = ""
        for i, line in enumerate(lines):
            if i > 0:
                result = result + "\n"
            result = result + line
        return result

    def _equation_str(self) -> str:
        def side(compounds):
            parts = []
            for formula, coeff in compounds.items():
                if coeff != 1:
                    parts.append(f"{coeff}{formula}")
                else:
                    parts.append(formula)

            text = ""
            for i, part in enumerate(parts):
                if i > 0:
                    text = text + " + "
                text = text + part
            return text

        return f"{side(self.reactants)} -> {side(self.products)}"

    def __repr__(self) -> str:
        return f"<Reaction {self._equation_str()}>"
