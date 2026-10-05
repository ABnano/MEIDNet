"""
Recompute the alignment results of one of the seven published checkpoints on your own computer (CPU, about a minute).

    meidnet download-data                                      # Perov-5 into data/perov5/ (once)
    python scripts/reproduce_alignment.py --seed 4             # cosine and L2 of seed 4
    python scripts/reproduce_alignment.py --seed 4 --structure-matching     # also rebuild every crystal (a few minutes)
    python scripts/reproduce_alignment.py --ckpt my_model.pt   # any MEIDNet checkpoint with the same two properties

Unless --ckpt is given, the checkpoint is downloaded once from https://huggingface.co/Babu09/MEIDNet (folder
reproduction/) to ~/.meidnet/reproduction/.
The numbers to expect are in benchmarks/reproduction/perov5/runs.csv and on the page
docs/benchmarks/perov5-reproduction.md.

What is measured, on all 18,928 Perov-5 materials:
  cosine, L2            between the structure latent and the property latent of the same material, each the normalised
                        output of its encoder (before the projection heads: where this model's contrastive loss acts)
  structure matching    the crystal decoded from the joint latent, with the most likely element on each site, compared
                        with the input by pymatgen's StructureMatcher (stol 0.5, angle_tol 10, ltol 0.3)
"""
import argparse
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
URL = "https://huggingface.co/Babu09/MEIDNet/resolve/main/reproduction/{name}"


def checkpoint_path(seed: int) -> str:
    """checkpoints/reproduction/ of the repository if the file is there, else downloaded once to ~/.meidnet/reproduction/
    (a plain download: no Hugging Face library needed)."""
    name = f"meidnet_paper_rerun_seed{seed}.pth"
    local = os.path.join(ROOT, "checkpoints", "reproduction", name)
    if os.path.exists(local):
        return local
    cache = os.path.join(os.path.expanduser("~"), ".meidnet", "reproduction", name)
    if not os.path.exists(cache):
        import urllib.request
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        print(f"downloading {name} (2.8 MB) to {cache} ...")
        urllib.request.urlretrieve(URL.format(name=name), cache + ".part")
        os.replace(cache + ".part", cache)
    return cache


def measure(ckpt: str, data_dir: str, structure_matching: bool = False, limit: int | None = None, log=print) -> dict:
    import numpy as np
    import torch
    import torch.nn.functional as F
    from torch.utils.data import DataLoader
    from meidnet import benchmark as B
    from meidnet.checkpoint import load_checkpoint
    from meidnet.data import MaterialsDataset, split_dense

    lm = load_checkpoint(ckpt, device="cpu")
    model, ms = lm.model.eval(), lm.model.max_sites
    records = []
    for split in ("train", "val", "test"):
        records += B.load_split(data_dir, split, list(lm.stats.columns), ms)[0]
    if limit:
        records = records[:limit]
    cos, l2, cos_proj, matched, tried = [], [], [], 0, 0
    matcher = None
    if structure_matching:
        from pymatgen.analysis.structure_matcher import StructureMatcher
        from pymatgen.core import Element, Lattice, Structure
        matcher = StructureMatcher(stol=0.5, angle_tol=10, ltol=0.3)
        scale = np.array([20, 20, 20, 180, 180, 180], dtype=float)

        def structure(lat, species_idx, coords, n):
            abc = lat * scale
            if not np.all(np.isfinite(abc)) or np.any(abc[:3] <= 0.5) or np.any(abc[3:] <= 5) or np.any(abc[3:] >= 175):
                return None                                  # a degenerate cell cannot match (and can crash spglib)
            return Structure(Lattice.from_parameters(*abc), [Element.from_Z(int(z) + 1) for z in species_idx[:n]], coords[:n] % 1.0)

    with torch.no_grad():
        for b in DataLoader(MaterialsDataset(records, lm.stats), batch_size=256, shuffle=False):
            cv, props = b["crystal_vec"], b["props"]
            a = F.normalize(model.crystal_encoder(cv)[0], p=2, dim=1)          # before the projection heads
            p = F.normalize(model.property_encoder(props), p=2, dim=1)
            cos.append((a * p).sum(1)); l2.append((a - p).norm(dim=1))
            zc, zp, lat, _, spc, crd, _ = model(cv, props)
            cos_proj.append((zc * zp).sum(1))
            if matcher is not None:
                true = split_dense(cv, ms)
                n_sites = (true["species"].sum(-1) > 0).sum(1).numpy()
                for i in range(len(cv)):
                    n = int(n_sites[i]); tried += 1
                    try:
                        s_true = structure(true["lat"][i].numpy(), true["species"][i].argmax(-1).numpy(), true["coords"][i].numpy(), n)
                        s_pred = structure(lat[i].numpy(), spc[i].argmax(-1).numpy(), crd[i].numpy(), n)
                        matched += bool(s_true is not None and s_pred is not None and matcher.fit(s_true, s_pred))
                    except Exception:
                        pass                                 # an invalid decoded crystal counts as not matched
                if tried % 2560 == 0:
                    log(f"  structure matching: {tried:,} of {len(records):,}")
    out = {"n": len(records), "cosine": float(torch.cat(cos).mean()), "l2": float(torch.cat(l2).mean()),
           "cosine_after_projection": float(torch.cat(cos_proj).mean())}
    if matcher is not None:
        out["structure_matching_pct"] = 100.0 * matched / max(1, tried)
        out["structure_matching_matched"] = matched
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=4, choices=range(7), help="which of the seven published checkpoints (default 4)")
    ap.add_argument("--ckpt", help="a checkpoint file instead of a published seed")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data", "perov5"))
    ap.add_argument("--structure-matching", action="store_true", help="also decode every crystal and compare it with the input")
    ap.add_argument("--limit", type=int, help="only the first N materials (a quick check)")
    a = ap.parse_args(argv)
    ck = a.ckpt or checkpoint_path(a.seed)
    t0 = time.time()
    r = measure(ck, a.data_dir, a.structure_matching, a.limit)
    print(f"checkpoint          {os.path.basename(ck)}")
    print(f"materials           {r['n']:,}")
    print(f"cosine              {r['cosine']:.4f}")
    print(f"L2                  {r['l2']:.4f}")
    if "structure_matching_pct" in r:
        print(f"structure matching  {r['structure_matching_pct']:.2f} %  ({r['structure_matching_matched']:,} of {r['n']:,}, most likely element)")
    print(f"(after the projection heads the cosine is {r['cosine_after_projection']:+.3f}; {time.time() - t0:.0f} s)")
    return r


if __name__ == "__main__":
    main()
