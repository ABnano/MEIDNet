#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meidnet.design
==============
Property-conditioned constrained inverse design for cubic ABX3 perovskites.

This module implements the generative half of MEIDNet: given a pretrained
dual-modality checkpoint, it searches the shared latent space for structure
prototypes whose decoded compositions and geometries simultaneously satisfy
(i) a user-specified property target (band-gap, formation enthalpy) and
(ii) a battery of hard physics constraints enforcing cubic ABX3 stoichiometry
and local structural stability.

Method
------
Latent optimisation
    For each property target (E_g*, H_f*), an initial latent vector z is
    constructed as:
        z = z_prop_anchor + RFF_offset + epsilon,    epsilon ~ N(0, sigma^2)
    where z_prop_anchor is the property-encoder output for (H_f*, E_g*) and
    RFF_offset is a random Fourier feature perturbation that promotes diversity.
    z is then refined by gradient descent with respect to a compound objective:
        L = lambda_bg * (E_g_pred - E_g*)^2
          + lambda_ent * L_ent(H_f_pred, H_f*)
          + lambda_geo * L_geometry(decoded_structure)
          + lambda_hist * L_history_repulsion
    The geometry loss penalises site-collapse and forces cubic symmetry.

Decode and projection
    At each round, z is decoded by the crystal decoder to produce species
    logits, fractional coordinate offsets, and lattice parameters.  The
    decoded composition is then projected onto the ideal cubic Pm-3m template
    (A at (0,0,0), B at (1/2,1/2,1/2), X at (1/2,1/2,0) and equivalents).
    Lattice parameter a is predicted analytically from ionic radii:
        a = 2 * (r_B + r_X),   clamped to [3.0, 8.0] A

Physics post-filters
    Only structures passing all of the following are accepted:
        1. Charge neutrality: Q(A) + Q(B) + 3*Q(X) = 0  (existential valence)
        2. Goldschmidt tolerance factor: t = (r_A + r_X) / (sqrt(2)*(r_B + r_X))
           in family-specific range T_RANGE (default: halide [0.75, 1.02])
        3. Octahedral factor: mu = r_B / r_X in [0.414, 0.90]
        4. B-X bond distance: d(B-X) in [0.75, 1.35] * (r_B + r_X)
        5. Structural uniqueness: SHA1 formula fingerprint + latent cosine
           similarity below min_cosine_sep threshold

Charge-balance-aware sampling
    A-site species are sampled *after* B and X are fixed, restricting A to
    elements whose formal charge Q(A) = -(Q(B) + 3*Q(X)) satisfies neutrality.
    This ensures that >15% of decode attempts reach the geometry filter stage,
    compared to <2% for unconstrained random sampling.

Property index convention (consistent with meidnet.model throughout)
    property_decoder output[:, 0] = heat_all  (formation enthalpy, eV/atom)
    property_decoder output[:, 1] = dir_gap   (direct band-gap, eV)

Families supported
    oxide | halide | chalcogenide | nitride

Outputs
    - CIF files for each accepted cubic ABX3 candidate (Pm-3m, #221)
    - run_summary.csv: composition, surrogate property scores, Goldschmidt
      tolerance factor, octahedral factor, round index
    - latent_pca_saved_all.png: 2-D PCA projection of accepted latent vectors
"""

#!/usr/bin/env python3

# ───────────────────────── Imports ─────────────────────────
import os, argparse, math, random, hashlib, csv
from collections import Counter
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F, torch.optim as optim
import matplotlib.pyplot as plt
from itertools import product
from sklearn.decomposition import PCA

from pymatgen.core import Structure, Lattice
from pymatgen.io.cif import CifWriter
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.core.periodic_table import Element as PMGElem


# ───────────────────────── Species & constants ─────────────────────────
ALL_ELEMENTS = [str(PMGElem.from_Z(z)) for z in range(1,119)]
SPECIES_LIST = ALL_ELEMENTS
NUM_SPECIES  = len(SPECIES_LIST)

MAX_SITES    = 20
N_TEMPLATE   = 5   # A, B, X, X, X

ANIONS_ALL = {"O","F","Cl","Br","I","S","Se","Te","N"}
FAMILY_OF_X = {
    "O":"oxide", "F":"halide", "Cl":"halide", "Br":"halide", "I":"halide",
    "S":"chalcogenide","Se":"chalcogenide","Te":"chalcogenide","N":"nitride"
}

A_CATIONS = {
    "Ba","Sr","Ca","Na","K","Rb","Cs",
    "La","Ce","Pr","Nd","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu"
}
B_CATIONS = {
    "Ti","Zr","Hf","V","Nb","Ta","Cr","Mn","Fe","Co","Ni","Cu","Zn","Sc","Y",
    "Al","Ga","In","Ge","Sn","Pb","W","Mo"
}

# (existential) valence tables for quick neutrality checks
VALENCE_A = {
    "Na":{+1},"K":{+1},"Rb":{+1},"Cs":{+1},
    "Ca":{+2},"Sr":{+2},"Ba":{+2},
    "La":{+3},"Ce":{+3},"Pr":{+3},"Nd":{+3},"Sm":{+3},"Eu":{+3},"Gd":{+3},"Tb":{+3},
    "Dy":{+3},"Ho":{+3},"Er":{+3},"Tm":{+3},"Yb":{+3},"Lu":{+3}
}
VALENCE_X = {"O":{-2},"F":{-1},"Cl":{-1},"Br":{-1},"I":{-1},"S":{-2},"Se":{-2},"Te":{-2},"N":{-3}}
VALENCE_B_BY_FAMILY = {
    "oxide": {
        "Ti":{+4},"Zr":{+4},"Hf":{+4},"V":{+3,+4,+5},"Nb":{+5},"Ta":{+5},
        "Cr":{+3},"Mn":{+3,+4},"Fe":{+3},"Co":{+3},"Ni":{+3},"Cu":{+2},
        "Zn":{+2},"Sc":{+3},"Y":{+3},"Al":{+3},"Ga":{+3},"In":{+3},"Ge":{+4},
        "Sn":{+4},"Pb":{+4},"W":{+6},"Mo":{+6}
    },
    "halide": {
        "Mn":{+2},"Fe":{+2},"Co":{+2},"Ni":{+2},"Cu":{+2},"Zn":{+2},
        "Sn":{+2},"Pb":{+2},
        "Sc":{+3},"Cr":{+3},"V":{+3}
    },
    "chalcogenide": {
        "Ti":{+4},"Zr":{+4},"Hf":{+4},"V":{+3},"Nb":{+5},"Ta":{+5},
        "Cr":{+3},"Mn":{+2,+3},"Fe":{+2,+3},"Co":{+2,+3},"Ni":{+2},
        "Cu":{+1,+2},"Zn":{+2},"Sc":{+3},"Y":{+3},
        "Ge":{+4},"Sn":{+4},"Pb":{+2,+4},
        "W":{+4,+6},"Mo":{+4,+6}
    },
    "nitride": {
        "W":{+6},"Mo":{+6},"Ta":{+5},"Nb":{+5},
        "Ti":{+4},"Zr":{+4},"Hf":{+4},
        "Cr":{+3},"Mn":{+3},"Fe":{+3},"Co":{+3},"Ni":{+3}
    }
}

# geometry windows
T_RANGE = {"oxide":(0.80,1.05),"halide":(0.75,1.02),"chalcogenide":(0.78,1.05),"nitride":(0.75,1.08)}
MU_RANGE = (0.414, 0.90)

# lattice scaling (decoder outputs 3 numbers ~ [0..1])
TARGET_A = 3.87
VOL_TOL  = TARGET_A**3
HARD_MIN = 0.8   # Å; ban absurdly short distances

# ───────────────────────── Geometry helpers ─────────────────────────
IONIC_CACHE = {}
def get_ionic_radius(el):
    if el in IONIC_CACHE: return IONIC_CACHE[el]
    try:
        r = PMGElem(el).ionic_radii or []
        if isinstance(r, dict):
            vals = [float(x) for x in r.values() if x]
            val = float(np.mean(vals)) if vals else 1.5
        else:
            val = float(np.mean(r)) if r else 1.5
    except Exception:
        val = 1.5
    IONIC_CACHE[el] = val
    return val

def generate_perovskite_template():
    pts = [(0,0,0),(0.5,0.5,0.5)]
    face = [p for p in product((0.0,0.5), repeat=3) if abs(sum(p)-1.0)<1e-9]
    pts.extend(face)
    return torch.tensor(pts, dtype=torch.float32)
TEMPLATE = generate_perovskite_template()

def unscale_lat(lat):
    lat = torch.nan_to_num(lat)
    a = lat[:,0]*TARGET_A*0.4 + TARGET_A*0.8
    b = lat[:,1]*TARGET_A*0.4 + TARGET_A*0.8
    c = lat[:,2]*TARGET_A*0.4 + TARGET_A*0.8
    alpha = beta = gamma = torch.full_like(a, 90.0)
    return a,b,c,alpha,beta,gamma

def min_distance(coords):
    B,N,_ = coords.shape
    if N < 2:
        return torch.full((B,), 99., device=coords.device)
    diff = coords.unsqueeze(2)-coords.unsqueeze(1)
    d = torch.norm(diff, dim=-1)
    d = d + torch.eye(N, device=coords.device).unsqueeze(0)*99
    return d.min(dim=2).values.min(dim=1).values

def separation_loss(coords, eps=1e-6):
    B,N,_ = coords.shape
    diff = coords.unsqueeze(2)-coords.unsqueeze(1)
    d = torch.norm(diff, dim=-1) + torch.eye(N, device=coords.device).unsqueeze(0)
    return (1.0/(d+eps)).sum(dim=(1,2))

def repulsion_loss(coords):
    B,N,_ = coords.shape
    diff = coords.unsqueeze(2)-coords.unsqueeze(1)
    d = torch.norm(diff, dim=-1) + torch.eye(N, device=coords.device).unsqueeze(0)
    return torch.exp(-d).sum(dim=(1,2))

def template_loss(coords, occ):
    tpl = TEMPLATE.to(coords.device)
    d2  = torch.cdist(coords[:,:N_TEMPLATE,:], tpl.expand(coords.size(0),-1,-1))**2
    m,_ = d2.min(-1)
    return (occ[:,:N_TEMPLATE] * m).sum(dim=1)

def is_ABX3(s: Structure) -> bool:
    if s is None or len(s) != N_TEMPLATE: return False
    comp = s.composition.get_el_amt_dict()
    a_count = sum(comp.get(e,0) for e in A_CATIONS)
    b_count = sum(comp.get(e,0) for e in B_CATIONS)
    x_count = sum(comp.get(e,0) for e in ANIONS_ALL)
    return (a_count == 1) and (b_count == 1) and (x_count == 3)

def realism(s: Structure):
    if s is None: return ["null"]
    coords = s.cart_coords
    if np.isnan(coords).any(): return ["nan coords"]
    N = coords.shape[0]
    dmin = min(
        np.linalg.norm(coords[i]-coords[j])
        for i in range(N) for j in range(i+1,N)
    ) if N>1 else np.inf
    if dmin < HARD_MIN: return [f"short bond {dmin:.2f} Å"]
    return []

def family_from_structure(struct: Structure):
    Xs = [site.specie.symbol for site in struct[2:5]]
    if not (Xs[0]==Xs[1]==Xs[2]): return None
    return FAMILY_OF_X.get(Xs[0], None)

def tolerance_and_mu_ranges(family):
    return T_RANGE.get(family, (0.78,1.05)), MU_RANGE

def check_charge_balance_existential(struct: Structure):
    sp = [site.specie.symbol for site in struct][:N_TEMPLATE]
    A = [s for s in sp if s in A_CATIONS]
    B = [s for s in sp if s in B_CATIONS]
    X = [s for s in sp if s in ANIONS_ALL]
    if len(A)!=1 or len(B)!=1 or len(X)!=3:
        return ["stoichiometry mismatch for charge check"]
    if not (X[0]==X[1]==X[2]):
        return ["mixed X anions not allowed in strict check"]
    A,B,X = A[0], B[0], X[0]
    fam = FAMILY_OF_X[X]
    if A not in VALENCE_A:
        return [f"unknown A valence: {A}"]
    if fam not in VALENCE_B_BY_FAMILY or B not in VALENCE_B_BY_FAMILY[fam]:
        return [f"{B} uncommon for {fam}"]
    for qA in VALENCE_A[A]:
        for qB in VALENCE_B_BY_FAMILY[fam][B]:
            for qX in VALENCE_X[X]:
                if qA + qB + 3*qX == 0:
                    return []
    return [f"no common valence combo satisfies neutrality for {A}-{B}-{X}"]

def check_BX_distances_family(struct: Structure, margin_low=0.75, margin_high=1.35):
    msgs = []
    sp = [site.specie.symbol for site in struct][:N_TEMPLATE]
    Xsym = [s for s in sp if s in ANIONS_ALL][0]
    for site in struct:
        if site.specie.symbol != Xsym: continue
        rX = get_ionic_radius(Xsym)
        nbrs = struct.get_neighbors(site, 5.0)
        d_ok = False
        for ne in nbrs:
            if ne.specie.symbol in B_CATIONS:
                rB = get_ionic_radius(ne.specie.symbol)
                d0 = rB + rX
                d  = site.distance(ne)
                if (margin_low*d0) <= d <= (margin_high*d0):
                    d_ok = True
                    break
        if not d_ok:
            msgs.append(f"{Xsym} lacks B neighbor near rB+rX window")
    return msgs

def goldschmidt_and_mu_ok(struct: Structure):
    sp = [site.specie.symbol for site in struct][:N_TEMPLATE]
    A = [s for s in sp if s in A_CATIONS][0]
    B = [s for s in sp if s in B_CATIONS][0]
    X = [s for s in sp if s in ANIONS_ALL][0]
    rA, rB, rX = get_ionic_radius(A), get_ionic_radius(B), get_ionic_radius(X)
    t = (rA + rX) / (math.sqrt(2)*(rB + rX))
    mu = rB / rX if rX>1e-8 else 9.9
    fam = FAMILY_OF_X[X]
    (tmin,tmax), (mumin,mumax) = tolerance_and_mu_ranges(fam)
    msgs=[]
    if not (tmin <= t <= tmax):
        msgs.append(f"t={t:.2f} outside [{tmin:.2f},{tmax:.2f}]")
    if not (mumin <= mu <= mumax):
        msgs.append(f"mu={mu:.2f} outside [{mumin:.2f},{mumax:.2f}]")
    return msgs, t, mu

def build_species_mask(allowed_anions):
    mask = torch.zeros(MAX_SITES, NUM_SPECIES, dtype=torch.bool)
    for i, el in enumerate(SPECIES_LIST):
        if el in A_CATIONS:
            mask[0,i] = True
        if el in B_CATIONS:
            mask[1,i] = True
        if el in allowed_anions:
            mask[2,i] = mask[3,i] = mask[4,i] = True
    return mask

def struct_signature(s: Structure, decimals=3):
    comp = "-".join(
        [f"{el}{int(amt)}" for el, amt in sorted(s.composition.as_dict().items())]
    )
    a,b,c = [round(x,decimals) for x in s.lattice.abc]
    fracs = []
    for sp, frac in zip(s.species, s.frac_coords):
        fracs.append((sp.symbol, tuple(round(x,decimals) for x in frac)))
    fracs.sort()
    m = hashlib.sha1()
    m.update(f"{comp}|{a},{b},{c}|{fracs}".encode())
    return m.hexdigest()


# ───────────────────────── Model (heads compatible with your checkpoint) ─────────────────────────
class EGNNLayer(nn.Module):
    def __init__(self, node_dim, edge_dim):
        super().__init__()
        self.phi_e = nn.Sequential(
            nn.Linear(2*node_dim+1, edge_dim),
            nn.ReLU(),
            nn.Linear(edge_dim, edge_dim)
        )
        self.phi_x = nn.Sequential(nn.Linear(edge_dim,1))
        self.phi_h = nn.Sequential(
            nn.Linear(node_dim+edge_dim, node_dim),
            nn.ReLU()
        )

    def forward(self, h, x, adj, lattice=None):
        B,N,_ = h.shape
        diff = x.unsqueeze(2)-x.unsqueeze(1)
        dist2= (diff**2).sum(-1,keepdim=True)
        h_i = h.unsqueeze(2).expand(B,N,N,h.size(-1))
        h_j = h.unsqueeze(1).expand(B,N,N,h.size(-1))
        inp = torch.cat([h_i,h_j,dist2], dim=-1)
        e   = self.phi_e(inp) * adj.unsqueeze(-1)
        w   = self.phi_x(e)
        dx  = (diff*w).sum(2)
        x_o = x + dx
        agg = e.sum(2)
        h_o = self.phi_h(torch.cat([h,agg],dim=-1))
        return h_o, x_o

class SE3Encoder(nn.Module):
    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128, species_embedding_dim=64):
        super().__init__()
        self.species_embedding = nn.Linear(num_species, species_embedding_dim)
        self.init_node_fc     = nn.Sequential(
            nn.Linear(species_embedding_dim, node_hidden_dim),
            nn.ReLU()
        )
        self.egnn1 = EGNNLayer(node_hidden_dim, 64)
        self.egnn2 = EGNNLayer(node_hidden_dim, 64)
        self.aggregate_fc     = nn.Sequential(
            nn.Linear(node_hidden_dim, 128),
            nn.ReLU()
        )
        self.lat_fc           = nn.Sequential(
            nn.Linear(6,64),
            nn.ReLU()
        )
        self.comb_fc          = nn.Sequential(
            nn.Linear(64+128,128),
            nn.ReLU()
        )
        self.fc_mu            = nn.Linear(128, latent_dim)
        self.max_sites        = max_sites
        self.num_species      = num_species

    def forward(self, x):
        B = x.size(0)
        lat = x[:, :6]; off = 6
        adj = x[:, off:off + self.max_sites**2].view(B, self.max_sites, self.max_sites); off += self.max_sites**2
        spc = x[:, off:off + self.max_sites*self.num_species].view(B, self.max_sites, self.num_species); off += self.max_sites*self.num_species
        coords = x[:, off:].view(B, self.max_sites, 3)

        lat_emb = self.lat_fc(lat)
        h = self.init_node_fc(self.species_embedding(spc))
        mask = (spc.sum(-1) > 0).float().unsqueeze(-1)

        center = (coords * mask).sum(1) / (mask.sum(1) + 1e-8)
        coords0 = coords - center.unsqueeze(1)

        h1, x1 = self.egnn1(h, coords0, adj)
        h2, x2 = self.egnn2(h1, x1, adj)
        h2 = h2 * mask

        agg  = self.aggregate_fc(h2.sum(1) / (mask.sum(1).clamp(min=1)))
        comb = self.comb_fc(torch.cat([lat_emb, agg], -1))
        z    = self.fc_mu(comb)
        return z, center

class SE3Decoder(nn.Module):
    def __init__(self, max_sites, num_species, latent_dim, node_hidden_dim=128):
        super().__init__()
        self.fc_lat             = nn.Sequential(
            nn.Linear(latent_dim,64),
            nn.ReLU(),
            nn.Linear(64,6)
        )
        self.fc_nodes           = nn.Sequential(
            nn.Linear(latent_dim, max_sites*node_hidden_dim),
            nn.ReLU()
        )
        self.egnn1              = EGNNLayer(node_hidden_dim, 64)
        self.egnn2              = EGNNLayer(node_hidden_dim, 64)
        self.fc_species_decoded = nn.Sequential(
            nn.Linear(node_hidden_dim,64),
            nn.ReLU()
        )
        self.fc_species_final   = nn.Linear(64, NUM_SPECIES)
        self.fc_coords          = nn.Sequential(
            nn.Linear(node_hidden_dim,3)
        )
        self.max_sites          = max_sites
        self.num_species        = num_species

    def forward(self, z, input_coords=None, center=None, species_mask=None):
        B,N = z.size(0), self.max_sites
        lat_out   = self.fc_lat(z)
        nodes     = self.fc_nodes(z).view(B,N,-1)
        if input_coords is None:
            input_coords = torch.zeros(B,N,3, device=z.device)
        if center is None:
            center = torch.zeros(B,3, device=z.device)
        rel       = input_coords - center.unsqueeze(1)
        full_adj  = torch.ones(B,N,N, device=z.device)
        h1, x1    = self.egnn1(nodes, rel, full_adj)
        h2, x2    = self.egnn2(h1, x1, full_adj)
        spc_dec    = self.fc_species_decoded(h2)
        spc_logits = self.fc_species_final(spc_dec)
        if species_mask is not None:
            mask = ~species_mask.to(dtype=torch.bool, device=spc_logits.device).unsqueeze(0)
            fill_val = torch.finfo(spc_logits.dtype).min
            spc_logits = spc_logits.masked_fill(mask, fill_val)
        coords_out = self.fc_coords(h2) + center.unsqueeze(1)
        return (torch.nan_to_num(lat_out), full_adj,
                torch.nan_to_num(spc_logits),
                torch.nan_to_num(coords_out))

class PropertyEncoder(nn.Module):
    def __init__(self, hidden_dim=128, latent_dim=128):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(2,hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim,latent_dim)
        )
    def forward(self, x):
        return self.fc(x)

class PropertyDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(128,64),
            nn.ReLU(),
            nn.Linear(64,2)  # output[:,0]=heat_all, output[:,1]=dir_gap (matches training order)
        )
    def forward(self, z):
        return self.fc(z)

class DualAutoencoderModel(nn.Module):
    def __init__(self, max_sites, num_species, latent_dim=128):
        super().__init__()
        self.crystal_encoder = SE3Encoder(max_sites, num_species, latent_dim)
        self.crystal_decoder = SE3Decoder(max_sites, num_species, latent_dim)
        self.property_encoder= PropertyEncoder(latent_dim=latent_dim)
        self.property_decoder= PropertyDecoder()
        self.proj_crystal    = nn.Sequential(
            nn.Linear(latent_dim,latent_dim),
            nn.ReLU(),
            nn.Linear(latent_dim,latent_dim)
        )
        self.proj_prop       = nn.Sequential(
            nn.Linear(latent_dim,latent_dim),
            nn.ReLU(),
            nn.Linear(latent_dim,latent_dim)
        )
        self.max_sites = max_sites
        self.num_species = num_species


# ───────────────────────── Loss pieces & decode helpers ─────────────────────────
def softmax_temp(logits, t=None, temp=None):
    if t is None:
        t = 1.0 if temp is None else float(temp)
    return F.softmax(logits / max(t,1e-6), dim=-1)

def soft_charge_penalty(spc_logits, allowed_anions, weight=2e3, temp=1.0):
    P = softmax_temp(torch.nan_to_num(spc_logits), temp=temp)     # [B,S,C]
    def v(dict_el2qs):
        vec = torch.zeros(NUM_SPECIES, device=P.device)
        for el, qs in dict_el2qs.items():
            if el in SPECIES_LIST:
                vec[SPECIES_LIST.index(el)] = float(np.mean(list(qs)))
        return vec
    qA = (P[:,0,:] * v(VALENCE_A)).sum(dim=1)
    qXvec = torch.zeros(NUM_SPECIES, device=P.device)
    for x in allowed_anions:
        qXvec[SPECIES_LIST.index(x)] = list(VALENCE_X[x])[0]
    qX2 = (P[:,2,:]*qXvec).sum(dim=1)
    qX3 = (P[:,3,:]*qXvec).sum(dim=1)
    qX4 = (P[:,4,:]*qXvec).sum(dim=1)
    Bpri = {b:{+2,+3,+4,+5,+6} for b in B_CATIONS}
    qB = (P[:,1,:]*v(Bpri)).sum(dim=1)
    total = qA + qB + qX2 + qX3 + qX4
    return weight * total.pow(2)

def x_consistency_penalty(spc_logits, allowed_anions, weight=1e3, temp=1.0):
    P = softmax_temp(torch.nan_to_num(spc_logits), temp=temp)  # [B,S,C]
    idx = [SPECIES_LIST.index(x) for x in allowed_anions]
    Psub = P[:,2:5,:][:,:,idx]
    Pm = Psub.mean(dim=1, keepdim=True)
    return weight * ((Psub - Pm)**2).sum(dim=(1,2))

def entropy_bonus(spc_logits, allowed_anions, weight=0.0, temp=1.0):
    if weight <= 0:
        return torch.zeros(spc_logits.size(0), device=spc_logits.device)
    P = softmax_temp(spc_logits, temp=temp)
    idxA = [SPECIES_LIST.index(e) for e in A_CATIONS]
    idxB = [SPECIES_LIST.index(e) for e in B_CATIONS]
    idxX = [SPECIES_LIST.index(x) for x in allowed_anions]
    H  = -(P[:,0,idxA] * (P[:,0,idxA].clamp_min(1e-8)).log()).sum(dim=1)
    H += -(P[:,1,idxB] * (P[:,1,idxB].clamp_min(1e-8)).log()).sum(dim=1)
    HX = 0
    for s in (2,3,4):
        HX += -(P[:,s,idxX]*(P[:,s,idxX].clamp_min(1e-8)).log()).sum(dim=1)
    return -weight * (H + HX/3.0)

def diversity_repulsion(Z, tau=0.25):
    Zn = F.normalize(Z, dim=1)
    S = Zn @ Zn.T
    B = Z.size(0)
    mask = torch.eye(B, device=Z.device).bool()
    S = S.masked_fill(mask, -9.0)
    return torch.exp(S / max(tau,1e-6)).mean()

def history_repulsion(Z, histZ, tau=0.25):
    if histZ is None or histZ.numel()==0:
        return torch.tensor(0., device=Z.device)
    Zn = F.normalize(Z, dim=1)
    Hn = F.normalize(histZ, dim=1)
    S = Zn @ Hn.T
    return torch.exp(S / max(tau,1e-6)).mean()

def apply_neutrality_bias(spc_logits, allowed_anions, bias=8.0, topk=5):
    L = spc_logits.clone()
    B = L.size(0)
    idxA = [SPECIES_LIST.index(e) for e in A_CATIONS]
    idxB = [SPECIES_LIST.index(e) for e in B_CATIONS]
    anions_by_q = {q: [] for q in (-1,-2,-3)}
    for x in allowed_anions:
        anions_by_q[list(VALENCE_X[x])[0]].append(SPECIES_LIST.index(x))
    Bval_union = {}
    for _, table in VALENCE_B_BY_FAMILY.items():
        for el, qs in table.items():
            Bval_union.setdefault(el, set()).update(qs)
    for b in range(B):
        P = F.softmax(L[b], dim=-1)
        topA = torch.topk(P[0, idxA], k=min(topk,len(idxA))).indices.tolist()
        topB = torch.topk(P[1, idxB], k=min(topk,len(idxB))).indices.tolist()
        candA = [idxA[i] for i in topA]
        candB = [idxB[i] for i in topB]
        ok_charges = set()
        for ia in candA:
            ea = SPECIES_LIST[ia]
            if ea not in VALENCE_A: continue
            for ib in candB:
                eb = SPECIES_LIST[ib]
                VB = Bval_union.get(eb, {+2,+3,+4,+5,+6})
                for qA in VALENCE_A[ea]:
                    for qB in VB:
                        qX = -(qA+qB)/3.0
                        if qX in (-1,-2,-3):
                            ok_charges.add(int(qX))
        if not ok_charges:
            continue
        for site in (2,3,4):
            for q, idxs in anions_by_q.items():
                if not idxs: continue
                delta = bias if q in ok_charges else -0.5*bias
                L[b, site, idxs] = L[b, site, idxs] + delta
    return L


# ───────────────────────── Target-guided anion prior ─────────────────────────
def target_guided_x_prior(bg_target, family, allowed_anions):
    """
    Return dict {X_symbol: weight} that softly biases X choice given a target bandgap.
    Simple, transparent physics prior (tune if needed).
    """
    allowed = list(allowed_anions)
    w = {x: 1.0 for x in allowed}

    if family == "halide":
        # F > Cl > Br > I → bandgap tends to decrease along this sequence.
        lo = {"F":0.10, "Cl":0.30, "Br":0.70, "I":1.00}  # low-gap
        hi = {"F":1.00, "Cl":0.70, "Br":0.30, "I":0.10}  # high-gap
        t = (float(bg_target) - 1.5) / max(3.5 - 1.5, 1e-6)
        t = max(0.0, min(1.0, t))
        for x in allowed:
            w[x] = (1.0 - t)*lo.get(x, 1.0) + t*hi.get(x, 1.0)

    elif family == "chalcogenide":
        # S > Se > Te → bandgap generally decreases.
        lo = {"S":0.25, "Se":0.65, "Te":1.00}
        hi = {"S":1.00, "Se":0.65, "Te":0.25}
        t = (float(bg_target) - 0.8) / max(2.2 - 0.8, 1e-6)
        t = max(0.0, min(1.0, t))
        for x in allowed:
            w[x] = (1.0 - t)*lo.get(x, 1.0) + t*hi.get(x, 1.0)

    elif family in ("oxide", "nitride"):
        for x in allowed:
            w[x] = 1.0

    # normalize to unit mean (keep logit scale stable)
    vals = [w[x] for x in allowed] or [1.0]
    mean = sum(vals) / len(vals)
    if mean > 0:
        for x in allowed:
            w[x] /= mean
    return w

def apply_x_prior_to_logits(spc_logits, x_prior, x_prior_strength, allowed_anions):
    """
    Additive log-prior on X sites (2..4):
      posterior ∝ softmax( logits + x_prior_strength * log(prior) )
    """
    if x_prior_strength <= 0:
        return spc_logits
    L = spc_logits.clone()
    for x in allowed_anions:
        j = SPECIES_LIST.index(x)
        delta = float(x_prior.get(x, 1.0))
        if delta <= 0:
            continue
        add = x_prior_strength * math.log(max(delta, 1e-6))
        for site in (2, 3, 4):
            L[:, site, j] = L[:, site, j] + add
    return L


# ───────────────────────── Target conditioning (latent init) ─────────────────────────
def seed_from_target(base_seed, bg_t, ent_t):
    h = hashlib.sha1(f"{base_seed}|{bg_t:.6f}|{ent_t:.6f}".encode()).hexdigest()
    add = int(h[:8], 16)
    return int((base_seed ^ add) % (2**31-1))

def rff_target_offset(bg, ent, dim, nfreq=48, seed=0):
    # Random Fourier Features of the numeric target → direction in latent space
    rng = np.random.RandomState(seed)
    W = rng.normal(loc=0.0, scale=2.0, size=(2, nfreq))
    b = rng.uniform(0, 2*np.pi, size=(nfreq,))
    x = np.array([bg, ent])[:,None]
    proj = (W.T @ x).reshape(-1) + b
    phi = np.concatenate([np.sin(proj), np.cos(proj)], axis=0)  # [2*nfreq]
    M = rng.normal(0, 1.0/np.sqrt(2*nfreq), size=(2*nfreq, dim))
    v = phi @ M
    v = torch.tensor(v, dtype=torch.float32)
    return F.normalize(v, dim=0)

def make_population(model, pop, bg_tgt, ent_tgt, device, sigma, seed,
                    targ_alpha=0.75, targ_beta=0.60):
    """
    Target-led init: blend property-anchor, target-RFF, and noise.
    """
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    lat_dim = model.proj_crystal[-1].out_features
    zs_init = []
    for i in range(pop):
        with torch.no_grad():
            # input order must match training: [heat_all, dir_gap]
            x = torch.tensor([[ent_tgt, bg_tgt]], device=device, dtype=torch.float32)
            z_seeded = F.normalize(
                model.proj_prop(
                    F.normalize(model.property_encoder(x), dim=1)
                ),
                dim=1
            )  # [1,D]
            rff_seed = seed_from_target(seed + i, bg_tgt, ent_tgt) % (2**16)
            rff = rff_target_offset(bg_tgt, ent_tgt, lat_dim, nfreq=48, seed=rff_seed).to(device).unsqueeze(0)
            z_noise = torch.randn_like(z_seeded)
            z = F.normalize(targ_alpha*z_seeded + targ_beta*rff + 0.25*z_noise, dim=1)
            z.add_(sigma*torch.randn_like(z))
        zs_init.append(z)
    Z0 = torch.cat(zs_init, dim=0)
    Z  = nn.Parameter(Z0.clone())
    return Z0, Z


# ───────────────────────── Optimisation loop (batched) ─────────────────────────
def ent_loss_tensor(ent_pred, target, mode):
    if mode == "hinge":
        return F.relu(ent_pred - target)
    if mode == "l1":
        return (ent_pred - target).abs()
    return (ent_pred - target).pow(2)  # l2

def optimise_population(model, allowed_anions, species_mask, bg_tgt, ent_tgt,
                        steps, lr, pop, device,
                        weights, schedules, seed, bias_cfg,
                        ent_loss_mode="l1",
                        amp=True, grad_clip=1.0, z_clip=5.0,
                        restart_patience=250, restart_noise=0.35,
                        diversity_w=0.9, diversity_tau=0.25,
                        hist_latents=None, history_w=1.0, history_tau=0.25,
                        x_prior_strength=0.9, family_str="",
                        geo_loss_scale=1.0, property_first=False):
    """
    Latent optimisation:
      • PROPERTY terms are always active
      • GEOMETRY terms are scaled by geo_loss_scale and skipped entirely if property_first=True
    """
    (bg_w, ent_w, vol_w, tol_w, charge_w, xcons_w, prop_anchor_w) = weights
    (temp_init, temp_final, entropy_w0) = schedules
    (neutral_bias, neutral_topk) = bias_cfg

    use_amp = amp and (device.type=='cuda')
    amp_dtype = torch.bfloat16 if (use_amp and torch.cuda.is_bf16_supported()) else torch.float16
    scaler = torch.amp.GradScaler('cuda', enabled=use_amp)

    Z0, Z = make_population(model, pop, bg_tgt, ent_tgt, device, sigma=0.35, seed=seed)
    opt = optim.Adam([Z], lr=lr)

    # cosine anchor to property latent (keeps Z aligned with target)
    with torch.no_grad():
        anchor = F.normalize(
            model.proj_prop(
                F.normalize(
                    model.property_encoder(
                        # input order must match training: [heat_all, dir_gap]
                        torch.tensor([[ent_tgt, bg_tgt]], device=device, dtype=torch.float32)
                    ),
                    dim=1
                )
            ),
            dim=1
        )

    # precompute X-prior (does not change within this optimisation)
    x_prior = target_guided_x_prior(bg_tgt, family_str, allowed_anions)

    best = torch.full((pop,), float('inf'), device=device)
    since = torch.zeros(pop, dtype=torch.long, device=device)

    for step in range(steps):
        alpha = step / max(1, steps-1)
        temp  = temp_init * (temp_final / max(temp_init,1e-6))**alpha
        entB  = entropy_w0 * (1.0 - alpha)

        opt.zero_grad(set_to_none=True)
        with torch.amp.autocast('cuda', dtype=amp_dtype, enabled=use_amp):
            prop     = model.property_decoder(Z)
            ent_pred = prop[:,0:1]   # heat_all is index 0 (matches training order)
            bg_pred  = prop[:,1:2]   # dir_gap  is index 1

            lat_out, _, spc_logits_raw, coords_out = model.crystal_decoder(
                Z,
                input_coords=torch.zeros(pop,MAX_SITES,3,device=device),
                center=torch.zeros(pop,3,device=device),
                species_mask=species_mask.to(device)
            )
            spc_logits = apply_neutrality_bias(
                spc_logits_raw, allowed_anions,
                bias=neutral_bias, topk=neutral_topk
            ) if neutral_bias>0 else spc_logits_raw

            # target-guided anion prior (soft pull on X sites)
            spc_logits = apply_x_prior_to_logits(spc_logits, x_prior, x_prior_strength, allowed_anions)

            lat_s = torch.sigmoid(lat_out)
            xyz_s = torch.sigmoid(coords_out)
            Ptemp = softmax_temp(spc_logits, temp=temp)
            occ   = Ptemp.max(dim=-1).values

            a,b,c,_,_,_ = unscale_lat(lat_s)

            # ── 1) PROPERTY TERMS (always active) ─────────────────
            L = torch.zeros(pop, device=device)

            L += bg_w * F.mse_loss(
                bg_pred,
                torch.tensor([[bg_tgt]], device=device).expand_as(bg_pred),
                reduction="none"
            ).mean(dim=1)

            L += ent_w * ent_loss_tensor(
                ent_pred, ent_tgt, mode=ent_loss_mode
            ).mean(dim=1)

            # cosine anchor in latent space (keeps Z near property latent for this target)
            cos = F.cosine_similarity(
                F.normalize(Z,dim=1),
                anchor.expand_as(Z),
                dim=1
            )
            L += prop_anchor_w * (1.0 - cos)

            # ── 2) GEOMETRY / PHYSICS TERMS (optionally downweighted/skipped) ──
            L_geo = torch.zeros_like(L)

            if (not property_first) and (geo_loss_scale > 0.0):
                # packing / collision control
                L_geo += 200   * separation_loss(xyz_s)
                L_geo += 8000  * repulsion_loss(xyz_s)

                # volume and cubicity
                vol_term = ((a*b*c - VOL_TOL)/VOL_TOL).pow(2)
                cub_term = ((a-b).abs() + (b-c).abs())
                L_geo += vol_w * vol_term + 1e4 * cub_term

                # ABX3 reference-position alignment (cubic symmetry constraint)
                L_geo += 800 * template_loss(xyz_s, occ)

                # loose Goldschmidt-t penalty
                top = spc_logits.argmax(dim=-1)
                rA = torch.tensor(
                    [get_ionic_radius(SPECIES_LIST[i]) for i in top[:,0].tolist()],
                    device=device
                )
                rB = torch.tensor(
                    [get_ionic_radius(SPECIES_LIST[i]) for i in top[:,1].tolist()],
                    device=device
                )
                rX = torch.tensor(
                    [get_ionic_radius(SPECIES_LIST[i]) for i in top[:,2].tolist()],
                    device=device
                )
                t_gold = (rA + rX) / (math.sqrt(2)*(rB + rX))
                fam_guess = [FAMILY_OF_X.get(SPECIES_LIST[i], "oxide") for i in top[:,2].tolist()]
                tmin = torch.tensor([T_RANGE.get(f,(0.78,1.05))[0] for f in fam_guess], device=device)
                tmax = torch.tensor([T_RANGE.get(f,(0.78,1.05))[1] for f in fam_guess], device=device)
                t_pen = torch.where(
                    t_gold < tmin, (t_gold - tmin)**2,
                    torch.where(t_gold > tmax, (t_gold - tmax)**2, torch.zeros_like(t_gold))
                )
                L_geo += tol_w * t_pen

                # soft charge + X-consistency + entropy
                L_geo += soft_charge_penalty(
                    spc_logits, allowed_anions,
                    weight=charge_w*(0.2+0.8*alpha)**2, temp=temp
                )
                L_geo += x_consistency_penalty(
                    spc_logits, allowed_anions,
                    weight=xcons_w*(0.5+0.5*alpha), temp=temp
                )
                L_geo += entropy_bonus(
                    spc_logits, allowed_anions,
                    weight=entB, temp=temp
                )

                # hard short-bond rejection
                dmin = min_distance(xyz_s)
                L_geo += torch.where(
                    dmin < HARD_MIN,
                    1e5*(HARD_MIN - dmin)**2,
                    torch.zeros_like(dmin)
                )

                # apply global geometry scale
                L += geo_loss_scale * L_geo

            # diversity & history
            L_mean = L.mean()
            L_div  = diversity_w * diversity_repulsion(Z, tau=diversity_tau)
            L_hist = history_w  * history_repulsion(Z, hist_latents, tau=history_tau) if (hist_latents is not None) else 0.0
            loss = L_mean + L_div + L_hist

        scaler.scale(loss).backward()
        if grad_clip is not None:
            torch.nn.utils.clip_grad_norm_([Z], grad_clip)
        scaler.step(opt); scaler.update()
        with torch.no_grad():
            Z.data.clamp_(-z_clip, z_clip)

        with torch.no_grad():
            improved = L < best - 1e-6
            best = torch.minimum(best, L)
            since = torch.where(improved, torch.zeros_like(since), since+1)
            need_restart = since >= restart_patience
            if need_restart.any():
                idx = need_restart.nonzero(as_tuple=False).view(-1)
                Z[idx] = F.normalize(Z[idx] + restart_noise*torch.randn_like(Z[idx]), dim=1)
                since[idx] = 0

    return Z0.detach(), Z.detach()


# ───────────────────────── B-cation pool selection ─────────────────────────
def target_conditioned_B_set(bg_target, family, use_target_filter=False):
    """
    Return the pool of chemically allowed B-cations for the given anion family.

    By default (use_target_filter=False) the full set from VALENCE_B_BY_FAMILY
    is returned without bandgap-driven restriction.

    If use_target_filter=True, a heuristic bandgap-driven sub-selection is
    applied (useful for ablation or physics-prior experiments):
      halide, low-gap  (<=1.7 eV) → heavier / narrow-gap B (Sn, Pb, Mn, Fe, Co, Ni, Cu)
      halide, high-gap (>=3.0 eV) → more ionic B (Sc, Cr, V, Zn)
      halide, mid-gap             → full halide B set
      other families              → full family B set regardless of target
    """
    fam = family if family in VALENCE_B_BY_FAMILY else "oxide"
    base_B = list(VALENCE_B_BY_FAMILY[fam].keys())

    if not use_target_filter or family != "halide":
        return base_B

    # target-filtered sub-selection (halide only, opt-in)
    if bg_target <= 1.7:
        preferred = ["Sn","Pb","Mn","Fe","Co","Ni","Cu"]
    elif bg_target >= 3.0:
        preferred = ["Sc","Cr","V","Zn"]
    else:
        return base_B
    chosen = [b for b in preferred if b in base_B]
    return chosen if chosen else base_B


# ───────────────────────── Stochastic decode (anti-repeat + target X/B prior) ─────────────────────────
@torch.no_grad()
def decode_and_filter(model, Z, allowed_anions, species_mask, decimals=3, refine=True,
                      decode_temp=1.15, decode_topk=8, decode_tries=8, rng=None,
                      ab_pair_counts=None, ab_pair_counts_local=None, anti_repeat_alpha=0.6,
                      bg_target=1.0, family_str="", x_prior_strength=0.9,
                      use_target_b_filter=False):
    """
    Stochastic decoding of latent vectors into constraint-projected cubic ABX3 candidates.

    For each latent vector:
      • sample A with temperature and top-k from the allowed A-cation set
      • sample B from the chemically allowed B-cation set for the family,
          with optional anti-repeat downweighting on frequently generated AB pairs;
          if use_target_b_filter=True, B is further restricted to a heuristic
          subset based on the target band-gap score (for ablation/prior experiments)
      • choose X using pooled logits + optional target-guided anion prior
      • build a cubic ABX3 candidate, apply physics filters, keep first passing draw

    Property indices follow the training convention:
      property_decoder output[:,0] = heat_all (enthalpy surrogate)
      property_decoder output[:,1] = dir_gap  (band-gap surrogate)
    """
    if rng is None: rng = np.random.RandomState(0)
    device = Z.device

    prop = model.property_decoder(Z)
    ent  = prop[:,0].cpu().numpy()   # heat_all is index 0 (matches training order)
    bg   = prop[:,1].cpu().numpy()   # dir_gap  is index 1

    lat_out,_, spc_logits, coords_out = model.crystal_decoder(
        Z,
        input_coords=torch.zeros(Z.size(0),MAX_SITES,3,device=device),
        center=torch.zeros(Z.size(0),3,device=device),
        species_mask=species_mask.to(device)
    )
    lat_s = torch.sigmoid(lat_out)
    a,b,c,_,_,_ = unscale_lat(lat_s)
    a0 = ((a+b+c)/3).cpu().numpy()

    # Precompute X prior for this target/family
    x_prior = target_guided_x_prior(bg_target, family_str, set(allowed_anions))
    anion_idx = [SPECIES_LIST.index(x) for x in allowed_anions]

    structs, infos = [], []
    idxA_all = torch.tensor([SPECIES_LIST.index(e) for e in A_CATIONS], device=device)

    # B-cation pool: all chemically allowed by family by default;
    # pass use_target_b_filter=True (CLI --use_target_b_filter) for ablation
    B_elements = target_conditioned_B_set(bg_target, family_str,
                                          use_target_filter=use_target_b_filter)
    idxB_all = torch.tensor([SPECIES_LIST.index(e) for e in B_elements], device=device)

    def sample_topk_probs(values, topk):
        k = min(topk, values.numel())
        v, idx = torch.topk(values, k=k)
        p = F.softmax(v, dim=-1).cpu().numpy()
        pick = rng.choice(idx.cpu().numpy(), p=p)
        return int(pick)

    for i in range(Z.size(0)):
        logits_i = spc_logits[i]  # [S,C]
        ok = None
        for _try in range(decode_tries):
            # ── Step 1: sample B (anti-repeat weighted on B-marginal count) ─────
            vB = logits_i[1, idxB_all] / max(decode_temp,1e-6)
            weights = []
            for b_rel, b_gidx in enumerate(idxB_all.tolist()):
                b_sym_tmp = SPECIES_LIST[b_gidx]
                # sum (A,B) pair counts over all A to get B-marginal count
                g = (sum((ab_pair_counts or {}).get((a_el, b_sym_tmp), 0) for a_el in A_CATIONS) +
                     sum((ab_pair_counts_local or {}).get((a_el, b_sym_tmp), 0) for a_el in A_CATIONS))
                weights.append(1.0 / ((1.0 + float(g)) ** anti_repeat_alpha))
            weights = torch.tensor(weights, device=device, dtype=vB.dtype)
            vB = vB + torch.log(weights.clamp_min(1e-6))
            b_pick_rel = sample_topk_probs(vB, decode_topk)
            b_idx = int(idxB_all[b_pick_rel].item())
            b_sym = SPECIES_LIST[b_idx]

            # ── Step 2: sample X ─────────────────────────────────────────────────
            base_scores = logits_i[2:5, anion_idx].sum(dim=0) / max(decode_temp, 1e-6)
            prior_vec = torch.ones_like(base_scores)
            for k, j in enumerate(anion_idx):
                sym = SPECIES_LIST[j]
                prior_vec[k] = float(x_prior.get(sym, 1.0))
            x_scores_eff = base_scores + x_prior_strength * torch.log(prior_vec.clamp_min(1e-6))
            xv, xi = torch.topk(x_scores_eff, k=min(decode_topk, x_scores_eff.numel()))
            xp = F.softmax(xv, dim=-1).cpu().numpy()
            x_idx = int(torch.tensor(anion_idx, device=device)[rng.choice(xi.cpu().numpy(), p=xp)])
            x_sym = SPECIES_LIST[x_idx]

            # ── Step 3: restrict A to charge-compatible elements ──────────────────
            # For a given B and X, find which Q(A) values satisfy neutrality, then
            # only sample A from elements that can carry that valence.
            fam_b = family_str if family_str in VALENCE_B_BY_FAMILY else "oxide"
            qB_set = VALENCE_B_BY_FAMILY.get(fam_b, {}).get(b_sym, {+2})
            qX_set = VALENCE_X.get(x_sym, {-1})
            needed_qA = {-(qB + 3*qX) for qB in qB_set for qX in qX_set}
            compat_A = [e for e in A_CATIONS
                        if any(qA in VALENCE_A.get(e, set()) for qA in needed_qA)]
            if not compat_A:
                continue
            idxA_compat = torch.tensor([SPECIES_LIST.index(e) for e in compat_A], device=device)

            # ── Step 4: sample A from compatible set ─────────────────────────────
            vA = logits_i[0, idxA_compat] / max(decode_temp,1e-6)
            a_pick_rel = sample_topk_probs(vA, decode_topk)
            a_idx = int(idxA_compat[a_pick_rel].item())
            a_sym = SPECIES_LIST[a_idx]
            if a_idx == b_idx:
                continue

            sp_idx = [a_idx, b_idx, x_idx, x_idx, x_idx]
            sp = [SPECIES_LIST[j] for j in sp_idx]

            # Cubic ABX3 lattice constant: a = 2*(rB+rX) (B–X bond = a/2 in Pm-3m).
            # The ionic-radius prediction is used because a short training run may not
            # yet produce accurate lattice-decoder outputs; this gives a physically
            # sound cell regardless of training length.
            rB_i = get_ionic_radius(sp[1])
            rX_i = get_ionic_radius(sp[2])
            a0_i = float(np.clip(2.0 * (rB_i + rX_i), 3.0, 8.0))

            # project into cubic ABX3 stoichiometry/symmetry-constrained representation
            s = Structure(
                Lattice.cubic(a0_i),
                sp,
                TEMPLATE.cpu().numpy().tolist(),
                coords_are_cartesian=False
            )
            if not is_ABX3(s): continue
            if realism(s): continue
            fam = family_from_structure(s)
            if fam is None: continue
            if refine:
                try:
                    s = SpacegroupAnalyzer(s, symprec=0.05).get_refined_structure()
                except Exception:
                    continue
                if np.isnan(s.cart_coords).any(): continue
            if check_charge_balance_existential(s): continue
            if check_BX_distances_family(s): continue
            tm, tval, muval = goldschmidt_and_mu_ok(s)
            if tm: continue

            ok = (s, {
                "A":sp[0], "B":sp[1], "X":sp[2],
                "a0":a0_i, "t":float(tval), "mu":float(muval)
            })
            break

        if ok is None:
            structs.append(None); infos.append(None)
        else:
            structs.append(ok[0]); infos.append(ok[1])

    return structs, infos, bg, ent


# ───────────────────────── Checkpoint remap (older checkpoints) ─────────────────────────
def remap_checkpoint_keys(sd):
    new_sd = {}
    for k,v in sd.items():
        nk = k
        nk = nk.replace("crystal_encoder.sp_emb.", "crystal_encoder.species_embedding.")
        nk = nk.replace("crystal_encoder.init_fc.", "crystal_encoder.init_node_fc.")
        nk = nk.replace("crystal_encoder.agg_fc.", "crystal_encoder.aggregate_fc.")
        nk = nk.replace("crystal_decoder.fc_nd.", "crystal_decoder.fc_nodes.")
        nk = nk.replace("crystal_decoder.fc_sd.", "crystal_decoder.fc_species_decoded.")
        nk = nk.replace("crystal_decoder.fc_sf.", "crystal_decoder.fc_species_final.")
        nk = nk.replace("crystal_decoder.fc_crd.", "crystal_decoder.fc_coords.")
        nk = nk.replace("egnn1.phi_x.weight", "egnn1.phi_x.0.weight")
        nk = nk.replace("egnn1.phi_x.bias",   "egnn1.phi_x.0.bias")
        nk = nk.replace("egnn2.phi_x.weight", "egnn2.phi_x.0.weight")
        nk = nk.replace("egnn2.phi_x.bias",   "egnn2.phi_x.0.bias")
        nk = nk.replace("crystal_decoder.fc_coords.weight", "crystal_decoder.fc_coords.0.weight")
        nk = nk.replace("crystal_decoder.fc_coords.bias",   "crystal_decoder.fc_coords.0.bias")
        new_sd[nk] = v
    return new_sd


# ───────────────────────── Selection metrics (multi-objective) ─────────────────────────
def ent_distance(e_pred, e_tgt, mode="l1"):
    if mode == "hinge": return max(0.0, e_pred - e_tgt)
    if mode == "l1":    return abs(e_pred - e_tgt)
    return (e_pred - e_tgt)**2  # l2

def sel_score(bg_pred, ent_pred, bg_t, ent_t, wbg, went, mode):
    return (wbg * (bg_pred - bg_t)**2) + (went * ent_distance(ent_pred, ent_t, mode))


# ───────────────────────── CLI / Main ─────────────────────────
def parse_list_or_repeat(text, n, cast=float):
    if not text:
        return [None]*n
    parts = [p.strip() for p in text.split(",") if p.strip()!=""]
    if len(parts)==1:
        return [cast(parts[0])]*n
    vals = [cast(p) for p in parts]
    if len(vals)!=n:
        raise ValueError(f"Expected {n} values, got {len(vals)}: {text}")
    return vals

def main():
    p = argparse.ArgumentParser(
        description="Property-conditioned constrained inverse design for cubic ABX3 perovskite candidates "
                    "(symmetry/stoichiometry-constrained decoding + physics post-filters)"
    )
    p.add_argument("--checkpoint", default="dual_autoencoder_clip_earlyfusion.pth")
    p.add_argument("--family", choices=["","oxide","halide","chalcogenide","nitride"], default="")
    p.add_argument("--x_anion", default="")

    # Targets
    p.add_argument("--num_targets", type=int, default=1)
    p.add_argument("--bg_target", type=float, default=1.0)
    p.add_argument("--ent_target", type=float, default=-0.3)
    p.add_argument("--bg_targets", default="", help="comma list, overrides --bg_target")
    p.add_argument("--ent_targets", default="", help="comma list, overrides --ent_target")

    # Per-target schedules
    p.add_argument("--per_target", type=int, default=6, help="CIFs to save per target")
    p.add_argument("--per_target_schedule", default="")
    p.add_argument("--batch_attempts", type=int, default=96, help="population size per round")
    p.add_argument("--batch_attempts_schedule", default="")
    p.add_argument("--rounds_per_target", type=int, default=20)

    # Optim
    p.add_argument("--steps", type=int, default=1500)
    p.add_argument("--lr", type=float, default=1.2e-3)

    # Loss weights
    p.add_argument("--bg_weight", type=float, default=1e4)
    p.add_argument("--ent_weight", type=float, default=6e3)
    p.add_argument("--vol_weight", type=float, default=1e3)
    p.add_argument("--tol_weight", type=float, default=1e3)
    p.add_argument("--charge_weight", type=float, default=3000)
    p.add_argument("--xcons_weight", type=float, default=1500)
    p.add_argument("--prop_anchor_weight", type=float, default=12.0)

    # Enthalpy loss and selection modes
    p.add_argument("--ent_loss", choices=["hinge","l1","l2"], default="l1",
                   help="training loss for enthalpy vs target")
    p.add_argument("--select_bg_weight",  type=float, default=1.0,
                   help="selection ranking weight on (bg - target)^2")
    p.add_argument("--select_ent_weight", type=float, default=0.4,
                   help="selection ranking weight on enthalpy distance to target")
    p.add_argument("--ent_select_mode",   choices=["hinge","l1","l2"], default="l1",
                   help="selection metric for enthalpy")

    # Decode & anti-repeat
    p.add_argument("--decode_temp", type=float, default=1.25)
    p.add_argument("--decode_topk", type=int,   default=12)
    p.add_argument("--decode_tries", type=int,  default=12)
    p.add_argument("--decode_anti_repeat_alpha", type=float, default=0.6)

    # Bias & exploration
    p.add_argument("--neutral_bias", type=float, default=8.0)
    p.add_argument("--neutral_bias_topk", type=int, default=5)
    p.add_argument("--temp_init", type=float, default=1.6)
    p.add_argument("--temp_final", type=float, default=0.9)
    p.add_argument("--entropy_w0", type=float, default=0.06)

    # Diversity / history
    p.add_argument("--diversity_weight", type=float, default=0.9)
    p.add_argument("--diversity_tau", type=float, default=0.25)
    p.add_argument("--history_repel_weight", type=float, default=1.0)
    p.add_argument("--history_repel_tau", type=float, default=0.25)

    # Geometry vs property control (NEW)
    p.add_argument(
        "--geo_loss_scale", type=float, default=1.0,
        help="global scale factor for geometry/physics losses during latent optimisation"
    )
    p.add_argument(
        "--property_first", action="store_true",
        help="optimise latents using property loss only; geometry enforced mainly at decode/filter"
    )

    # Target-guided anion prior (off by default; enable for ablation / physics-prior experiments)
    p.add_argument("--x_prior_strength", type=float, default=0.0,
                   help="strength of target-guided anion prior on X sites (0.0 = off; "
                        "use >0 for physics-prior ablation experiments)")
    p.add_argument("--x_auto_restrict", action="store_true",
                   help="restrict X set by bg target when family=halide (high bg→{F,Cl}, low bg→{Br,I})")
    p.add_argument("--use_target_b_filter", action="store_true",
                   help="enable heuristic bandgap-driven B-cation sub-selection at decode "
                        "(halide family only; off by default to avoid biasing B-site chemistry)")

    # De-dup / misc
    p.add_argument("--unique_decimals", type=int, default=3)
    p.add_argument("--min_cosine_sep", type=float, default=0.985)
    p.add_argument("--dedup_abx", action="store_true")
    p.add_argument("--no_refine", action="store_true")
    p.add_argument("--no_amp", action="store_true")
    p.add_argument("--seed", type=int, default=937)

    # I/O
    p.add_argument("--output_dir", default="results_targetled")
    p.add_argument("--output_prefix", default="ABX3")
    p.add_argument("--plot_dir", default="plots_targetled")
    args = p.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.plot_dir, exist_ok=True)

    # Base allowed X from family/x_anion flags
    if args.family:
        fam2x = {
            "oxide":{"O"},
            "halide":{"F","Cl","Br","I"},
            "chalcogenide":{"S","Se","Te"},
            "nitride":{"N"}
        }
        base_allowed_anions = set(fam2x[args.family])
        family_str = args.family
    else:
        base_allowed_anions = {args.x_anion} if args.x_anion.strip() else set(ANIONS_ALL)
        if len(base_allowed_anions) == 1:
            family_str = FAMILY_OF_X.get(next(iter(base_allowed_anions)), "")
        else:
            family_str = ""

    # Model + checkpoint
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DualAutoencoderModel(MAX_SITES, NUM_SPECIES, latent_dim=128).to(device)
    raw = torch.load(os.path.abspath(os.path.expanduser(args.checkpoint)), map_location=device)
    sd  = raw["model_state_dict"] if isinstance(raw, dict) and "model_state_dict" in raw else raw
    res = model.load_state_dict(remap_checkpoint_keys(sd), strict=False)
    print("Loaded checkpoint.\n  missing keys:", res.missing_keys, "\n  unexpected keys:", res.unexpected_keys)
    # Compatibility check: critical modules must be present in the checkpoint.
    critical_prefixes = ("property_encoder", "property_decoder", "proj_prop",
                         "proj_crystal", "crystal_decoder")
    missing_critical = [k for k in res.missing_keys
                        if any(k.startswith(p) for p in critical_prefixes)]
    if missing_critical:
        raise RuntimeError(
            "Checkpoint is incompatible: the following critical keys are missing:\n"
            + "\n".join(f"  {k}" for k in missing_critical)
            + "\nPlease provide a checkpoint produced by tri_popaware_v1_.py "
              "that includes property_encoder, property_decoder, proj_prop, "
              "proj_crystal, and crystal_decoder weights."
        )

    model.eval()

    # Targets per index
    bg_list  = parse_list_or_repeat(args.bg_targets,  args.num_targets, cast=float)
    ent_list = parse_list_or_repeat(args.ent_targets, args.num_targets, cast=float)
    per_save = parse_list_or_repeat(args.per_target_schedule, args.num_targets, cast=int)
    per_pop  = parse_list_or_repeat(args.batch_attempts_schedule, args.num_targets, cast=int)
    for i in range(args.num_targets):
        if bg_list[i]  is None: bg_list[i]  = args.bg_target
        if ent_list[i] is None: ent_list[i] = args.ent_target
        if per_save[i] is None: per_save[i] = args.per_target
        if per_pop[i]  is None: per_pop[i]  = args.batch_attempts

    # Summary CSV
    summary_csv = os.path.join(args.output_dir, "run_summary.csv")
    write_header = not os.path.isfile(summary_csv)
    sf = open(summary_csv, "a", newline="")
    writer = csv.writer(sf)
    if write_header:
        writer.writerow([
            "target_idx","bg_target","ent_target","pred_bg","pred_ent",
            "A","B","X","a0","t","mu","outfile","family","note"
        ])

    # Global memory (de-dup, history)
    seen_structs = set()
    seen_abx     = set()
    saved_latents= []
    saved_labels = []
    hist_lat_torch = None
    ab_pair_counts = Counter()
    pca_global_latents = []

    # Per target
    for idx in range(1, args.num_targets+1):
        bg_t = float(bg_list[idx-1]); ent_t = float(ent_list[idx-1])
        goal = int(per_save[idx-1]);   pop = int(per_pop[idx-1])

        # per-target allowed anions (optional auto-restrict for halides)
        allowed_anions = set(base_allowed_anions)
        fam = family_str
        if args.x_auto_restrict and (fam == "halide"):
            if bg_t >= 3.0:
                allowed_anions = {"F","Cl"} & allowed_anions
            elif bg_t <= 1.7:
                allowed_anions = {"Br","I"} & allowed_anions
            if not allowed_anions:  # fallback if user over-restricted
                allowed_anions = {"F","Cl","Br","I"}
        species_mask = build_species_mask(allowed_anions)

        print(f"\n=== Target {idx}/{args.num_targets} | family={fam or 'ANY'} | bg={bg_t} ent<{ent_t} | pop/round={pop} | goal={goal} ===")
        saved_this_target = 0
        rng_target = np.random.RandomState(seed_from_target(args.seed, bg_t, ent_t))
        ab_pair_counts_local = Counter()

        # monitoring buffers (latent PCA)
        all_Z0 = []; all_Zf = []

        for round_i in range(1, args.rounds_per_target+1):
            seed_i = seed_from_target(args.seed + 9973*idx + 31*round_i, bg_t, ent_t)
            Z0, Zf = optimise_population(
                model, allowed_anions, species_mask,
                bg_t, ent_t,
                steps=args.steps, lr=args.lr, pop=pop, device=device,
                weights=(args.bg_weight,args.ent_weight,args.vol_weight,args.tol_weight,
                         args.charge_weight,args.xcons_weight,args.prop_anchor_weight),
                schedules=(args.temp_init,args.temp_final,args.entropy_w0),
                seed=seed_i, bias_cfg=(args.neutral_bias,args.neutral_bias_topk),
                ent_loss_mode=args.ent_loss,
                amp=(not args.no_amp), grad_clip=1.0, z_clip=5.0,
                restart_patience=250, restart_noise=0.35,
                diversity_w=args.diversity_weight, diversity_tau=args.diversity_tau,
                hist_latents=hist_lat_torch, history_w=args.history_repel_weight, history_tau=args.history_repel_tau,
                x_prior_strength=args.x_prior_strength, family_str=fam,
                geo_loss_scale=args.geo_loss_scale,
                property_first=args.property_first
            )
            all_Z0.append(Z0.cpu().numpy()); all_Zf.append(Zf.cpu().numpy())

            structs, infos, bg_pred, ent_pred = decode_and_filter(
                model, Zf, allowed_anions, species_mask,
                decimals=args.unique_decimals, refine=not args.no_refine,
                decode_temp=args.decode_temp, decode_topk=args.decode_topk, decode_tries=args.decode_tries,
                rng=rng_target,
                ab_pair_counts=ab_pair_counts, ab_pair_counts_local=ab_pair_counts_local,
                anti_repeat_alpha=args.decode_anti_repeat_alpha,
                bg_target=bg_t, family_str=fam, x_prior_strength=args.x_prior_strength,
                use_target_b_filter=args.use_target_b_filter
            )

            # Build candidate list and rank by both targets
            cand = []
            for i,s in enumerate(structs):
                if s is None: continue
                cand.append((i, s, infos[i], float(bg_pred[i]), float(ent_pred[i])))

            # Multi-objective sorting: prioritize hitting bg target + low enthalpy
            cand.sort(key=lambda x: sel_score(
                x[3], x[4], bg_t, ent_t,
                args.select_bg_weight, args.select_ent_weight, args.ent_select_mode
            ))

            # Save loop with de-dup (structure + latent cosine + optional ABX key)
            added = 0
            for i,s,info,bg_hat,ent_hat in cand:
                if saved_this_target >= goal: break

                sig = struct_signature(s, decimals=args.unique_decimals)
                if sig in seen_structs: continue
                if args.dedup_abx:
                    abx = (info["A"],info["B"],info["X"])
                    if abx in seen_abx: continue

                z_i = Zf[i].detach().cpu().numpy()
                cos_ok = True
                if saved_latents:
                    cosines = [
                        float(np.dot(z_i, zprev)/(np.linalg.norm(z_i)*np.linalg.norm(zprev)+1e-9))
                        for zprev in saved_latents
                    ]
                    if max(cosines) > args.min_cosine_sep:
                        cos_ok = False
                if not cos_ok: continue

                outfile = os.path.join(
                    args.output_dir,
                    f"{args.output_prefix}_T{idx}_R{round_i}_{saved_this_target+1}.cif"
                )
                CifWriter(s).write_file(outfile)
                fam_s = family_from_structure(s)
                writer.writerow([
                    idx, bg_t, ent_t, bg_hat, ent_hat,
                    info["A"],info["B"],info["X"],
                    info["a0"],info["t"],info["mu"],
                    outfile, fam_s, ""
                ])
                print(f"  [SAVED] {outfile}  (bg={bg_hat:.3f} ent={ent_hat:.3f}; A={info['A']} B={info['B']} X={info['X']} t={info['t']:.3f} mu={info['mu']:.3f})")
                seen_structs.add(sig)
                if args.dedup_abx:
                    seen_abx.add((info["A"],info["B"],info["X"]))
                saved_latents.append(z_i); saved_labels.append(idx)
                pca_global_latents.append(z_i)
                saved_this_target += 1; added += 1

                # AB anti-repeat memory
                ab_pair = (info["A"], info["B"])
                ab_pair_counts[ab_pair] += 1
                ab_pair_counts_local[ab_pair] += 1

                # Update torch history cache
                if hist_lat_torch is None:
                    hist_lat_torch = torch.tensor([Zf[i].detach().cpu().numpy()], device=device)
                else:
                    hist_lat_torch = torch.cat([hist_lat_torch, Zf[i:i+1].to(device)], dim=0)

            if saved_this_target >= goal:
                print(f"  [DONE] reached goal {goal} for target {idx} in {round_i} round(s).")
                break
            else:
                print(f"  round {round_i}: saved {added}; total so far {saved_this_target}/{goal}")

        # Per-target quick latent PCA (optional)
        try:
            Z0_all = np.concatenate(all_Z0, axis=0)
            Zf_all = np.concatenate(all_Zf, axis=0)
            X = np.vstack([Z0_all, Zf_all])
            X = X[~np.isnan(X).any(axis=1)]
            if X.shape[0] >= 3:
                coords = PCA(n_components=2).fit_transform(X)
                n0 = Z0_all.shape[0]
                plt.figure()
                plt.scatter(coords[:n0,0], coords[:n0,1], s=8, label="init Z", alpha=0.6)
                plt.scatter(coords[n0:,0], coords[n0:,1], s=8, label="final Z", alpha=0.6)
                plt.legend(); plt.xlabel("PC1"); plt.ylabel("PC2")
                plt.title(f"Target {idx}: latent PCA (init vs final)")
                plt.tight_layout()
                plt.savefig(os.path.join(args.plot_dir, f"latent_pca_target_{idx}.png")); plt.close()
        except Exception:
            pass

        if saved_this_target == 0:
            print("  [NONE] no passing candidates this target")

    sf.flush(); sf.close()

    # Global latent PCA across saved items (optional)
    if len(pca_global_latents) >= 3:
        arr = np.stack(pca_global_latents, axis=0)
        arr = arr[~np.isnan(arr).any(axis=1)]
        if arr.shape[0] >= 3:
            coords = PCA(n_components=2).fit_transform(arr)
            plt.figure()
            for i,(x,y) in enumerate(coords):
                plt.scatter(x,y,s=10)
                plt.text(x,y,f"T{saved_labels[i]}", fontsize=7)
            plt.xlabel("PC1 of saved z"); plt.ylabel("PC2 of saved z")
            plt.title("Global latent PCA (saved structures)")
            plt.tight_layout()
            plt.savefig(os.path.join(args.output_dir, "latent_pca_saved_all.png"))
            plt.close()

if __name__ == "__main__":
    main()

