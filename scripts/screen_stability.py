#!/usr/bin/env python3
"""
scripts/screen_stability.py
============================
MACE-MP-0 stability screening and SUN rate evaluation for MEIDNet-generated
ABX3 perovskite candidates.

SUN Metrics
-----------
S — Stable
    A candidate is thermodynamically stable if its MACE-MP-0 formation energy
    DeltaH_f <= threshold (default 0.10 eV/atom).  This corresponds to the
    Materials Project "potentially synthesizable" criterion.  Formation energies
    are computed as:

        DeltaH_f = E(ABX3)/N - sum_i (x_i * E_ref(i))

    where E_ref(i) is the MACE-MP energy per atom of element i in its standard-
    state phase (metal, molecular, or bulk solid).  GGA overbinding corrections
    are applied to molecular references:
        O: +0.35 eV/atom  (O2 overbinding; equivalent to MP +0.70 eV/O2 molecule)
        N: +0.35 eV/atom  (analogous N2 correction)

    Structures with |DeltaH_f| > 5 eV/atom are flagged as artefacts and excluded
    from all rate calculations (typically indicates catastrophic relaxation or a
    missing elemental reference).

U — Unique
    No two accepted candidates are structurally equivalent under pymatgen
    StructureMatcher (ltol=0.20, stol=0.30, angle_tol=5 deg, primitive_cell=True).
    Matching is performed on the unrelaxed structures as parsed from CIF to measure
    the intrinsic diversity of the generative model.

N — Novel
    The reduced formula of each candidate does not appear in the training-set CSV
    (train.csv), ensuring the model is not merely memorising known compositions.

Scientific Notes
----------------
- Reference energies: E_ref(el) = E(phase)/N_atoms for ALL elements, including
  diatomics.  The factor-of-2 correction previously applied to O2 and F2 was
  erroneous (doubled the reference energy).
- Br and I standard states are orthorhombic bulk solids (Cmca), not molecular,
  because ASE does not include Br2 or I2 in its G2 molecule database.
- Relaxation: BFGS geometry optimisation with FrechetCellFilter (cell + atoms),
  fmax = 0.05 eV/A, max 500 steps.  Float32 precision is used for throughput;
  single-point energies agree with float64 to within ~0.01 eV/atom for oxides.

References
----------
Wang et al., Phys. Rev. B 73, 195107 (2006) — GGA+U and O2 overbinding corrections.
Batatia et al., "MACE: Higher Order Equivariant Message Passing Neural Networks
    for Fast and Accurate Force Fields," NeurIPS 2022.
Batatia et al., "A foundation model for atomistic materials chemistry," arXiv 2023.

Usage
-----
    python scripts/screen_stability.py \\
        --results_dir results/ \\
        --train_csv   data/train.csv \\
        --threshold   0.10 \\
        --device      cuda
"""
import os, glob, argparse, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

from pymatgen.core import Structure, Composition
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.io.ase import AseAtomsAdaptor

from ase.build import bulk, molecule
from ase.optimize import BFGS
from ase.filters import FrechetCellFilter
import torch

# ─── GGA overbinding corrections (eV per atom added to elemental reference) ───
# Positive value → reference made less negative → DeltaH_f more negative (more stable).
# Values from Materials Project compatibility scheme (oxide/peroxo corrections).
GGA_CORRECTIONS = {
    "O": +0.35,   # +0.70 eV per O2 molecule ÷ 2 atoms
    "N": +0.35,   # analogous N2 overbinding (applied for nitrides)
}

# ─── Artefact guard ───────────────────────────────────────────────────────────
ARTEFACT_THRESHOLD = 5.0   # |DeltaH_f| > this → likely a failed/corrupt structure

# ─── Elemental reference structures (standard-state phases) ───────────────────
# Only elements appearing in our design space are listed.
# For each: (constructor_fn, crystal_system_note)
# bulk() creates a primitive cell for the given structure type.
ELEMENT_STRUCTS = {
    # A-site cations
    "Ba": lambda: bulk("Ba", "bcc",  a=5.023),
    "Sr": lambda: bulk("Sr", "fcc",  a=6.084),
    "Ca": lambda: bulk("Ca", "fcc",  a=5.588),
    "Na": lambda: bulk("Na", "bcc",  a=4.225),
    "K":  lambda: bulk("K",  "bcc",  a=5.332),
    "Rb": lambda: bulk("Rb", "bcc",  a=5.703),
    "Cs": lambda: bulk("Cs", "bcc",  a=6.141),
    "La": lambda: bulk("La", "fcc",  a=5.303),
    "Ce": lambda: bulk("Ce", "fcc",  a=5.160),
    "Pr": lambda: bulk("Pr", "fcc",  a=5.170),
    "Nd": lambda: bulk("Nd", "fcc",  a=5.160),
    "Sm": lambda: bulk("Sm", "fcc",  a=5.124),
    "Eu": lambda: bulk("Eu", "bcc",  a=4.583),
    "Gd": lambda: bulk("Gd", "hcp",  a=3.636, c=5.783),
    "Tb": lambda: bulk("Tb", "hcp",  a=3.601, c=5.694),
    "Dy": lambda: bulk("Dy", "hcp",  a=3.591, c=5.651),
    "Ho": lambda: bulk("Ho", "hcp",  a=3.577, c=5.617),
    "Er": lambda: bulk("Er", "hcp",  a=3.559, c=5.587),
    "Tm": lambda: bulk("Tm", "hcp",  a=3.538, c=5.555),
    "Yb": lambda: bulk("Yb", "fcc",  a=5.485),
    "Lu": lambda: bulk("Lu", "hcp",  a=3.505, c=5.551),
    # B-site transition metals
    "Ti": lambda: bulk("Ti", "hcp",  a=2.951, c=4.684),
    "Zr": lambda: bulk("Zr", "hcp",  a=3.232, c=5.148),
    "Hf": lambda: bulk("Hf", "hcp",  a=3.196, c=5.051),
    "V":  lambda: bulk("V",  "bcc",  a=3.024),
    "Nb": lambda: bulk("Nb", "bcc",  a=3.301),
    "Ta": lambda: bulk("Ta", "bcc",  a=3.303),
    "Cr": lambda: bulk("Cr", "bcc",  a=2.884),
    "Mn": lambda: bulk("Mn", "bcc",  a=2.910),
    "Fe": lambda: bulk("Fe", "bcc",  a=2.867),
    "Co": lambda: bulk("Co", "hcp",  a=2.507, c=4.069),
    "Ni": lambda: bulk("Ni", "fcc",  a=3.524),
    "Cu": lambda: bulk("Cu", "fcc",  a=3.615),
    "Zn": lambda: bulk("Zn", "hcp",  a=2.664, c=4.947),
    "Sc": lambda: bulk("Sc", "hcp",  a=3.309, c=5.273),
    "Y":  lambda: bulk("Y",  "hcp",  a=3.648, c=5.731),
    "Al": lambda: bulk("Al", "fcc",  a=4.046),
    "Ga": lambda: bulk("Ga", "fcc",  a=4.510),   # approx (actual: orthorhombic)
    "In": lambda: bulk("In", "fcc",  a=4.590),   # approx (actual: bct)
    "Ge": lambda: bulk("Ge", "diamond", a=5.658),
    "Sn": lambda: bulk("Sn", "diamond", a=6.489),
    "Pb": lambda: bulk("Pb", "fcc",  a=4.951),
    "W":  lambda: bulk("W",  "bcc",  a=3.165),
    "Mo": lambda: bulk("Mo", "bcc",  a=3.147),
    # X anions — standard states
    # Reference energy per atom = E(molecule_or_bulk) / N_atoms  (no factor-of-2 adjustment)
    "O":  lambda: molecule("O2"),   # 2-atom molecule; E_ref/atom = E(O2)/2
    "F":  lambda: molecule("F2"),
    "Cl": lambda: molecule("Cl2"),
    # Br2 and I2 are not in ASE's G2 molecule database; use bulk crystal phases.
    # Orthorhombic Cmca structure (standard state for both Br and I).
    "Br": lambda: bulk("Br", "orthorhombic", a=6.67, b=4.48, c=8.72),
    "I":  lambda: bulk("I",  "orthorhombic", a=7.27, b=4.79, c=9.79),
    "S":  lambda: bulk("S",  "fcc",  a=6.36),   # simplified (true: alpha-S, 128 atoms)
    "Se": lambda: bulk("Se", "hcp",  a=3.66, c=4.95),  # simplified
    "Te": lambda: bulk("Te", "hcp",  a=4.456, c=5.921),
    "N":  lambda: molecule("N2"),
}


def get_ref_energies(elements, calc):
    """
    Compute MACE-MP energy per atom for each element's reference phase.

    Reference energy per atom = E(phase) / N_atoms for ALL elements including
    diatomics (O2, F2, etc.).  GGA_CORRECTIONS are then added on top.

    Returns dict {element: eV/atom}.  Elements whose reference computation fails
    are stored as NaN and trigger artefact flags downstream.
    """
    refs = {}
    for el in sorted(elements):
        if el not in ELEMENT_STRUCTS:
            print(f"  [WARN] no reference structure defined for {el}")
            refs[el] = float("nan")
            continue
        try:
            atoms = ELEMENT_STRUCTS[el]()
            atoms.calc = calc
            e = atoms.get_potential_energy()
            n = len(atoms)
            # Correct formula: E_ref(el) = E(phase) / N_atoms
            e_per_atom = e / n
            # Apply GGA overbinding correction if applicable
            e_per_atom += GGA_CORRECTIONS.get(el, 0.0)
            refs[el] = e_per_atom
            corr_str = (f" [+{GGA_CORRECTIONS[el]:.2f} eV GGA corr]"
                        if el in GGA_CORRECTIONS else "")
            print(f"  E_ref[{el:2s}] = {refs[el]:8.4f} eV/atom{corr_str}")
        except Exception as exc:
            print(f"  [WARN] reference energy FAILED for {el}: {exc}")
            refs[el] = float("nan")
    return refs


def relax_and_energy(atoms, calc, fmax=0.05, steps=500):
    """
    Relax cell + atomic positions with MACE-MP using FrechetCellFilter + BFGS.
    Returns (relaxed_atoms, converged, energy_per_atom).
    fmax=0.05 eV/A is a tighter criterion than the default 0.10.
    """
    atoms.calc = calc
    try:
        ecf = FrechetCellFilter(atoms)
        opt = BFGS(ecf, logfile=None)
        converged = opt.run(fmax=fmax, steps=steps)
        e_pa = atoms.get_potential_energy() / len(atoms)
        return atoms, bool(converged), e_pa
    except Exception as exc:
        print(f"    [WARN] relaxation failed: {exc}")
        return atoms, False, float("nan")


def formation_energy(e_pa_struct, composition, ref_energies, n_atoms):
    """
    DeltaH_f per atom:
        DeltaH_f = E(compound)/N - sum_i (n_i/N) * E_ref[i]
                 = e_pa_struct - ref_sum / n_atoms

    composition: dict {element_symbol: count}  (e.g. {"Ba":1,"Ti":1,"O":3})
    ref_energies: dict {element_symbol: eV/atom}
    """
    ref_sum = sum(composition[el] * ref_energies.get(el, float("nan"))
                  for el in composition)
    return e_pa_struct - ref_sum / n_atoms


def check_ref_complete(composition, ref_energies):
    """Return True if all elements in composition have valid (non-NaN) references."""
    return all(not np.isnan(ref_energies.get(el, float("nan")))
               for el in composition)


def load_train_compositions(train_csv):
    """
    Return set of reduced formula strings from train.csv.
    Tries 'pretty_formula' first, then any column containing 'formula'.
    Also stores pymatgen-reduced versions for robust matching.
    """
    formulas = set()
    try:
        df = pd.read_csv(train_csv)
        for col in df.columns:
            if "formula" in col.lower():
                raw = df[col].dropna().tolist()
                for f in raw:
                    formulas.add(str(f).strip())
                    try:
                        # also add pymatgen-reduced form for normalisation
                        formulas.add(Composition(f).reduced_formula)
                    except Exception:
                        pass
                break
    except Exception as exc:
        print(f"  [WARN] could not load train.csv: {exc}")
    return formulas


def main():
    p = argparse.ArgumentParser(description="SUN rate for generated ABX3 perovskite CIFs")
    p.add_argument("--results_dir", default="results_test")
    p.add_argument("--train_csv",   default="train.csv")
    p.add_argument("--threshold",   type=float, default=0.10,
                   help="DeltaH_f stability threshold eV/atom (default 0.10 = 100 meV/atom)")
    p.add_argument("--fmax",        type=float, default=0.05,
                   help="BFGS force convergence criterion eV/A (default 0.05)")
    p.add_argument("--steps",       type=int,   default=500)
    p.add_argument("--device",      default="cuda")
    args = p.parse_args()

    # ── Load MACE-MP ─────────────────────────────────────────────────────────
    print("Loading MACE-MP-0 (medium) calculator...")
    from mace.calculators import mace_mp
    calc = mace_mp(model="medium", dispersion=False,
                   default_dtype="float32", device=args.device)
    print(f"  device={args.device}  threshold={args.threshold} eV/atom  "
          f"fmax={args.fmax} eV/A\n")

    # ── Collect CIF files ─────────────────────────────────────────────────────
    cif_files = sorted(glob.glob(
        os.path.join(args.results_dir, "**", "*.cif"), recursive=True))
    if not cif_files:
        print(f"No CIFs found in {args.results_dir}"); return
    print(f"Found {len(cif_files)} CIF files.")

    # ── Parse structures ──────────────────────────────────────────────────────
    pmg_structs = []
    all_elements = set()
    for f in cif_files:
        try:
            s = Structure.from_file(f)
            pmg_structs.append((f, s))
            all_elements.update(str(el) for el in s.composition.elements)
        except Exception as e:
            print(f"  [WARN] parse failed: {f}: {e}")
            pmg_structs.append((f, None))

    # ── Pre-compute elemental reference energies ──────────────────────────────
    print(f"\nElements in candidate set: {sorted(all_elements)}")
    print("Computing elemental reference energies (MACE-MP)...\n"
          "  Note: E_ref = E(phase)/N_atoms; GGA corrections applied for O, N.")
    ref_e = get_ref_energies(all_elements, calc)

    # ── Training-set compositions ─────────────────────────────────────────────
    train_formulas = load_train_compositions(args.train_csv)
    print(f"\nTraining-set formulas: {len(train_formulas)} entries loaded.")

    # ── Per-structure stability + novelty ─────────────────────────────────────
    results = []
    print(f"\n{'='*70}")
    print("MACE-MP relaxation + formation energy")
    print(f"{'='*70}")

    for cif_path, pmg_s in pmg_structs:
        label = os.path.basename(cif_path)
        rec = {"file": label, "formula": "?", "dHf": float("nan"),
               "stable": False, "unique": None, "novel": None,
               "converged": False, "artefact": False}

        if pmg_s is None:
            results.append(rec); continue

        formula = pmg_s.composition.reduced_formula
        rec["formula"] = formula
        composition = {str(el): pmg_s.composition[el]
                       for el in pmg_s.composition.elements}

        # Novelty: check reduced formula against training set
        novel = (formula not in train_formulas and
                 pmg_s.composition.reduced_formula not in train_formulas)
        rec["novel"] = novel

        # Relax with MACE
        print(f"\n  Relaxing {label} ({formula})...")
        ase_atoms = AseAtomsAdaptor.get_atoms(pmg_s)
        ase_rel, converged, e_pa = relax_and_energy(
            ase_atoms, calc, fmax=args.fmax, steps=args.steps)
        rec["converged"] = converged

        # Formation energy
        if np.isnan(e_pa) or not check_ref_complete(composition, ref_e):
            dHf = float("nan")
            artefact = True
            if not check_ref_complete(composition, ref_e):
                missing = [el for el in composition
                           if np.isnan(ref_e.get(el, float("nan")))]
                print(f"    [SKIP] missing references for: {missing}")
        else:
            dHf = formation_energy(e_pa, composition, ref_e, len(ase_atoms))
            artefact = abs(dHf) > ARTEFACT_THRESHOLD

        rec["dHf"] = dHf
        rec["artefact"] = artefact

        if artefact and not np.isnan(dHf):
            print(f"    [ARTEFACT] dHf={dHf:+.3f} eV/atom — reference likely failed; excluded from stability count")
            stable = False
        elif np.isnan(dHf):
            stable = False
        else:
            stable = dHf <= args.threshold

        rec["stable"] = stable
        status = "ARTEFACT" if artefact else ("STABLE" if stable else "UNSTABLE")
        print(f"    E/atom={e_pa:.4f} eV  dHf={dHf:+.4f} eV/atom  "
              f"[{status}]  novel={'Y' if novel else 'N'}  conv={'Y' if converged else 'N'}")
        results.append(rec)

    # ── Uniqueness (StructureMatcher on unrelaxed CIF structures) ─────────────
    print(f"\n{'='*70}")
    print("Uniqueness check (pymatgen StructureMatcher on unrelaxed structures)")
    print(f"{'='*70}")
    sm = StructureMatcher(ltol=0.20, stol=0.30, angle_tol=5.0,
                          primitive_cell=True, allow_subset=False)
    accepted_idx = []
    for i, (cif_path, pmg_s) in enumerate(pmg_structs):
        if pmg_s is None:
            results[i]["unique"] = False; continue
        is_unique = True
        for j in accepted_idx:
            _, pmg_j = pmg_structs[j]
            if pmg_j is not None:
                try:
                    if sm.fit(pmg_s, pmg_j):
                        print(f"  DUPLICATE: {results[i]['file']} == {results[j]['file']}")
                        is_unique = False; break
                except Exception:
                    pass
        results[i]["unique"] = is_unique
        if is_unique:
            accepted_idx.append(i)

    # ── Compute SUN metrics ───────────────────────────────────────────────────
    valid = [r for r in results if not r["artefact"]]
    n_all   = len(results)
    n_valid = len(valid)
    n_art   = n_all - n_valid

    n_S   = sum(r["stable"]                                    for r in valid)
    n_U   = sum(r["unique"]                                    for r in valid if r["unique"] is not None)
    n_N   = sum(r["novel"]                                     for r in valid if r["novel"]  is not None)
    n_SU  = sum(r["stable"] and r["unique"]                    for r in valid if r["unique"] is not None)
    n_SUN = sum(r["stable"] and r["unique"] and r["novel"]     for r in valid
                if r["unique"] is not None and r["novel"] is not None)

    # ── Print table ───────────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print("SUN RATE RESULTS")
    print(f"{'='*72}")
    hdr = f"  {'File':<40} {'Formula':<12} {'dHf(eV/at)':>10}  S  U  N"
    print(hdr); print("-"*72)
    for r in results:
        s  = "Y" if r["stable"]  else ("!" if r["artefact"] else "N")
        u  = ("Y" if r["unique"] else "N") if r["unique"] is not None else "?"
        nv = ("Y" if r["novel"]  else "N") if r["novel"]  is not None else "?"
        dh = f"{r['dHf']:+.3f}" if not np.isnan(r["dHf"]) else "  nan"
        flag = " [ARTEFACT]" if r["artefact"] else ""
        print(f"  {r['file']:<40} {r['formula']:<12} {dh:>10}  {s}  {u}  {nv}{flag}")

    print(f"{'='*72}")
    print(f"Total structures      : {n_all}"
          + (f"  ({n_art} artefacts excluded from rates)" if n_art else ""))
    print(f"Valid (non-artefact)  : {n_valid}")
    print(f"")
    print(f"Stable  (S, dHf<={args.threshold:.2f} eV/at) : "
          f"{n_S}/{n_valid} = {100*n_S/max(n_valid,1):.1f}%")
    print(f"Unique  (U, StructMatcher)   : "
          f"{n_U}/{n_valid} = {100*n_U/max(n_valid,1):.1f}%")
    print(f"Novel   (N, not in train)    : "
          f"{n_N}/{n_valid} = {100*n_N/max(n_valid,1):.1f}%")
    print(f"SU  rate                     : "
          f"{n_SU}/{n_valid} = {100*n_SU/max(n_valid,1):.1f}%")
    print(f"SUN rate                     : "
          f"{n_SUN}/{n_valid} = {100*n_SUN/max(n_valid,1):.1f}%")
    print(f"{'='*72}")
    print(f"\nCorrections applied: O +0.35 eV/atom (GGA O2 overbinding), "
          f"N +0.35 eV/atom.")
    print(f"Artefact guard: |dHf| > {ARTEFACT_THRESHOLD} eV/atom excluded.")

    # ── Save CSV ──────────────────────────────────────────────────────────────
    out_csv = os.path.join(args.results_dir, "sun_rate.csv")
    pd.DataFrame(results).to_csv(out_csv, index=False)
    print(f"\nDetailed results saved to {out_csv}")


if __name__ == "__main__":
    main()
