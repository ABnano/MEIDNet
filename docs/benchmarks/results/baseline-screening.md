# Encoder screening

Enumerates the compositions of each chemical family that pass its rules and keeps those that the published model's structure encoder predicts closest to each target, ranked with the generator's own selection score. No latent search.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `perov5-v1` |
| Type | baseline |
| Inputs | `structure`, `property:heat_all`, `property:dir_gap` |
| Parameters | 0.70 M |
| Training data | Perov-5 train (11,356) |
| Status | Computed here on 2026-10-03 |
| Evidence level | MLIP validated |
| Added | 2026-10-03 by Anand Babu (UCLouvain) |
| Checkpoint | [dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth](https://huggingface.co/Babu09/MEIDNet/blob/main/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) · sha256 `f9493781d5bb…` |
| Links | [paper](https://doi.org/10.1038/s41524-026-02153-3) · [code](https://github.com/ABnano/MEIDNet) · [weights](https://huggingface.co/Babu09/MEIDNet/blob/main/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |

## Inverse design

| metric | value | definition |
|---|---|---|
| SUN | 0.852 | stable, unique and novel candidates divided by the budget of 54; a candidate that was not delivered counts as a failure |
| Stable | 0.852 | fraction of delivered candidates whose MACE-MP-0 formation energy after relaxation is at most 0.10 eV/atom, against elemental reference phases (the criterion of `meidnet screen` and of the paper) |
| Unique | 1.000 | fraction of delivered candidates whose composition does not repeat an earlier one |
| Novel | 1.000 | fraction of delivered candidates whose composition is not in the training split |
| ΔHf | -1.28 eV/atom | median MACE-MP-0 formation energy of the delivered candidates |
| DFT hit | – | among candidates whose A, B and X sites match a Perov-5 entry (so their DFT band gap is known), the fraction within 0.5 eV of the target |
| DFT known | 0 | candidates with a known DFT band gap (the denominator of DFT hit) |
| Delivered | 54 | candidates delivered out of the budget of 54 |
| Valid | 1.000 | fraction of the budget that passes every rule of the family |
| SUN count | 46 | stable, unique and novel candidates |
| Budget | 54 | candidates requested |

### Candidates

Every candidate with its MLIP formation energy, novelty and, where Perov-5 has the same sites, the DFT band gap.

| candidate | formula | target gap (eV) | ΔHf (eV/atom) | stable | novel | DFT gap (eV) |
|---|---|---|---|---|---|---|
| oxide_T1_1 | NdInO3 | 1.5 | -2.353 | yes | yes | – |
| oxide_T1_2 | HoNiO3 | 1.5 | -1.619 | yes | yes | – |
| oxide_T1_3 | ErNiO3 | 1.5 | -1.612 | yes | yes | – |
| oxide_T1_4 | YbNiO3 | 1.5 | -1.232 | yes | yes | – |
| oxide_T1_5 | EuNiO3 | 1.5 | -1.360 | yes | yes | – |
| oxide_T1_6 | NdScO3 | 1.5 | -3.504 | yes | yes | – |
| oxide_T2_1 | TmNiO3 | 2.5 | -1.618 | yes | yes | – |
| oxide_T2_2 | NdNiO3 | 2.5 | -1.710 | yes | yes | – |
| oxide_T2_3 | DyNiO3 | 2.5 | -1.636 | yes | yes | – |
| oxide_T2_4 | PrNiO3 | 2.5 | -1.712 | yes | yes | – |
| oxide_T2_5 | GdNiO3 | 2.5 | -1.643 | yes | yes | – |
| oxide_T2_6 | CeNiO3 | 2.5 | -1.821 | yes | yes | – |
| oxide_T3_1 | NdFeO3 | 3.5 | -2.033 | yes | yes | – |
| oxide_T3_2 | SmGaO3 | 3.5 | -2.813 | yes | yes | – |
| oxide_T3_3 | DyFeO3 | 3.5 | -1.922 | yes | yes | – |
| oxide_T3_4 | EuGaO3 | 3.5 | -2.478 | yes | yes | – |
| oxide_T3_5 | YbGaO3 | 3.5 | -2.336 | yes | yes | – |
| oxide_T3_6 | CeGaO3 | 3.5 | -2.822 | yes | yes | – |
| chalcogenide_T1_1 | RbTaTe3 | 1.5 | -1.290 | yes | yes | – |
| chalcogenide_T1_2 | GdMnSe3 | 1.5 | -1.284 | yes | yes | – |
| chalcogenide_T1_3 | TmMnSe3 | 1.5 | -1.060 | yes | yes | – |
| chalcogenide_T1_4 | KTaTe3 | 1.5 | -1.276 | yes | yes | – |
| chalcogenide_T1_5 | CeCoTe3 | 1.5 | -1.410 | yes | yes | – |
| chalcogenide_T1_6 | YbMnSe3 | 1.5 | -1.286 | yes | yes | – |
| chalcogenide_T2_1 | RbNbSe3 | 2.5 | 2.337 | no | yes | – |
| chalcogenide_T2_2 | CaMoSe3 | 2.5 | -1.089 | yes | yes | – |
| chalcogenide_T2_3 | PrVS3 | 2.5 | -40.822 | no | yes | – |
| chalcogenide_T2_4 | TmVS3 | 2.5 | -2084964401148.708 | no | yes | – |
| chalcogenide_T2_5 | LuVS3 | 2.5 | -162867401.493 | no | yes | – |
| chalcogenide_T2_6 | CeVS3 | 2.5 | -358782074876.452 | no | yes | – |
| chalcogenide_T3_1 | LaVS3 | 3.5 | -41.510 | no | yes | – |
| chalcogenide_T3_2 | LaScSe3 | 3.5 | -2.041 | yes | yes | – |
| chalcogenide_T3_3 | LaMnSe3 | 3.5 | -1.510 | yes | yes | – |
| chalcogenide_T3_4 | SrSnSe3 | 3.5 | 5.797 | no | yes | – |
| chalcogenide_T3_5 | KTaSe3 | 3.5 | -1.263 | yes | yes | – |
| chalcogenide_T3_6 | SrMoSe3 | 3.5 | -1.256 | yes | yes | – |
| halide_T1_1 | KFeI3 | 1.5 | -0.737 | yes | yes | – |
| halide_T1_2 | RbFeI3 | 1.5 | -0.773 | yes | yes | – |
| halide_T1_3 | KCoI3 | 1.5 | -0.754 | yes | yes | – |
| halide_T1_4 | NaFeI3 | 1.5 | -0.553 | yes | yes | – |
| halide_T1_5 | KCuI3 | 1.5 | -0.892 | yes | yes | – |
| halide_T1_6 | NaMnI3 | 1.5 | -0.900 | yes | yes | – |
| halide_T2_1 | NaCoI3 | 2.5 | -0.586 | yes | yes | – |
| halide_T2_2 | NaCoBr3 | 2.5 | -623037439245549568.000 | no | yes | – |
| halide_T2_3 | NaNiI3 | 2.5 | -0.723 | yes | yes | – |
| halide_T2_4 | RbMnI3 | 2.5 | -1.123 | yes | yes | – |
| halide_T2_5 | NaNiBr3 | 2.5 | -0.987 | yes | yes | – |
| halide_T2_6 | CsZnI3 | 2.5 | -1.165 | yes | yes | – |
| halide_T3_1 | NaCuI3 | 3.5 | -0.724 | yes | yes | – |
| halide_T3_2 | CsPbI3 | 3.5 | -1.302 | yes | yes | – |
| halide_T3_3 | NaSnI3 | 3.5 | -0.936 | yes | yes | – |
| halide_T3_4 | RbZnI3 | 3.5 | -1.136 | yes | yes | – |
| halide_T3_5 | RbPbI3 | 3.5 | -1.240 | yes | yes | – |
| halide_T3_6 | RbCuI3 | 3.5 | -0.922 | yes | yes | – |

## Outputs

- inverse_design: [`benchmarks/runs/perov5/baseline-screening/inverse_design`](https://github.com/ABnano/MEIDNet/tree/main/benchmarks/runs/perov5/baseline-screening/inverse_design)

## Reproduce

```
python scripts/benchmarks.py run perov5 --method baseline-screening
```

Computed on Intel64 Family 6 Model 197 Stepping 2, GenuineIntel (16 threads), CPU only; generating the candidates took 6 s.
