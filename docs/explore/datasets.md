# Datasets

Datasets that work with MEIDNet, and what has been done with each. **One card per dataset, never one score
across datasets**: the tasks, sizes and properties differ, so results are only compared within a dataset
(see [Benchmarks](../benchmarks/index.md)).

| dataset | structures | properties used | size | with MEIDNet |
|---|---|---|---|---|
| [Perov-5](#perov-5) | cubic ABX₃ perovskites, 5 atoms per cell | direct band gap, formation enthalpy | 18,928 | <span class="mstatus sup">trained model, configuration, tutorial, benchmark</span> |
| [MP-20](#mp-20) | Materials Project, up to 20 atoms | none aligned in the paper | about 45,000 | <span class="mstatus plan">structure representation, published</span> |
| [Carbon-24](#carbon-24) | carbon allotropes, up to 24 atoms | none aligned in the paper | about 10,000 | <span class="mstatus plan">structure representation, published</span> |
| [Double perovskites A₂BB′X₆](../examples/double-perovskite.md) | a family file, no dataset | none | 10,800 compositions (halide variant) | <span class="mstatus part">design space and rules only</span> |
| [Your dataset](#your-dataset) | one material family | any scalar columns | any | <span class="mstatus sup">supported</span> |

New to multimodal data? [Learn multimodality](../learn/index.md) explains what a modality is, and
[Databases by application](databases.md) lists 31 computed and experimental sources.

<div class="grid cards" markdown>

-   **Perov-5** — *published multimodal benchmark*
    { #perov-5 }

    ---

    **18,928 cubic ABX₃ perovskites** (CDVAE split: 11,356 train / 3,787 validation / 3,785 test), each with a
    relaxed structure, formation enthalpy (`heat_all`, eV/atom) and direct band gap (`dir_gap`, eV).

    **Modalities used in MEIDNet:** crystal structure · electronic property (band gap) · thermodynamic property
    (formation enthalpy).

    **What the paper does with it:** multimodal alignment of the structure and property encoders, property
    reconstruction, and the inverse-design demonstration (candidates generated from property targets, screened
    with MACE and validated by DFT).

    **In this repository:** `meidnet download-data` fetches it; the published checkpoint
    `checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth` was trained on it; it is the data behind
    the [live Studio](https://babu09-meidnet.hf.space/studio/).

    **Suitable tasks:** inverse design from a band gap and a stability target · property prediction from the
    structure · structure–property retrieval · measuring how well two modalities align.

    **MEIDNet implementation:** ✓ pretrained model · ✓ configuration (`examples/perov5/meidnet.yaml`) ·
    ✓ tutorial ([the paper's experiment](../examples/perov5.md), [Colab](../start/colab.md)) ·
    ✓ benchmark results.

    [Open in the Studio](https://babu09-meidnet.hf.space/studio/){ .md-button .md-button--primary }

    [Benchmark results](../benchmarks/perov5.md) · [The paper's experiment](../examples/perov5.md) ·
    [Dataset source (CDVAE)](https://github.com/txie-93/cdvae/tree/main/data/perov_5) ·
    Castelli *et al.* 2012, Xie *et al.* 2022

-   **MP-20** — *published: structure-representation generalization*
    { #mp-20 }

    ---

    **~45,000 structures** from the Materials Project with at most 20 atoms per cell (CDVAE split).

    **Published MEIDNet use:** generalization of the crystal encoder / decoder beyond perovskites (structure
    representation and reconstruction). It is not a multimodal benchmark in the paper: no property modality was
    aligned on it, and no MP-20 checkpoint is shipped here.

    [Benchmark results](../benchmarks/mp20.md) · [Dataset source (CDVAE)](https://github.com/txie-93/cdvae/tree/main/data/mp_20)

-   **Carbon-24** — *published: structure-representation generalization*
    { #carbon-24 }

    ---

    **~10,000 carbon structures** with up to 24 atoms per cell (CDVAE split).

    **Published MEIDNet use:** the same structure-representation test as MP-20. Not a multimodal benchmark; no
    Carbon-24 checkpoint is shipped here.

    [Benchmark results](../benchmarks/carbon24.md) · [Dataset source (CDVAE)](https://github.com/txie-93/cdvae/tree/main/data/carbon_24)

</div>

## Your dataset { #your-dataset }

[Use your dataset in the Studio](https://babu09-meidnet.hf.space/studio/?panel=data){ .md-button .md-button--primary }

Any table with an id, one or more scalar property columns and a crystal structure per row (CIF text in a column
or one `.cif` file per id) can be used directly: upload it in the [Studio](https://babu09-meidnet.hf.space/studio/)
or run `meidnet init` → `check` → `train` → `generate` ([bring your own dataset](../use/your-data.md)).
The structures must belong to one [material family](../reference/families.md) (prototype + site groups), which is
what the rules and the search need.

## Datasets we would like to see benchmarked

Battery conductors, MOFs, 2D materials and spinels are natural next families. If you run MEIDNet on one of them,
[contribute the result](../community/contribute.md): the dataset gets its own benchmark page, and a verified row
once the result has been reproduced here.
