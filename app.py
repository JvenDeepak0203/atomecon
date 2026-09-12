"""
Streamlit web app for atomecon.

Run locally with:
    streamlit run app.py

Deploy for free at share.streamlit.io (see README for steps).
"""

import pandas as pd
import streamlit as st

from atomecon import Reaction, ReactionLog, is_formula_plausible

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

# Saved reactions live here for the length of the browser session.
if "saved" not in st.session_state:
    st.session_state["saved"] = []

with st.expander("New here? What these numbers mean"):
    st.markdown(
        """
**Atom economy** asks: of all the atoms you put in, what fraction end up
in the product you actually wanted?

$$\\text{Atom economy} = \\frac{\\text{mass of desired product}}{\\text{total mass of reactants}} \\times 100$$

It depends only on the balanced equation, so it is the same number for
everyone who ever runs that reaction. You cannot improve it with better
technique - only by choosing a different route to the same product.

**Percent yield** is the opposite kind of number. It compares what you
actually isolated against the most the equation allows, so it measures
*you*: your technique, your losses, your conversion.

The two are independent, and that trips people up. A reaction can hit
100% yield and still be wasteful, if the equation sends half its atoms
into a by-product. Burning methane is exactly that - 55% atom economy,
because every single run discards the water.

**E-factor** counts grams of waste per gram of product. Lower is better;
0 would mean nothing wasted at all.

**The floor.** E-factor cannot go below what atom economy permits. Even a
flawless run discards whatever the equation sends elsewhere, so the best
achievable E-factor is `100 / atom economy - 1`. A reaction at 50% atom
economy can never beat 1.0, however carefully it is run. This app shows
you that floor and grades the waste *above* it - the part you could
actually have avoided.
        """
    )

st.divider()

st.subheader("1. Describe your reaction")

# Ready-made reactions so a first-time visitor sees the tool work
# immediately. Every one of these auto-balances - do not add an equation
# without checking, since some have more than one valid balancing ratio
# and Reaction.auto() will refuse them.
EXAMPLES = {
    "Start from an example...": None,
    "Methane combustion": ("CH4, O2", "CO2, H2O", "CO2"),
    "Haber process (ammonia)": ("N2, H2", "NH3", "NH3"),
    "Rusting of iron": ("Fe, O2", "Fe2O3", "Fe2O3"),
    "Neutralisation": ("NaOH, HCl", "NaCl, H2O", "NaCl"),
    "Ethanol combustion": ("C2H5OH, O2", "CO2, H2O", "CO2"),
    "Photosynthesis": ("CO2, H2O", "C6H12O6, O2", "C6H12O6"),
}


def load_example():
    preset = EXAMPLES[st.session_state["example_choice"]]
    if preset is not None:
        st.session_state["reactants_text"] = preset[0]
        st.session_state["products_text"] = preset[1]
        st.session_state["desired_product"] = preset[2]


st.selectbox(
    "Not sure what to type?",
    list(EXAMPLES.keys()),
    key="example_choice",
    on_change=load_example,
)

col1, col2 = st.columns(2)
with col1:
    reactants_text = st.text_input(
        "Reactants (comma-separated formulas)",
        placeholder="e.g. CH4, O2",
        key="reactants_text",
    )
with col2:
    products_text = st.text_input(
        "Products (comma-separated formulas)",
        placeholder="e.g. CO2, H2O",
        key="products_text",
    )

desired_product = st.text_input(
    "Which product do you care about?",
    placeholder="e.g. CO2",
    key="desired_product",
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

            # If the fields still hold an untouched example, that example's
            # label is the best name for it. Otherwise leave the box empty
            # and let the placeholder suggest a numbered fallback.
            chosen = st.session_state.get("example_choice")
            preset = EXAMPLES.get(chosen)
            came_from_example = preset is not None and (
                reactants_text.strip() == preset[0]
                and products_text.strip() == preset[1]
                and desired_clean == preset[2]
            )
            st.session_state["save_name"] = chosen if came_from_example else ""
        except ValueError as e:
            st.error(str(e))
            st.session_state.pop("reaction", None)

if "reaction" in st.session_state:
    rxn = st.session_state["reaction"]

    st.divider()
    st.subheader("2. Theoretical results")

    st.success(f"Balanced equation: **{rxn.pretty_equation()}**")
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
    has_lab_data = actual_yield > 0

    if not has_lab_data:
        st.info(
            "Drag the yield slider above 0 to see E-factor, percent yield, "
            "and the green grade."
        )
    else:
        st.divider()
        st.subheader("4. Full report")

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Percent yield", f"{rxn.percent_yield(reactant_masses, actual_yield):.1f}%")
        col_b.metric("E-factor", f"{rxn.e_factor(reactant_masses, actual_yield):.2f}")
        col_c.metric(
            "Avoidable waste",
            f"{rxn.excess_e_factor(reactant_masses, actual_yield):.2f}",
        )

        st.caption(
            f"This equation forces an E-factor of at least "
            f"**{rxn.e_factor_floor():.2f}** - that waste is unavoidable no "
            "matter how well you run it. Everything above that is avoidable, "
            "and that is the part the grade scores you on."
        )

        st.code(rxn.summary_table(reactant_masses, actual_yield))

    # --- Save to the comparison log --------------------------------------
    st.divider()
    st.subheader("5. Save this reaction to compare")
    st.caption(
        "Atom economy is fixed by the equation, so a wasteful route stays "
        "wasteful no matter how carefully you run it. Save a few routes "
        "here to see which one is actually worth doing."
    )

    fallback_name = f"Reaction {len(st.session_state['saved']) + 1}"

    save_name = st.text_input(
        "Give this reaction a name",
        placeholder=fallback_name,
        key="save_name",
    )

    if st.button("Save to comparison"):
        cleaned_name = save_name.strip()
        if not cleaned_name:
            cleaned_name = fallback_name
        entry = {
            "name": cleaned_name,
            "reaction": rxn,
            "reactant_masses_g": dict(reactant_masses) if has_lab_data else None,
            "actual_yield_g": actual_yield if has_lab_data else None,
        }
        st.session_state["saved"].append(entry)
        if has_lab_data:
            st.success(f"Saved '{cleaned_name}' with lab data.")
        else:
            st.success(
                f"Saved '{cleaned_name}'. No lab data, so it will show "
                "atom economy but no grade."
            )

# --- The comparison table, shown whenever anything is saved --------------
if st.session_state["saved"]:
    st.divider()
    st.subheader("6. Comparison")

    log = ReactionLog()
    for entry in st.session_state["saved"]:
        log.add(
            entry["name"],
            entry["reaction"],
            reactant_masses_g=entry["reactant_masses_g"],
            actual_yield_g=entry["actual_yield_g"],
        )

    table_rows = []
    for record in log.to_records():
        table_rows.append({
            "Name": record["name"],
            "Reaction": record["equation_pretty"],
            "Atom economy": record["atom_economy"],
            "Grade": record["grade_letter"] if record["grade_letter"] else "-",
            "E-factor": record["e_factor"],
            "Yield": record["percent_yield"],
        })

    comparison_df = pd.DataFrame(table_rows)

    st.dataframe(
        comparison_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Atom economy": st.column_config.NumberColumn(format="%.1f%%"),
            "E-factor": st.column_config.NumberColumn(format="%.2f"),
            "Yield": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    st.caption(
        f"{len(log)} reaction(s), greenest first. Blank cells mean no lab "
        "data was saved for that reaction. This list lives in your browser "
        "session only - refreshing the page clears it, so download it if "
        "you want to keep it."
    )

    st.download_button(
        "Download as CSV",
        comparison_df.to_csv(index=False),
        file_name="reaction_comparison.csv",
        mime="text/csv",
    )

    with st.expander("Plain text version (for copying into a report)"):
        st.code(log.comparison_table())

    with st.expander("Remove individual reactions"):
        st.caption(
            "Listed in the order you saved them, which is not the order of "
            "the table above (that one is sorted greenest first)."
        )
        for position, entry in enumerate(st.session_state["saved"]):
            col_label, col_button = st.columns([4, 1])
            col_label.write(
                f"**{entry['name']}** - {entry['reaction'].pretty_equation()}"
            )
            if col_button.button("Remove", key=f"remove_{position}"):
                st.session_state["saved"].pop(position)
                st.rerun()

    if st.button("Clear all"):
        st.session_state["saved"] = []
        st.rerun()

st.divider()
st.caption(
    "Built by Jven Deepak with atomecon - source code on "
    "[GitHub](https://github.com/JvenDeepak0203/atomecon)."
)
