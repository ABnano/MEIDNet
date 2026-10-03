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

## Results

| metric | value | split | note |
|---|---|---|---|
| `cosine_matched` | 0.97 | validation | mean cosine similarity between the structure and property latents of the same material, as reported in the paper |
| `l2_matched` | 0.24 | validation | mean L2 distance between the two latents of the same material, as reported in the paper |

## Validation

Evidence level: <span class="ladder" title="generated">●○○○○</span> generated.

Evidence:

- <https://doi.org/10.1038/s41524-026-02153-3>

## Reproduce

Configuration `examples/perov5/meidnet.yaml`, split val:

```
python scripts/benchmarks.py reproduce paper-representation
```


_These numbers are quoted from the paper and have not been re-run from this repository._

## Notes

Numbers quoted from the paper (npj Computational Materials, 2026). `reproduce` re-evaluates the shipped checkpoint on the CDVAE validation split and adds MAE, R2 and retrieval metrics; cosine_matched is compared with the quoted value.
