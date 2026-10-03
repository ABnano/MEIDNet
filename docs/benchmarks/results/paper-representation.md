# MEIDNet (paper): alignment of structure and property latents on Perov-5

<span class="bstatus pub">Published (from the paper)</span> · <span class="ladder" title="generated">●○○○○</span> generated

| | |
|---|---|
| Dataset | [Perov-5](../perov5.md) |
| Modalities | `structure`, `property:heat_all`, `property:dir_gap` |
| Model | MEIDNet early fusion + curriculum (production model) (MEIDNet 1.0 (paper), perovskite_abx3) |
| Category | Representation quality |
| Submitted by | Anand Babu (UCLouvain) on 2026-05-29 |
| Configuration | `examples/perov5/meidnet.yaml` |
| Checkpoint | [dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth](https://github.com/ABnano/MEIDNet/blob/main/checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |
| Notes on the model | 128-dimensional shared latent space; 2000 epochs, contrastive warm-up over the first 1200 |

## Results

| metric | value | split | meaning | note |
|---|---|---|---|---|
| `cosine_matched` | 0.97 | validation | mean cosine similarity between the structure and property latents of the same material (1 = aligned) | mean cosine similarity between the structure and property latents of the same material, as reported in the paper |
| `l2_matched` | 0.24 | validation | mean L2 distance between those two latents (0 = identical) | mean L2 distance between the two latents of the same material, as reported in the paper |

## Validation

Evidence level: <span class="ladder" title="generated">●○○○○</span> generated.

Evidence:

- <https://doi.org/10.1038/s41524-026-02153-3>

## Reproduce

Configuration `examples/perov5/meidnet.yaml`, split val:

```
python scripts/benchmarks.py reproduce paper-representation
```


_These numbers are quoted from the paper._

## Re-run here did not agree

On 2026-10-03 this repository's code re-ran the recipe above (AMD64 CPU, MEIDNet 2.0.0) and obtained different numbers. The row keeps its status; the comparison is shown so that readers can judge it. Possible reasons: a different split or protocol in the original measurement, a different definition of the metric, or a checkpoint that is not the one the numbers were measured on.

| metric | this row | obtained here | agree |
|---|---|---|---|
| `cosine_matched` | 0.97 | 0.771 | no |
| `l2_matched` | 0.24 | 0.676 | no |

Also obtained in that run: `mae_heat_all` = 0.392, `r2_heat_all` = 0.497, `mae_dir_gap` = 2.79, `r2_dir_gap` = -35.8, `retrieval_top1` = 0.0253, `retrieval_top5` = 0.0908, `n_evaluated` = 3,787


## Notes

Numbers quoted from the paper (npj Computational Materials, 2026). `reproduce` re-evaluates the shipped checkpoint on the CDVAE validation split and adds MAE, R2 and retrieval metrics; cosine_matched is compared with the quoted value.
