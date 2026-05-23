#!/usr/bin/env python3
"""
scripts/train.py
================
Training script for the MEIDNet dual-modality autoencoder.

Trains the DualAutoencoderModel (meidnet.model) on a paired dataset of
CIF crystal structures and scalar properties (formation enthalpy, direct
band-gap).  A compound multi-task loss is minimised:

    L = alpha  * L_recon_joint      (crystal reconstruction from joint latent)
      + beta   * L_prop_joint       (property prediction from joint latent)
      + gamma  * L_recon_from_prop  (cross-modal: decode crystal from z_prop)
      + delta  * L_prop_from_prop   (property cycle-consistency from z_prop)
      + lambda * L_contrastive      (CLIP-style InfoNCE alignment of z_c, z_p)

The contrastive weight lambda is ramped linearly from 0 to its full value
over the first 1200 epochs to allow the individual reconstructors to
stabilise before imposing inter-modal alignment.

Usage
-----
    # Train from scratch (200 epochs, save checkpoint every 50)
    python scripts/train.py --epochs 200 --save_every 50

    # Resume / continue training from a checkpoint
    python scripts/train.py --epochs 100 --checkpoint my_ckpt.pth

    # Reduce batch size if GPU memory is limited
    python scripts/train.py --batch 8

Output
------
    dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth  (default)
    heat_all_regression.png
    dir_gap_regression.png
"""
import argparse, os, sys, warnings, time
warnings.filterwarnings("ignore")
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader

# Allow running from the repo root or from inside scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from meidnet.model import (
    TripleModalityDataset,
    SE3Encoder, SE3Decoder,
    PropertyEncoder, PropertyDecoder,
    DualAutoencoderModel,
    contrastive_loss, reconstruction_loss,
    evaluate_latent_alignment,
    plot_property_regression,
    MAX_SITES, NUM_SPECIES,
)


def save_ckpt(model, latent_dim, species_embedding_dim, epochs_done, path):
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "latent_dim_struct": latent_dim,
            "latent_dim_prop": latent_dim,
            "latent_dim_common": latent_dim,
            "max_sites": MAX_SITES,
            "num_species": NUM_SPECIES,
            "species_embedding_dim": species_embedding_dim,
            "epochs_trained": epochs_done,
        },
        path,
    )
    print(f"  [ckpt] saved → {path}  (epoch {epochs_done})", flush=True)


def train_loop(model, dataset, epochs, batch_size, lr, contrastive_weight,
               temperature, alpha_joint_recon, beta_joint_prop,
               gamma_prop_recon, delta_prop_prop,
               latent_dim, species_embedding_dim, checkpoint_path,
               save_every, start_epoch=1):
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    device = next(model.parameters()).device
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for ep in range(start_epoch, start_epoch + epochs):
        model.train()
        total_loss = total_recon = total_prop = total_contrast = total_prop_r = total_prop_p = 0.0
        total_cos = total_l2 = cnt = 0

        for batch in loader:
            cv   = batch["crystal_vec"].to(device)
            heat = batch["heat_all"].to(device)
            gap  = batch["dir_gap"].to(device)

            zc, zp, lat_out, adj_logits, species_logits, coords_out, prop_out = model(cv, heat, gap)
            true_prop = torch.cat([heat.unsqueeze(1), gap.unsqueeze(1)], dim=1)

            loss_rj = reconstruction_loss(cv, lat_out, adj_logits, species_logits, coords_out)
            loss_pj = F.mse_loss(prop_out, true_prop)

            zc2, zp2, zj2, center, inp_sp, inp_co = model.encode_modalities(cv, heat, gap)
            lat_p, adj_p, sp_p, co_p = model.crystal_decoder(zp2, input_species=inp_sp,
                                                               input_coords=inp_co, center=center)
            loss_rp = reconstruction_loss(cv, lat_p, adj_p, sp_p, co_p)
            prop_fp = model.property_decoder(zp2)
            loss_pp = F.mse_loss(prop_fp, true_prop)

            loss_ct = contrastive_loss(zc, zp, temperature=temperature)
            eff_cw  = min(ep / 1200.0, 1.0) * contrastive_weight

            loss = (alpha_joint_recon * loss_rj + beta_joint_prop * loss_pj
                    + gamma_prop_recon * loss_rp + delta_prop_prop * loss_pp
                    + eff_cw * loss_ct)

            optimizer.zero_grad(); loss.backward(); optimizer.step()

            total_loss += loss.item(); total_recon += loss_rj.item()
            total_prop += loss_pj.item(); total_contrast += loss_ct.item()
            total_prop_r += loss_rp.item(); total_prop_p += loss_pp.item()
            total_cos += torch.mean(torch.sum(zc * zp, dim=1)).item()
            total_l2  += torch.mean(torch.norm(zc - zp, dim=1)).item()
            cnt += 1

        print(
            f"Epoch {ep}/{start_epoch+epochs-1} | Loss={total_loss/cnt:.4f} | "
            f"Recon={total_recon/cnt:.4f} | Prop={total_prop/cnt:.4f} | "
            f"PropLat={total_prop_r/cnt:.4f} | Contrast={total_contrast/cnt:.4f}",
            flush=True
        )
        print(
            f"   CosSim(zc,zp)={total_cos/cnt:.4f} | L2={total_l2/cnt:.4f}",
            flush=True
        )

        if ep % save_every == 0:
            save_ckpt(model, latent_dim, species_embedding_dim, ep, checkpoint_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cif_root",   default="cif_files")
    p.add_argument("--csv_file",   default="train.csv")
    p.add_argument("--epochs",     type=int,   default=200)
    p.add_argument("--batch",      type=int,   default=16)
    p.add_argument("--lr",         type=float, default=1e-3)
    p.add_argument("--save_every", type=int,   default=50,
                   help="save intermediate checkpoint every N epochs")
    p.add_argument("--checkpoint",
                   default="dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")
    args = p.parse_args()

    print(f"Loading dataset from {args.cif_root} / {args.csv_file} ...", flush=True)
    dataset = TripleModalityDataset(args.cif_root, args.csv_file)
    print(f"  {len(dataset)} samples", flush=True)

    latent_dim = 128
    species_embedding_dim = 64

    crystal_encoder = SE3Encoder(MAX_SITES, NUM_SPECIES, latent_dim,
                                 node_hidden_dim=128,
                                 species_embedding_dim=species_embedding_dim)
    crystal_decoder = SE3Decoder(MAX_SITES, NUM_SPECIES, latent_dim,
                                 node_hidden_dim=128,
                                 species_embedding_dim=species_embedding_dim)
    property_encoder = PropertyEncoder(hidden_dim=128, latent_dim=latent_dim)
    property_decoder = PropertyDecoder(latent_dim_common=latent_dim)

    model = DualAutoencoderModel(
        crystal_encoder, crystal_decoder,
        property_encoder, property_decoder,
        latent_dim_common=latent_dim,
        max_sites=MAX_SITES,
        num_species=NUM_SPECIES,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"Training on: {device}", flush=True)

    t0 = time.time()
    train_loop(
        model, dataset,
        epochs=args.epochs, batch_size=args.batch, lr=args.lr,
        contrastive_weight=5.0, temperature=0.01,
        alpha_joint_recon=1.0, beta_joint_prop=1.0,
        gamma_prop_recon=0.5, delta_prop_prop=0.5,
        latent_dim=latent_dim, species_embedding_dim=species_embedding_dim,
        checkpoint_path=args.checkpoint, save_every=args.save_every,
        start_epoch=1,
    )
    elapsed = time.time() - t0
    print(f"\nTraining complete: {args.epochs} epochs in {elapsed/60:.1f} min", flush=True)

    # Final evaluation and checkpoint
    evaluate_latent_alignment(model, dataset)
    plot_property_regression(model, dataset, "heat_all", "heat_all_regression.png")
    plot_property_regression(model, dataset, "dir_gap",  "dir_gap_regression.png")
    save_ckpt(model, latent_dim, species_embedding_dim, args.epochs, args.checkpoint)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
