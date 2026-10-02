"""
meidnet.model
=============
Neural-network architecture and data pipeline for MEIDNet: a dual-modality
autoencoder that jointly encodes crystal structure and scalar properties
into a shared latent space via CLIP-style contrastive alignment.

Architecture Overview
---------------------
Crystal modality
    SE3Encoder  — SE(3)-equivariant graph encoder (2 EGNN layers) that maps
                  a fixed-length dense crystal representation to a d-dimensional
                  latent vector z_c.  Equivariance is achieved by operating on
                  squared inter-atomic distances (rotation-invariant) and
                  updating coordinates via equivariant displacements.
    SE3Decoder  — Paired graph decoder that reconstructs lattice parameters,
                  adjacency, species logits, and fractional coordinates from z.

Property modality
    PropertyEncoder — Two-layer MLP that maps scalar property vectors
                      (formation enthalpy, direct band-gap) to a latent
                      vector z_p of the same dimensionality.
    PropertyDecoder — Inverse MLP from latent space to property predictions.
                      Output convention (fixed across all scripts):
                        [:, 0] = heat_all  (formation enthalpy surrogate, eV/atom)
                        [:, 1] = dir_gap   (direct band-gap surrogate, eV)

Joint model
    DualAutoencoderModel — Combines both encoders and decoders; exposes
                           encode_modalities() and both decode paths.
                           Trained with a compound loss:
                             alpha * L_recon_joint
                           + beta  * L_prop_joint
                           + gamma * L_recon_from_prop
                           + delta * L_prop_from_prop
                           + lambda_c * L_contrastive(z_c, z_p)

Dataset
    TripleModalityDataset — PyTorch Dataset that returns (crystal_vec,
                            heat_all, dir_gap) triplets matched by
                            material_id between CIF files and a CSV.

References
----------
Satorras et al., "E(n) Equivariant Graph Neural Networks," ICML 2021.
Radford et al., "Learning Transferable Visual Models from Natural Language
    Supervision (CLIP)," ICML 2021.
"""
import os
import warnings
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt

from pymatgen.core import Structure, Lattice
from pymatgen.io.cif import CifParser, CifWriter
from pymatgen.analysis.structure_matcher import StructureMatcher

import pandas as pd

warnings.filterwarnings("ignore", message="Issues encountered while parsing CIF")
warnings.filterwarnings("ignore", message="No\\sPauling\\selectronegativity")

################################
# 1) Global Config & Utility Functions
################################
from pymatgen.core.periodic_table import Element

ALL_ELEMENTS = [str(Element.from_Z(z)) for z in range(1, 119)]
SPECIES_LIST = ALL_ELEMENTS
NUM_SPECIES = len(SPECIES_LIST)  # 118

MAX_SITES = 20
CUTOFF = 4


def species_to_one_hot(sym: str):
    """
    Map an element symbol to a one-hot vector over all 118 elements.
    This is the categorical representation used by the EGNN.
    """
    vec = np.zeros(NUM_SPECIES, dtype=np.float32)
    if sym not in SPECIES_LIST:
        raise ValueError(f"Element {sym} not recognized among the known {NUM_SPECIES} elements.")
    idx = SPECIES_LIST.index(sym)
    vec[idx] = 1.0
    return vec


def scale_lattice_params(a, b, c, alpha, beta, gamma):
    """
    Rough scaling of lattice parameters into [0, 1]-like range
    so that the NN sees nicely scaled inputs.
    """
    return np.array(
        [a / 20.0, b / 20.0, c / 20.0, alpha / 180.0, beta / 180.0, gamma / 180.0],
        dtype=np.float32,
    )


def unscale_lattice_params(lat_vec):
    """
    Inverse of scale_lattice_params: back to physical units
    for writing CIFs.
    """
    a = lat_vec[0] * 20.0
    b = lat_vec[1] * 20.0
    c = lat_vec[2] * 20.0
    alpha = lat_vec[3] * 180.0
    beta = lat_vec[4] * 180.0
    gamma = lat_vec[5] * 180.0
    return a, b, c, alpha, beta, gamma


################################
# 2) Dense Representation Parsing from CIF
################################
def parse_cif_to_dense(cif_path, max_sites=MAX_SITES, cutoff=CUTOFF):
    """
    Parse a CIF into a fixed-length dense vector:
      [scaled lattice(6),
       adjacency(max_sites*max_sites),
       species(one-hot, max_sites*NUM_SPECIES),
       fractional coords(max_sites*3)]

    This is the single representation that the crystal encoder consumes.
    """
    parser = CifParser(cif_path)
    structs = parser.parse_structures(primitive=False)
    if not structs:
        raise ValueError(f"No structure in CIF {cif_path}")
    struct = structs[0]
    while isinstance(struct, list) and len(struct) > 0:
        struct = struct[0]
    if not isinstance(struct, Structure):
        raise ValueError("Could not parse a single Structure object.")

    n = len(struct)
    if n > max_sites:
        raise ValueError(f"Structure has {n} sites > max_sites={max_sites}, skipping...")

    latt = struct.lattice
    a, b, c = latt.abc
    alpha, beta, gamma = latt.angles
    lat_array = scale_lattice_params(a, b, c, alpha, beta, gamma)

    # Build adjacency with neighbor_list
    adj = np.zeros((max_sites, max_sites), dtype=np.float32)
    nn_idx0, nn_idx1, _, nn_dists = struct.get_neighbor_list(r=cutoff)
    for i, j, d in zip(nn_idx0, nn_idx1, nn_dists):
        if i < max_sites and j < max_sites and i != j:
            adj[i, j] = 1.0

    species_mat = np.zeros((max_sites, NUM_SPECIES), dtype=np.float32)
    for i, site in enumerate(struct):
        species_mat[i] = species_to_one_hot(site.specie.symbol)

    coords_mat = np.zeros((max_sites, 3), dtype=np.float32)
    for i, site in enumerate(struct):
        coords_mat[i] = site.frac_coords

    full_vec = np.concatenate(
        [
            lat_array.flatten(),
            adj.flatten(),
            species_mat.flatten(),
            coords_mat.flatten(),
        ],
        axis=0,
    )
    return full_vec


def parse_dense_to_components_batch(x, max_sites=MAX_SITES, num_species=NUM_SPECIES):
    """
    Inverse of parse_cif_to_dense, but in batched tensor form.
    Helps SE3Encoder/Decoder consume structured tensors instead of one big flat vector.
    """
    B = x.size(0)
    offset = 0

    lat = x[:, offset : offset + 6]
    offset += 6

    adj_sz = max_sites * max_sites
    adj = x[:, offset : offset + adj_sz].view(B, max_sites, max_sites)
    offset += adj_sz

    spc_sz = max_sites * num_species
    species = x[:, offset : offset + spc_sz].view(B, max_sites, num_species)
    offset += spc_sz

    coords = x[:, offset : offset + max_sites * 3].view(B, max_sites, 3)
    return {"lat": lat, "adj": adj, "species": species, "coords": coords}


################################
# 3) TripleModalityDataset (structure + 2 scalar properties)
################################
class TripleModalityDataset(Dataset):
    """
    Dataset that returns:
      - dense crystal vector
      - heat of formation (heat_all)
      - direct band gap (dir_gap)

    material_id is used to match CIF files and CSV rows.
    """

    def __init__(self, cif_root, csv_file):
        super().__init__()
        self.samples = []
        self.heat_dict = {}
        self.dir_dict = {}

        df = pd.read_csv(csv_file)
        if "heat_all" not in df.columns or "dir_gap" not in df.columns:
            raise KeyError("CSV must contain columns 'heat_all' and 'dir_gap'.")

        # Build lookup tables for properties
        for _, row in df.iterrows():
            try:
                mid = str(int(row["material_id"]))
            except Exception:
                mid = str(row["material_id"]).strip()
            self.heat_dict[mid] = float(row["heat_all"])
            self.dir_dict[mid] = float(row["dir_gap"])

        # Match CIFs with property rows
        files = [f for f in os.listdir(cif_root) if f.endswith(".cif")]
        for fname in files:
            try:
                mid_file = str(int(os.path.splitext(fname)[0]))
            except Exception:
                mid_file = os.path.splitext(fname)[0]
            if mid_file in self.heat_dict and mid_file in self.dir_dict:
                path = os.path.join(cif_root, fname)
                try:
                    vec = parse_cif_to_dense(path, max_sites=MAX_SITES)
                    self.samples.append((vec, mid_file))
                except Exception as e:
                    print(f"Skipping {fname}: {e}")

        if len(self.samples) == 0:
            raise ValueError(
                "No matching samples were found. Please check that the 'material_id' values in train.csv "
                "match the CIF filenames in the folder."
            )

        print(f"Loaded {len(self.samples)} samples from CIF and CSV.")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        vec, mid = self.samples[idx]
        heat_val = self.heat_dict[mid]
        dir_val = self.dir_dict[mid]
        return {
            "crystal_vec": torch.from_numpy(vec).float(),
            "heat_all": torch.tensor(heat_val, dtype=torch.float32),
            "dir_gap": torch.tensor(dir_val, dtype=torch.float32),
            "material_id": mid,
        }


################################
# 4) SE(3)-Equivariant Encoder & Decoder
################################
class EGNNLayer(nn.Module):
    """
    Simple EGNN-style layer:
      - Updates node features and coordinates based on pairwise interactions.
      - Uses squared distances only (rotation-equivariant).
    """

    def __init__(self, node_dim, edge_dim):
        super().__init__()
        self.phi_e = nn.Sequential(
            nn.Linear(2 * node_dim + 1, edge_dim),
            nn.ReLU(),
            nn.Linear(edge_dim, edge_dim),
        )
        self.phi_x = nn.Sequential(nn.Linear(edge_dim, 1))
        self.phi_h = nn.Sequential(
            nn.Linear(node_dim + edge_dim, node_dim),
            nn.ReLU(),
        )

    def forward(self, h, x, adj, lattice=None):
        B, N, _ = h.shape
        x_i = x.unsqueeze(2)  # (B, N, 1, 3)
        x_j = x.unsqueeze(1)  # (B, 1, N, 3)
        diff = x_i - x_j
        dist2 = (diff**2).sum(dim=-1, keepdim=True)  # (B, N, N, 1)

        h_i = h.unsqueeze(2).expand(B, N, N, h.size(-1))
        h_j = h.unsqueeze(1).expand(B, N, N, h.size(-1))
        edge_input = torch.cat([h_i, h_j, dist2], dim=-1)  # (B, N, N, 2*node_dim+1)

        edge_feat = self.phi_e(edge_input)
        edge_feat = edge_feat * adj.unsqueeze(-1)  # zero out edges that don't exist

        weight = self.phi_x(edge_feat)
        delta_x = (diff * weight).sum(dim=2)  # sum over j
        x_updated = x + delta_x

        agg = edge_feat.sum(dim=2)  # sum over j
        h_input = torch.cat([h, agg], dim=-1)
        h_updated = self.phi_h(h_input)
        return h_updated, x_updated


class SE3Encoder(nn.Module):
    """
    Crystal encoder:
      - embeds species,
      - runs 2 EGNN layers,
      - aggregates to a graph-level latent z_c (dimension = latent_dim),
      - also returns the geometric center (for stable decoding).
    """

    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.num_species = num_species

        self.species_embedding = nn.Linear(num_species, species_embedding_dim)
        self.init_node_fc = nn.Sequential(
            nn.Linear(species_embedding_dim, node_hidden_dim),
            nn.ReLU(),
        )
        self.egnn1 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)
        self.egnn2 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)

        self.aggregate_fc = nn.Sequential(
            nn.Linear(node_hidden_dim, 128),
            nn.ReLU(),
        )
        self.lat_fc = nn.Sequential(
            nn.Linear(6, 64),
            nn.ReLU(),
        )
        self.comb_fc = nn.Sequential(
            nn.Linear(64 + 128, 128),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(128, latent_dim)

    def forward(self, x):
        comp = parse_dense_to_components_batch(x, max_sites=self.max_sites, num_species=self.num_species)
        lat = comp["lat"]  # (B, 6)
        adj = comp["adj"]  # (B, N, N)
        species = comp["species"]  # (B, N, num_species)
        coords = comp["coords"]  # (B, N, 3)

        B, N, _ = coords.shape

        # lattice embedding
        lat_emb = self.lat_fc(lat)  # (B, 64)

        # embed species
        h = self.species_embedding(species)  # (B, N, species_embedding_dim)
        h = self.init_node_fc(h)  # (B, N, node_hidden_dim)

        # mask for padded sites
        mask = (species.sum(dim=-1) > 0).float().unsqueeze(-1)  # (B, N, 1)
        center = (coords * mask).sum(dim=1) / (mask.sum(dim=1) + 1e-8)  # (B, 3)
        coords_centered = coords - center.unsqueeze(1)  # (B, N, 3)

        # EGNN layers
        h, x_coords = self.egnn1(h, coords_centered, adj, lattice=None)
        h, x_coords = self.egnn2(h, x_coords, adj, lattice=None)

        # re-apply mask to ignore padded sites
        h = h * mask

        # aggregate node features
        agg_node = h.sum(dim=1) / (mask.sum(dim=1).clamp(min=1))
        agg_emb = self.aggregate_fc(agg_node)  # (B, 128)

        combined = torch.cat([lat_emb, agg_emb], dim=-1)  # (B, 64+128)
        combined = self.comb_fc(combined)  # (B, 128)
        z = self.fc_mu(combined)  # (B, latent_dim)

        return z, center


class SE3Decoder(nn.Module):
    """
    Crystal decoder:
      - takes a latent z (from the *common* latent space),
      - expands to per-node features,
      - runs EGNN layers,
      - outputs:
          • lattice parameters (lat_out),
          • species logits per site,
          • coordinates per site,
          • adjacency logits (via node–node dot products).
    """

    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.num_species = num_species

        self.fc_lat = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 6),
        )
        self.fc_nodes = nn.Sequential(
            nn.Linear(latent_dim, max_sites * node_hidden_dim),
            nn.ReLU(),
        )

        self.egnn1 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)
        self.egnn2 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)

        self.fc_species_decoded = nn.Sequential(
            nn.Linear(node_hidden_dim, 64),
            nn.ReLU(),
        )
        self.fc_species_final = nn.Linear(64, num_species)

        self.fc_coords = nn.Sequential(nn.Linear(node_hidden_dim, 3))

    def forward(self, z, input_species=None, input_coords=None, center=None):
        B = z.size(0)
        N = self.max_sites

        # decode lattice parameters
        lat_out = self.fc_lat(z)  # (B, 6)

        # Expand node features from z
        nodes = self.fc_nodes(z).view(B, N, -1)  # (B, N, node_hidden_dim)

        # If no coords provided, default to zeros
        if input_coords is None:
            input_coords = torch.zeros(B, N, 3, device=z.device)

        if center is None:
            center = torch.zeros(B, 3, device=z.device)

        relative_input = input_coords - center.unsqueeze(1)  # (B, N, 3)

        # For decoding, we assume a fully connected adjacency (decoder learns its own graph)
        full_adj = torch.ones(B, N, N, device=z.device)

        nodes, x_coords = self.egnn1(nodes, relative_input, full_adj, lattice=None)
        nodes, x_coords = self.egnn2(nodes, x_coords, full_adj, lattice=None)

        species_decoded = self.fc_species_decoded(nodes)
        species_logits = self.fc_species_final(species_decoded)  # (B, N, num_species)

        coords_out = self.fc_coords(nodes)  # (B, N, 3)
        coords_out = coords_out + center.unsqueeze(1)

        # adjacency logits (node-wise dot product)
        adj_logits = torch.bmm(nodes, nodes.transpose(1, 2))

        return lat_out, adj_logits, species_logits, coords_out


################################
# 5) Graph Autoencoder (crystal modality)
################################
class GraphAutoencoderHybridSE3(nn.Module):
    """
    Simple wrapper that ties SE3Encoder and SE3Decoder together.
    We mostly use the encoder/decoder separately inside the dual model.
    """

    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.encoder = SE3Encoder(max_sites, num_species, latent_dim, node_hidden_dim, species_embedding_dim)
        self.decoder = SE3Decoder(max_sites, num_species, latent_dim, node_hidden_dim, species_embedding_dim)

    def forward(self, x):
        z, center = self.encoder(x)
        B = x.size(0)
        N = self.max_sites
        species_offset = 6 + N * N
        species_len = N * NUM_SPECIES
        coords_offset = species_offset + species_len
        coords_len = N * 3

        input_species = x[:, species_offset : species_offset + species_len].view(B, N, NUM_SPECIES)
        input_coords = x[:, coords_offset : coords_offset + coords_len].view(B, N, 3)
        outputs = self.decoder(z, input_species=input_species, input_coords=input_coords, center=center)
        return outputs, z

    def encode(self, x):
        return self.encoder(x)


################################
# 6) Property Encoder & Decoder
################################
class PropertyEncoder(nn.Module):
    """
    Maps 2 scalar properties into a latent vector.
    Input order: [:, 0] = heat_all (enthalpy), [:, 1] = dir_gap (band gap).
    This order must be respected wherever the encoder is called.
    """

    def __init__(self, hidden_dim=128, latent_dim=128):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, x):
        return self.fc(x)


class PropertyDecoder(nn.Module):
    """
    Decodes 2 scalar properties from a latent vector in the *common* latent space.
    Output order: [:, 0] = heat_all (enthalpy), [:, 1] = dir_gap (band gap).
    This order must be respected in the inverse-design script.
    """

    def __init__(self, latent_dim_common=128):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(latent_dim_common, 64),
            nn.ReLU(),
            nn.Linear(64, 2),  # output[:,0]=heat_all, output[:,1]=dir_gap
        )

    def forward(self, z):
        return self.fc(z)


################################
# 7) Dual Autoencoder Model with CLIP-style Common Latent
################################
class DualAutoencoderModel(nn.Module):
    """
    Dual (crystal + property) autoencoder with:
      - Crystal encoder/decoder (EGNN-based).
      - Property encoder/decoder.
      - Projection heads proj_crystal, proj_prop into a *shared* latent space.

    IMPORTANT FOR INVERSE DESIGN:
      • The *common* latent (after projection) is what we use for:
          - property prediction (via PropertyDecoder),
          - structure generation (via SE3Decoder),
          - contrastive alignment.
      • We explicitly train the decoder to work on:
          - joint latent z_joint  = (z_c + z_p)/2,
          - property-only latent z_p.
    """

    def __init__(self, crystal_encoder, crystal_decoder, property_encoder, property_decoder,
                 latent_dim_common, max_sites, num_species):
        super().__init__()
        self.crystal_encoder = crystal_encoder    # returns (z_c_raw, center)
        self.crystal_decoder = crystal_decoder    # decodes crystal modality
        self.property_encoder = property_encoder  # encodes [heat_all, dir_gap] -> z_p_raw
        self.property_decoder = property_decoder  # decodes 2 properties from latent

        # Projection heads from modality-specific latent → common latent
        self.proj_crystal = nn.Sequential(
            nn.Linear(128, latent_dim_common),
            nn.ReLU(),
            nn.Linear(latent_dim_common, latent_dim_common),
        )
        self.proj_prop = nn.Sequential(
            nn.Linear(128, latent_dim_common),
            nn.ReLU(),
            nn.Linear(latent_dim_common, latent_dim_common),
        )
        self.max_sites = max_sites
        self.num_species = num_species
        self.latent_dim_common = latent_dim_common

    def encode_modalities(self, crystal_vec, heat_all, dir_gap):
        """
        Core helper:
          1) Encode crystal → z_c_raw, center.
          2) Encode properties → z_p_raw.
          3) Project both into a *common* latent:
               z_c_common, z_p_common, z_joint.
          4) Extract input species/coords (used by decoder as a "template").
        """
        # -- crystal branch
        z_c_raw, center = self.crystal_encoder(crystal_vec)  # (B,128), (B,3)

        # -- property branch
        prop = torch.cat(
            [heat_all.unsqueeze(1), dir_gap.unsqueeze(1)],
            dim=1,
        )  # (B,2)
        z_p_raw = self.property_encoder(prop)  # (B,128)

        # Normalize within each modality before projection (stabilizes training)
        z_c_norm = F.normalize(z_c_raw, p=2, dim=1)
        z_p_norm = F.normalize(z_p_raw, p=2, dim=1)

        # Project to common latent space and re-normalize
        z_c_common = F.normalize(self.proj_crystal(z_c_norm), p=2, dim=1)
        z_p_common = F.normalize(self.proj_prop(z_p_norm), p=2, dim=1)

        # Joint latent = simple average (CLIP-style fusion)
        z_joint = (z_c_common + z_p_common) / 2.0

        # Extract crystal species & coords as decoder reference input
        B = crystal_vec.size(0)
        N = self.max_sites
        species_offset = 6 + N * N
        species_len = N * self.num_species
        coords_offset = species_offset + species_len
        coords_len = N * 3

        input_species = crystal_vec[:, species_offset : species_offset + species_len].view(
            B, N, self.num_species
        )
        input_coords = crystal_vec[:, coords_offset : coords_offset + coords_len].view(B, N, 3)

        return z_c_common, z_p_common, z_joint, center, input_species, input_coords

    def forward(self, crystal_vec, heat_all, dir_gap):
        """
        Forward used during training & evaluation.
        Returns:
          z_c_common, z_p_common: common-space latents for contrastive alignment,
          lat_out, adj_logits, species_logits, coords_out: decoded from z_joint,
          prop_out: properties decoded from z_joint.
        """
        z_c, z_p, z_joint, center, input_species, input_coords = self.encode_modalities(
            crystal_vec, heat_all, dir_gap
        )

        # Decode CRYSTAL modality from JOINT latent
        lat_out, adj_logits, species_logits, coords_out = self.crystal_decoder(
            z_joint,
            input_species=input_species,
            input_coords=input_coords,
            center=center,
        )

        # Decode PROPERTIES from JOINT latent
        prop_out = self.property_decoder(z_joint)

        return z_c, z_p, lat_out, adj_logits, species_logits, coords_out, prop_out


################################
# 8) combine_decoder_outputs
################################
def combine_decoder_outputs(lat, adj_logits, species_logits, coords, tau=0.01):
    """
    Convert decoder outputs back into a dense vector:
      - sigmoid on adjacency,
      - Gumbel-softmax (hard) on species logits,
      - coords as is.
    """
    adj_prob = torch.sigmoid(adj_logits)
    species_one_hot = F.gumbel_softmax(species_logits, tau=tau, hard=True, dim=-1)
    full_vec = torch.cat(
        [
            lat.view(-1),
            adj_prob.view(-1),
            species_one_hot.view(-1),
            coords.view(-1),
        ],
        dim=0,
    )
    return full_vec.cpu().detach().numpy()


################################
# 9) Reconstruction Loss (crystal modality)
################################
def reconstruction_loss(
    crystal_vec, lat_out, adj_logits, species_logits, coords_out, max_sites=MAX_SITES, num_species=NUM_SPECIES
):
    """
    Multi-term reconstruction loss:
      - lattice MSE,
      - adjacency BCE,
      - species cross-entropy,
      - coordinates MSE.
    """
    B = crystal_vec.size(0)
    target_lat = crystal_vec[:, :6]
    target_adj = crystal_vec[:, 6 : 6 + max_sites * max_sites].view(B, max_sites, max_sites)
    target_species = crystal_vec[
        :,
        6
        + max_sites * max_sites : 6
        + max_sites * max_sites
        + max_sites * num_species,
    ].view(B, max_sites, num_species)
    target_coords = crystal_vec[
        :,
        6
        + max_sites * max_sites
        + max_sites * num_species :,
    ].view(B, max_sites, 3)

    loss_lat = F.mse_loss(lat_out, target_lat)
    loss_adj = F.binary_cross_entropy_with_logits(adj_logits, target_adj)

    target_species_idx = target_species.argmax(dim=-1)
    loss_species = F.cross_entropy(
        species_logits.view(-1, num_species),
        target_species_idx.view(-1),
    )

    loss_coords = F.mse_loss(coords_out, target_coords)
    return loss_lat + loss_adj + loss_species + loss_coords


################################
# 10) Contrastive Loss between modalities (in common latent space)
################################
def contrastive_loss(z1, z2, temperature=0.01):
    """
    Symmetric InfoNCE-style contrastive loss.
    We assume z1 and z2 are already in the *common* latent space.
    """
    logits = torch.matmul(z1, z2.t()) / temperature
    labels = torch.arange(z1.size(0), device=z1.device)

    loss1 = F.cross_entropy(logits, labels)
    loss2 = F.cross_entropy(logits.t(), labels)
    return 0.5 * (loss1 + loss2)


################################
# 11) Train Dual Autoencoder (with property-aware decoding)
################################
def train_dual_autoencoder(
    model,
    dataset,
    epochs=5,
    batch_size=16,
    lr=1e-3,
    contrastive_weight=5.0,
    temperature=0.01,
    alpha_joint_recon=1.0,
    beta_joint_prop=1.0,
    gamma_prop_recon=0.5,
    delta_prop_prop=0.5,
):
    """
    Training loop with the key idea:

      • Train on JOINT latent (z_joint):
          - reconstruct structure,
          - reconstruct properties.

      • ALSO train on PROPERTY-ONLY latent (z_p):
          - reconstruct same structure (one possible S for P),
          - reconstruct properties.

      This explicitly teaches the crystal decoder & property decoder
      that "property latents" alone live in a region of latent space
      where decoding is meaningful → crucial for inverse design.
    """
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for ep in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_loss_prop = 0.0
        total_loss_recon = 0.0
        total_loss_contrast = 0.0
        total_loss_prop_recon = 0.0
        total_loss_prop_prop = 0.0

        total_cos_sim = 0.0
        total_l2 = 0.0
        cnt = 0

        for batch in loader:
            crystal_vec = batch["crystal_vec"].to(device)
            heat_all = batch["heat_all"].to(device)
            dir_gap = batch["dir_gap"].to(device)

            # ---------------------------------
            # 1) Forward via JOINT latent
            # ---------------------------------
            zc, zp, lat_out, adj_logits, species_logits, coords_out, prop_out = model(
                crystal_vec, heat_all, dir_gap
            )

            # "true" property vector
            true_prop = torch.cat(
                [heat_all.unsqueeze(1), dir_gap.unsqueeze(1)],
                dim=1,
            )

            # Joint latent reconstruction & property loss
            loss_recon_joint = reconstruction_loss(
                crystal_vec,
                lat_out,
                adj_logits,
                species_logits,
                coords_out,
                max_sites=MAX_SITES,
                num_species=NUM_SPECIES,
            )
            loss_prop_joint = F.mse_loss(prop_out, true_prop)

            # ---------------------------------
            # 2) Explicit PROPERTY-ONLY decoding
            #    z_p (common) → structure + properties
            # ---------------------------------
            zc_common, zp_common, z_joint, center, input_species, input_coords = model.encode_modalities(
                crystal_vec, heat_all, dir_gap
            )

            # Decode crystal from PROPERTY-ONLY latent
            lat_p, adj_p, species_p, coords_p = model.crystal_decoder(
                zp_common,
                input_species=input_species,
                input_coords=input_coords,
                center=center,
            )
            loss_recon_prop = reconstruction_loss(
                crystal_vec,
                lat_p,
                adj_p,
                species_p,
                coords_p,
                max_sites=MAX_SITES,
                num_species=NUM_SPECIES,
            )

            # Decode properties from PROPERTY-ONLY latent
            prop_from_prop = model.property_decoder(zp_common)
            loss_prop_from_prop = F.mse_loss(prop_from_prop, true_prop)

            # ---------------------------------
            # 3) Contrastive alignment in common latent space
            #    (note: zc, zp returned from model() are already common latents)
            # ---------------------------------
            loss_contrast = contrastive_loss(zc, zp, temperature=temperature)

            # Curriculum learning: ramp contrastive_weight
            if ep <= 1200:
                effective_contrastive_weight = (ep / 1200.0) * contrastive_weight
            else:
                effective_contrastive_weight = contrastive_weight

            # Total loss
            loss = (
                alpha_joint_recon * loss_recon_joint
                + beta_joint_prop * loss_prop_joint
                + gamma_prop_recon * loss_recon_prop
                + delta_prop_prop * loss_prop_from_prop
                + effective_contrastive_weight * loss_contrast
            )

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            total_loss_recon += loss_recon_joint.item()
            total_loss_prop += loss_prop_joint.item()
            total_loss_contrast += loss_contrast.item()
            total_loss_prop_recon += loss_recon_prop.item()
            total_loss_prop_prop += loss_prop_from_prop.item()

            # Monitor cosine similarity & L2 distance in common latent space
            cos_sim = torch.mean(torch.sum(zc * zp, dim=1)).item()
            l2_dist = torch.mean(torch.norm(zc - zp, dim=1)).item()
            total_cos_sim += cos_sim
            total_l2 += l2_dist
            cnt += 1

        print(
            f"Epoch {ep}/{epochs} | "
            f"Total Loss={total_loss/cnt:.4f} | "
            f"Recon(Joint)={total_loss_recon/cnt:.4f} | "
            f"Prop(Joint)={total_loss_prop/cnt:.4f} | "
            f"Recon(PropLat)={total_loss_prop_recon/cnt:.4f} | "
            f"Prop(PropLat)={total_loss_prop_prop/cnt:.4f} | "
            f"Contrast={total_loss_contrast/cnt:.4f}"
        )
        print(
            f"   Avg Cosine Similarity (z_c vs z_p): {total_cos_sim/cnt:.4f} | "
            f"Avg L2 Distance: {total_l2/cnt:.4f}"
        )


################################
# 12) dense_to_structure
################################
def dense_to_structure(dense_vec, valid_indices=None, species_threshold=0.5):
    """
    Convert a dense vector back into a pymatgen Structure.
    valid_indices selects which sites to keep (non-padded).
    """
    lat = dense_vec[:6]
    a, b, c, alpha, beta, gamma = unscale_lattice_params(lat)

    offset = 6 + MAX_SITES * MAX_SITES
    spc_sz = MAX_SITES * NUM_SPECIES
    species_flat = dense_vec[offset : offset + spc_sz]
    offset += spc_sz

    species_mat = species_flat.reshape(MAX_SITES, NUM_SPECIES)
    coords_flat = dense_vec[offset : offset + MAX_SITES * 3]
    coords_mat = coords_flat.reshape(MAX_SITES, 3)

    lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)

    if valid_indices is None:
        valid_indices = [i for i in range(MAX_SITES) if np.max(species_mat[i]) > species_threshold]
    if len(valid_indices) == 0:
        return None

    final_species = []
    final_coords = []
    for i in valid_indices:
        idx = np.argmax(species_mat[i])
        sym = SPECIES_LIST[idx]
        final_species.append(sym)
        final_coords.append(coords_mat[i])

    return Structure(lattice, final_species, final_coords)


################################
# 13) Evaluate Latent Alignment (between crystal and property modalities)
################################
def evaluate_latent_alignment(model, dataset):
    loader = DataLoader(dataset, batch_size=16, shuffle=False)
    device = next(model.parameters()).device
    model.eval()
    cosine_sims = []
    l2_dists = []
    with torch.no_grad():
        for batch in loader:
            crystal_vec = batch["crystal_vec"].to(device)
            heat_all = batch["heat_all"].to(device)
            dir_gap = batch["dir_gap"].to(device)
            zc, zp, *_ = model(crystal_vec, heat_all, dir_gap)
            cos_sim = torch.sum(zc * zp, dim=1)
            l2 = torch.norm(zc - zp, dim=1)
            cosine_sims.append(cos_sim.cpu().numpy())
            l2_dists.append(l2.cpu().numpy())
    cosine_sims = np.concatenate(cosine_sims)
    l2_dists = np.concatenate(l2_dists)
    print(f"Average cosine similarity (crystal vs. property latent): {np.mean(cosine_sims):.4f}")
    print(f"Average L2 distance (crystal vs. property latent): {np.mean(l2_dists):.4f}")


################################
# 14) Plot Regression for each property (heat_all and dir_gap separately)
################################
def plot_property_regression(model, dataset, property_key, save_path):
    device = next(model.parameters()).device
    loader = DataLoader(dataset, batch_size=16, shuffle=False)
    gt_list = []
    pred_list = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            crystal_vec = batch["crystal_vec"].to(device)
            heat_all = batch["heat_all"].to(device)
            dir_gap = batch["dir_gap"].to(device)
            _, _, _, _, _, _, prop_out = model(crystal_vec, heat_all, dir_gap)
            # prop_out is (B,2); select index 0 for heat_all and 1 for dir_gap
            if property_key == "heat_all":
                pred = prop_out[:, 0]
                gt = heat_all
            elif property_key == "dir_gap":
                pred = prop_out[:, 1]
                gt = dir_gap
            else:
                raise ValueError("Unknown property key")
            gt_list.extend(gt.cpu().numpy())
            pred_list.extend(pred.cpu().numpy())
    plt.figure()
    plt.scatter(gt_list, pred_list, alpha=0.5, label="Data points")
    low = min(min(gt_list), min(pred_list))
    high = max(max(gt_list), max(pred_list))
    plt.plot([low, high], [low, high], "r--", label="Ideal (y=x)")
    plt.xlabel(f"Ground Truth {property_key}")
    plt.ylabel(f"Predicted {property_key}")
    plt.title(f"Regression Plot: Ground Truth vs Predicted {property_key}")
    plt.legend()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Regression plot saved to {save_path}")


################################
# 15) Evaluate Structure Matching for ALL (using joint latent)
################################
def evaluate_structure_matching_for_all(
    model,
    dataset,
    cif_root,
    output_dir="reconstructed_cifs_full",
    stol=0.5,
    angle_tol=10,
    ltol=0.3,
    species_threshold=0.5,
):
    """
    Reconstruct every structure via JOINT latent and compare to original CIF
    using pymatgen's StructureMatcher.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    device = next(model.parameters()).device
    model.eval()
    matcher = StructureMatcher(stol=stol, angle_tol=angle_tol, ltol=ltol)
    matched_count = 0
    total_count = 0

    def get_valid_indices(vec, max_sites=MAX_SITES):
        comp = parse_dense_to_components_batch(
            torch.tensor(vec).unsqueeze(0).float(),
            max_sites=max_sites,
            num_species=NUM_SPECIES,
        )
        valid_mask = (comp["species"].sum(dim=-1) > 0).squeeze(0).cpu().numpy()
        return np.where(valid_mask > 0.5)[0]

    for i in range(len(dataset)):
        sample = dataset[i]
        mid = sample["material_id"]
        crystal_vec = sample["crystal_vec"].unsqueeze(0).to(device)
        heat_val = sample["heat_all"].item()
        dir_val = sample["dir_gap"].item()

        with torch.no_grad():
            zc, zp, lat_out, adj_logits, species_logits, coords_out, prop_out = model(
                crystal_vec,
                torch.tensor([heat_val], dtype=torch.float32, device=device),
                torch.tensor([dir_val], dtype=torch.float32, device=device),
            )

        recon_dense = combine_decoder_outputs(
            lat_out.squeeze(0),
            adj_logits.squeeze(0),
            species_logits.squeeze(0),
            coords_out.squeeze(0),
            tau=0.01,
        )

        cif_file = os.path.join(cif_root, mid + ".cif")
        if not os.path.isfile(cif_file):
            continue

        try:
            parser = CifParser(cif_file)
            orig_struct = parser.parse_structures(primitive=False)[0]
        except Exception as e:
            print(f"Skipping {mid}: error parsing original CIF: {e}")
            continue

        dense_vec = sample["crystal_vec"].numpy()
        valid_inds = get_valid_indices(dense_vec, max_sites=MAX_SITES)
        recon_struct = dense_to_structure(
            recon_dense,
            valid_indices=valid_inds,
            species_threshold=species_threshold,
        )

        total_count += 1
        if recon_struct is None:
            print(f"DEBUG: Mismatch for {mid}.cif (no valid species)")
            continue

        if matcher.fit(orig_struct, recon_struct):
            matched_count += 1
        else:
            orig_species = [str(s.specie) for s in orig_struct]
            recon_species = [str(s.specie) for s in recon_struct]
            print(f"DEBUG: Mismatch for {mid}.cif")
            print(f"Original species: {orig_species}")
            print(f"Reconstructed species: {recon_species}")

        out_filename = os.path.join(output_dir, f"{mid}_recon.cif")
        try:
            CifWriter(recon_struct).write_file(out_filename)
        except Exception as e:
            print(f"Error writing CIF for {mid}: {e}")

    accuracy = (matched_count / total_count) * 100 if total_count > 0 else 0.0
    print(f"Structure matching accuracy: {accuracy:.2f}% ({matched_count}/{total_count})")


################################
# 16) Main
################################
if __name__ == "__main__":
    # Paths to your data
    cif_root = "cif_files"
    csv_file = "train.csv"

    # Load dataset
    dataset = TripleModalityDataset(cif_root, csv_file)
    print("Dataset size:", len(dataset))

    # Model config
    latent_dim_struct = 128      # encoder output dim
    latent_dim_prop = 128        # property encoder output dim
    latent_dim_common = 128      # common latent space dim (used for decoding)
    species_embedding_dim = 64

    # Crystal encoder/decoder
    crystal_encoder = SE3Encoder(
        MAX_SITES,
        NUM_SPECIES,
        latent_dim_struct,
        node_hidden_dim=128,
        species_embedding_dim=species_embedding_dim,
    )
    # Decoder works in common latent space (here same dim = 128)
    crystal_decoder = SE3Decoder(
        MAX_SITES,
        NUM_SPECIES,
        latent_dim_common,
        node_hidden_dim=128,
        species_embedding_dim=species_embedding_dim,
    )

    # Property encoder/decoder
    property_encoder = PropertyEncoder(hidden_dim=128, latent_dim=latent_dim_prop)
    property_decoder = PropertyDecoder(latent_dim_common=latent_dim_common)

    # Dual model
    dual_autoencoder = DualAutoencoderModel(
        crystal_encoder,
        crystal_decoder,
        property_encoder,
        property_decoder,
        latent_dim_common=latent_dim_common,
        max_sites=MAX_SITES,
        num_species=NUM_SPECIES,
    )

    # Train with updated hyperparameters and logging
    train_dual_autoencoder(
        dual_autoencoder,
        dataset,
        epochs=2000,          # Adjust as needed
        batch_size=16,
        lr=1e-3,
        contrastive_weight=5.0,   # contrastive pressure
        temperature=0.01,          # sharp InfoNCE
        alpha_joint_recon=1.0,
        beta_joint_prop=1.0,
        gamma_prop_recon=0.5,
        delta_prop_prop=0.5,
    )

    # Evaluate latent alignment
    evaluate_latent_alignment(dual_autoencoder, dataset)

    # Plot regression for both properties
    plot_property_regression(
        dual_autoencoder,
        dataset,
        property_key="heat_all",
        save_path="heat_all_regression.png",
    )
    plot_property_regression(
        dual_autoencoder,
        dataset,
        property_key="dir_gap",
        save_path="dir_gap_regression.png",
    )

    # (Optional) Reconstruct a few specific examples
    example_ids = ["112", "1280", "1210", "15664", "17084"]
    dual_autoencoder.eval()
    device = next(dual_autoencoder.parameters()).device

    def get_valid_indices(vec, max_sites=MAX_SITES):
        comp = parse_dense_to_components_batch(
            torch.tensor(vec).unsqueeze(0).float(),
            max_sites=max_sites,
            num_species=NUM_SPECIES,
        )
        valid_mask = (comp["species"].sum(dim=-1) > 0).squeeze(0).cpu().numpy()
        return np.where(valid_mask > 0.5)[0]

    for mid in example_ids:
        cif_file = os.path.join(cif_root, mid + ".cif")
        if not os.path.isfile(cif_file):
            print(f"File {mid}.cif not found, skipping.")
            continue
        try:
            dense_vec = parse_cif_to_dense(cif_file, max_sites=MAX_SITES)
        except Exception as e:
            print(f"Error parsing {mid}.cif: {e}")
            continue
        if mid not in dataset.heat_dict or mid not in dataset.dir_dict:
            print(f"No heat_all or dir_gap value found for {mid}, skipping.")
            continue

        heat_val = dataset.heat_dict[mid]
        dir_val = dataset.dir_dict[mid]

        x = torch.from_numpy(dense_vec).unsqueeze(0).float().to(device)
        heat_tensor = torch.tensor([heat_val], dtype=torch.float32, device=device)
        dir_tensor = torch.tensor([dir_val], dtype=torch.float32, device=device)

        with torch.no_grad():
            # joint-latent reconstruction
            zc, zp, lat_out, adj_logits, species_logits, coords_out, prop_out = dual_autoencoder(
                x, heat_tensor, dir_tensor
            )
            recon_dense_joint = combine_decoder_outputs(
                lat_out.squeeze(0),
                adj_logits.squeeze(0),
                species_logits.squeeze(0),
                coords_out.squeeze(0),
                tau=0.01,
            )

            # property-only reconstruction
            zc_common, zp_common, z_joint, center, input_species, input_coords = dual_autoencoder.encode_modalities(
                x, heat_tensor, dir_tensor
            )
            lat_p, adj_p, species_p, coords_p = dual_autoencoder.crystal_decoder(
                zp_common,
                input_species=input_species,
                input_coords=input_coords,
                center=center,
            )
            recon_dense_prop = combine_decoder_outputs(
                lat_p.squeeze(0),
                adj_p.squeeze(0),
                species_p.squeeze(0),
                coords_p.squeeze(0),
                tau=0.01,
            )

        valid_inds = get_valid_indices(dense_vec, max_sites=MAX_SITES)
        recon_struct_joint = dense_to_structure(
            recon_dense_joint,
            valid_indices=valid_inds,
            species_threshold=0.5,
        )
        recon_struct_prop = dense_to_structure(
            recon_dense_prop,
            valid_indices=valid_inds,
            species_threshold=0.5,
        )

        if recon_struct_joint is not None:
            out_filename_joint = mid + "_joint_recon.cif"
            CifWriter(recon_struct_joint).write_file(out_filename_joint)
            print(f"[JOINT] Reconstructed CIF written to {out_filename_joint}")
        else:
            print(f"[JOINT] Reconstruction for {mid} did not yield valid species.")

        if recon_struct_prop is not None:
            out_filename_prop = mid + "_prop_recon.cif"
            CifWriter(recon_struct_prop).write_file(out_filename_prop)
            print(f"[PROP] Reconstructed CIF written to {out_filename_prop}")
        else:
            print(f"[PROP] Reconstruction for {mid} (property-only) did not yield valid species.")

        print(f"Material {mid}: Original heat_all = {heat_val:.4f}, Original dir_gap = {dir_val:.4f}")

    # Finally, evaluate structure matching for ALL dataset items
    evaluate_structure_matching_for_all(
        model=dual_autoencoder,
        dataset=dataset,
        cif_root=cif_root,
        output_dir="reconstructed_cifs_full",
        stol=0.5,
        angle_tol=10,
        ltol=0.3,
        species_threshold=0.5,
    )

    save_path = "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"
    torch.save(
        {
            "model_state_dict": dual_autoencoder.state_dict(),
            "latent_dim_struct": latent_dim_struct,
            "latent_dim_prop": latent_dim_prop,
            "latent_dim_common": latent_dim_common,
            "max_sites": MAX_SITES,
            "num_species": NUM_SPECIES,
            "species_embedding_dim": species_embedding_dim,
        },
        save_path,
    )
    print(f"Model checkpoint saved to {save_path}")

