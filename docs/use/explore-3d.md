# Explore in 3D

The Studio can show any set of structures as a **map linked to a 3D viewer**: each point on the map is one
crystal; click a point and its structure appears next to the map, where you can rotate and zoom it. The viewer
is [chemiscope](https://chemiscope.org), an open-source structure–property explorer.

Open it from any button marked 🧊:

| Button | Where | Shows |
|---|---|---|
| 🧊 Explore all compositions in 3D | Family block | the **design space**: every composition of the family on its prototype |
| 🧊 Map + 3D of all compositions | Targets block | the same design space, to compare predictions with your targets |
| 🧊 All candidates in 3D | Candidates block | the **candidates** of your last search |
| 🧊 See these structures in 3D | Data block | **your data** after *Check my data*, or the Perov-5 training data behind the published model |
| 🧊 show in the 3D explorer | the details window of any composition | the design space, with that composition selected |

You can also open the page directly in the explorer with a [deep link](studio.md#deep-links):
`?explore=space`, `?explore=candidates` or `?explore=data`.

## Reading the map

- **Axes.** For the design space, the two predicted properties (for the published model: formation enthalpy
  across, band gap up). For your data, your property columns. For candidates, their predicted properties. Any
  other property can be put on an axis from the map's settings menu.
- **Colour** (design space): yellow = passes every rule, purple = rejected by at least one rule. **Symbol**:
  pass / rejected. For candidates the colour is the search score (lower = closer to the targets).
- **Properties you can plot or colour by:**

| Name | Meaning |
|---|---|
| `formula` | the composition |
| `site_A`, `site_B`, … | the element on each site group |
| `lattice_a` | the cubic cell edge estimated from ionic radii (Å) |
| `pred_<property>` | the model's prediction from the structure encoder, with its unit |
| `rule_<name>` | the value each rule measures, e.g. `rule_tolerance_factor` |
| `passes_all`, `verdict` | 1 / "pass" when every rule passes (with the limits currently set on the page) |
| `score`, `round`, `target_<property>`, `still_passes` | candidates only: search score, round found, the target, and whether it still passes the current rules |

The design space shows up to 2,000 compositions: those passing every rule first, then a fixed random sample of
the rest. Your data shows the structures that passed *Check my data*; the Perov-5 training data shows its first
1,500 structures.

## Clicking a point

The crystal appears on the right: drag to rotate, scroll to zoom. The panel below lists every property of that
structure. Bonds and the unit cell are drawn. Design-space structures are the ideal prototype filled with that
composition's elements, at the cell size the family's lattice rule estimates.

## When chemiscope cannot load

The explorer is downloaded from a public CDN the first time you open it (about 3 MB). Without internet access,
or if the CDN is blocked, the Studio switches to its **built-in viewer**: a scatter plot of the same two axes
(coloured points pass every rule) linked to the Studio's own crystal viewer — click a point, drag the cell to
rotate, double-click to spin. Nothing else changes.

## Save the dataset

**⬇ dataset JSON** saves what you see as a chemiscope dataset. Open it later at
[chemiscope.org](https://chemiscope.org) (the site reads the file inside your browser; nothing is uploaded),
share it with a colleague, or put it in a paper's supplementary material.

The same datasets can be produced without the Studio:

```bash
meidnet space meidnet.yaml --chemiscope space.json   # the design space of your configuration
```

and from Python:

```python
from meidnet.studio.chemiscope import space_dataset, candidates_dataset, records_dataset
```

In the Colab notebooks, the `show3d(...)` helper displays structures inline with `chemiscope.show`.

## Credits

chemiscope is a third-party library (BSD-3-Clause licence) by G. Fraux, R. K. Cersonsky and M. Ceriotti. If you
use the 3D explorer in published work, please cite: G. Fraux, R. K. Cersonsky, M. Ceriotti, *Chemiscope:
interactive structure-property explorer for materials and molecules*, Journal of Open Source Software 5, 2117
(2020).
