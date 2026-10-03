# 5-minute quickstart

=== "In the browser (nothing to install)"

    Open the [**live Studio**](https://babu09-meidnet.hf.space/). It runs the published perovskite model: move
    rule limits and targets and watch what passes, run a latent search and read each candidate's checklist,
    export the `meidnet.yaml`. (Search budgets are capped on the shared server; the local install below has
    no limits and takes your own data.)

=== "On your computer"

    ```bash
    pip install meidnet          # PyTorch CPU wheels are fine; CUDA is optional
    meidnet demo                 # halide perovskites, band gap 2.0 eV → runs/demo/
    ```

    `demo` downloads the 2.8 MB published checkpoint, searches for 3 candidates (about a minute on a CPU),
    checks them against the family's rules and opens `generation_report.html`.

    ```bash
    meidnet demo --family oxide --band-gap 3.0 --enthalpy -0.2 -n 5
    meidnet studio               # the live workbench with the same model
    ```

=== "In Colab"

    [Notebook 01 — quickstart](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/01_quickstart.ipynb){ .md-button }

## What the demo did

1. **Targets → latent.** The property encoder maps (band gap, enthalpy) to a point in the shared latent space.
2. **Search.** A population of latents near that point is optimised so that the decoder's output matches the
   targets and the family's soft terms (cubic cell, sensible charges, …).
3. **Decode + rules.** Each latent is decoded into one element per site; the composition is placed on the
   family's prototype and must pass every hard rule (charge balance, tolerance factor, …).
4. **Report.** The best new, unique candidates are saved as CIFs with a card that shows each rule's value and
   a gauge of predicted vs target property.

## Next

- [What data do I need?](what-data.md) then [Bring your own dataset](../use/your-data.md).
- [MEIDNet Studio](../use/studio.md) to see the effect of every change live.
