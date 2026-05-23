#!/usr/bin/env python3
"""
scripts/generate_all.py
========================
Full multi-family inverse-design run across all supported ABX3 perovskite
families (oxide, halide, chalcogenide, nitride).

Internally calls meidnet/design.py for each family with the specified property
targets and consolidates outputs into a common directory.

Usage
-----
    python scripts/generate_all.py
    python scripts/generate_all.py --checkpoint checkpoints/my_model.pth
    python scripts/generate_all.py --out_dir results/campaign_1
"""
import os, sys, subprocess, argparse

PYTHON = sys.executable
SCRIPT = os.path.join(os.path.dirname(__file__), "..", "meidnet", "design.py")

RUNS = [
    # (family, bg_targets, ent_targets, per_target, label)
    ("halide",       "1.5,2.5,3.5", "-0.10,-0.10,-0.10", 5, "halide"),
    ("oxide",        "2.0,3.0,4.0", "-0.20,-0.20,-0.20", 5, "oxide"),
    ("chalcogenide", "1.0,1.8,2.5", "-0.15,-0.15,-0.15", 5, "chalcogenide"),
]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint",
                   default="dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")
    p.add_argument("--out_dir",   default="results_inverse_design")
    p.add_argument("--rounds",    type=int, default=30)
    p.add_argument("--pop",       type=int, default=64)
    p.add_argument("--steps",     type=int, default=1000)
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    for family, bg_targets, ent_targets, per_target, label in RUNS:
        out_sub = os.path.join(args.out_dir, label)
        os.makedirs(out_sub, exist_ok=True)
        cmd = [
            PYTHON, "-u", SCRIPT,
            "--family",         family,
            "--checkpoint",     args.checkpoint,
            f"--bg_targets={bg_targets}",
            f"--ent_targets={ent_targets}",
            "--num_targets",    "3",
            "--per_target",     str(per_target),
            "--batch_attempts", str(args.pop),
            "--rounds_per_target", str(args.rounds),
            "--steps",          str(args.steps),
            "--output_dir",     out_sub,
            "--output_prefix",  label,
            "--dedup_abx",
            "--min_cosine_sep", "0.985",
        ]
        print(f"\n{'='*60}")
        print(f"GENERATING: family={family}, targets=[{bg_targets}] eV")
        print(f"{'='*60}")
        sys.stdout.flush()
        result = subprocess.run(cmd, text=True)
        if result.returncode != 0:
            print(f"[WARN] generation for {family} exited with code {result.returncode}")

    print("\n\nAll generation runs complete.")
    print(f"CIF files are in subdirectories under: {args.out_dir}")

if __name__ == "__main__":
    main()
