# Change the target properties

## A different value

```yaml
generation:
  targets:
    - {band_gap: 1.2}
    - {band_gap: 1.8}      # each entry is its own search
```

## A different kind of goal

`loss` says how a prediction is compared with the target:

| `loss` | meaning | typical use |
|---|---|---|
| `l2` | squared distance (default) | hit a value |
| `l1` | absolute distance | hit a value, less sensitive to outliers |
| `at_most` | only values above the target are penalised | formation enthalpy ≤ −0.1 eV/atom |
| `at_least` | only values below are penalised | dielectric constant ≥ 20 |

```yaml
objectives:
  - {property: band_gap,   loss: l2,       weight: 10000, select_weight: 1.0}
  - {property: enthalpy,   loss: at_most,  weight: 6000,  select_weight: 0.4}
```

`weight` acts during the latent search; `select_weight` when ranking finished candidates.

## A different property

The model knows the properties it was trained on (`meidnet info model.pt` lists them). To steer a property that
is not in the model, [add it to the data and retrain](add-property.md).

## In the Studio

Drag the target slider; the predicted-closest table and the scatter update at once, and a warning appears if
the target lies outside the training range. Export the YAML when you are happy.
