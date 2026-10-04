# Perov-5: choose a model and generate

From nothing installed to candidate materials checked with a machine-learned interatomic potential (MLIP), with the commands that were run for this page and what they printed. Then: which of the public checkpoints to use for what.

[Quick start](#quick-start) · [Which model](#which-model) · [Your own targets](#your-own-targets) · [Your own data](#your-own-data)
{ .lb-toolbar }

## Quick start

Three candidates for a direct band gap of 2 eV, generated and screened. Run on a laptop for this page: 29 seconds to generate, under 2 minutes to screen.

<div class="psteps" markdown>

1. **Install.**

    ```bash
    pip install "meidnet[stability] @ git+https://github.com/ABnano/MEIDNet.git"
    ```

    `[stability]` adds the MACE potential for step 3. Without it, steps 1 and 2 work the same.

2. **Generate.** The demo uses the published model and the cubic halide perovskite family.

    ```bash
    meidnet demo --family halide --band-gap 2.0 --enthalpy -0.10 -n 3 --out runs/demo
    ```

    It printed:

    | candidate | predicted band gap (eV) | predicted formation enthalpy (eV/atom) | note |
    |---|---|---|---|
    | NaNiI₃ | 1.97 | -0.10 |  |
    | KMnI₃ | 2.09 | 0.35 |  |
    | NaSnI₃ | 1.98 | -1.31 | extrapolating: outside the range of the training data |

    Each candidate is a CIF file in `runs/demo/generation/cifs/`; `runs/demo/generation_report.html` shows every rule each one passed.

3. **Screen with the MLIP.** MACE-MP-0 relaxes each crystal and computes its formation energy.

    ```bash
    meidnet screen runs/demo/generation/cifs --train-csv data/perov5/train.csv
    ```

    It printed:

    | candidate | MACE formation energy (eV/atom) | stable | unique | novel |
    |---|---|---|---|---|
    | NaNiI₃ | -0.72 | yes | yes | yes |
    | KMnI₃ | -1.08 | yes | yes | yes |
    | NaSnI₃ | -0.94 | yes | yes | yes |

    3 of 3 are stable (formation energy at most 0.10 eV/atom), unique and novel. `--train-csv` needs `meidnet download-data` once; without it, novelty is skipped.

4. **Confirm.** An MLIP is a first filter. Before any claim about a candidate, confirm its stability and its band gap with DFT.

</div>

The outputs of this run are kept in [`benchmarks/reproduction/perov5/demo/`](https://github.com/ABnano/MEIDNet/blob/main/benchmarks/reproduction/perov5/demo). No installation: the same search runs in the [Studio](https://babu09-meidnet.hf.space/studio/?panel=targets).

## Which model

All public checkpoints, measured under the same protocol ([leaderboard](perov5.md)): 54 candidates for three band-gap targets in three chemical families, screened with MACE-MP-0.

| model | stable, unique, novel (of 54) | stable (share) | band-gap target met, of candidates with a DFT value | alignment (cosine) | retrieval, top 1 |
|---|---|---|---|---|---|
| [MEIDNet (published model)](results/meidnet-2k.md) | 33 | 0.96 | 1 of 18 | 0.772 | 0.336 |
| [MEIDNet (shorter training)](results/meidnet-propertyaware.md) | 30 | 0.92 | 1 of 18 | 0.480 | 0.297 |
| [MEIDNet (first early-fusion model)](results/meidnet-earlyfusion.md) | 35 | 0.94 | 3 of 16 | 0.655 | 0.028 |
| [Encoder screening](results/baseline-screening.md) (baseline) | 46 | 0.85 | – | – | – |
| [Random sampling](results/baseline-random.md) (baseline) | 42 | 0.89 | 0 of 6 | – | – |

Checkpoint files: MEIDNet (published model): `dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth`; MEIDNet (shorter training): `…_propertyaware.pth`; MEIDNet (first early-fusion model): `dual_autoencoder_clip_earlyfusion.pth`.

!!! key "How to read this table, and what to start with"
    - **The checkpoints are close on stability.** They deliver between 30 and 35 stable, unique and novel candidates of 54. Each is a single run; how much this count changes with the seed has not been measured.
    - **Stable, unique and novel is not the design goal.** The two baselines score higher on it (46 and 42 of 54), in part because they rarely return a material of the data set. Whether the band-gap target is met is only known where a DFT value exists: 16 to 18 candidates per model, too few to rank the models.
    - **To generate, start with the published model**: it is the model of `meidnet demo` and of the Studio, and its decoder (like that of the shorter training) was trained to rebuild a crystal from the property latent alone, which is what inverse design asks of it. Compare its candidates with the encoder screening of the same family (`meidnet space`), which needs no search.
    - **To study the shared space, use the seven alignment models**: their modalities agree most closely (cosine 0.95 against 0.77 for the published model), and seven seeds show how much a result depends on the seed. They were not trained to decode from properties alone.

## Your own targets

Targets, families, elements and rules are settings of one file, `meidnet.yaml`.

```bash
meidnet init --template perov5 -o meidnet.yaml       # a starting file
# edit generation.targets, generation.variant, generation.exclude_elements …
meidnet generate meidnet.yaml --model checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth
meidnet screen runs/perov5/generation/cifs --train-csv data/perov5/train.csv
```

[Change the target properties](../recipes/change-targets.md) · [Exclude or restrict elements](../recipes/elements.md) · [Change the material family](../recipes/change-family.md) · [Add a rule](../recipes/add-constraint.md)

## Your own data

A table with one row per material, a CIF for each row and one numeric column per property is enough to train your own model: [Bring your own dataset](../use/your-data.md). When you train:

- keep the contrastive warm-up, train more than one seed and choose the checkpoint on the validation split ([why](perov5-insights.md#how-the-model-learns));
- expect the alignment of a short training to depend on the seed ([figure](perov5-reproduction.md#during-training));
- hold materials out, and report the scores on them ([what to expect](perov5-reproduction.md#unseen-materials)).
