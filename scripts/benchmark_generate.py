"""
Inverse-design candidates of one MEIDNet checkpoint under a dataset's benchmark protocol (the slow stage of
`python scripts/benchmarks.py run`, usable on its own so that several checkpoints can run in parallel).

    python scripts/benchmark_generate.py perov5 meidnet-2k checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth
    python scripts/benchmark_generate.py perov5 meidnet-2k <checkpoint> --threads 5

Writes benchmarks/runs/<dataset>/<method>/inverse_design/{candidates.csv, cifs/, generation/}.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("method")
    ap.add_argument("checkpoint")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = torch default)")
    a = ap.parse_args(argv)
    import torch
    if a.threads:
        torch.set_num_threads(a.threads)
    from meidnet import benchmark as B
    from meidnet.checkpoint import load_checkpoint
    from meidnet.config import load_config
    with open(os.path.join(ROOT, "benchmarks", "datasets", a.dataset + ".json"), encoding="utf-8") as f:
        proto = json.load(f)["protocol"]
    task = next(t for t in proto["tasks"] if t["id"] == "inverse_design")
    st = task["settings"]
    cfg = load_config(os.path.join(ROOT, st["generation_config"]))
    lm = load_checkpoint(a.checkpoint if os.path.isabs(a.checkpoint) else os.path.join(ROOT, a.checkpoint), device="cpu")
    run_dir = os.path.join(ROOT, "benchmarks", "runs", a.dataset, a.method, "inverse_design")
    os.makedirs(run_dir, exist_ok=True)
    log_path = os.path.join(run_dir, "generation.log")
    t0 = time.time()
    with open(log_path, "w", encoding="utf-8") as logf:
        def log(*x):
            line = " ".join(str(v) for v in x)
            logf.write(line + "\n")
            logf.flush()
        cands = B.design_meidnet(lm, cfg.generation, st, run_dir, log=log, device=torch.device("cpu"))
    B.write_candidates(cands, os.path.join(run_dir, "candidates.csv"))
    with open(os.path.join(run_dir, "timing.json"), "w", encoding="utf-8") as f:
        json.dump({"seconds": round(time.time() - t0, 1), "threads": torch.get_num_threads()}, f)
    print(f"{a.method}: {len(cands)} candidates in {time.time() - t0:.0f}s -> {os.path.relpath(run_dir, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
