# Capabilities: what works today

Generated from the code, so it cannot promise more than the code does. **Supported** = in this release; **Community-tested** = a benchmark result reproduced here names it; **Planned** = designed for, not implemented ([roadmap](../understand/limits.md)).

## Modalities

| modality | status | how |
|---|---|---|
| Crystal structure (CIF, up to `max_sites` atoms, default 20) | Supported | an equivariant graph encoder; structures are aligned to the family prototype |
| Scalar properties (any number of numeric columns) | Supported | one property encoder; every column becomes a target you can set |
| Published properties: direct band gap (`dir_gap`), formation enthalpy (`heat_all`) | Supported | the shipped Perov-5 checkpoint |
| Vector modalities: binned XRD, DOS | Planned | an encoder per vector modality into the shared latent space |
| Spectra (Raman, UV-Vis) | Planned | as vector modalities |
| Text (descriptions, synthesis) | Planned | a text encoder into the shared latent space |
| Images (microscopy) | Planned | an image encoder into the shared latent space |

## Fusion

One scheme: **early fusion** - the structure latent and the property latent of a material are averaged into the joint latent (`meidnet/model.py`), after a contrastive alignment whose weight ramps up over `training.contrastive_warmup_epochs` (the curriculum of the paper). There is no late-fusion option; a selector would be a fiction.

## Input formats

| format | note |
|---|---|
| CSV | any delimiter pandas reads |
| Excel (.xlsx, .xls) | first sheet |
| JSON table | records |
| Parquet | needs the optional pyarrow |
| CIF text in a column | one structure per row |
| CIF files (.cif, or a .zip of them) | named <id>.cif |

## Material families

| family | variants | site groups |
|---|---|---|
| `double_perovskite_a2bbx6` - Rock-salt ordered double perovskite A2BB'X6 (Fm-3m) | `halide`, `oxide` | A, B1, B2, X |
| `perovskite_abx3` - Cubic ABX3 perovskite (Pm-3m) | `oxide`, `halide`, `chalcogenide`, `nitride` | A, B, X |

Any other prototype family can be described in a [family file](../reference/families.md).

## Rules (hard constraints)

- `bond_window` - Sensible {from}–{to} bonds
- `charge_neutrality` - Charge balance
- `min_distance` - No overlapping atoms
- `octahedral_factor` - Octahedral factor
- `property_window` - Predicted {property} window
- `tolerance_factor` - Goldschmidt tolerance factor

## Search terms (soft)

- `cubic_cell` - Pulls the decoded cell towards a cube of the family's reference volume.
- `entropy_bonus` - Rewards uncertainty early in a round so the search explores (fades to zero).
- `group_consistency` - Sites of the same group should agree on their element (ramps up during a round).
- `prototype_alignment` - Pulls decoded positions onto the prototype's site positions.
- `short_distance_penalty` - Large penalty if any two decoded atoms come closer than `min`.
- `site_repulsion` - Short-range exponential repulsion between decoded atoms.
- `site_separation` - Keeps decoded atoms from collapsing onto each other (1/distance).
- `soft_charge` - Expected total charge of the most likely composition should be zero (ramps up during a round).
- `tolerance_penalty` - Soft version of the Goldschmidt tolerance-factor window, using the most likely elements.

## After generation

- `meidnet screen`: MACE-MP-0 relaxation and the stable / unique / novel (SUN) counts (optional `pip install meidnet[stability]`). DFT and experiments are yours: the [benchmark evidence ladder](../benchmarks/index.md) records them.
