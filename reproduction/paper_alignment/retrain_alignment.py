"""Re-run the training behind the article's alignment numbers (cosine ~0.97, L2 ~0.24) with the original script.

The original run (job `tril`, script tri_curri_v1_save.py: early fusion, linear contrastive warm-up over 1,500 epochs,
2,200 epochs, batch 16, Adam 1e-3, contrastive weight 5, temperature 0.01, all 18,928 Perov-5 materials) printed
cosine 0.9695, L2 0.2450 and structure matching 83.65 %; its checkpoint was later overwritten. This wrapper calls the
functions of that script unchanged (model, losses, training loop, evaluation); it only adds a seed, keeps the
checkpoint under its own name, and writes the final numbers to a JSON file.

    python -u retrain_alignment.py --seed 0                      # full run, as the original
    python -u retrain_alignment.py --seed 0 --epochs 2 --limit 96   # smoke test
    python -u retrain_alignment.py --ckpt some_checkpoint.pth       # no training: evaluate an existing checkpoint

Needs in the working directory (or via the options): tri_curri_v1_save.py, cif_files/<material_id>.cif, train.csv
with the columns material_id, heat_all, dir_gap (all 18,928 rows).
"""
import argparse, contextlib, importlib.util, io, json, os, random, re, sys, time

import numpy as np
import torch


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()
        return len(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="tri_curri_v1_save.py")
    ap.add_argument("--cif_root", default="cif_files")
    ap.add_argument("--csv", default="train.csv")
    ap.add_argument("--epochs", type=int, default=2200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="smoke test only: use the first N materials")
    ap.add_argument("--out", default="alignment_rerun")
    ap.add_argument("--ckpt", default="", help="evaluate this checkpoint (made by the same script) instead of training")
    a = ap.parse_args()

    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed); torch.cuda.manual_seed_all(a.seed)
    spec = importlib.util.spec_from_file_location("tri_curri_v1_save", a.script)
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)                      # the training in the script is under __main__ and does not run

    csv_file = a.csv
    if a.limit:
        import pandas as pd
        csv_file = f"{a.out}_seed{a.seed}_subset.csv"
        pd.read_csv(a.csv).head(a.limit).to_csv(csv_file, index=False)
    dataset = T.TripleModalityDataset(a.cif_root, csv_file)
    print("Dataset size:", len(dataset), flush=True)

    # the model exactly as the script's main builds it
    latent_dim = common_dim = 128
    species_embedding_dim = 64
    model = T.DualAutoencoderModelCLIP_EarlyFusion(
        T.SE3Encoder(T.MAX_SITES, T.NUM_SPECIES, latent_dim, node_hidden_dim=128, species_embedding_dim=species_embedding_dim),
        T.SE3Decoder(T.MAX_SITES, T.NUM_SPECIES, latent_dim, node_hidden_dim=128, species_embedding_dim=species_embedding_dim),
        T.PropertyEncoder(hidden_dim=128, latent_dim=latent_dim), T.PropertyDecoder(),
        latent_dim_common=common_dim, max_sites=T.MAX_SITES, num_species=T.NUM_SPECIES)

    t0 = time.time()
    if a.ckpt:
        state = torch.load(a.ckpt, map_location="cpu", weights_only=False)
        model.load_state_dict(state["model_state_dict"] if "model_state_dict" in state else state, strict=True)
        model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
        tag = "eval_" + os.path.splitext(os.path.basename(a.ckpt))[0]
    else:
        T.train_dual_autoencoder(model, dataset, epochs=a.epochs, batch_size=16, lr=1e-3, contrastive_weight=5.0, temperature=0.01)
        tag = f"{a.out}_seed{a.seed}"
        torch.save({"model_state_dict": model.state_dict(), "latent_dim": latent_dim, "common_dim": common_dim,
                    "max_sites": T.MAX_SITES, "num_species": T.NUM_SPECIES, "species_embedding_dim": species_embedding_dim,
                    "epochs": a.epochs, "seed": a.seed, "script": os.path.basename(a.script)}, tag + ".pth")
        print("Model checkpoint saved to", tag + ".pth", flush=True)
    train_seconds = time.time() - t0

    buf = io.StringIO()
    with contextlib.redirect_stdout(Tee(sys.__stdout__, buf)):
        T.evaluate_latent_alignment(model, dataset)
        T.evaluate_structure_matching_for_all(model=model, dataset=dataset, cif_root=a.cif_root, output_dir=tag + "_reconstructed",
                                              stol=0.5, angle_tol=10, ltol=0.3, species_threshold=0.5)
    text = buf.getvalue()
    cos = float(re.search(r"Average cosine similarity[^:]*:\s*([-\d.]+)", text).group(1))
    l2 = float(re.search(r"Average L2 distance[^:]*:\s*([-\d.]+)", text).group(1))
    m = re.search(r"Structure matching accuracy:\s*([\d.]+)% \((\d+)/(\d+)\)", text)
    res = {"script": os.path.basename(a.script), "evaluated_checkpoint": a.ckpt or tag + ".pth",
           "seed": None if a.ckpt else a.seed, "epochs": None if a.ckpt else a.epochs, "n_materials": len(dataset),
           "cosine": cos, "l2": l2, "structure_matching_pct": float(m.group(1)), "sm_matched": int(m.group(2)), "sm_total": int(m.group(3)),
           "article": {"cosine": 0.97, "l2": 0.24}, "original_log": {"cosine": 0.9695, "l2": 0.2450, "structure_matching_pct": 83.65},
           "train_hours": round(train_seconds / 3600, 2), "device": str(next(model.parameters()).device),
           "torch": torch.__version__}
    with open(tag + ".json", "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
