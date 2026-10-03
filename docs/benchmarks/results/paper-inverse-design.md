# MEIDNet (paper): inverse design of perovskites from property targets

<span class="bstatus pub">Published (from the paper)</span> · <span class="ladder" title="DFT validated">●●●●○</span> DFT validated

| | |
|---|---|
| Dataset | [Perov-5](../perov5.md) |
| Modalities | `structure`, `property:heat_all`, `property:dir_gap` |
| Model | MEIDNet early fusion + curriculum (production model) (MEIDNet 1.0 (paper), perovskite_abx3) |
| Category | Conditional design |
| Submitted by | Anand Babu (UCLouvain) on 2026-05-29 |
| Configuration | `examples/perov5/meidnet.yaml` |
| Checkpoint | [dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth](https://github.com/ABnano/MEIDNet/blob/main/checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |

## Results

| metric | value | split | note |
|---|---|---|---|
| `n_generated` | 140 structures |  | candidates generated from property targets in the campaign reported in the paper |
| `n_sun` | 19 structures |  | stable, unique and novel after screening |
| `sun_rate` | 0.136 |  | 19 of 140 |

## Validation

Evidence level: <span class="ladder" title="DFT validated">●●●●○</span> DFT validated.

Evidence:

- <https://doi.org/10.1038/s41524-026-02153-3>
- `examples/perov5/paper_results/`


_These numbers are quoted from the paper and have not been re-run from this repository._

## Notes

Numbers quoted from the paper. The 26 CIFs in examples/perov5/paper_results/ are the candidates shipped with the paper; the MLIP screening row re-runs `meidnet screen` on them.
