# Candidates shipped with the paper, screened here

The 26 candidate structures in examples/perov5/paper_results, relaxed with MACE-MP-0 and scored with the protocol's stability, uniqueness and novelty criteria. Their targets and budget are those of the paper, so the record is not ranked.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `paper` |
| Type | model |
| Inputs | `structure`, `property:heat_all`, `property:dir_gap` |
| Parameters | – |
| Training data | Perov-5 train (11,356) |
| Status | Computed here on 2026-10-03 |
| Evidence level | MLIP validated |
| Added | 2026-10-03 by Anand Babu (UCLouvain) |
| Links | [paper](https://doi.org/10.1038/s41524-026-02153-3) · [code](https://github.com/ABnano/MEIDNet) |

## Inverse design

| metric | value | definition |
|---|---|---|
| SUN | 0.731 | stable, unique and novel candidates divided by the budget of 54; a candidate that was not delivered counts as a failure |
| Stable | 1.000 | fraction of delivered candidates whose MACE-MP-0 formation energy after relaxation is at most 0.10 eV/atom, against elemental reference phases (the criterion of `meidnet screen` and of the paper) |
| Unique | 0.923 | fraction of delivered candidates whose composition does not repeat an earlier one |
| Novel | 0.769 | fraction of delivered candidates whose composition is not in the training split |
| ΔHf | -1.27 eV/atom | median MACE-MP-0 formation energy of the delivered candidates |
| Delivered | 26 | candidates delivered out of the budget of 54 |
| SUN count | 19 | stable, unique and novel candidates |

### Candidates

Every candidate with its MLIP formation energy, novelty and, where Perov-5 has the same sites, the DFT band gap.

| candidate | formula | target gap (eV) | ΔHf (eV/atom) | stable | novel | DFT gap (eV) |
|---|---|---|---|---|---|---|
| chalcogenide_chalcogenide_T1_R1_2 | LaCrTe3 |  | -1.485 | yes | yes | – |
| chalcogenide_chalcogenide_T1_R1_3 | NaNbTe3 |  | -1.208 | yes | yes | – |
| chalcogenide_chalcogenide_T2_R1_1 | KNbTe3 |  | -1.338 | yes | yes | – |
| chalcogenide_chalcogenide_T2_R1_2 | BaTe3W |  | -1.310 | yes | yes | – |
| chalcogenide_chalcogenide_T2_R1_3 | BaTe3Mo |  | -1.429 | yes | yes | – |
| halide_halide_T1_R1_1 | NaMnI3 |  | -0.900 | yes | yes | – |
| halide_halide_T1_R1_2 | NaNiI3 |  | -0.723 | yes | yes | – |
| halide_halide_T1_R1_3 | RbMnI3 |  | -1.123 | yes | yes | – |
| halide_halide_T1_R1_4 | NaNiI3 |  | -0.723 | yes | yes | – |
| halide_halide_T1_R2_4 | NaZnI3 |  | -0.928 | yes | yes | – |
| halide_halide_T2_R1_1 | RbPbI3 |  | -1.240 | yes | yes | – |
| halide_halide_T2_R1_2 | KMnI3 |  | -1.083 | yes | yes | – |
| halide_halide_T2_R1_3 | NaCoI3 |  | -0.586 | yes | yes | – |
| halide_halide_T2_R1_4 | NaSnI3 |  | -0.936 | yes | yes | – |
| halide_halide_T3_R1_1 | CsMnI3 |  | -1.160 | yes | yes | – |
| halide_halide_T3_R1_2 | NaFeI3 |  | -0.553 | yes | yes | – |
| halide_halide_T3_R2_3 | CsPbI3 |  | -1.302 | yes | yes | – |
| halide_halide_T3_R2_4 | RbSnI3 |  | -1.194 | yes | yes | – |
| oxide_oxide_T1_R1_1 | SrZrO3 |  | -3.478 | yes | no | – |
| oxide_oxide_T1_R1_2 | LaMnO3 |  | -2.467 | yes | no | – |
| oxide_oxide_T1_R1_3 | LaScO3 |  | -3.629 | yes | no | – |
| oxide_oxide_T1_R1_4 | NaTaO3 |  | -2.902 | yes | no | – |
| oxide_oxide_T2_R1_1 | LaMnO3 |  | -2.467 | yes | no | – |
| oxide_oxide_T2_R1_2 | BaMnO3 |  | -1.919 | yes | no | – |
| oxide_oxide_T2_R1_3 | SrVO3 |  | -2.416 | yes | yes | – |
| oxide_oxide_T2_R1_4 | BaPbO3 |  | -1.970 | yes | yes | – |

## Outputs

- inverse_design: [`benchmarks/runs/perov5/paper-candidates/inverse_design`](https://github.com/ABnano/MEIDNet/tree/main/benchmarks/runs/perov5/paper-candidates/inverse_design)

## Reproduce

```
python scripts/benchmarks.py paper-candidates perov5
```

Computed on Intel64 Family 6 Model 197 Stepping 2, GenuineIntel (16 threads), CPU only.
