#!/usr/bin/env python3
"""
demo.py  -  MEIDNet one-command demonstration
==============================================
Generates a small set of property-conditioned cubic ABX3 perovskite candidates
using the pretrained MEIDNet checkpoint, validates them against crystallographic
constraints, and prints both the live results and the pre-computed full-pipeline
SUN rate from results/sun_rate.csv.

Runtime: ~60 seconds on GPU.

Usage
-----
    python demo.py                              # halide, 3 candidates (default)
    python demo.py --family oxide               # oxide family
    python demo.py --family chalcogenide        # chalcogenide family
    python demo.py --n 5                        # generate 5 candidates
    python demo.py --checkpoint path/to/ckpt.pth
    python demo.py --out_dir my_demo_results

The pretrained checkpoint must be present.  All three shipped checkpoints are
in the checkpoints/ directory (see README).
"""
import os, sys, subprocess, argparse, csv

REPO_ROOT   = os.path.dirname(os.path.abspath(__file__))
PYTHON      = sys.executable
DESIGN      = os.path.join(REPO_ROOT, "meidnet",  "design.py")
VERIFY      = os.path.join(REPO_ROOT, "tools",    "verify_structures.py")
SUN_CSV     = os.path.join(REPO_ROOT, "results",  "sun_rate.csv")

DEFAULT_CKP = os.path.join(REPO_ROOT, "checkpoints",
                           "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")

# Band-gap and enthalpy targets per anion family
FAMILY_TARGETS = {
    "halide":       ("2.0", "-0.10"),
    "oxide":        ("2.5", "-0.20"),
    "chalcogenide": ("1.5", "-0.15"),
    "nitride":      ("2.0", "-0.15"),
}


# ── Formatting helpers ────────────────────────────────────────────────────────

def sep(char="=", n=72): print(char * n)


# ── Core pipeline steps ───────────────────────────────────────────────────────

def run_generation(family, checkpoint, out_dir, n_candidates, rounds, steps):
    bg, ent = FAMILY_TARGETS.get(family, ("2.0", "-0.10"))
    sub = os.path.join(out_dir, family)
    os.makedirs(sub, exist_ok=True)
    cmd = [
        PYTHON, "-u", DESIGN,
        "--family",            family,
        "--checkpoint",        checkpoint,
        f"--bg_targets={bg}",
        f"--ent_targets={ent}",
        "--num_targets",       "1",
        "--per_target",        str(n_candidates),
        "--batch_attempts",    "24",
        "--rounds_per_target", str(rounds),
        "--steps",             str(steps),
        "--output_dir",        sub,
        "--output_prefix",     family,
        "--dedup_abx",
        "--min_cosine_sep",    "0.98",
    ]
    print(f"  Target band-gap  : ~{bg} eV")
    print(f"  Target enthalpy  : ~{ent} eV/atom")
    print(f"  Optimisation     : {rounds} rounds x {steps} gradient steps")
    print()
    subprocess.run(cmd, text=True)
    cifs = sorted(f for f in os.listdir(sub) if f.endswith(".cif"))
    return sub, cifs


def run_verify(sub_dir):
    result = subprocess.run(
        [PYTHON, VERIFY, "--dir", sub_dir],
        text=True, capture_output=True,
    )
    print(result.stdout)


def show_candidate_table(sub_dir, cifs):
    try:
        from pymatgen.core import Structure
    except ImportError:
        print("  (pymatgen unavailable — skipping structure table)")
        return
    sep("-")
    print(f"  {'File':<38} {'Formula':<14} {'a (A)':>7}  {'b (A)':>7}  {'c (A)':>7}")
    sep("-")
    for fname in cifs:
        try:
            s = Structure.from_file(os.path.join(sub_dir, fname))
            formula = s.composition.reduced_formula
            a, b, c = s.lattice.abc
            print(f"  {fname:<38} {formula:<14} {a:7.3f}  {b:7.3f}  {c:7.3f}")
        except Exception as e:
            print(f"  {fname:<38}  [parse error: {e}]")
    sep("-")


def show_precomputed_sun():
    if not os.path.exists(SUN_CSV):
        return
    rows = []
    with open(SUN_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    if not rows:
        return

    valid  = [r for r in rows if r["artefact"] == "False"]
    n      = len(valid)
    stable = sum(1 for r in valid if r["stable"] == "True")
    unique = sum(1 for r in valid if r["unique"] == "True")
    novel  = sum(1 for r in valid if r["novel"]  == "True")
    sun    = sum(1 for r in valid
                 if r["stable"] == "True" and r["unique"] == "True"
                 and r["novel"] == "True")

    print()
    sep()
    print("  Pre-computed Full-Pipeline SUN Rate  (results/sun_rate.csv)")
    print("  27 CIFs | halide + oxide + chalcogenide | MACE-MP-0 (medium)")
    sep()
    print(f"  {'File':<36} {'Formula':<12} {'dHf (eV/at)':>11}  S  U  N")
    sep("-")
    for r in rows:
        art    = " [ARTEFACT]" if r["artefact"] == "True" else ""
        s_flag = "!" if r["artefact"] == "True" else ("Y" if r["stable"] == "True" else "N")
        u_flag = "Y" if r["unique"] == "True" else "N"
        n_flag = "Y" if r["novel"]  == "True" else "N"
        dhf    = float(r["dHf"])
        dhf_str = f"{dhf:.3f}" if abs(dhf) < 20 else f"{dhf:.1f}"
        print(f"  {r['file']:<36} {r['formula']:<12} {dhf_str:>11}  {s_flag}  {u_flag}  {n_flag}{art}")
    sep()
    print(f"  Structures (total / valid)          : {len(rows)} / {n}")
    print(f"  Stable  (S, DeltaH_f <= 0.10 eV/at): {stable}/{n} = {100*stable/n:.1f}%")
    print(f"  Unique  (U, StructureMatcher)       : {unique}/{n} = {100*unique/n:.1f}%")
    print(f"  Novel   (N, not in training set)    : {novel}/{n} = {100*novel/n:.1f}%")
    print(f"  SU  rate                            : {unique}/{n} = {100*unique/n:.1f}%")
    print(f"  SUN rate                            : {sun}/{n} = {100*sun/n:.1f}%")
    sep()
    print("  S — thermodynamically stable (MACE-MP-0 DFT-surrogate)")
    print("  U — structurally unique (no structural duplicate in candidate set)")
    print("  N — novel composition (reduced formula not in training set)")
    sep()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="MEIDNet demo: generate and verify cubic ABX3 perovskites"
    )
    p.add_argument("--checkpoint", default=DEFAULT_CKP,
                   help="Path to pretrained .pth checkpoint")
    p.add_argument("--family", default="halide",
                   choices=["halide", "oxide", "chalcogenide", "nitride"],
                   help="Anion family to generate (default: halide)")
    p.add_argument("--n", type=int, default=3,
                   help="Number of candidates to generate (default: 3)")
    p.add_argument("--rounds", type=int, default=5,
                   help="Latent optimisation rounds per target (default: 5)")
    p.add_argument("--steps", type=int, default=300,
                   help="Gradient steps per round (default: 300)")
    p.add_argument("--out_dir", default="results_demo",
                   help="Output directory (default: results_demo/)")
    args = p.parse_args()

    sep()
    print("  MEIDNet  —  Multimodal Equivariant Inverse Design Network")
    print("  Property-conditioned ABX3 Perovskite Generation Demo")
    sep()
    print(f"  Checkpoint : {os.path.basename(args.checkpoint)}")
    print(f"  Family     : {args.family}")
    print(f"  Candidates : {args.n}")
    print(f"  Output     : {args.out_dir}/")
    sep()

    # Checkpoint sanity check
    if not os.path.exists(args.checkpoint):
        print(f"\n  ERROR: checkpoint not found at: {args.checkpoint}")
        ckpt_dir = os.path.join(REPO_ROOT, "checkpoints")
        if os.path.isdir(ckpt_dir):
            avail = [f for f in os.listdir(ckpt_dir) if f.endswith(".pth")]
            if avail:
                print("  Available checkpoints:")
                for f in avail:
                    sz = os.path.getsize(os.path.join(ckpt_dir, f)) / 1e6
                    print(f"    checkpoints/{f}  ({sz:.1f} MB)")
        print("\n  Run:  python tools/extract_cifs.py  then  python scripts/train.py")
        sys.exit(1)

    # Step 1 — generation
    sep("-")
    print(f"[1/3]  Generating {args.n} {args.family} candidate(s) ...")
    sep("-")
    sub_dir, cifs = run_generation(
        args.family, args.checkpoint, args.out_dir,
        args.n, args.rounds, args.steps,
    )

    if not cifs:
        print("\n  No candidates accepted in this short run.")
        print("  Increase --rounds (try 15) or --n for more search budget.")
        show_precomputed_sun()
        return

    # Step 2 — structure table
    print(f"\n[2/3]  Accepted {len(cifs)} candidate(s) -> {sub_dir}/")
    show_candidate_table(sub_dir, cifs)

    # Step 3 — crystallographic verification
    print(f"\n[3/3]  Verifying cubic Pm-3m ABX3 constraints ...")
    run_verify(sub_dir)

    # Pre-computed SUN rate summary
    show_precomputed_sun()

    print(f"  Generated CIFs  : {sub_dir}/")
    print("  Stability screen: python scripts/screen_stability.py --results_dir results/")
    print()


if __name__ == "__main__":
    main()
