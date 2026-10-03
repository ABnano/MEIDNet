# MEIDNet (paper): inverse design

The inverse-design campaign reported in the paper: candidates generated from property targets with the published model, screened for stability, uniqueness and novelty, and checked by DFT.

| field | value |
|---|---|
| Dataset | [Perov-5](../perov5.md), protocol `paper` |
| Type | model |
| Inputs | `structure`, `property:heat_all`, `property:dir_gap` |
| Parameters | 0.70 M |
| Training data | Perov-5 train (11,356) |
| Status | Reported in the paper |
| Evidence level | DFT validated |
| Added | 2026-05-29 by Anand Babu (UCLouvain) |
| Checkpoint | [dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth](https://huggingface.co/Babu09/MEIDNet/blob/main/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |
| Links | [paper](https://doi.org/10.1038/s41524-026-02153-3) · [code](https://github.com/ABnano/MEIDNet) · [weights](https://huggingface.co/Babu09/MEIDNet/blob/main/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth) |

## Inverse design

| metric | value | definition |
|---|---|---|
| Generated | 140 | candidates generated (reported in the paper) |
| SUN count | 19 | stable, unique and novel candidates |
| SUN | 0.136 | stable, unique and novel candidates divided by the budget of 54; a candidate that was not delivered counts as a failure |

## Evidence

- <https://doi.org/10.1038/s41524-026-02153-3>
- `examples/perov5/paper_results/`

## Notes

Numbers quoted from the paper: 140 candidates generated from property targets, 19 of them stable, unique and novel (13.6%). The paper's targets and budget differ from the protocol, so this record is not ranked. The candidates shipped with the paper (examples/perov5/paper_results) are screened with the protocol's criteria in the record 'Candidates shipped with the paper, screened here'.
