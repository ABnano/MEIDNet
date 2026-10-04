# MEIDNet (alignment training, seed 3)

One of the seven alignment models: seed 3, the seed with the highest structure matching, chosen for the inverse-design task before any candidate was generated.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `perov5-v1.1` |
| Type | model |
| Inputs | `structure`, `property:heat_all`, `property:dir_gap` |
| Parameters | 0.70 M |
| Training data | Perov-5, all 18,928 materials (the test split included: scores on it are not held-out) |
| Status | Computed here on 2026-10-05 |
| Evidence level | MLIP validated |
| Added | 2026-10-05 by Anand Babu (UCLouvain) |
| Alignment space | the normalised encoder outputs, before the projection heads |
| Checkpoint | [meidnet_paper_rerun_seed3.pth](https://huggingface.co/Babu09/MEIDNet/blob/main/reproduction/meidnet_paper_rerun_seed3.pth) · sha256 `205de8b83390…` |
| Links | [paper](https://doi.org/10.1038/s41524-026-02153-3) · [code](https://github.com/ABnano/MEIDNet) · [weights](https://huggingface.co/Babu09/MEIDNet/blob/main/reproduction/meidnet_paper_rerun_seed3.pth) |

## Inverse design

| metric | value | definition |
|---|---|---|
| SUN | 0.611 | stable, unique and novel candidates divided by the budget of 54; a candidate that was not delivered counts as a failure |
| Stable | 0.872 | fraction of delivered candidates whose MACE-MP-0 formation energy after relaxation is at most 0.10 eV/atom, against elemental reference phases (the criterion of `meidnet screen` and of the paper) |
| Unique | 1.000 | fraction of delivered candidates whose composition does not repeat an earlier one |
| Novel | 0.830 | fraction of delivered candidates whose composition is not in the data set (training, validation and test splits) |
| ΔHf | -1.32 eV/atom | median MACE-MP-0 formation energy of the delivered candidates |
| DFT hit | 0.250 | among candidates whose A, B and X sites match a Perov-5 entry (so their DFT band gap is known), the fraction within 0.5 eV of the target |
| DFT known | 8 | candidates with a known DFT band gap (the denominator of DFT hit) |
| Delivered | 47 | candidates delivered out of the budget of 54 |
| Valid | 0.870 | fraction of the budget that passes every rule of the family |
| SUN count | 33 | stable, unique and novel candidates |
| Budget | 54 | candidates requested |

### Candidates

Every candidate with its MLIP formation energy, novelty and, where Perov-5 has the same sites, the DFT band gap.

| candidate | formula | target gap (eV) | ΔHf (eV/atom) | stable | novel | DFT gap (eV) |
|---|---|---|---|---|---|---|
| oxide_T1_1 | NdCrO3 | 1.5 | -2.477 | yes | yes | – |
| oxide_T1_2 | BaPbO3 | 1.5 | -1.970 | yes | no | 0.00 |
| oxide_T1_3 | SrSnO3 | 1.5 | -2.475 | yes | no | 3.40 |
| oxide_T1_4 | YbGaO3 | 1.5 | -2.336 | yes | yes | – |
| oxide_T1_5 | HoNiO3 | 1.5 | -1.619 | yes | yes | – |
| oxide_T1_6 | BaSnO3 | 1.5 | -2.476 | yes | no | 2.50 |
| oxide_T2_1 | SmNiO3 | 2.5 | -1.699 | yes | yes | – |
| oxide_T2_2 | SrZrO3 | 2.5 | -3.478 | yes | no | 6.60 |
| oxide_T2_3 | YbCoO3 | 2.5 | -1.655 | yes | yes | – |
| oxide_T2_4 | TbAlO3 | 2.5 | -3.505 | yes | yes | – |
| oxide_T2_5 | YbAlO3 | 2.5 | -3.069 | yes | yes | – |
| oxide_T2_6 | NdVO3 | 2.5 | -2.559 | yes | yes | – |
| oxide_T3_1 | NdFeO3 | 3.5 | -2.033 | yes | yes | – |
| oxide_T3_2 | LuAlO3 | 3.5 | -3.417 | yes | yes | – |
| oxide_T3_3 | CsNbO3 | 3.5 | -2.475 | yes | no | 2.90 |
| oxide_T3_4 | SrGeO3 | 3.5 | -2.485 | yes | no | 1.70 |
| oxide_T3_5 | RbNbO3 | 3.5 | -2.632 | yes | no | 3.90 |
| oxide_T3_6 | CaSnO3 | 3.5 | -2.366 | yes | no | 3.60 |
| chalcogenide_T1_1 | SrWSe3 | 1.5 | 4.343 | no | yes | – |
| chalcogenide_T1_2 | SrSnSe3 | 1.5 | 5.797 | no | yes | – |
| chalcogenide_T1_3 | YbVSe3 | 1.5 | -1.316 | yes | yes | – |
| chalcogenide_T1_4 | BaSnSe3 | 1.5 | -1.413 | yes | yes | – |
| chalcogenide_T1_5 | CaSnSe3 | 1.5 | -1.012 | yes | yes | – |
| chalcogenide_T1_6 | SmCoSe3 | 1.5 | -1.105 | yes | yes | – |
| chalcogenide_T2_1 | EuScSe3 | 2.5 | -1.919 | yes | yes | – |
| chalcogenide_T2_2 | CaWSe3 | 2.5 | -1.033 | yes | yes | – |
| chalcogenide_T2_3 | CaMoSe3 | 2.5 | -1.089 | yes | yes | – |
| chalcogenide_T2_4 | SrTiSe3 | 2.5 | -2209239531516.471 | no | yes | – |
| chalcogenide_T2_5 | SrGeSe3 | 2.5 | -33544873571.535 | no | yes | – |
| chalcogenide_T2_6 | GdVSe3 | 2.5 | -1.323 | yes | yes | – |
| chalcogenide_T3_1 | SmMnSe3 | 3.5 | -1.258 | yes | yes | – |
| chalcogenide_T3_2 | YbFeSe3 | 3.5 | -1.180 | yes | yes | – |
| chalcogenide_T3_3 | YbCoSe3 | 3.5 | -339207415395.052 | no | yes | – |
| chalcogenide_T3_4 | SmFeSe3 | 3.5 | -1.139 | yes | yes | – |
| chalcogenide_T3_5 | SmCrTe3 | 3.5 | -1.267 | yes | yes | – |
| chalcogenide_T3_6 | TbCoSe3 | 3.5 | -9150744981.631 | no | yes | – |
| halide_T1_1 | KPbI3 | 1.5 | -1.186 | yes | yes | – |
| halide_T1_2 | KSnI3 | 1.5 | -1.142 | yes | yes | – |
| halide_T1_3 | NaSnI3 | 1.5 | -0.936 | yes | yes | – |
| halide_T1_4 | KCoI3 | 1.5 | -0.826 | yes | yes | – |
| halide_T1_5 | CsPbI3 | 1.5 | -1.302 | yes | yes | – |
| halide_T1_6 | KFeI3 | 1.5 | -0.737 | yes | yes | – |
| halide_T2_1 | RbMnI3 | 2.5 | -1.123 | yes | yes | – |
| halide_T2_2 | KZnI3 | 2.5 | -1.102 | yes | yes | – |
| halide_T3_1 | KMnI3 | 3.5 | -1.083 | yes | yes | – |
| halide_T3_2 | KNiI3 | 3.5 | -0.883 | yes | yes | – |
| halide_T3_3 | NaNiI3 | 3.5 | -0.723 | yes | yes | – |

## Outputs

- inverse_design: [`benchmarks/runs/perov5/meidnet-alignment-seed3/inverse_design`](https://github.com/ABnano/MEIDNet/tree/main/benchmarks/runs/perov5/meidnet-alignment-seed3/inverse_design)

## Reproduce

```
python scripts/benchmarks.py run perov5 --method meidnet-alignment-seed3
```

Computed on Intel64 Family 6 Model 197 Stepping 2, GenuineIntel (16 threads), CPU only; generating the candidates took 54 min.
