# Scope, limitations and roadmap

These pages document the released package, meidnet 2.3.1. MEIDNet Matter, the applied companion, runs a development
snapshot of the engine and states the measured limits of its five case studies on its
[Scope and limits page](https://babu09-meidnet-matter.hf.space/limits).

## Limitations

- **A candidate is a proposal.** It is a composition placed on a family prototype, with properties predicted by the
  model. Nothing in the package runs DFT. `meidnet screen` relaxes candidates with MACE-MP-0 and applies a
  formation-energy filter (at most 0.10 eV/atom against the elemental phases): a first filter, not stability on the
  convex hull ([screening](../recipes/screen.md)).
- **The published model knows one chemistry.** It was trained on Perov-5, its test split included: cubic ABX₃ cells
  of five atoms whose anion sites hold oxygen and nitrogen, with fluorine and sulfur only in mixed sets. Perov-5 has no
  Cl, Br, I or Se, and La is its only lanthanide, so halide and lanthanide candidates from this model are
  extrapolations; the demo and the Studio nevertheless start from the halide variant.
- **Its property predictions are rough.** On Perov-5's test split, which was part of its training data, the band gap
  read from a structure alone misses by 2.79 eV on average, against 0.17 eV for always predicting the training mean
  (1.68 against 2.14 eV on the non-zero gaps); the formation enthalpy does better than the mean (0.40 against
  0.57 eV/atom). See the [Perov-5 leaderboard](../benchmarks/perov5.md).
- **What has been validated.** Only Perov-5 has a benchmark protocol. Its inverse-design score combines the
  formation-energy filter, uniqueness, novelty and a DFT check that is possible only where Perov-5 holds the same sites,
  in practice for oxides: the published model met the band-gap target in 1 of 18 such checks, and its ΔHf·U·N (0.611)
  is below both baselines (0.778 and 0.852). MP-20 and Carbon-24 have no protocol yet. Nothing has been tested
  experimentally.
- **Which crystal structures.** Both built-in families are cubic: Pm-3m ABX₃, and Fm-3m A₂BB′X₆ in its rhombohedral
  primitive cell. A family file may use a general cell (`a, b, c, alpha, beta, gamma`); it is scaled from one edge with
  its shape fixed, needs a model trained on structures of that prototype, and its rules must be written for it, since
  the tolerance and octahedral factors are perovskite rules. No non-cubic family ships or has been tested, and the
  hosted Studio takes the built-in families only.
- **The rules are approximations.** The tolerance and octahedral factors use ionic radii averaged over every oxidation
  state pymatgen lists, which shrinks every anion except oxygen: with the built-in bounds, CsPbBr₃ (octahedral factor
  1.27) and CsPbCl₃ (1.44) fail the 0.90 limit. Read halide and nitride results with this in mind; a fix will use the
  radius of the oxidation state that balances charge.

## What a dataset needs

What the rows contain matters more than how many there are. Measured on MEIDNet Matter's case studies:

| to do this | what it needs | measured |
|---|---|---|
| predict a property from structure | a well-posed property: continuous, few zero values, few materials sharing one property profile | 166 training structures read a band gap with r 0.97 and a 0.65 eV error (34 test structures); 897 with 35 % zero gaps fell short on telling metals from non-metals |
| screen an enumerated family | data that fit one family, and a property model that passes | 166 to 897 training structures |
| generate | one prototype, and hundreds of distinct compositions per element for the decoder | Perov-5 generates; data with 11 to 48 compositions per element went to screening |

A few hundred structures train a property model, not a generator. The package's own checks: `meidnet check` warns
below 200 usable rows; the training report's note below 500 training materials is a rule of thumb, not a measurement;
training needs at least `batch_size` materials (16 by default); the validation split is a random 10 %, and there is
none below 10 rows. The published model cannot be fine-tuned on new properties yet, so a small dataset trains a model
from scratch. [What data do I need?](../start/what-data.md)

## Current capabilities

| | |
|---|---|
| **Structures** | any CIF with up to `max_sites` atoms (default 20); any elements |
| **Properties** | any number of scalar columns |
| **Training** | your data, your properties; the published settings by default |
| **Generation** | prototype families: a fixed arrangement of sites whose occupants and cell size are chosen. Built in: cubic ABX₃, A₂BB′X₆; write your own in YAML |
| **Rules** | charge balance, tolerance and octahedral factors, bond windows, minimum distance, predicted-property windows, element filters, and your own Python rules |
| **Explanations** | reports for data, training and generation; the Studio for live what-if |

On the hosted Studio: up to 1,500 rows and 8 MB per upload, 30 training epochs, 20 atoms per cell
([the Studio](../use/studio.md)).

## Not yet supported

- **New atomic arrangements.** The decoder's positions are not used to create geometry; candidates are
  compositions placed on the family prototype. Generating free geometry needs a decoder trained to produce it
  (the published decoder receives the true positions during training). MEIDNet Matter runs a development snapshot of
  the engine, meidnet 2.4.0.dev4, whose symmetry decoder, trained on MP-20, builds new cells without a family and
  samples at the target's anchor instead of optimising the latent point. It is not in a release of this package yet;
  its measured limits (on MP-20 more than half of the relaxed cells collapse, and a delivered gap is good to about
  ±0.7 eV) are on [Matter's Scope and limits page](https://babu09-meidnet-matter.hf.space/limits).
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
5. Ionic radii from the charge-balancing oxidation state in the tolerance and octahedral factors.

Contributions of family files and rules are the easiest way to help; see the GitHub repository.
