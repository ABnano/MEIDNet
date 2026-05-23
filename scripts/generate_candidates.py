#!/usr/bin/env python3
"""
scripts/generate_candidates.py
===============================
Multi-family ABX3 candidate generation using the MEIDNet pretrained checkpoint.

Sequentially generates property-conditioned cubic perovskite candidates for
halide, oxide, and chalcogenide families, then invokes the structural verifier
to confirm all outputs satisfy Pm-3m ABX3 constraints.

Property targets are specified as comma-separated lists aligned positionally:
    --bg_targets  1.5,2.5,3.5   (band-gap targets in eV)
    --ent_targets -0.10,-0.10,-0.10  (enthalpy targets in eV/atom)

Note: pass negative values with the = syntax to avoid argparse ambiguity:
    "--ent_targets=-0.10,-0.10,-0.10"

Usage
-----
    # Default: 3 targets per family, 4 candidates each, 20 rounds
    python scripts/generate_candidates.py

    # Custom checkpoint and output directory
    python scripts/generate_candidates.py \\
        --checkpoint checkpoints/my_model.pth \\
        --out_dir    results/my_run \\
        --rounds     30 --pop 64 --steps 1000
"""
import os, sys, subprocess, argparse

PYTHON = sys.executable
GEN  = os.path.join(os.path.dirname(__file__), "..", "meidnet", "design.py")
VER  = os.path.join(os.path.dirname(__file__), "..", "tools",   "verify_structures.py")

RUNS = [
    # (family, bg_targets, ent_targets, num_targets, per_target, label)
    ("halide",       "1.5,2.5,3.5", "-0.10,-0.10,-0.10", "3", "4", "halide"),
    ("oxide",        "2.0,3.5",     "-0.20,-0.20",        "2", "4", "oxide"),
    ("chalcogenide", "1.0,2.0",     "-0.15,-0.15",        "2", "3", "chalcogenide"),
]


def run_gen(family, bg_targets, ent_targets, num_targets, per_target,
            label, checkpoint, out_dir, rounds, pop, steps):
    sub = os.path.join(out_dir, label)
    os.makedirs(sub, exist_ok=True)
    cmd = [
        PYTHON, "-u", GEN,
        "--family",            family,
        "--checkpoint",        checkpoint,
        f"--bg_targets={bg_targets}",
        f"--ent_targets={ent_targets}",
        "--num_targets",       num_targets,
        "--per_target",        per_target,
        "--batch_attempts",    str(pop),
        "--rounds_per_target", str(rounds),
        "--steps",             str(steps),
        "--output_dir",        sub,
        "--output_prefix",     label,
        "--dedup_abx",
        "--min_cosine_sep",    "0.985",
    ]
    print(f"\n{'='*60}")
    print(f"Generating: family={family}  targets=[{bg_targets}] eV")
    print(f"{'='*60}", flush=True)
    subprocess.run(cmd, text=True)
    return sub


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint",
                   default="dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")
    p.add_argument("--out_dir",  default="results_test")
    p.add_argument("--rounds",   type=int, default=20)
    p.add_argument("--pop",      type=int, default=48)
    p.add_argument("--steps",    type=int, default=800)
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    sub_dirs = []

    for family, bg_targets, ent_targets, num_targets, per_target, label in RUNS:
        sub = run_gen(family, bg_targets, ent_targets, num_targets, per_target,
                      label, args.checkpoint, args.out_dir,
                      args.rounds, args.pop, args.steps)
        sub_dirs.append(sub)

    # Verify all generated CIFs
    print(f"\n{'='*60}")
    print("VERIFICATION: checking all generated CIFs")
    print(f"{'='*60}", flush=True)
    for sub in sub_dirs:
        if any(f.endswith(".cif") for f in os.listdir(sub)):
            subprocess.run([PYTHON, VER, "--dir", sub], text=True)
        else:
            print(f"  [no CIFs found in {sub}]")


if __name__ == "__main__":
    main()
