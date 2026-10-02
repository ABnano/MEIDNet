# Perov-5 — the paper's experiment

The published MEIDNet model: cubic ABX₃ perovskites from the Perov-5 dataset (CDVAE split of Castelli et al.),
properties *formation enthalpy* (`heat_all`, eV/atom) and *direct band gap* (`dir_gap`, eV).

## Use the published checkpoint

```bash
meidnet demo --family halide --band-gap 2.0            # or: oxide, chalcogenide, nitride
meidnet studio                                          # explore it live
```

The three checkpoints from the paper are in `checkpoints/`; `..._propertyaware_2k.pth` is the recommended one.
`meidnet info checkpoints/<file>` describes any of them. They load into MEIDNet 2 unchanged.

## Retrain from scratch

```bash
meidnet download-data                       # train/val/test CSVs → data/perov5/ (18,928 rows, 18 MB)
meidnet train examples/perov5/meidnet.yaml  # 200 epochs ≈ 1 h on a laptop GPU
meidnet generate examples/perov5/meidnet.yaml
```

`examples/perov5/meidnet.yaml` reproduces the paper's settings, including two that differ from MEIDNet 2's
defaults: `normalize: false` for both properties and `align_to_prototype: false` (atoms in file order), and the
1200-epoch alignment ramp.

## The paper's generated structures

`examples/perov5/paper_results/` holds the 27 CIFs (halide, oxide, chalcogenide) reported in the paper.
`meidnet screen examples/perov5/paper_results --train-csv data/perov5/train.csv` recomputes their MACE
stability.

## Regression against v1

`tests/legacy_v1/` contains the v1.0 code byte for byte. `pytest -m slow` runs it and MEIDNet 2 on the same
targets and asserts identical CIFs, predictions and file names.
