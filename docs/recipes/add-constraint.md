# Add a rule (constraint)

A rule is a function that looks at a candidate and returns pass/fail, the measured value, the allowed window
and a sentence. The search enforces it; every report and the Studio explain it.

## 1. Write it

`my_rules.py`:

```python
from meidnet.constraints import CONSTRAINTS

@CONSTRAINTS.register("no_lead", "Rejects any composition containing Pb.")
def no_lead(cand):
    return cand.result("no_lead", "Pb" not in cand.elements.values())

@CONSTRAINTS.register("mass_window", "Mean atomic mass must lie between min and max (g/mol).")
def mass_window(cand, min=0.0, max=200.0):
    from pymatgen.core import Element
    m = sum(Element(e).atomic_mass for e in cand.structure.species) / len(cand.structure)
    return cand.result("mass_window", min <= m <= max, float(m), (min, max), f"mean mass {m:.1f}")
```

What a candidate gives you: `cand.elements` (`{group: element}`), `cand.structure` (pymatgen, after symmetry
refinement), `cand.raw` (before), `cand.lattice_a`, `cand.predictions` (`{property: value}`), `cand.radius(group)`.

## 2. Register the file and name the rule

```yaml
plugins: [my_rules.py]
generation:
  family: my_perovskite.yaml      # a copy of the built-in family with the rules appended:
```

```yaml
constraints:
  - {name: charge_neutrality}
  - ...
  - {name: no_lead}
  - {name: mass_window, min: 0, max: 120}
```

## 3. Run

`meidnet generate meidnet.yaml`. The candidate cards list *No lead* and *mass window* with the measured value;
the funnel shows how many compositions each removed.

A complete example lives in `examples/custom_rules/` (a *no toxic elements* rule and a *max cell edge* rule), and
[notebook 03](../start/colab.md) does the same in Colab.

## Soft terms

Rules decide acceptance. To *steer* the latent search instead (a penalty with a gradient), register a search term
with `@SEARCH_TERMS.register` in `meidnet.terms`; it receives a `SearchContext` with the decoder's outputs. See
[rules and search terms](../reference/rules.md).
