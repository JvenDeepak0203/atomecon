"""
Streamlit web app for atomecon.

Run locally with:
    streamlit run app.py

Deploy for free at share.streamlit.io (see README for steps).
"""

import streamlit as st

from atomecon import Reaction, is_formula_plausible

# Slider bounds for reactant masses, in grams.
MIN_REACTANT_G = 0.1
MAX_REACTANT_G = 100.0
MASS_STEP_G = 0.1

st.set_page_config(page_title="atomecon", page_icon="🧪")

st.title("🧪 atomecon")
st.caption(
    "Green chemistry metrics from plain chemical formulas - "
    "no RDKit, no SMILES needed."
)

st.divider()

st.subheader("1. Describe your reaction")

col1, col2 = st.columns(2)
with col1:
    reactants_text = st.text_input(
        "Reactants (comma-separated formulas)",
        placeholder="e.g. CH4, O2",
    )
with col2:
    products_text = st.text_input(
        "Products (comma-separated formulas)",
        placeholder="e.g. CO2, H2O",
    )

desired_product = st.text_input(
    "Which product do you care about?",
    placeholder="e.g. CO2",
)

build_clicked = st.button("Balance and analyze", type="primary")

if build_clicked:
    reactant_list = []
    for piece in reactants_text.split(","):
        cleaned = piece.strip()
        if cleaned:
            reactant_list.append(cleaned)

    product_list = []
    for piece in products_text.split(","):
        cleaned = piece.strip()
        if cleaned:
            product_list.append(cleaned)

    desired_clean = desired_product.strip()

    if not reactant_list or not product_list or not desired_clean:
        st.error("Please fill in reactants, products, and the desired product.")
    else:
        implausible_formulas = []
        for formula in reactant_list + product_list:
            if not is_formula_plausible(formula):
                implausible_formulas.append(formula)

        if implausible_formulas:
            st.warning(
                "These formulas look chemically impossible (odd total "
                f"valence): {', '.join(implausible_formulas)}. Double-check "
                "for typos - proceeding anyway, but the result may not "
                "correspond to a real molecule."
            )

        try:
            rxn = Reaction.auto(reactant_list, product_list, desired_clean)
            st.session_state["reaction"] = rxn
            st.session_state["reactant_list"] = reactant_list
            # New reaction means the old yield figure is meaningless.
            st.session_state.pop("actual_yield", None)
        except ValueError as e:
            st.error(str(e))
            st.session_state.pop("reaction", None)

if "reaction" in st.session_state:
    rxn = st.session_state["reaction"]

    st.divider()
    st.subheader("2. Theoretical results")

    st.success(f"Balanced equation: **{rxn.equation()}**")
    st.metric("Atom economy", f"{rxn.atom_economy():.1f}%")

    with st.expander("See the step-by-step calculation"):
        st.text(rxn.explain_atom_economy())

    st.divider()
    st.subheader("3. Optional: add real lab data")
    st.caption(
        "Atom economy above needs no lab data. Drag these only if you "
        "actually ran the reaction and want E-factor / yield too."
    )

    # --- Reactant masses -------------------------------------------------
    reactant_masses = {}
    for formula in st.session_state["reactant_list"]:
        reactant_masses[formula] = st.slider(
            f"Grams of {formula} used",
            min_value=MIN_REACTANT_G,
            max_value=MAX_REACTANT_G,
            value=1.0,
            step=MASS_STEP_G,
            key=f"mass_{formula}",
        )

    # --- The ceiling, recomputed from whatever the sliders now say -------
    theoretical = rxn.theoretical_yield_g(reactant_masses)
    limiting = rxn.limiting_reactant(reactant_masses)

    # Never let the max collapse to zero, or the slider becomes invalid.
    max_yield = round(theoretical, 2)
    if max_yield < 0.01:
        max_yield = 0.01

    # If the reactant sliders moved down, an older yield value may now sit
    # above the new ceiling. Pull it back before drawing the slider.
    if st.session_state.get("actual_yield", 0.0) > max_yield:
        st.session_state["actual_yield"] = max_yield

    st.slider(
        f"Grams of {rxn.desired_product} actually obtained",
        min_value=0.0,
        max_value=max_yield,
        step=0.01,
        key="actual_yield",
    )
    actual_yield = st.session_state["actual_yield"]

    st.caption(
        f"Capped at {max_yield:.2f} g - the theoretical maximum. **{limiting}** "
        "runs out first, so it sets the ceiling. You cannot isolate more "
        "product than the atoms you started with can build."
    )

    # --- Live report -----------------------------------------------------
    if actual_yield <= 0:
        st.info(
            "Drag the yield slider above 0 to see E-factor, percent yield, "
            "and the green grade."
        )
    else:
        st.divider()
        st.subheader("4. Full report")

        col_a, col_b = st.columns(2)
        col_a.metric("Percent yield", f"{rxn.percent_yield(reactant_masses, actual_yield):.1f}%")
        col_b.metric("E-factor", f"{rxn.e_factor(reactant_masses, actual_yield):.2f}")

        st.code(rxn.summary_table(reactant_masses, actual_yield))

st.divider()
st.caption(
    "Built by Jven Deepak with atomecon - source code on "
    "[GitHub](https://github.com/JvenDeepak0203/atomecon)."
)
