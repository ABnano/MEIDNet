# MEIDNet (paper): alignment of the two latents

Agreement of the structure latent and the property latent of the same material on the validation split, as reported in the paper for the published model.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `paper` |
| Type | model |
| Inputs | `structure`, `property:heat_all`, `property:dir_gap` |
| Parameters | 0.70 M |
| Training data | Perov-5 train (11,356) |
| Status | Reported in the paper |
| Evidence level | generated |
| Added | 2026-05-29 by Anand Babu (UCLouvain) |
| Checkpoint | [dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth](https://huggingface.co/Babu09/MEIDNet/blob/main/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |
| Links | [paper](https://doi.org/10.1038/s41524-026-02153-3) · [code](https://github.com/ABnano/MEIDNet) · [weights](https://huggingface.co/Babu09/MEIDNet/blob/main/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |

## Representation

| metric | value | definition |
|---|---|---|
| cos | 0.970 | mean cosine similarity between the structure latent and the property latent of the same material |
| L2 | 0.240 | mean L2 distance between the two latents of the same material (unit latents) |

## Evidence

- <https://doi.org/10.1038/s41524-026-02153-3>

## Re-evaluated here

On 2026-10-03 this repository's code re-evaluated the shipped checkpoint on the same split (MEIDNet 2.0.0).

| metric | reported | obtained here |
|---|---|---|
| cos | 0.970 | 0.771 |
| L2 | 0.240 | 0.676 |

## Notes

Numbers quoted from the paper (validation split). Re-evaluating the shipped checkpoint with this repository's code on the same split gives a mean cosine of 0.77 and an L2 distance of 0.68; the protocol's representation table reports the test-split values of this code.
