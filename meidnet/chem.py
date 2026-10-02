"""
Element tables and small chemistry helpers shared by every part of MEIDNet.

The crystal modality represents each site with a one-hot vector over all 118
elements, so ``ELEMENTS`` fixes the meaning of every species index used by the
encoder, the decoder and the generation code.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from pymatgen.core.periodic_table import Element

ELEMENTS: list[str] = [str(Element.from_Z(z)) for z in range(1, 119)]
NUM_SPECIES: int = len(ELEMENTS)  # 118
ELEMENT_INDEX: dict[str, int] = {el: i for i, el in enumerate(ELEMENTS)}

DEFAULT_RADIUS = 1.5  # Å, used when pymatgen has no ionic radius for an element


def element_index(symbol: str) -> int:
    """Return the species index of an element symbol (raises a readable error)."""
    try:
        return ELEMENT_INDEX[symbol]
    except KeyError:
        raise ValueError(f"'{symbol}' is not a chemical element symbol") from None


@lru_cache(maxsize=None)
def ionic_radius(symbol: str) -> float:
    """
    Mean of the ionic radii pymatgen lists for an element, in Å.

    This is the radius used by the lattice rule and by the tolerance/octahedral
    factor checks.  It averages over all oxidation states pymatgen knows, which
    is a coarse but transparent choice (identical to MEIDNet v1).
    """
    try:
        r = Element(symbol).ionic_radii or []
        if isinstance(r, dict):
            vals = [float(x) for x in r.values() if x]
            return float(np.mean(vals)) if vals else DEFAULT_RADIUS
        return float(np.mean(r)) if r else DEFAULT_RADIUS
    except Exception:
        return DEFAULT_RADIUS
