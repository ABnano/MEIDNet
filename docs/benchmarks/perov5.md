# Perov-5

18,928 cubic ABX3 perovskites with relaxed structures, formation enthalpy (heat_all, eV/atom) and direct band gap (dir_gap, eV). The CDVAE split of the Castelli et al. (2012) perovskite set; the dataset behind the published MEIDNet model and the live Studio.

**18,928 rows** · split: CDVAE: 11,356 train / 3,785 val / 3,787 test · properties: `heat_all`, `dir_gap` · role in the paper: the published multimodal benchmark: alignment, property reconstruction and inverse design · [dataset source](https://github.com/txie-93/cdvae/tree/main/data/perov_5)

!!! note "Read a row"
    Rows are compared only within this dataset and category. The ladder ●○○○○ … ●●●●● is the
    evidence level (generated → ML filtered → MLIP validated → DFT validated → experimentally validated).
    *Published* = taken from the paper; *MEIDNet verified* = reproduced here from the submitted configuration.

## Representation quality

| result | model | modalities | cosine_matched | l2_matched | evidence | status |
|---|---|---|---|---|---|---|
| [MEIDNet (paper): alignment of structure and property latents on Perov-5](results/paper-representation.md) | MEIDNet early fusion + curriculum (production model) | structure, property:heat_all, property:dir_gap | 0.97 | 0.24 | <span class="ladder" title="generated">●○○○○</span> generated | <span class="bstatus pub">Published (from the paper)</span> |

## Conditional design

| result | model | modalities | n_generated | n_sun | sun_rate | evidence | status |
|---|---|---|---|---|---|---|---|
| [MEIDNet (paper): inverse design of perovskites from property targets](results/paper-inverse-design.md) | MEIDNet early fusion + curriculum (production model) | structure, property:heat_all, property:dir_gap | 140 structures | 19 structures | 0.136 | <span class="ladder" title="DFT validated">●●●●○</span> DFT validated | <span class="bstatus pub">Published (from the paper)</span> |

## Validation level

| result | model | modalities | n_screened | evidence | status |
|---|---|---|---|---|---|
| [MLIP screening of the shipped paper candidates (MACE-MP-0)](results/paper-results-mace-screen.md) | MEIDNet early fusion + curriculum (production model) | structure, property:heat_all, property:dir_gap | 26 structures | <span class="ladder" title="MLIP validated">●●●○○</span> MLIP validated | <span class="bstatus sub">Community submitted</span> |
