# Scope and roadmap

## What works today

| | |
|---|---|
| **Structures** | any CIF with up to `max_sites` atoms (default 20); any elements |
| **Properties** | any number of scalar columns |
| **Training** | your data, your properties; the published settings by default |
| **Generation** | prototype families: a fixed arrangement of sites whose occupants and cell size are chosen. Built in: cubic ABX₃, A₂BB′X₆; write your own in YAML |
| **Rules** | charge balance, tolerance and octahedral factors, bond windows, minimum distance, predicted-property windows, element filters, and your own Python rules |
| **Explanations** | reports for data, training and generation; the Studio for live what-if |

## What does not work (yet)

- **New atomic arrangements.** The decoder's positions are not used to create geometry; candidates are
  compositions placed on the family prototype. Generating free geometry needs a decoder trained to produce it
  (the published decoder receives the true positions during training).
- **Spectra, images, text as modalities.** The property modality is a vector of scalars. Binned XRD or DOS
  could be added as a vector modality with its own encoder; it is designed for but not implemented.
- **Large cells.** `max_sites` can be raised, but memory and time grow with the square of it, and the
  published model was trained on 5-atom cells.
- **Fine-tuning the published model on new properties.** Its property head has two outputs; train a new model.

## Roadmap (in order of likely value)

1. Vector modalities (XRD, DOS) with a shared-latent encoder each.
2. A `training.init_from` option to continue training from a checkpoint with the same properties.
3. A geometry-generating decoder variant (trained from prototype positions instead of true positions —
   `model.decoder_coordinate_input: prototype` is the first step and is available as an experimental setting).
4. More built-in families (spinel, Heusler, rocksalt/zincblende, MXene M₂XT₂).

Contributions of family files and rules are the easiest way to help; see the GitHub repository.
