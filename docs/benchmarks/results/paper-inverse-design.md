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

| metric | value | split | meaning | note |
|---|---|---|---|---|
| `n_generated` | 140 structures |  | candidates the search produced | candidates generated from property targets in the campaign reported in the paper |
| `n_sun` | 19 structures |  | stable, unique and novel candidates | stable, unique and novel after screening |
| `sun_rate` | 0.136 |  | n_sun / n_generated | 19 of 140 |

<div class="bench-chart" markdown="0"><svg class="chart wide" viewBox="0 0 560 76" role="img"><title>MEIDNet (paper): inverse design of perovskites from property targets: from generated to validated</title><text class="tick" x="8" y="23">generated</text><rect class="bar" x="200" y="9" width="310.0" height="22"/><text class="val" x="516.0" y="23">140</text><text class="tick" x="8" y="57">stable, unique, novel</text><rect class="ok" x="200" y="43" width="42.1" height="22"/><text class="val" x="248.1" y="57">19</text></svg></div>

## Validation

Evidence level: <span class="ladder" title="DFT validated">●●●●○</span> DFT validated.

Evidence:

- <https://doi.org/10.1038/s41524-026-02153-3>
- `examples/perov5/paper_results/`


_These numbers are quoted from the paper._

## Notes

Numbers quoted from the paper. The 26 CIFs in examples/perov5/paper_results/ are the candidates shipped with the paper; the MLIP screening row re-runs `meidnet screen` on them.
