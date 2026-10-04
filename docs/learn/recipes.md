# Recipes by problem

Start from a research question. Each recipe goes **problem → architecture → why → data → implementation →
tutorial → references**. The implementation is MEIDNet where it applies; otherwise the recipe names established
alternatives.

For step-by-step changes to a MEIDNet configuration (another target, another family, a new rule), see the
[how-to guides](../recipes/change-targets.md).

| problem | architecture | implementation |
|---|---|---|
| [Perovskites with a target band gap that are likely to be stable](#target-band-gap) | shared latent + contrastive | MEIDNet |
| [Candidates from your own DFT results for one family](#own-family) | shared latent + contrastive | MEIDNet |
| [Screen a whole family for a target before searching](#screen-family) | structure encoder of the shared space | MEIDNet |
| [Identify the crystal structure from an XRD pattern](#xrd-structure) | 1D convolutional network; contrastive pattern ↔ structure | 1D CNN classifiers; pattern encoder planned for MEIDNet |
| [Predict a property when only the formula is known](#formula-only) | composition network | Roost and similar composition models |
| [Connect synthesis text with structures](#synthesis-text) | text encoder + contrastive or cross-attention | text encoder planned for MEIDNet |
| [Design new atomic arrangements](#new-arrangements) | conditional generative model over full geometry | MatterGen, CDVAE |

## Perovskites with a target band gap that are likely to be stable { #target-band-gap }

| | |
|---|---|
| **Problem** | Find cubic ABX₃ halide perovskites with a direct band gap near 1.5 eV and a negative formation enthalpy. |
| **Architecture** | [Shared latent space](architectures.md#shared-latent) with [contrastive alignment](architectures.md#contrastive): MEIDNet. |
| **Why** | The question runs from properties to structure. A shared space whose crystal decoder is also trained from the property latent alone gives that direction, and the family's rules keep the chemistry sensible. |
| **Data** | Perov-5: 18,928 structures with DFT band gap and formation enthalpy ([dataset card](../explore/datasets.md)). The published checkpoint is trained on it. |
| **Implementation** | MEIDNet: `meidnet demo`, `meidnet generate` or the Studio's Targets and Search blocks. |
| **Tutorial** | [The paper's experiment](../examples/perov5.md) · in the browser: [Studio, Targets block](https://babu09-meidnet.hf.space/studio/?panel=targets) · [screen the candidates with MACE](../recipes/screen.md) |
| **References** | Babu *et al.* 2026 (MEIDNet); Castelli *et al.* 2012 (the dataset); Babu, Gouvêa and Rignanese 2026 (review of inverse design). |

One command with the published model:

```bash
meidnet demo --family halide --band-gap 1.5 --enthalpy -0.10
```

Or in `meidnet.yaml` (from `examples/perov5/meidnet.yaml`):

```yaml
generation:
  family: perovskite_abx3
  variant: halide
  objectives:
    - {property: dir_gap,  loss: l2, weight: 10000, select_weight: 1.0}
    - {property: heat_all, loss: l1, weight: 6000,  select_weight: 0.4}
  targets:
    - {dir_gap: 1.5, heat_all: -0.10}
```

## Candidates from your own DFT results for one family { #own-family }

| | |
|---|---|
| **Problem** | You computed structures and properties for one prototype family, for example A₂BB′X₆ double perovskites, and want new compositions with chosen property values. |
| **Architecture** | [Shared latent space](architectures.md#shared-latent) with [contrastive alignment](architectures.md#contrastive), trained on your table. |
| **Why** | The same reasoning as above. Every scalar column you give becomes a target you can set, and the family file says which sites exist and which elements may sit on them. |
| **Data** | A table with an id, numeric property columns and one CIF per row. Public sources by application are on [Databases by application](../explore/databases.md). |
| **Implementation** | MEIDNet: `meidnet init`, `check`, `train`, `generate`, or the Studio's Data and Model blocks. |
| **Tutorial** | [Bring your own dataset](../use/your-data.md) · in the browser: [Studio, Data block](https://babu09-meidnet.hf.space/studio/?panel=data) · [change the material family](../recipes/change-family.md) |
| **References** | Babu *et al.* 2026 (MEIDNet). |

```yaml
data:
  table: my_results.csv
  id_column: id
  cif_column: cif
  properties:
    - {column: band_gap, unit: eV}
    - {column: e_form,   unit: eV/atom}
generation:
  family: double_perovskite_a2bbx6
  variant: halide
  objectives:
    - {property: band_gap, loss: l2,      weight: 10000}
    - {property: e_form,   loss: at_most, weight: 6000}
  targets:
    - {band_gap: 1.8, e_form: -0.10}
```

Then `meidnet check` → `meidnet train` → `meidnet generate`; each step writes a report.

## Screen a whole family for a target before searching { #screen-family }

| | |
|---|---|
| **Problem** | Before running a search, see every composition the family allows, its rule values and its predicted properties, and which are predicted closest to the target. |
| **Architecture** | The structure encoder of the [shared space](architectures.md#shared-latent), read in the forward direction (structure → properties). |
| **Why** | For a prototype family the set of compositions is finite, so it can be scored exhaustively in seconds. Comparing these predictions with the search's candidates is a useful sanity check. |
| **Data** | A trained model and a family. |
| **Implementation** | MEIDNet: `meidnet space` or the Studio's design-space view. |
| **Tutorial** | [Explore in 3D](../use/explore-3d.md) · in the browser: [Studio, design space](https://babu09-meidnet.hf.space/studio/?explore=space) · [How MEIDNet works](../understand/how-it-works.md#the-design-space) |
| **References** | Babu *et al.* 2026 (MEIDNet). |

```bash
meidnet space examples/perov5/meidnet.yaml --model checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth -o space.csv
```

## Identify the crystal structure from an XRD pattern { #xrd-structure }

| | |
|---|---|
| **Problem** | Given a powder diffraction pattern, tell which crystal system, space group or known structure it comes from. |
| **Architecture** | A 1D convolutional classifier on the pattern (one modality). Multimodal: a pattern encoder aligned with a structure encoder by [contrastive learning](architectures.md#contrastive), so a pattern retrieves the structures it matches. |
| **Why** | A pattern is a fingerprint of the lattice. A classifier needs labels; a contrastive model needs only (pattern, structure) pairs, which can be simulated from any structure database. |
| **Data** | Simulate patterns from computed or experimental structures ([semiconductor physics](../explore/databases.md#semiconductor-physics), [all databases](../explore/databases.md#all-databases)), for example with pymatgen's XRD calculator; validate on measured patterns. |
| **Implementation** | 1D convolutional classifiers such as Park *et al.* (2017). In MEIDNet, an encoder for binned XRD patterns is the first item of the [roadmap](../understand/limits.md) and is not yet available. |
| **References** | Park *et al.* 2017; Baltrušaitis *et al.* 2019; Babu and Krishnan 2026. |

## Predict a property when only the formula is known { #formula-only }

| | |
|---|---|
| **Problem** | Predict a band gap or a stability measure for compositions whose crystal structure is unknown, as in many experimental tables. |
| **Architecture** | A composition network that reads the formula as a weighted set of elements, such as Roost. With extra numeric inputs (temperature, doping), [early fusion](architectures.md#early-fusion) of composition features and those numbers is a strong baseline. |
| **Why** | MEIDNet needs a structure for every row. If your formulas all sit on one prototype (for example ABX₃), you can build those structures on the prototype and use MEIDNet; otherwise a composition model is the appropriate choice. |
| **Data** | Experimental band gaps and Matbench tasks are listed on [Databases by application](../explore/databases.md#semiconductor-physics). |
| **Implementation** | Roost or another composition model; outside MEIDNet, which requires a crystal structure per material. |
| **References** | Goodall and Lee 2020 (Roost); Dunn *et al.* 2020 (Matbench). |

## Connect synthesis text with structures { #synthesis-text }

| | |
|---|---|
| **Problem** | Link written synthesis procedures to the structures they produce, to suggest how a candidate might be made or which candidates resemble known syntheses. |
| **Architecture** | A text encoder (a language model) aligned with a structure encoder by [contrastive learning](architectures.md#contrastive); [cross-attention](architectures.md#cross-attention) when individual words must be tied to individual elements or steps. |
| **Why** | Text and structures have no common format; a shared space lets each be compared with the other. |
| **Data** | Text-mined synthesis recipes (Kononova *et al.* 2019) paired with structures from a structure database. |
| **Implementation** | A text encoder that maps into MEIDNet's shared space is planned and not yet available. |
| **References** | Kononova *et al.* 2019; Moro, Loh *et al.* 2025; Babu and Krishnan 2026. |

## Design new atomic arrangements { #new-arrangements }

| | |
|---|---|
| **Problem** | Generate crystals whose atomic arrangement is not one of a few known prototypes. |
| **Architecture** | A conditional generative model over the full geometry: diffusion (MatterGen) or a variational autoencoder (CDVAE). |
| **Why** | MEIDNet places compositions on a family prototype and does not invent arrangements ([scope](../understand/limits.md)). Models that generate positions and cells directly can. |
| **Data** | Large structure databases; the generative benchmarks are listed under [generative-model benchmarks](../explore/databases.md#generative-model-benchmarks). |
| **Implementation** | MatterGen, CDVAE and related generative models. |
| **References** | Zeni *et al.* 2025 (MatterGen); Xie *et al.* 2022 (CDVAE); Babu, Gouvêa and Rignanese 2026 (review). |

## References { #references }

- A. Babu, R. Almeida Gouvêa, P. Vandergheynst, G.-M. Rignanese, "MEIDNet: Multimodal generative AI framework for
  inverse materials design", *npj Comput. Mater.* (2026). [doi:10.1038/s41524-026-02153-3](https://doi.org/10.1038/s41524-026-02153-3)
- I. E. Castelli *et al.*, "New cubic perovskites for one- and two-photon water splitting using the computational
  materials repository", *Energy Environ. Sci.* **5**, 9034 (2012). [doi:10.1039/C2EE22341D](https://doi.org/10.1039/C2EE22341D)
- W. B. Park *et al.*, "Classification of crystal structure using a convolutional neural network", *IUCrJ* **4**,
  486–494 (2017). [doi:10.1107/S205225251700714X](https://doi.org/10.1107/S205225251700714X)
- R. E. A. Goodall, A. A. Lee, "Predicting materials properties without crystal structure: deep representation
  learning from stoichiometry", *Nat. Commun.* **11**, 6280 (2020). [doi:10.1038/s41467-020-19964-7](https://doi.org/10.1038/s41467-020-19964-7)
- A. Dunn *et al.*, "Benchmarking materials property prediction methods: the Matbench
  test set and Automatminer reference algorithm", *npj Comput. Mater.* **6**, 138 (2020). [doi:10.1038/s41524-020-00406-3](https://doi.org/10.1038/s41524-020-00406-3)
- O. Kononova *et al.*, "Text-mined dataset of inorganic materials synthesis recipes", *Sci. Data* **6**, 203 (2019).
  [doi:10.1038/s41597-019-0224-1](https://doi.org/10.1038/s41597-019-0224-1)
- A. Babu, R. Almeida Gouvêa, G.-M. Rignanese, "Toward automated discovery with generative models multimodal
  learning and closed loop workflows in inverse materials design", *Cell Rep. Phys. Sci.* **7**, 103561 (2026).
  [doi:10.1016/j.xcrp.2026.103561](https://doi.org/10.1016/j.xcrp.2026.103561)
- A. Babu, N. M. A. Krishnan, "Multimodal and cross-modal learning techniques", *APL Mach. Learn.* **4**, 030901
  (2026). [doi:10.1063/5.0346744](https://doi.org/10.1063/5.0346744)
- C. Zeni *et al.*, "A generative model for inorganic materials design", *Nature* **639**, 624–632 (2025).
  [doi:10.1038/s41586-025-08628-5](https://doi.org/10.1038/s41586-025-08628-5)
- T. Xie *et al.*, "Crystal diffusion variational autoencoder for periodic material generation", *ICLR* (2022).
  [arXiv:2110.06197](https://arxiv.org/abs/2110.06197)
- T. Baltrušaitis, C. Ahuja, L.-P. Morency, "Multimodal machine learning: a survey and taxonomy", *IEEE TPAMI*
  **41**, 423–443 (2019). [doi:10.1109/TPAMI.2018.2798607](https://doi.org/10.1109/TPAMI.2018.2798607)
- V. Moro, C. Loh *et al.*, "Multimodal foundation models for material property prediction and discovery",
  *Newton* (2025). [doi:10.1016/j.newton.2025.100016](https://doi.org/10.1016/j.newton.2025.100016)
