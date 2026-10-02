# Change the material family

A family file tells MEIDNet what kind of crystal to build. The built-in ones are
`meidnet/families/perovskite_abx3.yaml` and `double_perovskite_a2bbx6.yaml`; `meidnet families <name>` prints
a summary. To use your own, copy one, edit it, and point to it:

```yaml
generation:
  family: my_family.yaml
  variant: null          # or a variant you define
```

## The parts of a family file

```yaml
name: spinel_ab2x4
title: Normal spinel AB2X4 (Fd-3m, primitive cell)

prototype:                    # WHERE atoms sit (fractional coordinates, in decoder slot order)
  lattice: fcc_primitive      # cubic | fcc_primitive | bcc_primitive | explicit a,b,c,alpha,beta,gamma
  reference_a: 8.1
  sites:
    - {group: A, frac: [0.125, 0.125, 0.125]}
    - ...

groups:                       # WHO may sit there, and with which charges
  A: {description: tetrahedral cation, elements: [Mg, Zn, Fe, Co, Ni, Mn], oxidation_states: {Mg: [2], ...}}
  B: {...}
  X: {...}

sampling_order: [B, X, A]     # the LAST group is restricted to charge-balancing elements

lattice:                      # HOW BIG the cell is
  rule: bond_sum              # a = factor × Σ ionic radii of the listed groups (or rule: fixed)
  groups: [B, X]
  factor: 2.0
  min: 3.0
  max: 12.0

variants:                     # named sub-families: element subsets and rule parameters
  oxide: {groups: {X: {elements: [O]}}, params: {tolerance_factor: {min: 0.8, max: 1.05}}}

search_terms:                 # soft penalties during the latent search (see reference/rules)
  - {name: site_separation, weight: 200}
  - ...

constraints:                  # hard rules every saved candidate must pass
  - {name: charge_neutrality}
  - {name: min_distance, min: 0.8}
  - ...
```

## Alignment of training data

For generation to mean anything, the model must have been trained on structures whose atoms are in the
prototype's site order. `data.align_to_prototype: true` (default) re-orders every training structure to match
the family named in `generation.family` (or top-level `family:`); structures that do not fit are reported by
`meidnet check`. Raise `data.prototype_tolerance` for distorted cells.

## Checking a family file

```bash
meidnet families my_family.yaml --variant oxide
meidnet space meidnet.yaml      # every composition with rule values → CSV
```

Errors name the problem: unknown element symbols, a prototype group without a definition, an override that
matches no rule, a group left empty after your filters.

## Worked example

The [double perovskite](../examples/double-perovskite.md) page walks through a 10-site, non-cubic-primitive
family written this way.
