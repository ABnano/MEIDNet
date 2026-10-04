# Training mean

Predicts the training-set mean of each property.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `perov5-v1.1` |
| Type | baseline |
| Inputs | `structure` |
| Parameters | – |
| Training data | Perov-5 train (11,356) |
| Status | Computed here on 2026-10-05 |
| Evidence level | generated |
| Added | 2026-10-03 by Anand Babu (UCLouvain) |
| Links | [code](https://github.com/ABnano/MEIDNet) |

## Property prediction

| metric | value | definition |
|---|---|---|
| MAE ΔH | 0.566 eV/atom | mean absolute error of the formation enthalpy (heat_all) |
| RMSE ΔH | 0.744 eV/atom | root-mean-square error of the formation enthalpy |
| R² ΔH | -0.000 | coefficient of determination of the formation enthalpy (0 = no better than the mean) |
| MAE gap | 0.173 eV | mean absolute error of the direct band gap over all test materials; 96% of them have a gap of 0 eV |
| MAE gap > 0 | 2.135 eV | mean absolute error of the direct band gap on the test materials with a non-zero gap, the range that inverse design targets |
| RMSE gap | 0.536 eV | root-mean-square error of the direct band gap |
| R² gap | -0.000 | coefficient of determination of the direct band gap; not informative here, because the gap is zero for most materials |
| MAE ΔH ≠ 0 | 0.566 eV/atom | mean absolute error of the formation enthalpy on materials where it is not zero |
| n | 3,785 | test materials evaluated |

## Reproduce

```
python scripts/benchmarks.py run perov5 --method baseline-train-mean
```

Computed on Intel64 Family 6 Model 197 Stepping 2, GenuineIntel (16 threads), CPU only; the evaluation took 22 s.
