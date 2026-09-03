"""
A small in-memory "database" for collecting several Reaction objects
and comparing them side by side.

This is intentionally simple: it's just a Python list living inside
an object, so everything you add is lost once your program ends.
There is no file saving here - if you want that, you'd need to write
the results to a file yourself (a natural next feature, not included).
"""

from typing import Dict, Optional

from .reaction import Reaction


class ReactionLog:
    def __init__(self):
        self._entries = []

    def add(
        self,
        name: str,
        reaction: Reaction,
        reactant_masses_g: Optional[Dict[str, float]] = None,
        actual_yield_g: Optional[float] = None,
    ) -> None:
        entry = {
            "name": name,
            "reaction": reaction,
            "reactant_masses_g": reactant_masses_g,
            "actual_yield_g": actual_yield_g,
        }
        self._entries.append(entry)

    def comparison_table(self) -> str:
        if not self._entries:
            return "No reactions added yet. Use log.add(name, reaction) first."

        rows = []
        for entry in self._entries:
            name = entry["name"]
            reaction = entry["reaction"]
            reactant_masses_g = entry["reactant_masses_g"]
            actual_yield_g = entry["actual_yield_g"]

            ae = reaction.atom_economy()

            has_lab_data = reactant_masses_g is not None and actual_yield_g is not None
            if has_lab_data:
                grade = reaction.green_grade(reactant_masses_g, actual_yield_g)
            else:
                grade = "(no lab data)"

            rows.append({
                "name": name,
                "equation": reaction._equation_str(),
                "atom_economy": ae,
                "grade": grade,
            })

        n = len(rows)
        for i in range(n):
            for j in range(n - 1 - i):
                if rows[j]["atom_economy"] < rows[j + 1]["atom_economy"]:
                    temp = rows[j]
                    rows[j] = rows[j + 1]
                    rows[j + 1] = temp

        name_width = len("Name")
        equation_width = len("Reaction")
        ae_width = len("Atom Economy")
        grade_width = len("Grade")

        for row in rows:
            if len(row["name"]) > name_width:
                name_width = len(row["name"])
            if len(row["equation"]) > equation_width:
                equation_width = len(row["equation"])
            ae_text = f"{row['atom_economy']:.1f}%"
            if len(ae_text) > ae_width:
                ae_width = len(ae_text)
            if len(row["grade"]) > grade_width:
                grade_width = len(row["grade"])

        lines = []

        header = (
            "Name".ljust(name_width) + " | "
            + "Reaction".ljust(equation_width) + " | "
            + "Atom Economy".ljust(ae_width) + " | "
            + "Grade".ljust(grade_width)
        )
        lines.append(header)

        separator = (
            ("-" * name_width) + "-+-"
            + ("-" * equation_width) + "-+-"
            + ("-" * ae_width) + "-+-"
            + ("-" * grade_width)
        )
        lines.append(separator)

        for row in rows:
            ae_text = f"{row['atom_economy']:.1f}%"
            row_text = (
                row["name"].ljust(name_width) + " | "
                + row["equation"].ljust(equation_width) + " | "
                + ae_text.ljust(ae_width) + " | "
                + row["grade"].ljust(grade_width)
            )
            lines.append(row_text)

        text = ""
        for i, line in enumerate(lines):
            if i > 0:
                text = text + "\n"
            text = text + line
        return text

    def __len__(self):
        return len(self._entries)
