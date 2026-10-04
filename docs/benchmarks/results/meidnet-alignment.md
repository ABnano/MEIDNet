# MEIDNet (alignment training, 7 seeds)

The alignment training script (early fusion, contrastive weight raised over the first 1,500 of 2,200 epochs), trained seven times with seeds 0 to 6. Values are the mean over the seven models; ± is the standard deviation.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `perov5-v1.1` |
| Type | model |
| Inputs | `structure`, `property:heat_all`, `property:dir_gap` |
| Parameters | 0.70 M |
| Training data | Perov-5, all 18,928 materials (the test split included: scores on it are not held-out) |
| Status | Computed here on 2026-10-05 |
| Evidence level | generated |
| Added | 2026-10-05 by Anand Babu (UCLouvain) |
| Runs | 7 independent training runs (seeds); values are the mean ± the standard deviation |
| Alignment space | the normalised encoder outputs, before the projection heads |
| Links | [paper](https://doi.org/10.1038/s41524-026-02153-3) · [code](https://github.com/ABnano/MEIDNet) · [weights](https://huggingface.co/Babu09/MEIDNet/tree/main/reproduction) |

## Representation

| metric | value | definition |
|---|---|---|
| R@1 | 0.297 ± 0.062 | fraction of test materials for which, among the distinct property profiles of the test split, their own profile's latent is the nearest to their structure latent (materials with identical property values share one profile) |
| R@5 | 0.855 ± 0.065 | the same within the five nearest profiles |
| cos | 0.954 ± 0.011 | mean cosine similarity between the structure latent and the property latent of the same material, in the space where the model aligns them (before or after its projection heads; stated on the method's page) |
| k-NN MAE ΔH | 0.025 ± 0.004 eV/atom | formation-enthalpy error of a 5-nearest-neighbour probe: each test material takes the mean property of its five nearest training materials in the representation |
| k-NN MAE gap | 0.049 ± 0.016 eV | direct-band-gap error of the same probe |
| L2 | 0.302 ± 0.034 | mean L2 distance between the two latents of the same material (unit latents) |
| cos, encoder outputs | 0.954 | the matched cosine between the normalised encoder outputs, before the projection heads |
| cos, projection heads | -0.978 | the matched cosine between the outputs of the projection heads |
| profiles | 367 | distinct property profiles among the test materials: the candidates of retrieval (chance level of R@1 is one over this number) |
| n | 3,785 | test materials evaluated |

## Reproduce

```
python scripts/benchmarks.py run perov5 --method meidnet-alignment
```

Computed on Intel64 Family 6 Model 197 Stepping 2, GenuineIntel (16 threads), CPU only; the evaluation took 4 min.

## Notes

This model has no structure-only property head: its property decoder reads the joint latent, which contains the properties themselves. Prediction from the structure alone is therefore measured by the k-nearest-neighbour probe of this table, and the model is not listed under property prediction.
