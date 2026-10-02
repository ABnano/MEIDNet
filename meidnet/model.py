"""
The MEIDNet network: two encoders, two decoders and a shared latent space.

    crystal  ──SE3Encoder──► z_c ─┐                        ┌─► SE3Decoder   ──► crystal
                                  ├─ shared latent space ──┤
    properties ─PropertyEncoder─► z_p ─┘  (CLIP alignment)  └─► PropertyDecoder ─► properties

Both encoders project into the same space and are pulled together by a
contrastive (InfoNCE) loss, so a latent made from target *properties* can be
decoded into a *structure*.  Layer names, shapes and the order in which layers
are created are kept identical to MEIDNet v1, so published checkpoints load and
give bit-identical outputs; the only generalisation is that the property
modality may have any number of properties.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from meidnet.chem import NUM_SPECIES
from meidnet.data import split_dense


class EGNNLayer(nn.Module):
    """E(n)-equivariant message passing on squared inter-atomic distances (Satorras et al. 2021)."""

    def __init__(self, node_dim, edge_dim):
        super().__init__()
        self.phi_e = nn.Sequential(nn.Linear(2 * node_dim + 1, edge_dim), nn.ReLU(), nn.Linear(edge_dim, edge_dim))
        self.phi_x = nn.Sequential(nn.Linear(edge_dim, 1))
        self.phi_h = nn.Sequential(nn.Linear(node_dim + edge_dim, node_dim), nn.ReLU())

    def forward(self, h, x, adj):
        B, N, _ = h.shape
        diff = x.unsqueeze(2) - x.unsqueeze(1)
        dist2 = (diff ** 2).sum(dim=-1, keepdim=True)
        h_i = h.unsqueeze(2).expand(B, N, N, h.size(-1))
        h_j = h.unsqueeze(1).expand(B, N, N, h.size(-1))
        edge = self.phi_e(torch.cat([h_i, h_j, dist2], dim=-1))
        edge = edge * adj.unsqueeze(-1)
        x_new = x + (diff * self.phi_x(edge)).sum(dim=2)
        h_new = self.phi_h(torch.cat([h, edge.sum(dim=2)], dim=-1))
        return h_new, x_new


class SE3Encoder(nn.Module):
    """Crystal → latent.  Embeds elements, runs two EGNN layers, pools atoms, adds the lattice."""

    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64, edge_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.num_species = num_species
        self.species_embedding = nn.Linear(num_species, species_embedding_dim)
        self.init_node_fc = nn.Sequential(nn.Linear(species_embedding_dim, node_hidden_dim), nn.ReLU())
        self.egnn1 = EGNNLayer(node_hidden_dim, edge_dim)
        self.egnn2 = EGNNLayer(node_hidden_dim, edge_dim)
        self.aggregate_fc = nn.Sequential(nn.Linear(node_hidden_dim, 128), nn.ReLU())
        self.lat_fc = nn.Sequential(nn.Linear(6, 64), nn.ReLU())
        self.comb_fc = nn.Sequential(nn.Linear(64 + 128, 128), nn.ReLU())
        self.fc_mu = nn.Linear(128, latent_dim)

    def forward(self, x):
        comp = split_dense(x, self.max_sites)
        lat, adj, species, coords = comp["lat"], comp["adj"], comp["species"], comp["coords"]
        lat_emb = self.lat_fc(lat)
        h = self.init_node_fc(self.species_embedding(species))
        mask = (species.sum(dim=-1) > 0).float().unsqueeze(-1)
        center = (coords * mask).sum(dim=1) / (mask.sum(dim=1) + 1e-8)
        h, xc = self.egnn1(h, coords - center.unsqueeze(1), adj)
        h, xc = self.egnn2(h, xc, adj)
        h = h * mask
        agg = self.aggregate_fc(h.sum(dim=1) / (mask.sum(dim=1).clamp(min=1)))
        z = self.fc_mu(self.comb_fc(torch.cat([lat_emb, agg], dim=-1)))
        return z, center


class SE3Decoder(nn.Module):
    """Latent → lattice, per-site element scores, positions and adjacency."""

    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, edge_dim=64):
        super().__init__()
        self.max_sites = max_sites
        self.num_species = num_species
        self.fc_lat = nn.Sequential(nn.Linear(latent_dim, 64), nn.ReLU(), nn.Linear(64, 6))
        self.fc_nodes = nn.Sequential(nn.Linear(latent_dim, max_sites * node_hidden_dim), nn.ReLU())
        self.egnn1 = EGNNLayer(node_hidden_dim, edge_dim)
        self.egnn2 = EGNNLayer(node_hidden_dim, edge_dim)
        self.fc_species_decoded = nn.Sequential(nn.Linear(node_hidden_dim, 64), nn.ReLU())
        self.fc_species_final = nn.Linear(64, num_species)
        self.fc_coords = nn.Sequential(nn.Linear(node_hidden_dim, 3))

    def forward(self, z, input_coords=None, center=None, species_mask=None):
        B, N = z.size(0), self.max_sites
        lat_out = self.fc_lat(z)
        nodes = self.fc_nodes(z).view(B, N, -1)
        if input_coords is None:
            input_coords = torch.zeros(B, N, 3, device=z.device)
        if center is None:
            center = torch.zeros(B, 3, device=z.device)
        full_adj = torch.ones(B, N, N, device=z.device)
        h, xc = self.egnn1(nodes, input_coords - center.unsqueeze(1), full_adj)
        h, xc = self.egnn2(h, xc, full_adj)
        species_logits = self.fc_species_final(self.fc_species_decoded(h))
        if species_mask is not None:
            keep = species_mask.to(dtype=torch.bool, device=species_logits.device).unsqueeze(0)
            species_logits = species_logits.masked_fill(~keep, torch.finfo(species_logits.dtype).min)
        coords_out = self.fc_coords(h) + center.unsqueeze(1)
        adj_logits = torch.bmm(h, h.transpose(1, 2))
        return lat_out, adj_logits, species_logits, coords_out


class PropertyEncoder(nn.Module):
    """Property vector (normalised, in model column order) → latent."""

    def __init__(self, n_properties=2, hidden_dim=128, latent_dim=128):
        super().__init__()
        self.fc = nn.Sequential(nn.Linear(n_properties, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, latent_dim))

    def forward(self, x):
        return self.fc(x)


class PropertyDecoder(nn.Module):
    """Latent → property vector (normalised, in model column order)."""

    def __init__(self, latent_dim=128, n_properties=2):
        super().__init__()
        self.fc = nn.Sequential(nn.Linear(latent_dim, 64), nn.ReLU(), nn.Linear(64, n_properties))

    def forward(self, z):
        return self.fc(z)


class DualAutoencoderModel(nn.Module):
    def __init__(self, n_properties=2, max_sites=20, latent_dim=128, node_hidden_dim=128,
                 species_embedding_dim=64, edge_dim=64, property_hidden_dim=128):
        super().__init__()
        self.max_sites = max_sites
        self.num_species = NUM_SPECIES
        self.n_properties = n_properties
        self.latent_dim = latent_dim
        # creation order matters for reproducible initialisation (same as v1)
        self.crystal_encoder = SE3Encoder(max_sites, NUM_SPECIES, latent_dim, node_hidden_dim,
                                          species_embedding_dim, edge_dim)
        self.crystal_decoder = SE3Decoder(max_sites, NUM_SPECIES, latent_dim, node_hidden_dim, edge_dim)
        self.property_encoder = PropertyEncoder(n_properties, property_hidden_dim, latent_dim)
        self.property_decoder = PropertyDecoder(latent_dim, n_properties)
        self.proj_crystal = nn.Sequential(nn.Linear(latent_dim, latent_dim), nn.ReLU(), nn.Linear(latent_dim, latent_dim))
        self.proj_prop = nn.Sequential(nn.Linear(latent_dim, latent_dim), nn.ReLU(), nn.Linear(latent_dim, latent_dim))

    # ── encoders ─────────────────────────────────────────────────────────────
    def encode_crystal(self, crystal_vec):
        z_raw, center = self.crystal_encoder(crystal_vec)
        return F.normalize(self.proj_crystal(F.normalize(z_raw, p=2, dim=1)), p=2, dim=1), center

    def encode_properties(self, props):
        return F.normalize(self.proj_prop(F.normalize(self.property_encoder(props), p=2, dim=1)), p=2, dim=1)

    def encode_modalities(self, crystal_vec, props):
        """Returns z_c, z_p, z_joint = (z_c + z_p)/2, the encoder's centre, input species and coordinates."""
        z_c, center = self.encode_crystal(crystal_vec)
        z_p = self.encode_properties(props)
        z_joint = (z_c + z_p) / 2.0
        comp = split_dense(crystal_vec, self.max_sites)
        return z_c, z_p, z_joint, center, comp["species"], comp["coords"]

    def forward(self, crystal_vec, props, coords=None, center=None):
        """Training forward pass: decode crystal and properties from the joint latent."""
        z_c, z_p, z_joint, enc_center, _, data_coords = self.encode_modalities(crystal_vec, props)
        lat, adj, spc, crd = self.crystal_decoder(
            z_joint,
            input_coords=data_coords if coords is None else coords,
            center=enc_center if center is None else center,
        )
        return z_c, z_p, lat, adj, spc, crd, self.property_decoder(z_joint)
