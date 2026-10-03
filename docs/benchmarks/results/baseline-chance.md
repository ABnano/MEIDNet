# Chance level

Retrieval by random choice among the 3,785 test materials.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `perov5-v1` |
| Type | baseline |
| Inputs | `structure` |
| Parameters | – |
| Training data | – |
| Status | Computed here on 2026-10-03 |
| Evidence level | generated |
| Added | 2026-10-03 by Anand Babu (UCLouvain) |
| Links | [code](https://github.com/ABnano/MEIDNet) |

## Representation

| metric | value | definition |
|---|---|---|
| R@1 | 0.003 | fraction of test materials for which, among the distinct property profiles of the test split, their own profile's latent is the nearest to their structure latent (materials with identical property values share one profile) |
| R@5 | 0.014 | the same within the five nearest profiles |
| cos | 0.000 | mean cosine similarity between the structure latent and the property latent of the same material |
| profiles | 367 | distinct property profiles among the test materials: the candidates of retrieval (chance level of R@1 is one over this number) |
| n | 3,785 | test materials evaluated |

## Reproduce

```
python scripts/benchmarks.py run perov5 --method baseline-chance
```

Computed on Intel64 Family 6 Model 197 Stepping 2, GenuineIntel (16 threads), CPU only; the evaluation took 16 s.
