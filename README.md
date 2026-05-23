<p align="center">
  <img src="MEIDNet_logo.png" alt="MEIDNet — Multimodal Equivariant Inverse Design Network" width="540"/>
</p>

<p align="center">
  <em>Property-conditioned constrained inverse design of cubic ABX₃ perovskites</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/PyTorch-2.0%2B-orange?logo=pytorch" alt="PyTorch"/>
  <img src="https://img.shields.io/badge/CUDA-12.x-green?logo=nvidia" alt="CUDA"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License"/>
</p>

---

## Overview

MEIDNet is a generative machine-learning framework for the inverse design of cubic
ABX₃ perovskites with user-specified electronic and thermodynamic properties.  Given
target values for the **direct band-gap** (Eg) and **formation enthalpy** (ΔHf),
MEIDNet searches a shared structure–property latent space and decodes candidate
compositions subject to hard crystallographic and electrostatic constraints.

All accepted candidates are guaranteed to satisfy:

- Cubic Pm-3m symmetry (space group #221) with the ideal five-atom unit cell
- Formal charge neutrality (existential valence)
- Goldschmidt tolerance factor in the family-specific stability window
- Octahedral factor μ = r_B / r_X ∈ [0.414, 0.90]
- B–X bond distance within [0.75, 1.35] × (r_B + r_X)

---

## How It Works

### 1 — Dual-Modality Autoencoder with CLIP-style Alignment

MEIDNet trains two autoencoders simultaneously on a dataset of ~23 k ABX₃
perovskite structures with DFT-computed properties:

```
Crystal modality                     Property modality
────────────────                     ─────────────────
CIF → dense vector                   (ΔH_f, E_g) ──────┐
       │                                                 │
       ▼                                                 ▼
  SE3Encoder ──► z_c ──┐       PropertyEncoder ──► z_p ──┤
       ▲               │ CLIP alignment (InfoNCE)        │
  SE3Decoder ◄── z ◄──┘◄──────────────────────────────┘
  (reconstruct CIF)          PropertyDecoder
                             (reconstruct ΔH_f, E_g)
```

The **SE3Encoder** is built from two EGNN (E(n)-Equivariant Graph Neural
Network) layers that operate on squared inter-atomic distances — making the
crystal embedding invariant to global rotation and translation.  The
**PropertyEncoder** is a two-layer MLP.  Both encoders project into the
same *d*-dimensional latent space (*d* = 128), aligned by a CLIP-style
InfoNCE contrastive loss that pushes structure–property pairs together and
pulls unrelated pairs apart.

The joint training objective is:

```
L = α · L_recon(crystal)   +  β · L_prop(crystal → property)
  + γ · L_recon(prop→crystal)  +  δ · L_prop(prop→property)
  + λ · L_contrastive(z_c, z_p)
```

The contrastive weight λ is linearly warmed up over the first 1 200 training
epochs to allow individual decoders to stabilise before imposing cross-modal
alignment.

---

### 2 — Property-Conditioned Latent Optimisation

At inference time, a target property tuple (E_g*, ΔH_f*) conditions the
initial latent vector:

```
z₀ = PropertyEncoder(ΔH_f*, E_g*) + RFF_offset + ε,   ε ~ N(0, σ²)
```

The **Random Fourier Feature offset** ensures population diversity across
parallel decode attempts.  Starting from z₀, gradient descent minimises a
multi-objective loss:

```
L_opt = λ_bg  · (E_g_pred - E_g*)²
      + λ_ent · L_ent(ΔH_f_pred, ΔH_f*)      (hinge / L1 / L2)
      + λ_geo · L_geometry(decoded coords)
      + λ_hist· L_history_repulsion
```

The history-repulsion term discourages the latent from revisiting regions
that already yielded accepted candidates, promoting chemical diversity across
rounds.

---

### 3 — Decode and Physics Projection

After optimisation, the latent is decoded by the crystal decoder:

1. **Composition sampling** — species logits are converted to probabilities;
   the **A-site is sampled last** to guarantee charge balance:
   ```
   Sample B → Sample X → Compute Q(A) = -(Q(B) + 3·Q(X)) → Sample A from compatible set
   ```

2. **Lattice prediction** — the lattice parameter is predicted analytically
   from ionic radii rather than from the undertrained decoder output:
   ```
   a = 2 · (r_B + r_X),   clamped to [3.0, 8.0] Å
   ```

3. **Physics post-filters** — charge balance, Goldschmidt tolerance,
   octahedral factor, B–X bond distance, and structural uniqueness.

Only structures that pass **all** five filters are written as CIF output.

---

## Installation

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | ≥ 3.9 |
| NVIDIA GPU | ≥ 6 GB VRAM (recommended) |
| CUDA | 12.x (RTX 40/50 series) |

### Step 1 — Install PyTorch with CUDA support

```bash
# CUDA 12.8  (RTX 40/50 series, A100, H100)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# CUDA 11.8  (older Ampere/Volta GPUs)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CPU only  (generation will be significantly slower)
pip install torch torchvision torchaudio
```

### Step 2 — Install all other dependencies

```bash
pip install pymatgen scikit-learn matplotlib pandas numpy
```

### Step 3 — (Optional) Install MACE-MP for stability screening

Required only for `scripts/screen_stability.py`.  Downloads ~500 MB model
weights on first run.

```bash
pip install ase mace-torch
```

### Step 4 — Install MEIDNet as a package (optional)

```bash
pip install -e .
```

---

## Quick Start

### One-command demo

```bash
python demo.py
```

Generates a small set of ABX₃ perovskite candidates for the halide family with
a user-specified band-gap target and validates all outputs against the cubic
Pm-3m crystallographic constraints (stoichiometry, lattice angles, spacegroup,
bond distances). **Runtime: ~60 seconds on GPU.**

Options:
```bash
python demo.py --family oxide              # switch to oxide family
python demo.py --family chalcogenide --n 5 # 5 chalcogenide candidates
python demo.py --help                      # full option list
```

---

## Full Pipeline

### Step 0 — Extract CIF Files (run once before training)

```bash
python tools/extract_cifs.py        # train.csv → cif_files/  (~17k structures)
python tools/extract_cifs.py --all  # also val.csv and test.csv
```

### Step 1 — Train the Model

```bash
python scripts/train.py --epochs 200 --batch 16 --save_every 50
```

| Flag | Default | Description |
|------|---------|-------------|
| `--epochs` | 200 | Total training epochs |
| `--batch` | 16 | Batch size (use 8 if GPU memory < 8 GB) |
| `--lr` | 1e-3 | Adam learning rate |
| `--save_every` | 50 | Checkpoint interval (epochs) |
| `--checkpoint` | `checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth` | Output path |


### Step 2 — Generate Candidates

#### All three families at once

```bash
python scripts/generate_candidates.py
python scripts/generate_candidates.py --checkpoint checkpoints/my_model.pth \
    --out_dir results/run_1 --rounds 20 --pop 48 --steps 800
```

#### Single family (fine-grained control)

```bash
python meidnet/design.py \
    --family            halide \
    --checkpoint        checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth \
    "--bg_targets=1.5,2.5,3.5" \
    "--ent_targets=-0.10,-0.10,-0.10" \
    --num_targets       3 \
    --per_target        4 \
    --batch_attempts    48 \
    --rounds_per_target 20 \
    --steps             800 \
    --output_dir        results/halide \
    --output_prefix     halide \
    --dedup_abx
```

### Step 3 — Verify Generated Structures

```bash
python tools/verify_structures.py --dir results/halide
python tools/verify_structures.py --dir results/oxide
python tools/verify_structures.py --dir results/chalcogenide
```

### Step 4 — Stability Screening and SUN Rate

```bash
python scripts/screen_stability.py \
    --results_dir results/ \
    --train_csv   train.csv \
    --threshold   0.10 \
    --device      cuda
```

Requires `ase` and `mace-torch`.  Downloads ~500 MB MACE-MP-0 weights on
first use.  Runtime: ~2–3 minutes for 27 structures on an RTX GPU.

---

## Repository Structure

```
MEIDNet/
│
├── README.md                       This file
├── requirements.txt                Python dependencies
├── setup.py                        Package installation (pip install -e .)
├── demo.py                         One-command end-to-end demonstration
├── MEIDNet_logo.png                Project logo
│
├── meidnet/                        Core Python package
│   ├── __init__.py
│   ├── model.py                    Dual-modality autoencoder architecture
│   │   ├── EGNNLayer               SE(3)-equivariant message passing layer
│   │   ├── SE3Encoder              Crystal graph encoder (2 EGNN layers)
│   │   ├── SE3Decoder              Crystal graph decoder
│   │   ├── PropertyEncoder         Scalar property encoder (MLP)
│   │   ├── PropertyDecoder         Scalar property decoder (MLP)
│   │   ├── DualAutoencoderModel    Joint model with contrastive alignment
│   │   └── TripleModalityDataset   Dataset: CIF + ΔH_f + E_g
│   │
│   └── design.py                   Inverse design and candidate generation
│       ├── Latent optimisation     Gradient descent in latent space
│       ├── Decode & projection     Crystal decoder + Pm-3m template snap
│       └── Physics post-filters    Charge, Goldschmidt, μ, B-X distance
│
├── scripts/                        Pipeline scripts
│   ├── train.py                    Training runner
│   ├── generate_candidates.py      Multi-family generation (all families)
│   ├── generate_all.py             Full batch generation wrapper
│   └── screen_stability.py         MACE-MP-0 stability + SUN rate
│
├── tools/                          Utilities
│   ├── extract_cifs.py             Extract CIFs from dataset CSVs
│   └── verify_structures.py        Crystallographic structure validator
│
├── checkpoints/                    Pretrained model checkpoints
│   ├── dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth  [BEST]
│   ├── dual_autoencoder_clip_earlyfusion_propertyaware.pth
│   └── dual_autoencoder_clip_earlyfusion.pth
│
└── results/                        Generation outputs (written by pipeline scripts)
    ├── halide/                     Halide perovskite CIFs
    ├── oxide/                      Oxide perovskite CIFs
    ├── chalcogenide/               Chalcogenide perovskite CIFs
    └── sun_rate.csv                MACE-MP-0 screening results (S/U/N labels)
```

---

## Pretrained Checkpoints

| File | Status | Notes |
|------|--------|-------|
| `dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth` | **Recommended** | Highest weight norm (~40), best property alignment |
| `dual_autoencoder_clip_earlyfusion_propertyaware.pth` | Earlier | Intermediate training stage |
| `dual_autoencoder_clip_earlyfusion.pth` | Earliest | Baseline, coarser property alignment |

Place checkpoints in `checkpoints/` or specify `--checkpoint path/to/file.pth`.

## Generation CLI Reference

```
python meidnet/design.py --help
```

| Flag | Default | Description |
|------|---------|-------------|
| `--family` | `oxide` | Anion family: `oxide` \| `halide` \| `chalcogenide` \| `nitride` |
| `--checkpoint` | *(required)* | Path to `.pth` checkpoint |
| `--bg_targets` | `2.0` | Comma-separated band-gap targets (eV) |
| `--ent_targets` | `-0.20` | Comma-separated enthalpy targets (eV/atom) |
| `--num_targets` | `1` | Number of property targets |
| `--per_target` | `4` | Candidates to accept per target |
| `--batch_attempts` | `48` | Decode attempts per round |
| `--rounds_per_target` | `20` | Optimisation rounds |
| `--steps` | `800` | Gradient steps per round |
| `--output_dir` | `results_targetled` | CIF output directory |
| `--dedup_abx` | off | Enable formula deduplication |
| `--min_cosine_sep` | `0.985` | Latent cosine deduplication threshold |
| `--x_prior_strength` | `0.0` | Anion prior weight (0 = disabled) |
| `--decode_temp` | `1.0` | Species sampling temperature |
| `--anti_repeat_alpha` | `0.5` | Anti-repeat downweighting exponent |
| `--steps` | `800` | Gradient steps per round |


## Citation

If you use MEIDNet in your research, please cite:

```bibtex
@software{meidnet2025,
  title   = {MEIDNet: Multimodal generative AI framework for inverse materials design},
  author  = {Anand Babu, Rogério Almeida Gouvêa, Pierre Vandergheynst, Gian-Marco Rignanese},
  year    = {2026},
  url     = {https://arxiv.org/abs/2601.22009},
}
```

---
