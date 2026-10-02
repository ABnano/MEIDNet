"""
Helpers shared by the v1-vs-v2 regression tests: run both implementations on the
same small generation problem and return comparable per-candidate records.
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CKPT = os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")

CASES = {
    "halide": dict(variant="halide", targets=[(1.5, -0.10), (2.5, -0.10)]),
    "oxide": dict(variant="oxide", targets=[(2.0, -0.20)]),
}
SMALL = dict(per_target=3, population=16, rounds=3, steps=60, seed=937)


def run_v1(case: str, out_dir: str, hashseed: str = "0") -> list[dict]:
    c = CASES[case]
    bg = ",".join(str(t[0]) for t in c["targets"])
    ent = ",".join(str(t[1]) for t in c["targets"])
    cmd = [sys.executable, os.path.join(ROOT, "tests", "legacy_v1", "run_v1_ordered.py"),
           "--checkpoint", CKPT, "--family", c["variant"], f"--bg_targets={bg}", f"--ent_targets={ent}",
           "--num_targets", str(len(c["targets"])), "--per_target", str(SMALL["per_target"]),
           "--batch_attempts", str(SMALL["population"]), "--rounds_per_target", str(SMALL["rounds"]),
           "--steps", str(SMALL["steps"]), "--output_dir", out_dir, "--output_prefix", case,
           "--plot_dir", os.path.join(out_dir, "plots"), "--dedup_abx", "--min_cosine_sep", "0.985",
           "--seed", str(SMALL["seed"])]
    env = dict(os.environ, PYTHONHASHSEED=hashseed, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", CUDA_VISIBLE_DEVICES="")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    rows = list(csv.DictReader(open(os.path.join(out_dir, "run_summary.csv"))))
    out = []
    for row in rows:
        with open(row["outfile"], "rb") as f:
            cif = f.read()
        out.append({"file": os.path.basename(row["outfile"]), "A": row["A"], "B": row["B"], "X": row["X"],
                    "dir_gap": float(row["pred_bg"]), "heat_all": float(row["pred_ent"]),
                    "a0": float(row["a0"]), "t": float(row["t"]), "mu": float(row["mu"]), "cif": cif})
    return out


def v2_config(case: str) -> dict:
    c = CASES[case]
    return {
        "family": "perovskite_abx3", "variant": c["variant"],
        "objectives": [
            {"property": "dir_gap", "loss": "l2", "weight": 10000.0, "select_weight": 1.0},
            {"property": "heat_all", "loss": "l1", "weight": 6000.0, "select_weight": 0.4},
        ],
        "targets": [{"dir_gap": bg, "heat_all": ent} for bg, ent in c["targets"]],
        "per_target": SMALL["per_target"], "population": SMALL["population"], "rounds": SMALL["rounds"],
        "steps": SMALL["steps"], "seed": SMALL["seed"], "output_prefix": case,
        "dedup_formula": True, "min_cosine_sep": 0.985,
        # v1 design.py CLI defaults (the published run used these)
        "learning_rate": 1.2e-3, "anchor_weight": 12.0, "decode_temperature": 1.25, "decode_topk": 12,
        "decode_tries": 12, "anti_repeat_alpha": 0.6,
    }


def run_v2(case: str, out_dir: str) -> list[dict]:
    """Run MEIDNet 2 in a subprocess (same thread settings as v1)."""
    cfg_path = os.path.join(out_dir, "gen.json")
    os.makedirs(out_dir, exist_ok=True)
    with open(cfg_path, "w") as f:
        json.dump(v2_config(case), f)
    code = (
        "import json,sys,torch; torch.set_num_threads(1); sys.path.insert(0, %r)\n"
        "from meidnet.config import GenerationSection\n"
        "from meidnet.checkpoint import load_checkpoint\n"
        "from meidnet.family import load_family\n"
        "from meidnet.generate import Designer\n"
        "g = GenerationSection(**json.load(open(%r)))\n"
        "lm = load_checkpoint(%r)\n"
        "fam = load_family(g.family, variant=g.variant)\n"
        "Designer(lm, fam, g, log=lambda *a: None).run(%r)\n"
    ) % (ROOT, cfg_path, CKPT, out_dir)
    env = dict(os.environ, PYTHONHASHSEED="123", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", CUDA_VISIBLE_DEVICES="")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-3000:])
    out = []
    for row in csv.DictReader(open(os.path.join(out_dir, "candidates.csv"), encoding="utf-8")):
        with open(os.path.join(out_dir, row["file"]), "rb") as f:
            cif = f.read()
        out.append({"file": os.path.basename(row["file"]), "A": row["site_A"], "B": row["site_B"], "X": row["site_X"],
                    "dir_gap": float(row["pred_dir_gap"]), "heat_all": float(row["pred_heat_all"]),
                    "a0": float(row["lattice_a"]), "t": float(row["tolerance_factor"]),
                    "mu": float(row["octahedral_factor"]), "cif": cif})
    return out
