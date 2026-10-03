# MLIP screening of the shipped paper candidates (MACE-MP-0)

<span class="bstatus sub">Community submitted</span> · <span class="ladder" title="MLIP validated">●●●○○</span> MLIP validated

| | |
|---|---|
| Dataset | [Perov-5](../perov5.md) |
| Modalities | `structure`, `property:heat_all`, `property:dir_gap` |
| Model | MEIDNet early fusion + curriculum (production model) (MEIDNet 2.0.0, perovskite_abx3) |
| Category | Validation level |
| Submitted by | Anand Babu (UCLouvain) on 2026-10-03 |
| Configuration | `examples/perov5/meidnet.yaml` |
| Checkpoint | [dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth](https://github.com/ABnano/MEIDNet/blob/main/checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |
| Resources | laptop CPU |

## Results

| metric | value | split | note |
|---|---|---|---|
| `n_screened` | 26 structures |  | the CIFs in examples/perov5/paper_results/ |

## Validation

Evidence level: <span class="ladder" title="MLIP validated">●●●○○</span> MLIP validated.

Evidence:

- `examples/perov5/paper_results/`

## Reproduce

Configuration `examples/perov5/meidnet.yaml`:

```
meidnet screen examples/perov5/paper_results --train-csv data/perov5/train.csv
```

## Notes

n_stable / n_unique / n_novel / n_sun are filled in by `python scripts/benchmarks.py reproduce paper-results-mace-screen` (MACE-MP-0 relaxation, about ten minutes on a CPU).
