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

    def to_records(self):
        """Return the log as plain data, sorted greenest first.

        This separates the numbers from the way they are printed, so a
        caller can render them however they like - a terminal table, a
        spreadsheet, a web page - instead of being stuck with the ASCII
        layout that comparison_table() produces.
        """
        rows = []
        for entry in self._entries:
            reaction = entry["reaction"]
            reactant_masses_g = entry["reactant_masses_g"]
            actual_yield_g = entry["actual_yield_g"]

            has_lab_data = reactant_masses_g is not None and actual_yield_g is not None

            if has_lab_data:
                grade = reaction.green_grade(reactant_masses_g, actual_yield_g)
                # green_grade() returns e.g. "B  (Atom economy: 75% | ...)",
                # so the letter is the first whitespace-separated piece.
                grade_letter = grade.split()[0]
                e_factor = reaction.e_factor(reactant_masses_g, actual_yield_g)
                percent_yield = reaction.percent_yield(reactant_masses_g, actual_yield_g)
            else:
                grade = "(no lab data)"
                grade_letter = None
                e_factor = None
                percent_yield = None

            rows.append({
                "name": entry["name"],
                "equation": reaction._equation_str(),
                "atom_economy": reaction.atom_economy(),
                "grade": grade,
                "grade_letter": grade_letter,
                "e_factor": e_factor,
                "percent_yield": percent_yield,
                "has_lab_data": has_lab_data,
            })

        n = len(rows)
        for i in range(n):
            for j in range(n - 1 - i):
                if rows[j]["atom_economy"] < rows[j + 1]["atom_economy"]:
                    temp = rows[j]
                    rows[j] = rows[j + 1]
                    rows[j + 1] = temp

        return rows

    def comparison_table(self) -> str:
        if not self._entries:
            return "No reactions added yet. Use log.add(name, reaction) first."

        rows = self.to_records()

        # Fixed / minimum column widths so the table keeps the same shape
        # as rows are added and removed, instead of resizing every time.
        # Names are user-typed and can be any length, so that column is
        # truly fixed and long names are truncated. The others have a
        # sensible minimum and only grow if the content genuinely needs it.
        NAME_WIDTH = 24
        MIN_EQUATION_WIDTH = 26
        AE_WIDTH = len("Atom Economy")
        MIN_GRADE_WIDTH = 40

        name_width = NAME_WIDTH
        equation_width = MIN_EQUATION_WIDTH
        ae_width = AE_WIDTH
        grade_width = MIN_GRADE_WIDTH

        for row in rows:
            if len(row["name"]) > name_width:
                row["name"] = row["name"][: name_width - 1] + "\u2026"
            if len(row["equation"]) > equation_width:
                equation_width = len(row["equation"])
            if len(row["grade"]) > grade_width:
                grade_width = len(row["grade"])

        lines = []

        header = (
            "Name".ljust(name_width) + " | "
            + "Reaction".ljust(equation_width) + " | "
            + "Atom Economy".rjust(ae_width) + " | "
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
                + ae_text.rjust(ae_width) + " | "
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
