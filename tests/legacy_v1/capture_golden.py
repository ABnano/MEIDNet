"""
Capture reference ("golden") outputs from the UNMODIFIED MEIDNet v1.0 code.

model_v1.py and design_v1.py in this folder are byte-for-byte copies of
meidnet/model.py and meidnet/design.py at GitHub commit ed62f6a (v1.0.0).
MEIDNet 2.0 is tested against the files this script writes to tests/golden/,
so the refactor cannot silently change the published method.

Run once (CPU, fixed hash seed):
    PYTHONHASHSEED=0 python tests/legacy_v1/capture_golden.py
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GOLDEN = os.path.join(ROOT, "tests", "golden")
MINI_CSV = os.path.join(ROOT, "tests", "data", "perov5_mini.csv")
CKPT = os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")

sys.path.insert(0, HERE)
import model_v1 as M  # noqa: E402


def extract_cifs(csv_path, out_dir):
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        with open(os.path.join(out_dir, f"{row['material_id']}.cif"), "w") as f:
            f.write(row["cif"])
    return df


def build_v1_model():
    enc = M.SE3Encoder(M.MAX_SITES, M.NUM_SPECIES, 128, node_hidden_dim=128, species_embedding_dim=64)
    dec = M.SE3Decoder(M.MAX_SITES, M.NUM_SPECIES, 128, node_hidden_dim=128, species_embedding_dim=64)
    pe = M.PropertyEncoder(hidden_dim=128, latent_dim=128)
    pd_ = M.PropertyDecoder(latent_dim_common=128)
    return M.DualAutoencoderModel(enc, dec, pe, pd_, latent_dim_common=128,
                                  max_sites=M.MAX_SITES, num_species=M.NUM_SPECIES)


def state_digest(model):
    h = hashlib.sha256()
    for k, v in sorted(model.state_dict().items()):
        h.update(k.encode())
        h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def main():
    os.makedirs(GOLDEN, exist_ok=True)
    torch.set_num_threads(1)
    meta = {"hashseed": os.environ.get("PYTHONHASHSEED"), "torch": torch.__version__}

    with tempfile.TemporaryDirectory() as cif_dir:
        df = extract_cifs(MINI_CSV, cif_dir)

        # G1: featurisation (dense vectors) for every mini-set structure, in CSV order
        ids = [str(m) for m in df["material_id"]]
        dense = np.stack([M.parse_cif_to_dense(os.path.join(cif_dir, f"{m}.cif")) for m in ids])
        np.savez_compressed(os.path.join(GOLDEN, "g1_dense.npz"), ids=np.array(ids), dense=dense)

        # G2: forward pass of the published checkpoint
        model = build_v1_model()
        raw = torch.load(CKPT, map_location="cpu", weights_only=False)
        model.load_state_dict(raw["model_state_dict"], strict=True)
        model.eval()
        x = torch.from_numpy(dense).float()
        heat = torch.tensor(df["heat_all"].values, dtype=torch.float32)
        gap = torch.tensor(df["dir_gap"].values, dtype=torch.float32)
        with torch.no_grad():
            zc, zp, lat, adj, spc, crd, prop = model(x, heat, gap)
            _, _, zj, *_ = model.encode_modalities(x, heat, gap)
            prop_from_zc = model.property_decoder(zc)
        np.savez_compressed(os.path.join(GOLDEN, "g2_forward.npz"),
                            zc=zc.numpy(), zp=zp.numpy(), zj=zj.numpy(), lat=lat.numpy(),
                            spc=spc.numpy(), crd=crd.numpy(), prop=prop.numpy(),
                            prop_from_zc=prop_from_zc.numpy())

        # G3: two training epochs from a fixed seed on the mini set (scripts/train.py loop)
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        torch.manual_seed(0)
        np.random.seed(0)
        tmodel = build_v1_model()
        dataset = M.TripleModalityDataset(cif_dir, MINI_CSV)
        # TripleModalityDataset lists files with os.listdir (filesystem order); record it.
        order = [mid for _, mid in dataset.samples]
        losses = []
        loader = torch.utils.data.DataLoader(dataset, batch_size=16, shuffle=True, drop_last=True)
        opt = torch.optim.Adam(tmodel.parameters(), lr=1e-3)
        for ep in range(1, 3):
            tmodel.train()
            for batch in loader:
                cv, ha, dg = batch["crystal_vec"], batch["heat_all"], batch["dir_gap"]
                zc_, zp_, lo, al, sl, co, po = tmodel(cv, ha, dg)
                tp = torch.cat([ha.unsqueeze(1), dg.unsqueeze(1)], dim=1)
                l_rj = M.reconstruction_loss(cv, lo, al, sl, co)
                l_pj = torch.nn.functional.mse_loss(po, tp)
                a, b, c, center, isp, ico = tmodel.encode_modalities(cv, ha, dg)
                lp, ap, sp, cp = tmodel.crystal_decoder(b, input_species=isp, input_coords=ico, center=center)
                l_rp = M.reconstruction_loss(cv, lp, ap, sp, cp)
                l_pp = torch.nn.functional.mse_loss(tmodel.property_decoder(b), tp)
                l_ct = M.contrastive_loss(zc_, zp_, temperature=0.01)
                eff = min(ep / 1200.0, 1.0) * 5.0
                loss = 1.0 * l_rj + 1.0 * l_pj + 0.5 * l_rp + 0.5 * l_pp + eff * l_ct
                opt.zero_grad()
                loss.backward()
                opt.step()
                losses.append([loss.item(), l_rj.item(), l_pj.item(), l_rp.item(), l_pp.item(), l_ct.item()])
        meta["g3_order"] = order
        meta["g3_losses"] = losses
        meta["g3_state_sha256"] = state_digest(tmodel)

    # G4: small generation runs with the v1 CLI, two families
    runs = {
        "halide": ["--family", "halide", "--bg_targets=1.5,2.5", "--ent_targets=-0.10,-0.10"],
        "oxide": ["--family", "oxide", "--bg_targets=2.0", "--ent_targets=-0.20"],
    }
    for fam, extra in runs.items():
        out = os.path.join(GOLDEN, f"g4_{fam}")
        os.makedirs(out, exist_ok=True)
        for f in os.listdir(out):
            os.remove(os.path.join(out, f))
        n_t = str(len(extra[2].split("=")[1].split(",")))
        cmd = [sys.executable, os.path.join(HERE, "design_v1.py"), "--checkpoint", CKPT, *extra,
               "--num_targets", n_t, "--per_target", "3", "--batch_attempts", "16",
               "--rounds_per_target", "3", "--steps", "60", "--output_dir", out,
               "--output_prefix", fam, "--plot_dir", os.path.join(out, "plots"), "--dedup_abx",
               "--min_cosine_sep", "0.985", "--seed", "937"]
        env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   CUDA_VISIBLE_DEVICES="")
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        with open(os.path.join(out, "stdout.txt"), "w") as f:
            f.write(r.stdout)
        if r.returncode != 0:
            print(r.stderr)
            raise SystemExit(f"v1 generation failed for {fam}")
        meta[f"g4_{fam}_cmd"] = cmd[2:]

    with open(os.path.join(GOLDEN, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("golden outputs written to", GOLDEN)


if __name__ == "__main__":
    main()
