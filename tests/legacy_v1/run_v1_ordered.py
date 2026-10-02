"""
Run the UNMODIFIED MEIDNet v1 design.py with its Python sets made deterministic.

MEIDNet v1 iterates over Python ``set`` objects (A_CATIONS, B_CATIONS, the allowed
anions, ...).  Set order depends on PYTHONHASHSEED, and the latent optimiser
amplifies the resulting floating-point differences, so v1 output changes from one
Python process to the next even with the same --seed.

This wrapper replaces every set in design_v1 by an insertion-ordered set whose
order follows the element order written in the v1 source code.  Any fixed order
is a valid execution of v1, and this is the order MEIDNet 2 uses, so the two
implementations can be compared candidate by candidate.

    python tests/legacy_v1/run_v1_ordered.py <design.py arguments>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Element order exactly as written in the v1 source literals.
RANK = {}
for el in ["Ba", "Sr", "Ca", "Na", "K", "Rb", "Cs", "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho",
           "Er", "Tm", "Yb", "Lu",
           "Ti", "Zr", "Hf", "V", "Nb", "Ta", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Sc", "Y", "Al", "Ga", "In",
           "Ge", "Sn", "Pb", "W", "Mo",
           "O", "F", "Cl", "Br", "I", "S", "Se", "Te", "N"]:
    RANK.setdefault(el, len(RANK))


class OSet:
    """Insertion-ordered set; elements known to RANK are kept in source order."""

    def __init__(self, items=()):
        items = list(items)
        if items and all(isinstance(x, str) and x in RANK for x in items):
            items = sorted(set(items), key=RANK.__getitem__)
        self._d = dict.fromkeys(items)

    def add(self, x):
        self._d[x] = None

    def update(self, items):
        for x in items:
            self._d[x] = None

    def __contains__(self, x):
        return x in self._d

    def __iter__(self):
        return iter(list(self._d))

    def __len__(self):
        return len(self._d)

    def __and__(self, other):
        return OSet(x for x in self if x in other)

    def __or__(self, other):
        return OSet(list(self) + [x for x in other if x not in self._d])

    def __repr__(self):
        return "OSet(%r)" % list(self._d)


import design_v1 as D  # noqa: E402

D.set = OSet
D.A_CATIONS = OSet(D.A_CATIONS)
D.B_CATIONS = OSet(D.B_CATIONS)
D.ANIONS_ALL = OSet(D.ANIONS_ALL)

if __name__ == "__main__":
    import torch
    torch.set_num_threads(1)
    sys.argv = ["design_v1.py"] + sys.argv[1:]
    D.main()
