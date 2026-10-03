# Architecture Atlas

Five ways to build a model from several modalities, drawn the same way: inputs on the left, what the model produces
on the right. Each card says when the design fits, what it costs, an example from materials science and whether
MEIDNet implements it. At the end, [the advisor](#advisor) recommends one for your data and your goal.

New to the topic? Start with [Learn multimodality](index.md).

<div class="atlas" markdown>

<div class="atlas-card" markdown>
<div class="atlas-fig" markdown="0"><svg class="ad" viewBox="0 0 360 132" role="img" aria-label="Early fusion: features of two modalities are concatenated and given to one model">
<defs><marker id="ah-early" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L8,4L0,8z" fill="#8a8a8a"/></marker></defs>
<rect class="ma" x="4" y="16" width="74" height="30" rx="6"/><text x="41" y="35" text-anchor="middle">Modality A</text>
<rect class="mb" x="4" y="86" width="74" height="30" rx="6"/><text x="41" y="105" text-anchor="middle">Modality B</text>
<path class="arr" d="M78,31 L104,58" marker-end="url(#ah-early)"/><path class="arr" d="M78,101 L104,74" marker-end="url(#ah-early)"/>
<rect class="ma" x="106" y="50" width="34" height="32" rx="4"/><rect class="mb" x="140" y="50" width="34" height="32" rx="4"/>
<text x="140" y="44" text-anchor="middle" class="sm">concatenate</text><text x="123" y="70" text-anchor="middle">a</text><text x="157" y="70" text-anchor="middle">b</text>
<path class="arr" d="M174,66 L196,66" marker-end="url(#ah-early)"/>
<rect class="box" x="198" y="50" width="70" height="32" rx="6"/><text x="233" y="70" text-anchor="middle">one model</text>
<path class="arr" d="M268,66 L288,66" marker-end="url(#ah-early)"/>
<rect class="out" x="290" y="50" width="66" height="32" rx="6"/><text x="323" y="70" text-anchor="middle">prediction</text>
</svg></div>
<div class="atlas-body" markdown>

### Early fusion { #early-fusion }

<span class="mstatus no">Not in MEIDNet</span>

**Idea.** Join the modalities at the input: turn each into features, concatenate them into one vector, train one
model on it.

**When it fits.** Every material has every modality; the features have a fixed length and similar scales; you want
a quick baseline.

**Strengths.** Simple. The model can use interactions between features from the first layer.
**Weaknesses.** A missing modality breaks the input. Very different shapes (a graph and a curve) are hard to
concatenate. A large modality can drown a small one.

**Materials example.** Composition descriptors, the processing temperature and a few peak positions from an XRD
pattern, concatenated and given to a gradient-boosted regressor.

*References:* Snoek *et al.* 2005; Baltrušaitis *et al.* 2019.

</div>
</div>

<div class="atlas-card" markdown>
<div class="atlas-fig" markdown="0"><svg class="ad" viewBox="0 0 360 132" role="img" aria-label="Late fusion: one model per modality, the predictions are combined">
<defs><marker id="ah-late" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L8,4L0,8z" fill="#8a8a8a"/></marker></defs>
<rect class="ma" x="4" y="16" width="74" height="30" rx="6"/><text x="41" y="35" text-anchor="middle">Modality A</text>
<rect class="mb" x="4" y="86" width="74" height="30" rx="6"/><text x="41" y="105" text-anchor="middle">Modality B</text>
<path class="arr" d="M78,31 L98,31" marker-end="url(#ah-late)"/><path class="arr" d="M78,101 L98,101" marker-end="url(#ah-late)"/>
<rect class="box" x="100" y="16" width="64" height="30" rx="6"/><text x="132" y="35" text-anchor="middle">model A</text>
<rect class="box" x="100" y="86" width="64" height="30" rx="6"/><text x="132" y="105" text-anchor="middle">model B</text>
<path class="arr" d="M164,31 L184,31" marker-end="url(#ah-late)"/><path class="arr" d="M164,101 L184,101" marker-end="url(#ah-late)"/>
<rect class="out" x="186" y="16" width="64" height="30" rx="6"/><text x="218" y="35" text-anchor="middle">guess A</text>
<rect class="out" x="186" y="86" width="64" height="30" rx="6"/><text x="218" y="105" text-anchor="middle">guess B</text>
<path class="arr" d="M250,31 L282,58" marker-end="url(#ah-late)"/><path class="arr" d="M250,101 L282,74" marker-end="url(#ah-late)"/>
<rect class="fz" x="284" y="50" width="72" height="32" rx="6"/><text x="320" y="70" text-anchor="middle">combine</text>
<text x="320" y="98" text-anchor="middle" class="sm">average or vote</text>
</svg></div>
<div class="atlas-body" markdown>

### Late fusion { #late-fusion }

<span class="mstatus no">Not in MEIDNet</span>

**Idea.** One model per modality, each makes its own prediction; the predictions are combined by averaging, voting
or a small model on top.

**When it fits.** Modalities are often missing, models for each already exist, or robustness matters more than
squeezing out the last bit of accuracy.

**Strengths.** Modular. Tolerates a missing modality. Each model can be trained on its own, larger dataset.
**Weaknesses.** Cannot learn how the modalities interact. There is no shared representation, so no translation
from one modality to another and no inverse design.

**Materials example.** A structure-based graph network and a spectrum-based convolutional network each predict a
phase label; the final label averages their probabilities.

*References:* Snoek *et al.* 2005; Baltrušaitis *et al.* 2019.

</div>
</div>

<div class="atlas-card core" markdown>
<div class="atlas-fig" markdown="0"><svg class="ad" viewBox="0 0 360 140" role="img" aria-label="Shared latent space: one encoder per modality into a common space where the two latents are aligned and averaged, then decoded">
<defs><marker id="ah-shared" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L8,4L0,8z" fill="#8a8a8a"/></marker></defs>
<rect class="ms" x="4" y="18" width="70" height="30" rx="6"/><text x="39" y="37" text-anchor="middle">Structure</text>
<rect class="mp" x="4" y="92" width="70" height="30" rx="6"/><text x="39" y="111" text-anchor="middle">Properties</text>
<path class="arr" d="M74,33 L90,33" marker-end="url(#ah-shared)"/><path class="arr" d="M74,107 L90,107" marker-end="url(#ah-shared)"/>
<rect class="box" x="92" y="18" width="56" height="30" rx="6"/><text x="120" y="37" text-anchor="middle">EGNN</text>
<rect class="box" x="92" y="92" width="56" height="30" rx="6"/><text x="120" y="111" text-anchor="middle">MLP</text>
<ellipse class="space" cx="222" cy="70" rx="56" ry="58"/><text x="222" y="9" text-anchor="middle" class="sm">shared space (128-d)</text>
<path class="arr" d="M148,33 L196,48" marker-end="url(#ah-shared)"/><path class="arr" d="M148,107 L196,94" marker-end="url(#ah-shared)"/>
<path class="align" d="M204,56 L204,86"/><text x="198" y="75" text-anchor="end" class="sm">align</text>
<circle class="zc" cx="204" cy="50" r="6"/><circle class="zp" cx="204" cy="92" r="6"/>
<path class="thin" d="M209,53 L238,68"/><path class="thin" d="M209,89 L238,74"/>
<circle class="zj" cx="244" cy="71" r="7"/><text x="244" y="95" text-anchor="middle" class="sm">average</text>
<path class="arr" d="M278,71 L292,71" marker-end="url(#ah-shared)"/>
<rect class="out" x="294" y="55" width="62" height="32" rx="6"/><text x="325" y="75" text-anchor="middle">decoders</text>
<text x="325" y="104" text-anchor="middle" class="sm">structure and</text><text x="325" y="117" text-anchor="middle" class="sm">properties</text>
</svg></div>
<div class="atlas-body" markdown>

### Shared latent space (joint and coordinated) { #shared-latent }

<span class="mstatus core">Core idea used by MEIDNet</span> <span class="mstatus sup">Supported</span>

**Idea.** One encoder per modality maps into a common space. In a *coordinated* representation the latents stay
separate but are trained to agree; in a *joint* representation they are merged into one vector that the decoders
read. MEIDNet does both: the structure latent and the property latent are aligned by
[contrastive learning](#contrastive), then averaged into the joint latent; the decoders read the joint latent and
the property latent alone.

**When it fits.** You want to translate between modalities (properties → structure for inverse design), retrieve
one modality from another, or search a space that both understand. You have paired examples.

**Strengths.** Translation in both directions, retrieval, and one space to optimise in. Each modality keeps the
encoder that suits its shape.
**Weaknesses.** Needs paired data. The space is only as good as the alignment. Several losses must be balanced.

**Materials example.** MEIDNet: crystal structures and DFT properties of 18,928 cubic perovskites, searched for
compositions with a target band gap and formation enthalpy ([the paper's experiment](../examples/perov5.md)).

*References:* Ngiam *et al.* 2011; Baltrušaitis *et al.* 2019; Babu *et al.* 2026; Moro, Loh *et al.* 2025.

</div>
</div>

<div class="atlas-card" markdown>
<div class="atlas-fig" markdown="0"><svg class="ad" viewBox="0 0 360 132" role="img" aria-label="Cross-attention: tokens of one modality attend to the tokens of the other">
<defs><marker id="ah-cross" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L8,4L0,8z" fill="#8a8a8a"/></marker></defs>
<g class="ma"><rect x="8" y="18" width="18" height="18" rx="3"/><rect x="30" y="18" width="18" height="18" rx="3"/><rect x="52" y="18" width="18" height="18" rx="3"/><rect x="74" y="18" width="18" height="18" rx="3"/></g>
<text x="50" y="52" text-anchor="middle" class="sm">A tokens (atoms)</text>
<g class="mb"><rect x="8" y="94" width="18" height="18" rx="3"/><rect x="30" y="94" width="18" height="18" rx="3"/><rect x="52" y="94" width="18" height="18" rx="3"/><rect x="74" y="94" width="18" height="18" rx="3"/></g>
<text x="50" y="126" text-anchor="middle" class="sm">B tokens (spectrum)</text>
<path class="thin" d="M17,36 L150,58 M39,36 L150,58 M61,36 L150,58 M83,36 L150,58"/>
<path class="thin" d="M17,94 L150,80 M39,94 L150,80 M61,94 L150,80 M83,94 L150,80"/>
<text x="118" y="40" class="sm">queries</text><text x="104" y="104" class="sm">keys, values</text>
<rect class="fz" x="150" y="50" width="92" height="38" rx="6"/><text x="196" y="73" text-anchor="middle">cross-attention</text>
<path class="arr" d="M242,69 L260,69" marker-end="url(#ah-cross)"/>
<g class="fzt"><rect x="262" y="60" width="18" height="18" rx="3"/><rect x="284" y="60" width="18" height="18" rx="3"/><rect x="306" y="60" width="18" height="18" rx="3"/><rect x="328" y="60" width="18" height="18" rx="3"/></g>
<text x="304" y="96" text-anchor="middle" class="sm">fused tokens</text><text x="304" y="109" text-anchor="middle" class="sm">→ prediction</text>
</svg></div>
<div class="atlas-body" markdown>

### Cross-attention and transformer fusion { #cross-attention }

<span class="mstatus no">Not in MEIDNet</span>

**Idea.** Each modality becomes a sequence of tokens (atoms, segments of a spectrum, words). Attention lets every
token of one modality look up the tokens of the other that matter to it, layer after layer.

**When it fits.** The modalities have parts that interact in detail and are not aligned in advance; the dataset is
large.

**Strengths.** Learns which parts relate to which, and handles sequences of different lengths without manual
alignment.
**Weaknesses.** Needs much data and compute; the cost grows with the product of the two sequence lengths; harder
to interpret than a single shared vector.

**Materials example.** Spectrum segments attend to the atoms of the structure, so the model learns which sites shape
which spectral features.

*References:* Tsai *et al.* 2019 (Multimodal Transformer); Lu *et al.* 2019 (ViLBERT).

</div>
</div>

<div class="atlas-card core" markdown>
<div class="atlas-fig" markdown="0"><svg class="ad" viewBox="0 0 360 140" role="img" aria-label="Contrastive learning: in a table of similarities between the structures and the properties of a batch, the diagonal pairs are pulled together and the rest pushed apart">
<text x="160" y="12" text-anchor="middle" class="sm">properties of the batch</text>
<text x="100" y="76" text-anchor="end" class="sm">structures</text>
<g class="cell">
<rect x="110" y="20" width="20" height="20"/><rect x="130" y="20" width="20" height="20"/><rect x="150" y="20" width="20" height="20"/><rect x="170" y="20" width="20" height="20"/><rect x="190" y="20" width="20" height="20"/>
<rect x="110" y="40" width="20" height="20"/><rect x="130" y="40" width="20" height="20"/><rect x="150" y="40" width="20" height="20"/><rect x="170" y="40" width="20" height="20"/><rect x="190" y="40" width="20" height="20"/>
<rect x="110" y="60" width="20" height="20"/><rect x="130" y="60" width="20" height="20"/><rect x="150" y="60" width="20" height="20"/><rect x="170" y="60" width="20" height="20"/><rect x="190" y="60" width="20" height="20"/>
<rect x="110" y="80" width="20" height="20"/><rect x="130" y="80" width="20" height="20"/><rect x="150" y="80" width="20" height="20"/><rect x="170" y="80" width="20" height="20"/><rect x="190" y="80" width="20" height="20"/>
<rect x="110" y="100" width="20" height="20"/><rect x="130" y="100" width="20" height="20"/><rect x="150" y="100" width="20" height="20"/><rect x="170" y="100" width="20" height="20"/><rect x="190" y="100" width="20" height="20"/>
</g>
<g class="diag"><rect x="110" y="20" width="20" height="20"/><rect x="130" y="40" width="20" height="20"/><rect x="150" y="60" width="20" height="20"/><rect x="170" y="80" width="20" height="20"/><rect x="190" y="100" width="20" height="20"/></g>
<rect class="diag" x="226" y="44" width="12" height="12"/><text x="244" y="54" class="sm">true pairs:</text><text x="244" y="67" class="sm">pulled together</text>
<rect class="cellk" x="226" y="84" width="12" height="12"/><text x="244" y="94" class="sm">other pairs:</text><text x="244" y="107" class="sm">pushed apart</text>
</svg></div>
<div class="atlas-body" markdown>

### Contrastive learning { #contrastive }

<span class="mstatus core">Used by MEIDNet</span> <span class="mstatus sup">Supported</span>

**Idea.** A training objective rather than a wiring. In a batch of paired examples, each example's two embeddings
must be more similar to each other than to any other example's. It is how the latents of a
[shared space](#shared-latent) are coordinated.

**When it fits.** You have pairs (a structure and its properties, a pattern and its structure) and want a space in
which nearest neighbours are meaningful across modalities.

**Strengths.** Learns from the pairing alone; gives retrieval for free; scales to large datasets.
**Weaknesses.** Needs batches with enough other examples; sensitive to the temperature; two genuinely similar
materials in one batch are still pushed apart.

**In MEIDNet.** Symmetric InfoNCE with temperature 0.01 and weight 5, switched on gradually over the warm-up
(the paper's curriculum). [The formula and a playground](index.md#contrastive-learning).

*References:* van den Oord *et al.* 2018 (InfoNCE); Radford *et al.* 2021 (CLIP).

</div>
</div>

</div>

## Side by side { #side-by-side }

| | early fusion | late fusion | shared latent | cross-attention | contrastive (objective) |
|---|---|---|---|---|---|
| where the modalities meet | input features | predictions | a common latent space | inside the network, token by token | the latent space, through the loss |
| every modality needed for every sample | yes | no | paired examples for training | usually | paired examples |
| learns interactions between modalities | yes | no | yes | yes, in detail | for whole samples |
| translates one modality into another | no | no | yes | with a decoder | retrieval |
| data needed | small to medium | small per model | medium | large | medium to large |
| in MEIDNet | no | no | **yes, the core** | no | **yes** |

**Beyond these five.** Conditional generative models such as diffusion (MatterGen) or variational autoencoders
(CDVAE) also translate from properties to structures, and they generate free atomic arrangements, which MEIDNet does
not. MEIDNet instead decodes compositions onto a prototype family and checks them against chemical rules.

## Which architecture should I use? { #advisor }

Tick the data you have and choose what you want to do. The recommendation says why, what it costs and whether
MEIDNet can do it today.

<div class="advisor" id="arch-advisor" aria-live="polite"></div>

<noscript>The advisor needs JavaScript. In short: structures with scalar properties, for design or retrieval →
shared latent space with contrastive alignment (MEIDNet). Formula only → a composition model such as Roost.
A pattern or spectrum to identify a phase → a 1D convolutional classifier. Modalities that are often missing →
late fusion. Long sequences that interact in detail → cross-attention.</noscript>

## A note on words { #terminology }

**"Early fusion" in the MEIDNet paper** names the model in which the structure latent and the property latent are
averaged into one joint latent: `z_joint = (z_c + z_p) / 2` in `meidnet/model.py`. In the survey literature, early
fusion usually means joining raw features at the input, as in the [first card](#early-fusion); averaging two learned
latents, each from its own encoder, is *intermediate* or *model-level* fusion, the [shared-latent card](#shared-latent).
Both names describe the same code. The checkpoints shipped here are the paper's early-fusion models, and the code
implements only this fusion: there is no late-fusion option in MEIDNet.

**"Curriculum"** in the paper is the contrastive warm-up: the alignment weight grows from zero to its full value
over `training.contrastive_warmup_epochs`, so that the decoders learn first.

## References { #references }

- C. G. M. Snoek, M. Worring, A. W. M. Smeulders, "Early versus late fusion in semantic video analysis",
  *ACM Multimedia* (2005). [doi:10.1145/1101149.1101236](https://doi.org/10.1145/1101149.1101236)
- T. Baltrušaitis, C. Ahuja, L.-P. Morency, "Multimodal machine learning: a survey and taxonomy",
  *IEEE TPAMI* **41**, 423–443 (2019). [doi:10.1109/TPAMI.2018.2798607](https://doi.org/10.1109/TPAMI.2018.2798607)
- J. Ngiam *et al.*, "Multimodal deep learning", *ICML* (2011).
- Y.-H. H. Tsai *et al.*, "Multimodal Transformer for unaligned multimodal language sequences", *ACL* (2019).
  [doi:10.18653/v1/P19-1656](https://doi.org/10.18653/v1/P19-1656)
- J. Lu, D. Batra, D. Parikh, S. Lee, "ViLBERT: pretraining task-agnostic visiolinguistic representations for
  vision-and-language tasks", *NeurIPS* (2019). [arXiv:1908.02265](https://arxiv.org/abs/1908.02265)
- A. van den Oord, Y. Li, O. Vinyals, "Representation learning with contrastive predictive coding" (2018).
  [arXiv:1807.03748](https://arxiv.org/abs/1807.03748)
- A. Radford *et al.*, "Learning transferable visual models from natural language supervision", *ICML* (2021).
  [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
- R. E. A. Goodall, A. A. Lee, "Predicting materials properties without crystal structure: deep representation
  learning from stoichiometry" (Roost), *Nat. Commun.* **11**, 6280 (2020). [doi:10.1038/s41467-020-19964-7](https://doi.org/10.1038/s41467-020-19964-7)
- W. B. Park *et al.*, "Classification of crystal structure using a convolutional neural network", *IUCrJ* **4**,
  486–494 (2017). [doi:10.1107/S205225251700714X](https://doi.org/10.1107/S205225251700714X)
- C. Zeni *et al.*, "A generative model for inorganic materials design" (MatterGen), *Nature* **639**, 624–632 (2025).
  [doi:10.1038/s41586-025-08628-5](https://doi.org/10.1038/s41586-025-08628-5)
- T. Xie *et al.*, "Crystal diffusion variational autoencoder for periodic material generation" (CDVAE), *ICLR*
  (2022). [arXiv:2110.06197](https://arxiv.org/abs/2110.06197)
- V. Moro, C. Loh *et al.*, "Multimodal foundation models for material property prediction and discovery",
  *Newton* (2025). [doi:10.1016/j.newton.2025.100016](https://doi.org/10.1016/j.newton.2025.100016)
- A. Babu, R. Almeida Gouvêa, P. Vandergheynst, G.-M. Rignanese, "MEIDNet: Multimodal generative AI framework for
  inverse materials design", *npj Comput. Mater.* (2026). [doi:10.1038/s41524-026-02153-3](https://doi.org/10.1038/s41524-026-02153-3)
