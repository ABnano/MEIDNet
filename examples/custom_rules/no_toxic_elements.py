"""
Example plugin: two custom rules for MEIDNet.

List this file under ``plugins:`` in meidnet.yaml and the rules become available in
family files and in ``generation.overrides``::

    plugins: [examples/custom_rules/no_toxic_elements.py]

Then add them to the family's ``constraints`` (copy the built-in family file and
append) - or, for a quick experiment, to ``generation.extra_constraints`` once that
exists.  Each rule receives the candidate and returns ``cand.result(...)`` with the
measured value, the allowed window and a sentence shown in reports.
"""
from meidnet.constraints import CONSTRAINTS

TOXIC = {"Pb", "Cd", "Hg", "Tl", "As"}


@CONSTRAINTS.register("no_toxic_elements", "Rejects compositions containing Pb, Cd, Hg, Tl or As.")
def no_toxic_elements(cand, extra=()):
    banned = TOXIC | set(extra)
    used = sorted(set(cand.elements.values()) & banned)
    return cand.result("no_toxic_elements", not used, None, None,
                       f"contains {', '.join(used)}" if used else "no toxic element")


@CONSTRAINTS.register("max_cell_edge", "The cubic cell edge must not exceed `max` Å (a proxy for density/cost).")
def max_cell_edge(cand, max=6.0):  # noqa: A002
    a = float(cand.lattice_a)
    return cand.result("max_cell_edge", a <= max, a, (None, max), f"a = {a:.2f} Å")
