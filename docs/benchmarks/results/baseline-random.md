# Random sampling

Draws compositions at random, without repetition, from those that pass the family's rules.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `perov5-v1.1` |
| Type | baseline |
| Inputs | `structure` |
| Parameters | – |
| Training data | – |
| Status | Computed here on 2026-10-05 |
| Evidence level | MLIP validated |
| Added | 2026-10-03 by Anand Babu (UCLouvain) |
| Links | [code](https://github.com/ABnano/MEIDNet) |

## Inverse design

| metric | value | definition |
|---|---|---|
| SUN | 0.778 | stable, unique and novel candidates divided by the budget of 54; a candidate that was not delivered counts as a failure |
| Stable | 0.889 | fraction of delivered candidates whose MACE-MP-0 formation energy after relaxation is at most 0.10 eV/atom, against elemental reference phases (the criterion of `meidnet screen` and of the paper) |
| Unique | 1.000 | fraction of delivered candidates whose composition does not repeat an earlier one |
| Novel | 0.889 | fraction of delivered candidates whose composition is not in the data set (training, validation and test splits) |
| ΔHf | -1.34 eV/atom | median MACE-MP-0 formation energy of the delivered candidates |
| DFT hit | 0.000 | among candidates whose A, B and X sites match a Perov-5 entry (so their DFT band gap is known), the fraction within 0.5 eV of the target |
| DFT known | 6 | candidates with a known DFT band gap (the denominator of DFT hit) |
| Delivered | 54 | candidates delivered out of the budget of 54 |
| Valid | 1.000 | fraction of the budget that passes every rule of the family |
| SUN count | 42 | stable, unique and novel candidates |
| Budget | 54 | candidates requested |

### Candidates

Every candidate with its MLIP formation energy, novelty and, where Perov-5 has the same sites, the DFT band gap.

| candidate | formula | target gap (eV) | ΔHf (eV/atom) | stable | novel | DFT gap (eV) |
|---|---|---|---|---|---|---|
| oxide_T1_1 | PrGaO3 | 1.5 | -2.837 | yes | yes | – |
| oxide_T1_2 | TmNiO3 | 1.5 | -1.618 | yes | yes | – |
| oxide_T1_3 | NdFeO3 | 1.5 | -2.033 | yes | yes | – |
| oxide_T1_4 | BaGeO3 | 1.5 | -2.357 | yes | no | 0.00 |
| oxide_T1_5 | LaMnO3 | 1.5 | -2.467 | yes | no | 0.00 |
| oxide_T1_6 | SmScO3 | 1.5 | -3.469 | yes | yes | – |
| oxide_T2_1 | SmFeO3 | 2.5 | -1.998 | yes | yes | – |
| oxide_T2_2 | NdCrO3 | 2.5 | -2.477 | yes | yes | – |
| oxide_T2_3 | YbVO3 | 2.5 | -2.555 | yes | yes | – |
| oxide_T2_4 | LaAlO3 | 2.5 | -3.587 | yes | no | 6.30 |
| oxide_T2_5 | SmMnO3 | 2.5 | -2.318 | yes | yes | – |
| oxide_T2_6 | PrVO3 | 2.5 | -2.572 | yes | yes | – |
| oxide_T3_1 | EuAlO3 | 3.5 | -3.186 | yes | yes | – |
| oxide_T3_2 | RbVO3 | 3.5 | -1.599 | yes | no | 0.00 |
| oxide_T3_3 | SmNiO3 | 3.5 | -1.699 | yes | yes | – |
| oxide_T3_4 | CaHfO3 | 3.5 | -3.529 | yes | no | 7.30 |
| oxide_T3_5 | LaNiO3 | 3.5 | -1.800 | yes | no | 0.00 |
| oxide_T3_6 | TmCoO3 | 3.5 | -1.903 | yes | yes | – |
| chalcogenide_T1_1 | SrMoTe3 | 1.5 | -1.308 | yes | yes | – |
| chalcogenide_T1_2 | TbCoS3 | 1.5 | -93642942051.475 | no | yes | – |
| chalcogenide_T1_3 | LuCoS3 | 1.5 | -2.538 | yes | yes | – |
| chalcogenide_T1_4 | BaMoSe3 | 1.5 | -1.401 | yes | yes | – |
| chalcogenide_T1_5 | CsTaTe3 | 1.5 | -1.295 | yes | yes | – |
| chalcogenide_T1_6 | SrWSe3 | 1.5 | 4.343 | no | yes | – |
| chalcogenide_T2_1 | EuMnTe3 | 2.5 | -1.422 | yes | yes | – |
| chalcogenide_T2_2 | LuVTe3 | 2.5 | -1.088 | yes | yes | – |
| chalcogenide_T2_3 | SmFeTe3 | 2.5 | -1.290 | yes | yes | – |
| chalcogenide_T2_4 | SmScTe3 | 2.5 | -1.644 | yes | yes | – |
| chalcogenide_T2_5 | ErVS3 | 2.5 | -62.703 | no | yes | – |
| chalcogenide_T2_6 | NdVTe3 | 2.5 | -1.364 | yes | yes | – |
| chalcogenide_T3_1 | NaNbTe3 | 3.5 | -1.208 | yes | yes | – |
| chalcogenide_T3_2 | SrGeS3 | 3.5 | -251.214 | no | yes | – |
| chalcogenide_T3_3 | EuCrTe3 | 3.5 | -1.365 | yes | yes | – |
| chalcogenide_T3_4 | BaGeSe3 | 3.5 | -1.507 | yes | yes | – |
| chalcogenide_T3_5 | NdMnSe3 | 3.5 | -1.320 | yes | yes | – |
| chalcogenide_T3_6 | SmVTe3 | 3.5 | -1.307 | yes | yes | – |
| halide_T1_1 | NaFeI3 | 1.5 | -0.553 | yes | yes | – |
| halide_T1_2 | NaCoBr3 | 1.5 | -177820821092.041 | no | yes | – |
| halide_T1_3 | CsZnI3 | 1.5 | -1.165 | yes | yes | – |
| halide_T1_4 | KCoI3 | 1.5 | -0.754 | yes | yes | – |
| halide_T1_5 | NaNiI3 | 1.5 | -0.723 | yes | yes | – |
| halide_T1_6 | RbZnI3 | 1.5 | -1.136 | yes | yes | – |
| halide_T2_1 | KMnI3 | 2.5 | -1.083 | yes | yes | – |
| halide_T2_2 | NaSnI3 | 2.5 | -0.936 | yes | yes | – |
| halide_T2_3 | NaCuI3 | 2.5 | -0.724 | yes | yes | – |
| halide_T2_4 | CsPbI3 | 2.5 | -1.302 | yes | yes | – |
| halide_T2_5 | RbSnI3 | 2.5 | -1.194 | yes | yes | – |
| halide_T2_6 | KCuI3 | 2.5 | -0.892 | yes | yes | – |
| halide_T3_1 | KFeI3 | 3.5 | -0.737 | yes | yes | – |
| halide_T3_2 | RbFeI3 | 3.5 | -0.773 | yes | yes | – |
| halide_T3_3 | KNiI3 | 3.5 | -0.883 | yes | yes | – |
| halide_T3_4 | RbPbI3 | 3.5 | -1.240 | yes | yes | – |
| halide_T3_5 | RbCoI3 | 3.5 | 1.502 | no | yes | – |
| halide_T3_6 | KPbI3 | 3.5 | -1.186 | yes | yes | – |

## Outputs

- inverse_design: [`benchmarks/runs/perov5/baseline-random/inverse_design`](https://github.com/ABnano/MEIDNet/tree/main/benchmarks/runs/perov5/baseline-random/inverse_design)

## Reproduce

```
python scripts/benchmarks.py run perov5 --method baseline-random
```

Computed on Intel64 Family 6 Model 197 Stepping 2, GenuineIntel (16 threads), CPU only; generating the candidates took 8 s.
