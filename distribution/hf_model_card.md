---
license: mit
language:
  - en
library_name: meidnet
pipeline_tag: other
tags:
  - materials-science
  - inverse-design
  - crystal-structures
  - perovskites
  - multimodal
  - generative
  - pytorch
  - chemistry
datasets:
  - perov-5
metrics:
  - mae
model-index:
  - name: MEIDNet Perov-5 (early fusion + curriculum, 2000 epochs)
    results:
      - task:
          type: other
          name: structure-property alignment and inverse design
        dataset:
          type: perov-5
          name: Perov-5 (CDVAE split)
        metrics:
          - type: cosine_similarity
            name: cosine similarity of matched structure / property latents
            value: 0.97
          - type: l2_distance
            name: L2 distance of matched latents
            value: 0.24
          - type: sun_rate
            name: stable-unique-novel rate of generated candidates (19 of 140)
            value: 0.136
        source:
          name: npj Computational Materials (2026)
          url: https://doi.org/10.1038/s41524-026-02153-3
---

<p align="center"><a href="https://babu09-meidnet.hf.space/"><img src="https://babu09-meidnet.hf.space/docs/assets/meidnet_prism_logo.png" width="640" alt="MEIDNet Prism"></a></p>

# MEIDNet — pretrained Perov-5 models

**MEIDNet** (Multimodal Equivariant Inverse Design Network) designs crystalline materials from the
properties you want. One shared latent space holds crystal structures and their properties; a prototype
*material family* with chemistry rules defines what may be generated; a latent search proposes candidates
that pass every rule and sit closest to the target.

| | |
|---|---|
| **Try it now** | [MEIDNet Prism — live Studio](https://babu09-meidnet.hf.space/studio/) (nothing to install; bring your own table and train in the browser) |
| **Paper** | A. Babu, R. A. Gouvêa, P. Vandergheynst, G.-M. Rignanese, *npj Computational Materials* (2026) — [doi:10.1038/s41524-026-02153-3](https://doi.org/10.1038/s41524-026-02153-3) · [arXiv:2601.22009](https://arxiv.org/abs/2601.22009) |
| **Code** | [github.com/ABnano/MEIDNet](https://github.com/ABnano/MEIDNet) (MIT) · [documentation](https://babu09-meidnet.hf.space/docs/) · [Colab notebooks](https://babu09-meidnet.hf.space/docs/start/colab.html) |
| **Benchmarks** | [MEIDNet Benchmarks](https://babu09-meidnet.hf.space/docs/benchmarks/index.html) — per-dataset results with an evidence ladder; [contribute yours](https://babu09-meidnet.hf.space/docs/community/contribute.html) |

## Files

| file | what it is |
|---|---|
| `dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth` | **the production model of the paper**: early fusion, property-aware decoding, 2000 epochs with a contrastive warm-up over the first 1200. Use this one. |
| `dual_autoencoder_clip_earlyfusion_propertyaware.pth` | the same architecture, shorter training |
| `dual_autoencoder_clip_earlyfusion.pth` | the earliest ablation (no property-aware decoding) |
| `meidnet.yaml` | the configuration that reproduces the Perov-5 experiment with the MEIDNet 2 package |
| `perovskite_abx3.yaml` | the cubic ABX₃ family file: prototype sites, allowed elements per site, oxidation states, rules |

Each checkpoint is 2.8 MB (about 0.7 M parameters) and runs on a laptop CPU.

## What the model does

- **Inputs:** a crystal structure (CIF, up to 20 atoms per cell) and/or scalar properties — here the
  direct band gap (`dir_gap`, eV) and the formation enthalpy (`heat_all`, eV/atom).
- **Model:** an equivariant graph encoder for the structure and an MLP encoder for the properties are
  aligned contrastively (CLIP-style) into one 128-dimensional latent space; the joint latent is the
  average of the two (early fusion); decoders reconstruct the crystal and the properties.
- **Inverse design:** start at the latent of the target properties, optimise a population of latents,
  decode each into one element per prototype site, keep the candidates that pass every chemistry rule,
  rank by closeness to the target. Candidates must be confirmed by DFT or experiment; the package ships
  a MACE-based stability / uniqueness / novelty screen.

**Training data:** Perov-5 (CDVAE split; 11,356 training structures). Element coverage follows that data:
oxides, nitrides, fluorides, sulfides and their mixtures. Predictions for elements absent from it (for
example Cl, Br, I and most lanthanides) are extrapolations — the Studio and the reports say so.

## Use it

```bash
pip install git+https://github.com/ABnano/MEIDNet.git
meidnet demo                         # downloads this checkpoint and designs three candidates
```

```python
from huggingface_hub import hf_hub_download
from meidnet.checkpoint import load_checkpoint, describe

path = hf_hub_download("Babu09/MEIDNet", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")
lm = load_checkpoint(path)
print(describe(lm))                  # properties, units, training ranges
```

With a configuration file (`meidnet.yaml` from this repository, `model_path` pointing at the checkpoint):

```bash
meidnet generate meidnet.yaml --quick      # candidates + a plain-language HTML report
meidnet studio meidnet.yaml                # the same workflow as a live web page
```

## Results reported in the paper (Perov-5)

| quantity | value |
|---|---|
| cosine similarity between the structure and property latents of the same material | ≈ 0.97 |
| L2 distance between those latents | ≈ 0.24 |
| inverse-design campaign: candidates generated → stable, unique and novel | 140 → 19 (13.6 %) |

These numbers are quoted from the paper; the benchmark pages mark which rows have been re-run from the
public code.

## Citation

```bibtex
@article{meidnet2026,
  title   = {MEIDNet: Multimodal generative AI framework for inverse materials design},
  author  = {Anand Babu and Rog{\'e}rio Almeida Gouv{\^e}a and Pierre Vandergheynst and Gian-Marco Rignanese},
  journal = {npj Computational Materials},
  year    = {2026},
  doi     = {10.1038/s41524-026-02153-3}
}
```

Software: Anand Babu, *MEIDNet* (MIT), https://github.com/ABnano/MEIDNet.
