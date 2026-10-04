# Learn multimodality

A material can be described in many ways: by its atoms and their positions, by a formula, by measured or computed
properties, by a diffraction pattern, a spectrum, a micrograph or a paragraph in a paper. Each way of describing it
is a **modality**. Multimodal learning trains one model on several modalities of the same materials, so that it can
connect them: read a structure and predict a property, or start from the properties you want and propose a
structure, which is what MEIDNet does.

This short course takes about ten minutes. It covers the main ideas of multimodal learning for materials and, for
each, how MEIDNet implements it. For a full review, see Babu and Krishnan (2026).

<div class="learn-steps" markdown>

1. [What is a modality?](#what-is-a-modality)
2. [The multimodality map](#the-multimodality-map) (interactive)
3. [Five challenges of multimodal learning](#five-challenges)
4. [Contrastive learning: how two modalities are aligned](#contrastive-learning)
5. [From a shared space to inverse design](#inverse-design)
6. [Where to go next](#where-next)

</div>

## 1. What is a modality? { #what-is-a-modality }

A modality is one kind of observation of a material, with its own shape of data. The shape decides which kind of
neural network can read it.

| modality | what the data looks like | example | a network that reads it |
|---|---|---|---|
| Crystal structure | atoms with positions in a unit cell: a graph | a CIF file | graph neural network |
| Composition | elements and their fractions: a set | CsPbI₃ | set or element network |
| Scalar properties | a short vector of numbers | band gap, formation enthalpy | small fully connected network (MLP) |
| Diffraction pattern | a curve: intensity versus angle 2θ | powder XRD | 1D convolutional network |
| Spectra and DOS | a curve: signal versus energy | density of states, XAS, Raman | 1D convolutional network or transformer |
| Image | a grid of pixels | SEM or TEM micrograph | 2D convolutional network or vision transformer |
| Text | a sequence of words | a synthesis procedure | language model |

**Why combine them?** Each modality sees part of the material. A structure fixes the atoms but does not tell you
the band gap without a calculation; a band gap says nothing about which atoms produce it. A model that learns both
together can translate between them in either direction.

**What it needs:** *paired* data, where several modalities describe the same material. In Perov-5, every one of the
18,928 structures comes with its DFT band gap and formation enthalpy, which makes it a two-modality dataset.

## 2. The multimodality map { #the-multimodality-map }

Select a modality to see what it contains, which networks encode it, how it is combined with other modalities and
how MEIDNet handles it. The centre describes the shared representation.

<div class="mm" id="mm-map" aria-label="Interactive map of materials modalities"></div>

??? note "The map as a table"

    | modality | MEIDNet | how |
    |---|---|---|
    | Crystal structure | available | an E(n)-equivariant graph network (EGNN) encodes up to `max_sites` atoms (default 20) |
    | Scalar properties | available | all numeric columns form one vector, read by one MLP; every column becomes a target |
    | Composition | via the structure | the element on each site is part of the structure; formula-only data needs a composition model |
    | Processing conditions | partial | numeric conditions can be extra scalar columns, encoded together with the properties |
    | Diffraction (XRD) | planned | a vector-modality encoder for binned patterns, first item of the [roadmap](../understand/limits.md) |
    | Spectra and DOS | planned | as vector modalities |
    | Microscopy images | planned | an image encoder into the shared space |
    | Text | planned | a text encoder into the shared space |

    The [capabilities page](../explore/capabilities.md) lists the same information, generated from the code.

## 3. Five challenges of multimodal learning { #five-challenges }

Baltrušaitis, Ahuja and Morency organise multimodal machine learning around five challenges. Every multimodal model
answers each of them in some way, even if only by leaving it out.

| challenge | the question | a materials example | in MEIDNet |
|---|---|---|---|
| **Representation** | How is each modality encoded, and do they share one space (*joint*) or keep separate spaces tied by a constraint (*coordinated*)? | a graph network for the structure, an MLP for the property vector | both: two encoders whose outputs are coordinated by contrastive learning and then averaged into one joint latent of 128 numbers |
| **Translation** | How is one modality mapped to another? | structure → properties (prediction), properties → structure (inverse design) | both directions: decoders read the joint latent and the property latent alone |
| **Alignment** | Which parts of one modality correspond to which parts of another? | which XRD peaks come from which lattice planes | only whole materials: each structure is matched with its own property vector, not part by part |
| **Fusion** | How are the modalities joined to make a prediction? | one descriptor from structure and band gap together | the structure latent and the property latent are averaged ([a note on the word "early"](architectures.md#terminology)) |
| **Co-learning** | Can one modality help learn another, for example a scarce one? | learn from many simulated XRD patterns to read a few measured ones | closest analogue: the property branch is trained to rebuild the crystal on its own, so at design time properties alone are enough |

*Further reading:* Baltrušaitis *et al.* 2019 (the taxonomy) · Guo *et al.* 2019 (deep multimodal
representation learning) · Ngiam *et al.* 2011 (shared representations between modalities) · Babu and Krishnan
2026 (multimodal and cross-modal learning techniques).

## 4. Contrastive learning: how two modalities are aligned { #contrastive-learning }

Take a batch of $N$ materials. Each gives two vectors of length one: $z_c$ from its structure and $z_p$ from its
properties. The dot product of two such vectors is their cosine similarity. Lay out all $N \times N$ similarities
in a table: the diagonal holds the true pairs, everything else is a structure next to someone else's properties.

Contrastive learning turns each row into a multiple-choice question: *which of the $N$ property vectors belongs to
this structure?* The right answer is on the diagonal. It asks the same question for each column, from properties to
structures. The loss MEIDNet uses is this symmetric **InfoNCE** loss:

$$
\mathcal{L}_\text{InfoNCE} = \frac{1}{2N}\sum_{i=1}^{N}\left[
-\log\frac{\exp\!\big(z_c^{(i)}\!\cdot z_p^{(i)}/\tau\big)}{\sum_{j=1}^{N}\exp\!\big(z_c^{(i)}\!\cdot z_p^{(j)}/\tau\big)}
-\log\frac{\exp\!\big(z_p^{(i)}\!\cdot z_c^{(i)}/\tau\big)}{\sum_{j=1}^{N}\exp\!\big(z_p^{(i)}\!\cdot z_c^{(j)}/\tau\big)}
\right]
$$

The **temperature** $\tau$ sets how sharply the model must prefer the right answer. Move the slider to see its
effect on a batch of five materials: each row shows how much probability the model gives to each candidate.

<div class="nce" id="nce-play" aria-label="Contrastive loss playground"></div>

| setting in MEIDNet | value | in `meidnet.yaml` |
|---|---|---|
| temperature $\tau$ | 0.01 | `training.temperature` |
| strength of the alignment | 5.0 | `training.contrastive_weight` |
| warm-up: the strength grows from 0 to its full value over | 60 % of the epochs (the paper: 1,200 epochs) | `training.contrastive_warmup_epochs` |
| size of the shared space | 128 | `model.latent_dim` |

The warm-up is the paper's *curriculum*: the decoders first learn to rebuild crystals and properties, then the two
latents are pulled together. After training, the [training report](../use/reports.md) measures the alignment with
*retrieval*: how often the nearest property vector to a structure is its own (top 1) or among the five nearest
(top 5). The Studio's Model block plots the mean cosine between matched pairs during training.

The same loss pairs pictures with their captions in CLIP; MEIDNet pairs crystals with their properties.

*Further reading:* van den Oord *et al.* 2018 (InfoNCE) · Radford *et al.* 2021 (CLIP) · Babu and Krishnan 2026 ·
[Contrastive learning in the Architecture Atlas](architectures.md#contrastive).

## 5. From a shared space to inverse design { #inverse-design }

Once both modalities live in one space, a point in it can be read in both directions. MEIDNet makes the reverse
direction possible with one extra training term: the crystal decoder is also trained from the **property latent
alone**. A vector of wanted properties can then be encoded and decoded into a structure.

The search in practice:

1. **Encode the target.** The property encoder turns the target values into a starting point in the shared space.
2. **Optimise a population** of latent points so that their decoded properties approach the target, while staying
   diverse and near the target's latent.
3. **Decode** one element per site of a *material family* (a prototype such as cubic ABX₃), so candidates are
   compositions placed on a known arrangement of sites.
4. **Check the rules** (charge balance, tolerance factor, distances and your own) and keep only what passes.
5. **Rank** by distance to the target and save each candidate as a CIF with a report.

The full objective and every step are in [How MEIDNet works](../understand/how-it-works.md). Two limits matter:
MEIDNet does not invent new atomic arrangements, and its predicted properties are estimates to confirm with DFT or
experiment ([scope and roadmap](../understand/limits.md)).

*Further reading:* the MEIDNet paper (Babu *et al.* 2026) · Babu, Gouvêa and Rignanese 2026 (generative models,
multimodal learning and closed-loop workflows in inverse materials design) · Moro, Loh *et al.* 2025 (multimodal
foundation models for materials).

## 6. Where to go next { #where-next }

<div class="grid cards" markdown>

-   **Architecture Atlas**

    ---

    Early fusion, late fusion, shared latent spaces, cross-attention and contrastive learning, drawn the same way,
    with an advisor that recommends one for your data.

    [:octicons-arrow-right-24: Architecture Atlas](architectures.md)

-   **Recipes by problem**

    ---

    From a research question to an architecture, a dataset, a configuration and a tutorial.

    [:octicons-arrow-right-24: Recipes by problem](recipes.md)

-   **Build it**

    ---

    Upload a table of structures and properties, train in the browser, set targets, run the search.

    [:octicons-arrow-right-24: Open the Studio](https://babu09-meidnet.hf.space/studio/)

-   **Find data**

    ---

    Datasets that work with MEIDNet, and 31 computed and experimental databases grouped by application.

    [:octicons-arrow-right-24: Datasets](../explore/datasets.md)

</div>

## References { #references }

- T. Baltrušaitis, C. Ahuja, L.-P. Morency, "Multimodal machine learning: a survey and taxonomy",
  *IEEE Trans. Pattern Anal. Mach. Intell.* **41**, 423–443 (2019). [doi:10.1109/TPAMI.2018.2798607](https://doi.org/10.1109/TPAMI.2018.2798607)
- W. Guo, J. Wang, S. Wang, "Deep multimodal representation learning: a survey", *IEEE Access* **7**, 63373–63394
  (2019). [doi:10.1109/ACCESS.2019.2916887](https://doi.org/10.1109/ACCESS.2019.2916887)
- J. Ngiam *et al.*, "Multimodal deep learning", *ICML* (2011).
- A. van den Oord, Y. Li, O. Vinyals, "Representation learning with contrastive predictive coding" (2018).
  [arXiv:1807.03748](https://arxiv.org/abs/1807.03748)
- A. Radford *et al.*, "Learning transferable visual models from natural language supervision" (CLIP), *ICML*
  (2021). [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
- V. G. Satorras, E. Hoogeboom, M. Welling, "E(n) equivariant graph neural networks", *ICML* (2021).
  [arXiv:2102.09844](https://arxiv.org/abs/2102.09844)
- V. Moro, C. Loh *et al.*, "Multimodal foundation models for material property prediction and discovery",
  *Newton* (2025). [doi:10.1016/j.newton.2025.100016](https://doi.org/10.1016/j.newton.2025.100016)
- A. Babu, R. Almeida Gouvêa, G.-M. Rignanese, "Toward automated discovery with generative models multimodal
  learning and closed loop workflows in inverse materials design", *Cell Rep. Phys. Sci.* **7**, 103561 (2026).
  [doi:10.1016/j.xcrp.2026.103561](https://doi.org/10.1016/j.xcrp.2026.103561)
- A. Babu, N. M. A. Krishnan, "Multimodal and cross-modal learning techniques", *APL Mach. Learn.* **4**, 030901
  (2026). [doi:10.1063/5.0346744](https://doi.org/10.1063/5.0346744)
- A. Babu, R. Almeida Gouvêa, P. Vandergheynst, G.-M. Rignanese, "MEIDNet: Multimodal generative AI framework for
  inverse materials design", *npj Comput. Mater.* (2026). [doi:10.1038/s41524-026-02153-3](https://doi.org/10.1038/s41524-026-02153-3)
