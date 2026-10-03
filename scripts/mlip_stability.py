"""
Relax candidate structures with the MACE-MP-0 universal potential and compute their formation energy against
elemental reference phases: the stability criterion of `meidnet screen` and of the benchmark protocol.

    python scripts/mlip_stability.py candidates.csv stability.csv [--model medium] [--device cpu]

candidates.csv needs the columns `id` and `cif` (path relative to the CSV). The output has one row per candidate:
id, formula, energy_per_atom, dHf (eV/atom), converged, artefact.

Runs in any Python environment with mace-torch, ase and pymatgen; MEIDNet itself is not imported (the reference
phases are read from meidnet/screen.py next to this script), so the MLIP can live in its own environment.
"""
import argparse
import csv
import importlib.util
import os
import sys
import time
import types
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))


def _mace():
    try:
        import h5py  # noqa: F401
    except Exception:
        # Some Windows application-control policies block h5py's compiled libraries. MACE imports h5py only to
        # read training datasets, which relaxation never does, so an empty stand-in is enough.
        sys.modules["h5py"] = types.ModuleType("h5py")
    from mace.calculators import mace_mp
    return mace_mp


def _screen():
    spec = importlib.util.spec_from_file_location("meidnet_screen", os.path.join(HERE, "..", "meidnet", "screen.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates")
    ap.add_argument("output")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--dtype", default="float32")
    ap.add_argument("--fmax", type=float, default=0.05)
    ap.add_argument("--steps", type=int, default=500)
    a = ap.parse_args(argv)

    from pymatgen.core import Structure
    from pymatgen.io.ase import AseAtomsAdaptor
    scr = _screen()
    calc = _mace()(model=a.model, dispersion=False, default_dtype=a.dtype, device=a.device)
    base = os.path.dirname(os.path.abspath(a.candidates))
    with open(a.candidates, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    structs, elements = [], set()
    for r in rows:
        try:
            s = Structure.from_file(os.path.join(base, r["cif"]))
            elements.update(str(e) for e in s.composition.elements)
        except Exception as e:
            print(f"  [warn] {r['id']}: could not read {r['cif']}: {e}", flush=True)
            s = None
        structs.append(s)
    refs = scr.reference_energies(elements, calc, log=lambda *x: print(*x, flush=True))
    out = []
    t0 = time.time()
    for i, (r, s) in enumerate(zip(rows, structs), start=1):
        rec = {"id": r["id"], "formula": "", "energy_per_atom": "", "dHf": "", "converged": False, "artefact": True}
        if s is not None:
            rec["formula"] = s.composition.reduced_formula
            atoms = AseAtomsAdaptor.get_atoms(s)
            conv, e_pa = scr.relax(atoms, calc, a.fmax, a.steps)
            comp = {str(e): s.composition[e] for e in s.composition.elements}
            rec["converged"] = conv
            if e_pa == e_pa and all(refs.get(el) == refs.get(el) for el in comp):   # not NaN
                dhf = e_pa - sum(comp[el] * refs[el] for el in comp) / len(atoms)
                rec.update(energy_per_atom=f"{e_pa:.5f}", dHf=f"{dhf:.5f}", artefact=abs(dhf) > scr.ARTEFACT_THRESHOLD)
        out.append(rec)
        print(f"  {i:>3}/{len(rows)} {rec['id']:<22} {rec['formula']:<12} dHf {rec['dHf'] or 'n/a':>9}  "
              f"{'converged' if rec['converged'] else 'not converged'}  ({time.time() - t0:.0f}s)", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]) if out else ["id"])
        w.writeheader()
        w.writerows(out)
    print(f"wrote {a.output} ({len(out)} structures)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
