# Double perovskites A₂BB′X₆

`meidnet/families/double_perovskite_a2bbx6.yaml` is a second family written with the same ingredients as the
perovskite one. It shows what a family file can express:

- a **10-site prototype** in the rhombohedral primitive cell of an fcc lattice (`lattice: fcc_primitive`:
  edge a/√2, angles 60°), A at (¼,¼,¼) and (¾,¾,¾), B at the origin, B′ at (½,½,½), six X;
- **four site groups** with their own element lists and oxidation states (B: +1/+2, B′: +3/+4);
- a **cell-size rule** `a = 2 (r_B + r_B′ + 2 r_X)` (one B–X–B′ chain per half cell edge);
- rules that **average radii over several groups**: `tolerance_factor: {A: A, B: [B1, B2], X: X}`.

```bash
meidnet families double_perovskite_a2bbx6 --variant halide
```

```
Rock-salt ordered double perovskite A2BB'X6 (Fm-3m)  [variant: halide]
  formula pattern: A2B1B2X6   (10 atoms per cell)
  A: 9 candidate elements - Large cation in the cuboctahedral cavity
  B1: 15 candidate elements - First octahedral cation (usually +1 or +2)
  B2: 20 candidate elements - Second octahedral cation (usually +3 or +4)
  X: 4 candidate elements - Anion shared between neighbouring B and B' octahedra
```

The halide variant has 10,800 compositions; 305 pass every rule (Cs₂AgBiI₆ among them). Candidates are built
in the 10-atom primitive cell; the symmetry refinement step writes them out as the conventional 40-atom Fm-3m
cell, which is what the CIF files contain.

## Using it

A model for this family must be trained on double-perovskite structures aligned to the prototype:

```yaml
family: double_perovskite_a2bbx6
data:
  table: double_perovskites.csv
  properties: [{column: band_gap, unit: eV}]
  align_to_prototype: true
generation:
  family: double_perovskite_a2bbx6
  variant: halide
  objectives: [{property: band_gap}]
  targets: [{band_gap: 2.0}]
```

!!! warning "The published checkpoint"
    The Perov-5 model was trained on 5-atom ABX₃ cells. The Studio will score double-perovskite compositions
    with it (the encoder accepts any cell up to 20 atoms), but those predictions are far outside its training
    distribution — a demonstration of the mechanics, not a result.
