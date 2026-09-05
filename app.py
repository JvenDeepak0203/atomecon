"""
Streamlit web app for atomecon.

Run locally with:
    streamlit run app.py

Deploy for free at share.streamlit.io (see README for steps).
"""

import streamlit as st

from atomecon import Reaction

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
        try:
            rxn = Reaction.auto(reactant_list, product_list, desired_clean)
            st.session_state["reaction"] = rxn
            st.session_state["reactant_list"] = reactant_list
        except ValueError as e:
            st.error(str(e))
            st.session_state.pop("reaction", None)

if "reaction" in st.session_state:
    rxn = st.session_state["reaction"]

    st.divider()
    st.subheader("2. Theoretical results")

    st.success(f"Balanced equation: **{rxn}**".replace("<Reaction ", "").replace(">", ""))
    st.metric("Atom economy", f"{rxn.atom_economy():.1f}%")

    with st.expander("See the step-by-step calculation"):
        st.text(rxn.explain_atom_economy())

    st.divider()
    st.subheader("3. Optional: add real lab data")
    st.caption(
        "Atom economy above needs no lab data. Fill this in only if you "
        "actually ran the reaction and want E-factor / yield too."
    )

    reactant_masses = {}
    for formula in st.session_state["reactant_list"]:
        mass = st.number_input(
            f"Grams of {formula} used", min_value=0.0, value=0.0, key=f"mass_{formula}"
        )
        reactant_masses[formula] = mass

    actual_yield = st.number_input(
        f"Grams of {rxn.desired_product} actually obtained", min_value=0.0, value=0.0
    )

    if st.button("Calculate experimental metrics"):
        all_masses_given = True
        for mass in reactant_masses.values():
            if mass <= 0:
                all_masses_given = False

        if not all_masses_given or actual_yield <= 0:
            st.error("Please enter a positive mass for every reactant and the actual yield.")
        else:
            st.divider()
            st.subheader("4. Full report")
            st.code(rxn.summary_table(reactant_masses, actual_yield))

st.divider()
st.caption(
    "Built with atomecon - source code on "
    "[GitHub](https://github.com/JvenDeepak0203/atomecon)."
)
