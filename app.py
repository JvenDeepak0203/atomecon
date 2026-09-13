"""
Streamlit web app for atomecon.

Run locally with:
    streamlit run app.py

Deploy for free at share.streamlit.io (see README for steps).
"""

import html
import io

import pandas as pd
import streamlit as st

from atomecon import Reaction, ReactionLog, is_formula_plausible, to_subscripts

# Mass ranges for the reactant sliders: (minimum, maximum, step) in grams.
# A single fixed range cannot serve both microscale lab work and industrial
# comparisons, so the user picks.
MASS_SCALES = {
    "Up to 1 g": (0.01, 1.0, 0.01),
    "Up to 5 g": (0.01, 5.0, 0.05),
    "Up to 10 g": (0.1, 10.0, 0.1),
    "Up to 50 g": (0.1, 50.0, 0.5),
    "Up to 100 g": (0.1, 100.0, 1.0),
    "Up to 1 kg": (1.0, 1000.0, 5.0),
}
DEFAULT_SCALE = "Up to 100 g"

# Ready-made reactions so a first-time visitor sees the tool work
# immediately. Every one of these auto-balances - do not add an equation
# without checking, since some have more than one valid balancing ratio.
EXAMPLES = {
    "Start from an example...": None,
    "Methane combustion": ("CH4, O2", "CO2, H2O", "CO2"),
    "Haber process (ammonia)": ("N2, H2", "NH3", "NH3"),
    "Rusting of iron": ("Fe, O2", "Fe2O3", "Fe2O3"),
    "Neutralisation": ("NaOH, HCl", "NaCl, H2O", "NaCl"),
    "Ethanol combustion": ("C2H5OH, O2", "CO2, H2O", "CO2"),
    "Photosynthesis": ("CO2, H2O", "C6H12O6, O2", "C6H12O6"),
}

# Column names in the exported CSV. The first six are for reading; the
# last five carry the raw inputs so the file can be loaded back in.
# Computed results cannot be reversed into a reaction, so they are not
# what gets re-imported.
MACHINE_COLUMNS = [
    "Reactant coefficients",
    "Product coefficients",
    "Desired product",
    "Reactant masses (g)",
    "Actual yield (g)",
]


def encode_species(mapping):
    """{'CH4': 1, 'O2': 2} -> 'CH4:1;O2:2'"""
    if not mapping:
        return ""
    parts = []
    for formula, value in mapping.items():
        parts.append(f"{formula}:{value}")
    return ";".join(parts)


def decode_species(text, cast):
    """'CH4:1;O2:2' -> {'CH4': 1, 'O2': 2}. Raises ValueError if malformed."""
    result = {}
    if text is None:
        return result
    text = str(text).strip()
    if not text or text.lower() == "nan":
        return result
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(
                f"'{chunk}' should look like FORMULA:NUMBER, e.g. CH4:1"
            )
        formula, _, value = chunk.partition(":")
        result[formula.strip()] = cast(value.strip())
    return result


st.set_page_config(page_title="atomecon", page_icon="🧪")

st.title("🧪 atomecon")
st.caption(
    "Green chemistry metrics from plain chemical formulas - "
    "no RDKit, no SMILES needed."
)

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


def split_formulas(text):
    pieces = []
    for piece in text.split(","):
        cleaned = piece.strip()
        if cleaned:
            pieces.append(cleaned)
    return pieces


def note_example_label(reactant_list, product_list, desired_clean):
    """Suggest a name if the fields still hold an untouched example.

    Which product you care about does not change the reaction's identity,
    so only the formulas are compared. A different target is noted in
    brackets so two rows from the same equation stay tellable apart.
    """
    chosen = st.session_state.get("example_choice")
    preset = EXAMPLES.get(chosen)
    if preset is None:
        st.session_state["example_label"] = None
        return

    same_equation = (
        sorted(reactant_list) == sorted(split_formulas(preset[0]))
        and sorted(product_list) == sorted(split_formulas(preset[1]))
    )
    if same_equation and desired_clean == preset[2]:
        st.session_state["example_label"] = chosen
    elif same_equation:
        st.session_state["example_label"] = f"{chosen} ({desired_clean})"
    else:
        st.session_state["example_label"] = None


if build_clicked:
    reactant_list = split_formulas(reactants_text)
    product_list = split_formulas(products_text)
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

        st.session_state.pop("actual_yield", None)
        st.session_state["save_name"] = ""
        note_example_label(reactant_list, product_list, desired_clean)

        try:
            rxn = Reaction.auto(reactant_list, product_list, desired_clean)
            st.session_state["reaction"] = rxn
            st.session_state["reactant_list"] = reactant_list
            st.session_state.pop("needs_coefficients", None)
        except ValueError as e:
            # Could be a genuine mistake, or an equation with more than one
            # valid balancing ratio. Either way the user can supply
            # coefficients by hand rather than being stuck.
            st.session_state.pop("reaction", None)
            st.session_state["needs_coefficients"] = {
                "reactants": reactant_list,
                "products": product_list,
                "desired": desired_clean,
                "error": str(e),
            }

# --- Manual coefficients, when automatic balancing cannot decide ---------
if "needs_coefficients" in st.session_state:
    pending = st.session_state["needs_coefficients"]

    st.divider()
    st.subheader("Automatic balancing could not settle this one")
    st.warning(pending["error"])
    st.markdown(
        "Some equations have more than one valid balancing ratio. That is a "
        "real mathematical ambiguity, not a bug: the atom counts alone do "
        "not say which one is the chemistry. Aspirin is the classic case - "
        "`11C7H6O3 + C4H6O3 -> 9C9H8O4` balances perfectly and is complete "
        "nonsense. Enter the coefficients yourself and the balance will be "
        "checked."
    )

    manual_reactants = {}
    manual_products = {}

    st.markdown("**Reactants**")
    reactant_columns = st.columns(len(pending["reactants"]))
    for column, formula in zip(reactant_columns, pending["reactants"]):
        manual_reactants[formula] = column.number_input(
            to_subscripts(formula),
            min_value=1,
            max_value=99,
            value=1,
            step=1,
            key=f"coeff_r_{formula}",
        )

    st.markdown("**Products**")
    product_columns = st.columns(len(pending["products"]))
    for column, formula in zip(product_columns, pending["products"]):
        manual_products[formula] = column.number_input(
            to_subscripts(formula),
            min_value=1,
            max_value=99,
            value=1,
            step=1,
            key=f"coeff_p_{formula}",
        )

    if st.button("Use these coefficients"):
        try:
            rxn = Reaction(
                reactants=manual_reactants,
                products=manual_products,
                desired_product=pending["desired"],
            )
            st.session_state["reaction"] = rxn
            st.session_state["reactant_list"] = pending["reactants"]
            st.session_state.pop("needs_coefficients", None)
            st.session_state.pop("actual_yield", None)
            st.rerun()
        except ValueError as e:
            st.error(str(e))

# --- The analysis -------------------------------------------------------
if "reaction" in st.session_state:
    rxn = st.session_state["reaction"]

    st.divider()
    st.subheader("2. Theoretical results")

    st.success(f"Balanced equation: **{rxn.pretty_equation()}**")
    st.metric("Atom economy", f"{rxn.atom_economy():.1f}%")

    with st.expander("See the step-by-step calculation"):
        parts = rxn.atom_economy_breakdown()
        target = to_subscripts(parts["desired_product"])

        st.markdown(f"**Step 1: the product you want ({target})**")
        st.markdown(
            f"One unit weighs **{parts['desired_molar_mass']:.2f} g/mol**, and "
            f"the balanced equation makes **{parts['desired_coefficient']}** of "
            "them."
        )
        st.latex(
            r"%.2f \times %d = %.2f \text{ g}"
            % (
                parts["desired_molar_mass"],
                parts["desired_coefficient"],
                parts["desired_mass"],
            )
        )

        st.markdown("**Step 2: everything you put in**")
        breakdown_rows = []
        for row in parts["reactants"]:
            breakdown_rows.append({
                "Reactant": to_subscripts(row["formula"]),
                "Coefficient": row["coefficient"],
                "Molar mass (g/mol)": row["molar_mass"],
                "Contributes (g)": row["mass"],
            })
        st.dataframe(
            pd.DataFrame(breakdown_rows),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Molar mass (g/mol)": st.column_config.NumberColumn(format="%.2f"),
                "Contributes (g)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.markdown(
            f"Total mass of reactants: **{parts['total_reactant_mass']:.2f} g**"
        )

        st.markdown("**Step 3: the ratio**")
        st.latex(
            r"\frac{%.2f}{%.2f} \times 100 = %.1f\%%"
            % (
                parts["desired_mass"],
                parts["total_reactant_mass"],
                parts["atom_economy"],
            )
        )
        st.caption(
            "Every gram that is not in that top number leaves as something "
            "you did not want."
        )

        st.markdown("**Plain text.** Use the copy icon in the corner:")
        st.code(rxn.explain_atom_economy(), language=None)

    st.divider()
    st.subheader("3. Optional: add real lab data")
    st.caption(
        "Atom economy above needs no lab data. Drag these only if you "
        "actually ran the reaction and want E-factor / yield too."
    )

    scale_name = st.selectbox(
        "Roughly how much are you working with?",
        list(MASS_SCALES.keys()),
        index=list(MASS_SCALES.keys()).index(DEFAULT_SCALE),
        key="mass_scale",
    )
    scale_min, scale_max, scale_step = MASS_SCALES[scale_name]

    reactant_masses = {}
    for formula in st.session_state["reactant_list"]:
        slider_key = f"mass_{formula}"
        # Switching scale can leave a stored value outside the new range,
        # which Streamlit rejects. Pull it back in first.
        stored = st.session_state.get(slider_key)
        if stored is not None:
            if stored < scale_min:
                st.session_state[slider_key] = scale_min
            elif stored > scale_max:
                st.session_state[slider_key] = scale_max

        reactant_masses[formula] = st.slider(
            f"Grams of {to_subscripts(formula)} used",
            min_value=scale_min,
            max_value=scale_max,
            value=min(max(1.0, scale_min), scale_max),
            step=scale_step,
            key=slider_key,
        )

    theoretical = rxn.theoretical_yield_g(reactant_masses)
    limiting = rxn.limiting_reactant(reactant_masses)

    max_yield = round(theoretical, 2)
    if max_yield < 0.01:
        max_yield = 0.01

    if st.session_state.get("actual_yield", 0.0) > max_yield:
        st.session_state["actual_yield"] = max_yield

    st.slider(
        f"Grams of {to_subscripts(rxn.desired_product)} actually obtained",
        min_value=0.0,
        max_value=max_yield,
        step=0.01,
        key="actual_yield",
    )
    actual_yield = st.session_state["actual_yield"]

    st.caption(
        f"Capped at {max_yield:.2f} g - the theoretical maximum. "
        f"**{to_subscripts(limiting)}** runs out first, so it sets the "
        "ceiling. You cannot isolate more product than the atoms you "
        "started with can build."
    )

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

        floor = rxn.e_factor_floor()
        if floor < 0.005:
            st.caption(
                "Every atom in this equation can end up in your product, so "
                "nothing is wasted by design. That means all of the E-factor "
                "above is avoidable, and the grade holds you to that."
            )
        else:
            st.caption(
                f"This equation cannot do better than an E-factor of "
                f"**{floor:.2f}**. That much leaves as by-product however well "
                "you run it. Anything above the floor is waste you could have "
                "avoided, and that is the part the grade scores."
            )

        st.code(rxn.summary_table(reactant_masses, actual_yield))

    st.divider()
    st.subheader("5. Save this reaction to compare")
    st.caption(
        "Atom economy is fixed by the equation, so a wasteful route stays "
        "wasteful no matter how carefully you run it. Save a few routes "
        "here to see which one is actually worth doing."
    )

    suggested_name = st.session_state.get("example_label")
    if not suggested_name:
        suggested_name = f"Reaction {len(st.session_state['saved']) + 1}"

    save_name = st.text_input(
        "Give this reaction a name",
        placeholder=suggested_name,
        key="save_name",
    )

    if st.button("Save to comparison"):
        cleaned_name = save_name.strip()
        if not cleaned_name:
            cleaned_name = suggested_name
        st.session_state["saved"].append({
            "name": cleaned_name,
            "reaction": rxn,
            "reactant_masses_g": dict(reactant_masses) if has_lab_data else None,
            "actual_yield_g": actual_yield if has_lab_data else None,
        })
        st.success(f"Saved '{cleaned_name}'.")

# --- Comparison, export, import -----------------------------------------
st.divider()
st.subheader("6. Comparison")

if not st.session_state["saved"]:
    st.caption(
        "Nothing saved yet. Analyse a reaction above and save it, or load a "
        "comparison you exported earlier."
    )
else:
    log = ReactionLog()
    for entry in st.session_state["saved"]:
        log.add(
            entry["name"],
            entry["reaction"],
            reactant_masses_g=entry["reactant_masses_g"],
            actual_yield_g=entry["actual_yield_g"],
        )

    display_rows = []
    for record in log.to_records():
        display_rows.append({
            "Name": record["name"],
            "Reaction": record["equation_pretty"],
            "Atom economy": f"{record['atom_economy']:.1f}%",
            "Grade": record["grade_letter"] if record["grade_letter"] else "",
            "E-factor": "" if record["e_factor"] is None else f"{record['e_factor']:.2f}",
            "Yield": "" if record["percent_yield"] is None else f"{record['percent_yield']:.1f}%",
        })

    # Built by hand rather than with st.dataframe because that widget gives
    # no control over column alignment. Names are user-typed, so every cell
    # is escaped before it reaches the page.
    table_css = """
    <style>
    .atomecon-table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
    .atomecon-table th, .atomecon-table td {
        padding: 0.45rem 0.6rem;
        text-align: center;
        border-bottom: 1px solid rgba(140, 140, 140, 0.28);
    }
    .atomecon-table th {
        font-weight: 600;
        border-bottom: 2px solid rgba(140, 140, 140, 0.5);
    }
    .atomecon-table td.left, .atomecon-table th.left { text-align: left; }
    </style>
    """

    table_parts = ["<table class='atomecon-table'><thead><tr>"]
    table_parts.append(
        "<th class='left'>Name</th><th class='left'>Reaction</th>"
        "<th>Atom economy</th><th>Grade</th><th>E-factor</th><th>Yield</th>"
    )
    table_parts.append("</tr></thead><tbody>")
    for row in display_rows:
        table_parts.append(
            "<tr>"
            f"<td class='left'>{html.escape(row['Name'])}</td>"
            f"<td class='left'>{html.escape(row['Reaction'])}</td>"
            f"<td>{row['Atom economy']}</td>"
            f"<td>{html.escape(row['Grade'])}</td>"
            f"<td>{row['E-factor']}</td>"
            f"<td>{row['Yield']}</td>"
            "</tr>"
        )
    table_parts.append("</tbody></table>")

    st.markdown(table_css + "".join(table_parts), unsafe_allow_html=True)

    st.caption(
        f"{len(log)} reaction(s), greenest first. Blank cells mean no lab "
        "data was saved for that reaction."
    )

    # The export carries the raw inputs alongside the readable columns,
    # because computed results cannot be turned back into a reaction.
    export_rows = []
    for entry in st.session_state["saved"]:
        entry_reaction = entry["reaction"]
        readable = None
        for record in log.to_records():
            if record["name"] == entry["name"]:
                readable = record
                break

        export_rows.append({
            "Name": entry["name"],
            "Reaction": entry_reaction.pretty_equation(),
            "Atom economy": f"{entry_reaction.atom_economy():.1f}%",
            "Grade": (readable or {}).get("grade_letter") or "",
            "E-factor": (
                "" if entry["actual_yield_g"] is None
                else f"{entry_reaction.e_factor(entry['reactant_masses_g'], entry['actual_yield_g']):.2f}"
            ),
            "Yield": (
                "" if entry["actual_yield_g"] is None
                else f"{entry_reaction.percent_yield(entry['reactant_masses_g'], entry['actual_yield_g']):.1f}%"
            ),
            "Reactant coefficients": encode_species(entry_reaction.reactants),
            "Product coefficients": encode_species(entry_reaction.products),
            "Desired product": entry_reaction.desired_product,
            "Reactant masses (g)": encode_species(entry["reactant_masses_g"] or {}),
            "Actual yield (g)": (
                "" if entry["actual_yield_g"] is None else entry["actual_yield_g"]
            ),
        })

    # utf-8-sig writes a byte-order mark, which is what tells Excel on
    # Windows to read the file as UTF-8. Without it the subscripts and the
    # arrow arrive as mojibake.
    csv_bytes = pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "Download as CSV",
        csv_bytes,
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

with st.expander("Load a comparison from a CSV"):
    st.markdown(
        "Upload a file this app exported. Alongside the readable columns it "
        "stores the raw inputs, which is what gets loaded back - the "
        "computed results are recalculated rather than trusted."
    )
    st.markdown("Required columns: **Name**, plus " + ", ".join(f"**{c}**" for c in MACHINE_COLUMNS))
    st.caption(
        "Coefficients and masses use FORMULA:NUMBER separated by "
        "semicolons, e.g. `CH4:1;O2:2`. Leave the mass and yield columns "
        "empty for a reaction with no lab data."
    )

    uploaded = st.file_uploader("Choose a CSV", type=["csv"], key="csv_upload")

    if uploaded is not None and st.button("Load reactions"):
        try:
            frame = pd.read_csv(uploaded, encoding="utf-8-sig")
        except Exception as e:
            frame = None
            st.error(f"Could not read that file: {e}")

        if frame is not None:
            missing_columns = []
            for column in ["Name"] + MACHINE_COLUMNS:
                if column not in frame.columns:
                    missing_columns.append(column)

            if missing_columns:
                st.error(
                    "That CSV is missing these columns: "
                    + ", ".join(missing_columns)
                    + ". Export a file from this app to see the expected "
                    "format."
                )
            else:
                loaded = 0
                problems = []
                for position, row in frame.iterrows():
                    line = position + 2  # +1 for zero-index, +1 for header
                    try:
                        reactants = decode_species(row["Reactant coefficients"], int)
                        products = decode_species(row["Product coefficients"], int)
                        masses = decode_species(row["Reactant masses (g)"], float)

                        raw_yield = row["Actual yield (g)"]
                        if pd.isna(raw_yield) or str(raw_yield).strip() == "":
                            actual = None
                            masses = None
                        else:
                            actual = float(raw_yield)

                        restored = Reaction(
                            reactants=reactants,
                            products=products,
                            desired_product=str(row["Desired product"]).strip(),
                        )
                        st.session_state["saved"].append({
                            "name": str(row["Name"]),
                            "reaction": restored,
                            "reactant_masses_g": masses,
                            "actual_yield_g": actual,
                        })
                        loaded += 1
                    except (ValueError, KeyError, TypeError) as e:
                        problems.append(f"Row {line}: {e}")

                if loaded:
                    st.success(f"Loaded {loaded} reaction(s).")
                if problems:
                    st.warning(
                        "These rows were skipped:\n\n- " + "\n- ".join(problems)
                    )
                if loaded:
                    st.rerun()

st.divider()
st.caption(
    "Built by Jven Deepak with atomecon - source code on "
    "[GitHub](https://github.com/JvenDeepak0203/atomecon)."
)
