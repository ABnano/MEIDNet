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
    vec = np.zeros(NUM_SPECIES, dtype=np.float32)
    if sym not in SPECIES_LIST:
        raise ValueError(f"Element {sym} not recognized among the known {NUM_SPECIES} elements.")
    idx = SPECIES_LIST.index(sym)
    vec[idx] = 1.0
    return vec

def scale_lattice_params(a, b, c, alpha, beta, gamma):
    return np.array([a/20.0, b/20.0, c/20.0, alpha/180.0, beta/180.0, gamma/180.0], dtype=np.float32)

def unscale_lattice_params(lat_vec):
    a = lat_vec[0]*20.0; b = lat_vec[1]*20.0; c = lat_vec[2]*20.0
    alpha = lat_vec[3]*180.0; beta = lat_vec[4]*180.0; gamma = lat_vec[5]*180.0
    return a, b, c, alpha, beta, gamma

################################
# 2) Dense Representation Parsing from CIF
################################
def parse_cif_to_dense(cif_path, max_sites=MAX_SITES, cutoff=CUTOFF):
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

    full_vec = np.concatenate([
        lat_array.flatten(),
        adj.flatten(),
        species_mat.flatten(),
        coords_mat.flatten()
    ], axis=0)
    return full_vec

def parse_dense_to_components_batch(x, max_sites=MAX_SITES, num_species=NUM_SPECIES):
    B = x.size(0)
    offset = 0
    lat = x[:, offset:offset+6]
    offset += 6

    adj_sz = max_sites * max_sites
    adj = x[:, offset:offset+adj_sz].view(B, max_sites, max_sites)
    offset += adj_sz

    spc_sz = max_sites * num_species
    species = x[:, offset:offset+spc_sz].view(B, max_sites, num_species)
    offset += spc_sz

    coords = x[:, offset:offset+max_sites*3].view(B, max_sites, 3)
    return {"lat": lat, "adj": adj, "species": species, "coords": coords}

################################
# 3) TripleModalityDataset (same as before)
################################
class TripleModalityDataset(Dataset):
    def __init__(self, cif_root, csv_file):
        super().__init__()
        self.samples = []
        self.heat_dict = {}
        self.dir_dict = {}

        df = pd.read_csv(csv_file)
        if "heat_all" not in df.columns or "dir_gap" not in df.columns:
            raise KeyError("CSV must contain columns 'heat_all' and 'dir_gap'.")

        for _, row in df.iterrows():
            try:
                mid = str(int(row["material_id"]))
            except:
                mid = str(row["material_id"]).strip()
            self.heat_dict[mid] = float(row["heat_all"])
            self.dir_dict[mid] = float(row["dir_gap"])

        files = [f for f in os.listdir(cif_root) if f.endswith(".cif")]
        for fname in files:
            try:
                mid_file = str(int(os.path.splitext(fname)[0]))
            except:
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
            "material_id": mid
        }

################################
# 4) SE(3)-Equivariant Encoder & Decoder (as before)
################################
class EGNNLayer(nn.Module):
    def __init__(self, node_dim, edge_dim):
        super().__init__()
        self.phi_e = nn.Sequential(
            nn.Linear(2*node_dim + 1, edge_dim),
            nn.ReLU(),
            nn.Linear(edge_dim, edge_dim)
        )
        self.phi_x = nn.Sequential(
            nn.Linear(edge_dim, 1)
        )
        self.phi_h = nn.Sequential(
            nn.Linear(node_dim + edge_dim, node_dim),
            nn.ReLU()
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
    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.num_species = num_species

        self.species_embedding = nn.Linear(num_species, species_embedding_dim)
        self.init_node_fc = nn.Sequential(
            nn.Linear(species_embedding_dim, node_hidden_dim),
            nn.ReLU()
        )
        self.egnn1 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)
        self.egnn2 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)

        self.aggregate_fc = nn.Sequential(
            nn.Linear(node_hidden_dim, 128),
            nn.ReLU()
        )
        self.lat_fc = nn.Sequential(
            nn.Linear(6, 64),
            nn.ReLU()
        )
        self.comb_fc = nn.Sequential(
            nn.Linear(64+128, 128),
            nn.ReLU()
        )
        self.fc_mu = nn.Linear(128, latent_dim)

    def forward(self, x):
        comp = parse_dense_to_components_batch(x, max_sites=self.max_sites, num_species=self.num_species)
        lat = comp["lat"]       # (B, 6)
        adj = comp["adj"]       # (B, N, N)
        species = comp["species"]  # (B, N, num_species)
        coords = comp["coords"] # (B, N, 3)

        B, N, _ = coords.shape

        lat_emb = self.lat_fc(lat)  # (B, 64)

        # embed species
        h = self.species_embedding(species)  # (B, N, species_embedding_dim)
        h = self.init_node_fc(h)             # (B, N, node_hidden_dim)

        # mask for padded sites
        mask = (species.sum(dim=-1) > 0).float().unsqueeze(-1)  # (B, N, 1)
        center = (coords * mask).sum(dim=1) / (mask.sum(dim=1) + 1e-8)  # (B, 3)
        coords_centered = coords - center.unsqueeze(1)  # (B, N, 3)

        # EGNN layers
        h, x_coords = self.egnn1(h, coords_centered, adj, lattice=None)
        h, x_coords = self.egnn2(h, x_coords, adj, lattice=None)

        # re-apply mask to ignore padded sites
        h = h * mask

        # aggregate
        agg_node = h.sum(dim=1) / (mask.sum(dim=1).clamp(min=1))
        agg_emb = self.aggregate_fc(agg_node)  # (B, 128)

        combined = torch.cat([lat_emb, agg_emb], dim=-1)  # (B, 64+128)
        combined = self.comb_fc(combined)                 # (B, 128)
        z = self.fc_mu(combined)                          # (B, latent_dim)

        return z, center

class SE3Decoder(nn.Module):
    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.num_species = num_species

        self.fc_lat = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 6)
        )
        self.fc_nodes = nn.Sequential(
            nn.Linear(latent_dim, max_sites*node_hidden_dim),
            nn.ReLU()
        )

        self.egnn1 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)
        self.egnn2 = EGNNLayer(node_dim=node_hidden_dim, edge_dim=64)

        self.fc_species_decoded = nn.Sequential(
            nn.Linear(node_hidden_dim, 64),
            nn.ReLU()
        )
        self.fc_species_final = nn.Linear(64, num_species)

        self.fc_coords = nn.Sequential(
            nn.Linear(node_hidden_dim, 3)
        )

    def forward(self, z, input_species=None, input_coords=None, center=None):
        B = z.size(0)
        N = self.max_sites

        lat_out = self.fc_lat(z)  # (B, 6)

        # Expand node features from z
        nodes = self.fc_nodes(z).view(B, N, -1)  # (B, N, node_hidden_dim)

        # If no coords provided, default to zeros
        if input_coords is None:
            input_coords = torch.zeros(B, N, 3, device=z.device)

        relative_input = input_coords - center.unsqueeze(1)  # (B, N, 3)

        # For decoding, we assume a fully connected adjacency
        full_adj = torch.ones(B, N, N, device=z.device)

        nodes, x_coords = self.egnn1(nodes, relative_input, full_adj, lattice=None)
        nodes, x_coords = self.egnn2(nodes, x_coords, full_adj, lattice=None)

        species_decoded = self.fc_species_decoded(nodes)
        species_logits = self.fc_species_final(species_decoded)  # (B, N, num_species)

        coords_out = self.fc_coords(nodes)  # (B, N, 3)
        coords_out = coords_out + center.unsqueeze(1)

        # adjacency logits (node-wise dot product)
        adj_logits = torch.bmm(nodes, nodes.transpose(1,2))

        return lat_out, adj_logits, species_logits, coords_out

################################
# 5) Graph Autoencoder (crystal modality)
################################
class GraphAutoencoderHybridSE3(nn.Module):
    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.encoder = SE3Encoder(max_sites, num_species, latent_dim, node_hidden_dim, species_embedding_dim)
        self.decoder = SE3Decoder(max_sites, num_species, latent_dim, node_hidden_dim, species_embedding_dim)

    def forward(self, x):
        z, center = self.encoder(x)
        B = x.size(0)
        N = self.max_sites
        species_offset = 6 + N*N
        species_len = N * NUM_SPECIES
        coords_offset = species_offset + species_len
        coords_len = N * 3

        input_species = x[:, species_offset:species_offset+species_len].view(B, N, NUM_SPECIES)
        input_coords = x[:, coords_offset:coords_offset+coords_len].view(B, N, 3)
        outputs = self.decoder(z, input_species=input_species, input_coords=input_coords, center=center)
        return outputs, z

    def encode(self, x):
        return self.encoder(x)

################################
# 6) Early Fusion of Scalar Properties: Property Encoder & Decoder
################################
class PropertyEncoder(nn.Module):
    def __init__(self, hidden_dim=128, latent_dim=128):
        super().__init__()
        # Input dimension is 2 (heat_all and dir_gap)
        self.fc = nn.Sequential(
            nn.Linear(2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim)
        )
    def forward(self, x):
        return self.fc(x)

class PropertyDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 2)  # Reconstruct two scalars: heat_all and dir_gap
        )
    def forward(self, z):
        return self.fc(z)

################################
# 7) Dual Autoencoder Model with Early Fusion (CLIP-style)
################################
class DualAutoencoderModelCLIP_EarlyFusion(nn.Module):
    def __init__(self, crystal_encoder, crystal_decoder, property_encoder, property_decoder,
                 latent_dim_common, max_sites, num_species):
        super().__init__()
        self.crystal_encoder = crystal_encoder    # returns (z, center)
        self.crystal_decoder = crystal_decoder    # decodes crystal modality
        self.property_encoder = property_encoder  # fuses [heat_all, dir_gap] into z_prop
        self.property_decoder = property_decoder  # decodes properties from latent
        
        # Projection heads to common latent space for each modality
        self.proj_crystal = nn.Sequential(
            nn.Linear(128, latent_dim_common),
            nn.ReLU(),
            nn.Linear(latent_dim_common, latent_dim_common)
        )
        self.proj_prop = nn.Sequential(
            nn.Linear(128, latent_dim_common),
            nn.ReLU(),
            nn.Linear(latent_dim_common, latent_dim_common)
        )
        self.max_sites = max_sites
        self.num_species = num_species

    def forward(self, crystal_vec, heat_all, dir_gap):
        # Crystal branch
        z_crystal, center = self.crystal_encoder(crystal_vec)
        # Fuse property scalars (concatenate heat_all and dir_gap)
        prop = torch.cat([heat_all.unsqueeze(1), dir_gap.unsqueeze(1)], dim=1)  # shape: (B,2)
        z_prop = self.property_encoder(prop)
        
        # L2 normalize and project to common latent space
        z_crystal = F.normalize(z_crystal, p=2, dim=1)
        z_prop = F.normalize(z_prop, p=2, dim=1)
        proj_z_crystal = F.normalize(self.proj_crystal(z_crystal), p=2, dim=1)
        proj_z_prop = F.normalize(self.proj_prop(z_prop), p=2, dim=1)
        
        # Joint latent: average of the two modalities
        z_joint = (proj_z_crystal + proj_z_prop) / 2.0
        
        # Decode crystal modality
        B = crystal_vec.size(0)
        N = self.max_sites
        species_offset = 6 + N * N
        species_len = N * self.num_species
        coords_offset = species_offset + species_len
        coords_len = N * 3
        input_species = crystal_vec[:, species_offset:species_offset+species_len].view(B, N, self.num_species)
        input_coords = crystal_vec[:, coords_offset:coords_offset+coords_len].view(B, N, 3)
        lat_out, adj_logits, species_logits, coords_out = self.crystal_decoder(
            z_joint, input_species=input_species, input_coords=input_coords, center=center
        )
        
        # Decode property modality
        prop_out = self.property_decoder(z_joint)  # outputs a 2D vector [heat_all, dir_gap]
        
        return z_crystal, z_prop, lat_out, adj_logits, species_logits, coords_out, prop_out

    def encode(self, crystal_vec, heat_all, dir_gap):
        z_crystal, _ = self.crystal_encoder(crystal_vec)
        prop = torch.cat([heat_all.unsqueeze(1), dir_gap.unsqueeze(1)], dim=1)
        z_prop = self.property_encoder(prop)
        return z_crystal, z_prop

################################
# 8) combine_decoder_outputs (same as before)
################################
def combine_decoder_outputs(lat, adj_logits, species_logits, coords, tau=0.01):
    adj_prob = torch.sigmoid(adj_logits)
    species_one_hot = F.gumbel_softmax(species_logits, tau=tau, hard=True, dim=-1)
    full_vec = torch.cat([
        lat.view(-1),
        adj_prob.view(-1),
        species_one_hot.view(-1),
        coords.view(-1)
    ], dim=0)
    return full_vec.cpu().detach().numpy()

################################
# 9) Reconstruction Loss (crystal modality, same as before)
################################
def reconstruction_loss(crystal_vec, lat_out, adj_logits, species_logits, coords_out,
                        max_sites=MAX_SITES, num_species=NUM_SPECIES):
    B = crystal_vec.size(0)
    target_lat = crystal_vec[:, :6]
    target_adj = crystal_vec[:, 6:6+max_sites*max_sites].view(B, max_sites, max_sites)
    target_species = crystal_vec[:, 6+max_sites*max_sites : 6+max_sites*max_sites+max_sites*num_species].view(B, max_sites, num_species)
    target_coords = crystal_vec[:, 6+max_sites*max_sites+max_sites*num_species:].view(B, max_sites, 3)
    loss_lat = F.mse_loss(lat_out, target_lat)
    loss_adj = F.binary_cross_entropy_with_logits(adj_logits, target_adj)
    target_species_idx = target_species.argmax(dim=-1)
    loss_species = F.cross_entropy(species_logits.view(-1, num_species), target_species_idx.view(-1))
    loss_coords = F.mse_loss(coords_out, target_coords)
    return loss_lat + loss_adj + loss_species + loss_coords

################################
# 10) Contrastive Loss between two modalities
################################
def contrastive_loss(z1, z2, temperature=0.01):
    logits = torch.matmul(z1, z2.t()) / temperature
    labels = torch.arange(z1.size(0), device=z1.device)
    loss1 = F.cross_entropy(logits, labels)
    loss2 = F.cross_entropy(logits.t(), labels)
    return 0.5 * (loss1 + loss2)

################################
# 11) Train Dual Autoencoder with Early Fusion (with logging)
################################
def train_dual_autoencoder(model, dataset, epochs=5, batch_size=16, lr=1e-3,
                           contrastive_weight=5.0, temperature=0.01):
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for ep in range(1, epochs+1):
        model.train()
        total_loss = 0.0
        total_loss_prop = 0.0
        total_loss_recon = 0.0
        total_loss_contrast = 0.0

        total_cos_sim = 0.0
        total_l2 = 0.0
        cnt = 0

        for batch in loader:
            crystal_vec = batch["crystal_vec"].to(device)
            heat_all = batch["heat_all"].to(device)
            dir_gap = batch["dir_gap"].to(device)

            zc, zp, lat_out, adj_logits, species_logits, coords_out, prop_out = model(crystal_vec, heat_all, dir_gap)
            # Reconstruction loss for crystal modality
            loss_recon = reconstruction_loss(crystal_vec, lat_out, adj_logits, species_logits, coords_out,
                                             max_sites=MAX_SITES, num_species=NUM_SPECIES)
            # Property loss: MSE for both scalars (fused into a 2D vector)
            true_prop = torch.cat([heat_all.unsqueeze(1), dir_gap.unsqueeze(1)], dim=1)
            loss_prop = F.mse_loss(prop_out, true_prop)
            # Contrastive loss aligning zc and zp
            loss_contrast = contrastive_loss(zc, zp, temperature=temperature)
            loss = loss_recon + loss_prop + contrastive_weight * loss_contrast

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            total_loss_recon += loss_recon.item()
            total_loss_prop += loss_prop.item()
            total_loss_contrast += loss_contrast.item()

            # Compute cosine similarity and L2 distance between zc and zp
            cos_sim = torch.mean(torch.sum(zc * zp, dim=1)).item()
            l2_dist = torch.mean(torch.norm(zc - zp, dim=1)).item()
            total_cos_sim += cos_sim
            total_l2 += l2_dist

            cnt += 1

        print(f"Epoch {ep}/{epochs} | Total Loss={total_loss/cnt:.4f} | Recon Loss={total_loss_recon/cnt:.4f} | Prop Loss={total_loss_prop/cnt:.4f} | Contrast Loss={total_loss_contrast/cnt:.4f}")
        print(f"   Avg Cosine Similarity (crystal vs. prop): {total_cos_sim/cnt:.4f} | Avg L2 Distance: {total_l2/cnt:.4f}")

################################
# 12) dense_to_structure (same as before)
################################
def dense_to_structure(dense_vec, valid_indices=None, species_threshold=0.5):
    lat = dense_vec[:6]
    a, b, c, alpha, beta, gamma = unscale_lattice_params(lat)
    offset = 6 + MAX_SITES*MAX_SITES
    spc_sz = MAX_SITES * NUM_SPECIES
    species_flat = dense_vec[offset:offset+spc_sz]
    offset += spc_sz
    species_mat = species_flat.reshape(MAX_SITES, NUM_SPECIES)
    coords_flat = dense_vec[offset:offset+MAX_SITES*3]
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
    print(f"Average cosine similarity (crystal vs. fused property): {np.mean(cosine_sims):.4f}")
    print(f"Average L2 distance (crystal vs. fused property): {np.mean(l2_dists):.4f}")

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
                pred = prop_out[:,0]
                gt = heat_all
            elif property_key == "dir_gap":
                pred = prop_out[:,1]
                gt = dir_gap
            else:
                raise ValueError("Unknown property key")
            gt_list.extend(gt.cpu().numpy())
            pred_list.extend(pred.cpu().numpy())
    plt.figure()
    plt.scatter(gt_list, pred_list, alpha=0.5, label="Data points")
    low = min(min(gt_list), min(pred_list))
    high = max(max(gt_list), max(pred_list))
    plt.plot([low, high], [low, high], 'r--', label="Ideal (y=x)")
    plt.xlabel(f"Ground Truth {property_key}")
    plt.ylabel(f"Predicted {property_key}")
    plt.title(f"Regression Plot: Ground Truth vs Predicted {property_key}")
    plt.legend()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Regression plot saved to {save_path}")

################################
# 15) Evaluate Structure Matching for ALL (same as before)
################################
def evaluate_structure_matching_for_all(model, dataset, cif_root, output_dir="reconstructed_cifs_full",
                                          stol=0.5, angle_tol=10, ltol=0.3, species_threshold=0.5):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    device = next(model.parameters()).device
    model.eval()
    matcher = StructureMatcher(stol=stol, angle_tol=angle_tol, ltol=ltol)
    matched_count = 0
    total_count = 0
    for i in range(len(dataset)):
        sample = dataset[i]
        mid = sample["material_id"]
        crystal_vec = sample["crystal_vec"].unsqueeze(0).to(device)
        heat_val = sample["heat_all"].item()
        dir_val = sample["dir_gap"].item()
        with torch.no_grad():
            _, _, lat_out, adj_logits, species_logits, coords_out, prop_out = model(crystal_vec,
                                                                                     torch.tensor([heat_val], device=device),
                                                                                     torch.tensor([dir_val], device=device))
        recon_dense = combine_decoder_outputs(lat_out.squeeze(0), adj_logits.squeeze(0),
                                               species_logits.squeeze(0), coords_out.squeeze(0), tau=0.01)
        cif_file = os.path.join(cif_root, mid + ".cif")
        if not os.path.isfile(cif_file):
            continue
        try:
            parser = CifParser(cif_file)
            orig_struct = parser.parse_structures(primitive=False)[0]
        except Exception as e:
            print(f"Skipping {mid}: error parsing original CIF: {e}")
            continue
        def get_valid_indices(vec, max_sites=MAX_SITES):
            comp = parse_dense_to_components_batch(torch.tensor(vec).unsqueeze(0).float(),
                                                    max_sites=max_sites, num_species=NUM_SPECIES)
            valid_mask = (comp["species"].sum(dim=-1) > 0).squeeze(0).cpu().numpy()
            return np.where(valid_mask > 0.5)[0]
        dense_vec = sample["crystal_vec"].numpy()
        valid_inds = get_valid_indices(dense_vec, max_sites=MAX_SITES)
        recon_struct = dense_to_structure(recon_dense, valid_indices=valid_inds, species_threshold=species_threshold)
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
    latent_dim = 128
    common_dim = 128
    species_embedding_dim = 64
    crystal_encoder = SE3Encoder(MAX_SITES, NUM_SPECIES, latent_dim,
                                 node_hidden_dim=128, species_embedding_dim=species_embedding_dim)
    crystal_decoder = SE3Decoder(MAX_SITES, NUM_SPECIES, latent_dim,
                                 node_hidden_dim=128, species_embedding_dim=species_embedding_dim)
    property_encoder = PropertyEncoder(hidden_dim=128, latent_dim=latent_dim)
    property_decoder = PropertyDecoder()
    dual_autoencoder = DualAutoencoderModelCLIP_EarlyFusion(
        crystal_encoder, crystal_decoder, property_encoder, property_decoder,
        latent_dim_common=common_dim, max_sites=MAX_SITES, num_species=NUM_SPECIES
    )
    # Train with updated hyperparameters and logging
    train_dual_autoencoder(
        dual_autoencoder, dataset,
        epochs=2500,          # Adjust as needed
        batch_size=16, lr=1e-3,
        contrastive_weight=5.0,   # Increased contrastive weight
        temperature=0.01          # Lowered contrastive temperature
    )
    # Evaluate latent alignment
    evaluate_latent_alignment(dual_autoencoder, dataset)
    # Plot regression for both properties
    plot_property_regression(dual_autoencoder, dataset, property_key="heat_all", save_path="heat_all_regression.png")
    plot_property_regression(dual_autoencoder, dataset, property_key="dir_gap", save_path="dir_gap_regression.png")
    # (Optional) Reconstruct a few specific examples
    example_ids = ["112", "1280", "1210", "15664", "17084"]
    dual_autoencoder.eval()
    device = next(dual_autoencoder.parameters()).device
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
            zc, zp, lat_out, adj_logits, species_logits, coords_out, prop_out = dual_autoencoder(x, heat_tensor, dir_tensor)
        def get_valid_indices(vec, max_sites=MAX_SITES):
            comp = parse_dense_to_components_batch(torch.tensor(vec).unsqueeze(0).float(), max_sites=max_sites, num_species=NUM_SPECIES)
            valid_mask = (comp["species"].sum(dim=-1) > 0).squeeze(0).cpu().numpy()
            return np.where(valid_mask > 0.5)[0]
        valid_inds = get_valid_indices(dense_vec, max_sites=MAX_SITES)
        recon_dense = combine_decoder_outputs(lat_out.squeeze(0), adj_logits.squeeze(0), species_logits.squeeze(0), coords_out.squeeze(0), tau=0.01)
        recon_struct = dense_to_structure(recon_dense, valid_indices=valid_inds, species_threshold=0.5)
        if recon_struct is None:
            print(f"Skipping {mid}: Reconstruction did not yield valid species.")
            continue
        out_filename = mid + "_recon.cif"
        CifWriter(recon_struct).write_file(out_filename)
        print(f"Structure match for material {mid}: (Not checked here)")
        print(f"Reconstructed CIF written to {out_filename}")
        print(f"Material {mid}: Original heat_all = {heat_val:.4f}, Original dir_gap = {dir_val:.4f}")
    # Finally, evaluate structure matching for ALL dataset items
    evaluate_structure_matching_for_all(
        model=dual_autoencoder, dataset=dataset, cif_root=cif_root,
        output_dir="reconstructed_cifs_full", stol=0.5, angle_tol=10, ltol=0.3, species_threshold=0.5
    )

