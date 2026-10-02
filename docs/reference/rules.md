# Rules and search terms

**Rules** (hard constraints) decide whether a candidate is saved. **Search terms** (soft penalties) steer the latent search towards decodable, sensible outputs. Both are referenced by name in family files.

## Built-in rules

### `bond_window` — Sensible {from}–{to} bonds

Every {from} atom needs a {to} neighbour at {low}–{high} × the sum of their ionic radii: bonds may be neither squashed nor stretched.

### `charge_neutrality` — Charge balance

The formal charges must add up to zero for at least one combination of the listed oxidation states (e.g. Cs⁺ Pb²⁺ I⁻×3 = 0).

### `min_distance` — No overlapping atoms

Two atoms closer than {min} Å would overlap, which is physically impossible.

### `octahedral_factor` — Octahedral factor

μ = r_B / r_X says whether the B cation is large enough to hold six X anions around it ({min} ≤ μ ≤ {max}).

### `property_window` — Predicted {property} window

The model's predicted {property} must lie between {min} and {max}.

### `tolerance_factor` — Goldschmidt tolerance factor

t = (r_A + r_X) / (√2 (r_B + r_X)) measures how well the A cation fits the cage of B–X octahedra. Cubic perovskites form roughly for {min} ≤ t ≤ {max}.

## Search terms

- `cubic_cell` — Pulls the decoded cell towards a cube of the family's reference volume.
- `entropy_bonus` — Rewards uncertainty early in a round so the search explores (fades to zero).
- `group_consistency` — Sites of the same group should agree on their element (ramps up during a round).
- `prototype_alignment` — Pulls decoded positions onto the prototype's site positions.
- `short_distance_penalty` — Large penalty if any two decoded atoms come closer than `min`.
- `site_repulsion` — Short-range exponential repulsion between decoded atoms.
- `site_separation` — Keeps decoded atoms from collapsing onto each other (1/distance).
- `soft_charge` — Expected total charge of the most likely composition should be zero (ramps up during a round).
- `tolerance_penalty` — Soft version of the Goldschmidt tolerance-factor window, using the most likely elements.

## Logit transforms

- `neutrality_bias` — Raises the scores of anions whose charge can neutralise the most likely cations.

## Your own rule

```python
from meidnet.constraints import CONSTRAINTS

@CONSTRAINTS.register("no_lead", "Rejects any composition containing Pb.")
def no_lead(cand):
    return cand.result("no_lead", "Pb" not in cand.elements.values())
```

Save it as `my_rules.py`, list it under `plugins:` in `meidnet.yaml`, and add `- {name: no_lead}` to the family's `constraints`. See [Add a rule](../recipes/add-constraint.md).
