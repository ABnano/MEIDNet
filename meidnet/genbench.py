"""
Score a set of generated crystal structures, from any model, with the metric families of LeMat-GenBench and
MEIDNet's conditional extension.

    meidnet score generated/ --reference data/perov5                       # a folder of CIF files
    meidnet score generated/ --reference data/perov5 --targets targets.csv  # + the conditional metrics
    meidnet score generated/ --reference data/perov5 --mlip                 # + stability and SUN with MACE

Metric families, named as in LeMat-GenBench (Siron et al. 2025):

    validity      charge neutrality (an oxidation-state assignment that sums to zero), minimum interatomic distance
                  against the atomic radii, physical plausibility (density, cell lengths and angles)
    uniqueness    distinct structures within the set (pymatgen StructureMatcher)
    novelty       structures not in the reference set: by composition (reduced formula) and by structure
                  (StructureMatcher against the reference entries of the same composition)
    diversity     Shannon entropy and counts of elements, space groups and site numbers; spread of the density
    distribution  Jensen-Shannon distance of the element frequencies and of the number of sites, against the reference
    stability     with --mlip: relaxation with MACE and the formation energy against elemental references
                  (meidnet.screen); "stable" means a formation energy of at most 0.1 eV/atom. This is a proxy, not the
                  energy above the convex hull that LeMat-GenBench computes
    sun           stable and unique and novel (structure novelty), with --mlip

The conditional extension needs targets.csv with a column `file` (the CIF file name) and, per property, a point target
`<p>_target` and/or a window `<p>_min` / `<p>_max` (a bound such as "at most 1.0" is `<p>_max` = 1.0), and optionally
`<p>_value` (the value the submitter reports for the structure; `source` says how it was obtained). Without
`<p>_value`, --model <meidnet checkpoint> predicts it from the structure (labelled "model-predicted").

    target_success        inside the window when one is given, else |value - target| <= tolerance (per property)
    target_error          mean |value - target|, or the distance outside the window when there is no point target
    multi_success         every targeted property within tolerance
    constraint_success    valid structures among those that hit their targets
    conditional_diversity distinct compositions among the successes, over the successes
    target_coverage       distinct target vectors with at least one success, over the distinct targets
    interpolation_share   targets inside the reference's property range (with --reference property columns)

Everything that could not be computed is listed under "not_computed", with the reason.
"""
from __future__ import annotations

import csv
import math
import os
import warnings
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

warnings.filterwarnings("ignore")

MATCHER = {"ltol": 0.2, "stol": 0.3, "angle_tol": 5.0}
DISTANCE_FACTOR = 0.6          # the closest pair must be at least this times the sum of the two atomic radii
DISTANCE_FLOOR = 0.8           # Å, whatever the radii
DENSITY_RANGE = (0.5, 25.0)    # g/cm3
LENGTH_RANGE = (1.0, 60.0)     # Å
ANGLE_RANGE = (10.0, 170.0)    # degrees
STABLE_DHF = 0.10              # eV/atom, formation energy against elemental references (meidnet.screen's proxy)


@dataclass
class Entry:
    name: str
    structure: object           # pymatgen Structure
    formula: str = ""
    n_sites: int = 0
    valid: bool = False
    checks: dict = field(default_factory=dict)
    space_group: int | None = None
    density: float = float("nan")
    unique: bool = True
    novel_composition: bool | None = None
    novel_structure: bool | None = None
    dhf: float | None = None
    stable: bool | None = None


# ───────────────────────── loading ─────────────────────────
def load_structures(path: str, limit: int | None = None, log=print) -> list[Entry]:
    """CIF files of a folder (recursively), or the `cif` column of a CSV (`id`/`file`/`material_id` names the entry)."""
    from pymatgen.core import Structure
    entries, failed = [], []
    if os.path.isdir(path):
        files = sorted(os.path.join(d, f) for d, _, fs in os.walk(path) for f in fs if f.lower().endswith(".cif"))
        if limit:
            files = files[:limit]
        for p in files:
            try:
                entries.append(Entry(os.path.basename(p), Structure.from_file(p)))
            except Exception as e:
                failed.append(f"{os.path.basename(p)}: {type(e).__name__}")
    else:
        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if "cif" not in (rows[0].keys() if rows else {}):
            raise SystemExit(f"{path} has no 'cif' column")
        idc = next((c for c in ("file", "id", "material_id") if rows and c in rows[0]), None)
        for i, r in enumerate(rows[:limit] if limit else rows):
            name = str(r[idc]) if idc else f"row{i}"
            try:
                entries.append(Entry(name, Structure.from_str(r["cif"], fmt="cif")))
            except Exception as e:
                failed.append(f"{name}: {type(e).__name__}")
    for e in entries:
        e.formula = e.structure.composition.reduced_formula
        e.n_sites = len(e.structure)
    if failed:
        log(f"  {len(failed)} file(s) could not be read: {', '.join(failed[:5])}{' …' if len(failed) > 5 else ''}")
    if not entries:
        raise SystemExit(f"no structures read from {path}")
    return entries


class Reference:
    """The reference set: compositions, lazily parsed structures per composition, and property columns if present."""

    def __init__(self, path: str, log=print):
        self.name = os.path.basename(os.path.normpath(path))
        self.rows: list[dict] = []
        files = ([os.path.join(path, f"{s}.csv") for s in ("train", "val", "test")] if os.path.isdir(path) else [path])
        files = [p for p in files if os.path.exists(p)]
        if not files:
            raise SystemExit(f"no reference CSV found at {path} (expected train/val/test.csv or one CSV with a 'cif' or 'formula' column)")
        for p in files:
            with open(p, encoding="utf-8", newline="") as f:
                self.rows += list(csv.DictReader(f))
        self.has_cif = bool(self.rows) and "cif" in self.rows[0]
        self.formulas: set[str] = set()
        self.by_formula: dict[str, list[int]] = {}
        from pymatgen.core import Composition
        for i, r in enumerate(self.rows):
            f = r.get("formula") or ""
            try:
                key = Composition(f).reduced_formula if f else None
            except Exception:
                key = None
            if key:
                self.formulas.add(key)
                self.by_formula.setdefault(key, []).append(i)
        self.properties = [c for c in (self.rows[0].keys() if self.rows else [])
                           if c and c not in ("cif", "formula", "material_id", "id") and not c.startswith("Unnamed") and _numeric_column(self.rows, c)]
        self._parsed: dict[int, object] = {}
        self.elements = Counter()
        self.sites = Counter()
        for r in self.rows:
            try:
                comp = Composition(r.get("formula") or "")
                for el, n in comp.get_el_amt_dict().items():
                    self.elements[el] += n
                self.sites[int(round(comp.num_atoms))] += 1
            except Exception:
                pass
        log(f"  reference {self.name}: {len(self.rows):,} entries, {len(self.formulas):,} compositions"
            + (f", properties {', '.join(self.properties)}" if self.properties else ""))

    def structures_of(self, formula: str) -> list:
        from pymatgen.core import Structure
        out = []
        for i in self.by_formula.get(formula, []):
            if i not in self._parsed:
                try:
                    self._parsed[i] = Structure.from_str(self.rows[i]["cif"], fmt="cif") if self.has_cif else None
                except Exception:
                    self._parsed[i] = None
            if self._parsed[i] is not None:
                out.append(self._parsed[i])
        return out

    def property_range(self, column: str) -> tuple[float, float] | None:
        vals = [float(r[column]) for r in self.rows if _is_number(r.get(column))]
        return (min(vals), max(vals)) if vals else None


def _is_number(v) -> bool:
    try:
        return v is not None and v != "" and math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _numeric_column(rows, c) -> bool:
    sample = [r.get(c) for r in rows[:50]]
    return any(_is_number(v) for v in sample) and all(_is_number(v) or v in (None, "") for v in sample)


# ───────────────────────── metric families ─────────────────────────
def validity(entries: list[Entry]) -> dict:
    from pymatgen.core import Element
    for e in entries:
        s, checks = e.structure, {}
        try:
            checks["charge_neutral"] = bool(s.composition.oxi_state_guesses(max_sites=-1))
        except Exception:
            checks["charge_neutral"] = False
        try:
            dm = s.distance_matrix
            np.fill_diagonal(dm, np.inf)
            radii = np.array([float(Element(sp.symbol).atomic_radius or 1.0) for sp in s.species])
            need = np.maximum(DISTANCE_FLOOR, DISTANCE_FACTOR * (radii[:, None] + radii[None, :]))
            checks["min_distance"] = bool(len(s) == 1 or np.all(dm >= need))
        except Exception:
            checks["min_distance"] = False
        try:
            abc, ang = s.lattice.abc, s.lattice.angles
            e.density = float(s.density)
            checks["plausible"] = bool(DENSITY_RANGE[0] <= e.density <= DENSITY_RANGE[1] and all(LENGTH_RANGE[0] <= x <= LENGTH_RANGE[1] for x in abc)
                                       and all(ANGLE_RANGE[0] <= x <= ANGLE_RANGE[1] for x in ang))
        except Exception:
            checks["plausible"] = False
        e.checks = checks
        e.valid = all(checks.values())
    n = len(entries)
    return {"n": n, "valid_rate": sum(e.valid for e in entries) / n,
            "charge_neutral_rate": sum(e.checks["charge_neutral"] for e in entries) / n,
            "min_distance_rate": sum(e.checks["min_distance"] for e in entries) / n,
            "plausible_rate": sum(e.checks["plausible"] for e in entries) / n,
            "definition": f"charge neutrality by oxidation-state assignment; closest pair >= max({DISTANCE_FLOOR} Å, "
                          f"{DISTANCE_FACTOR} x the sum of the atomic radii); density {DENSITY_RANGE[0]}-{DENSITY_RANGE[1]} g/cm3, "
                          f"cell lengths {LENGTH_RANGE[0]}-{LENGTH_RANGE[1]} Å, angles {ANGLE_RANGE[0]}-{ANGLE_RANGE[1]} degrees"}


def uniqueness(entries: list[Entry]) -> dict:
    from pymatgen.analysis.structure_matcher import StructureMatcher
    sm = StructureMatcher(primitive_cell=True, **MATCHER)
    groups = sm.group_structures([e.structure for e in entries])
    seen = {}
    for g in groups:
        for k, s in enumerate(g):
            seen[id(s)] = k == 0
    for e in entries:
        e.unique = seen.get(id(e.structure), True)
    n = len(entries)
    return {"n": n, "unique": len(groups), "unique_rate": len(groups) / n, "duplicates": n - len(groups),
            "definition": f"pymatgen StructureMatcher (ltol {MATCHER['ltol']}, stol {MATCHER['stol']}, angle_tol {MATCHER['angle_tol']}, primitive cells)"}


def novelty(entries: list[Entry], ref: Reference) -> dict:
    from pymatgen.analysis.structure_matcher import StructureMatcher
    sm = StructureMatcher(primitive_cell=True, **MATCHER)
    for e in entries:
        e.novel_composition = e.formula not in ref.formulas
        if e.novel_composition:
            e.novel_structure = True
        elif ref.has_cif:
            e.novel_structure = not any(sm.fit(e.structure, r) for r in ref.structures_of(e.formula))
        else:
            e.novel_structure = None
    n = len(entries)
    out = {"n": n, "reference": ref.name, "reference_entries": len(ref.rows),
           "novel_composition_rate": sum(bool(e.novel_composition) for e in entries) / n,
           "definition": "composition: the reduced formula does not occur in the reference; structure: no reference entry of the "
                         "same composition matches (StructureMatcher)"}
    if ref.has_cif:
        out["novel_structure_rate"] = sum(bool(e.novel_structure) for e in entries) / n
    return out


def _entropy(counter: Counter) -> float:
    tot = sum(counter.values())
    return max(0.0, float(-sum((c / tot) * math.log2(c / tot) for c in counter.values() if c))) if tot else 0.0


def diversity(entries: list[Entry]) -> dict:
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    elements, groups, sites = Counter(), Counter(), Counter()
    for e in entries:
        for el, n in e.structure.composition.get_el_amt_dict().items():
            elements[el] += n
        sites[e.n_sites] += 1
        try:
            e.space_group = int(SpacegroupAnalyzer(e.structure, symprec=0.1).get_space_group_number())
        except Exception:
            e.space_group = None
        if e.space_group:
            groups[e.space_group] += 1
    dens = np.array([e.density for e in entries if math.isfinite(e.density)])
    return {"n": len(entries), "elements": len(elements), "element_entropy_bits": _entropy(elements),
            "space_groups": len(groups), "space_group_entropy_bits": _entropy(groups),
            "site_numbers": len(sites), "site_number_entropy_bits": _entropy(sites),
            "density_mean": float(dens.mean()) if len(dens) else None, "density_std": float(dens.std()) if len(dens) else None,
            "compositions": len({e.formula for e in entries}),
            "definition": "Shannon entropy (bits) and counts of the elements, the space groups (spglib, symprec 0.1) and the numbers of sites; the density's spread"}


def _jsd(p: Counter, q: Counter) -> float:
    keys = set(p) | set(q)
    sp, sq = sum(p.values()) or 1, sum(q.values()) or 1
    P = np.array([p.get(k, 0) / sp for k in keys]); Q = np.array([q.get(k, 0) / sq for k in keys])
    M = (P + Q) / 2
    kl = lambda a, b: float(sum(x * math.log2(x / y) for x, y in zip(a, b) if x > 0))  # noqa: E731
    return math.sqrt(max(0.0, (kl(P, M) + kl(Q, M)) / 2))


def distribution(entries: list[Entry], ref: Reference) -> dict:
    elements, sites = Counter(), Counter()
    for e in entries:
        for el, n in e.structure.composition.get_el_amt_dict().items():
            elements[el] += n
        sites[e.n_sites] += 1
    return {"element_jsd": _jsd(elements, ref.elements), "site_number_jsd": _jsd(sites, ref.sites), "reference": ref.name,
            "definition": "Jensen-Shannon distance (base 2, 0 = identical) of the element frequencies and of the numbers of sites, generated against reference"}


def stability(entries: list[Entry], model_path: str = "medium", device: str = "auto", fmax: float = 0.05, steps: int = 500, log=print) -> dict:
    try:
        from ase.io import read as ase_read  # noqa: F401
        from mace.calculators import mace_mp
        from pymatgen.io.ase import AseAtomsAdaptor
    except ImportError:
        raise SystemExit("stability needs the optional packages: pip install 'meidnet[stability]'") from None
    from meidnet.screen import ARTEFACT_THRESHOLD, reference_energies, relax
    import torch
    dev = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
    calc = mace_mp(model=model_path, device=dev, default_dtype="float32")
    elements = {sp.symbol for e in entries for sp in e.structure.species}
    refs = reference_energies(elements, calc, log=log)
    stable = 0
    for e in entries:
        atoms = AseAtomsAdaptor.get_atoms(e.structure)
        converged, energy = relax(atoms, calc, fmax=fmax, steps=steps)
        comp = e.structure.composition.get_el_amt_dict()
        ref_e = sum(refs.get(el, float("nan")) * n for el, n in comp.items()) / sum(comp.values())
        dhf = energy - ref_e
        e.dhf = float(dhf) if math.isfinite(dhf) else None
        e.stable = bool(e.dhf is not None and abs(e.dhf) <= ARTEFACT_THRESHOLD and e.dhf <= STABLE_DHF)
        stable += e.stable
    n = len(entries)
    vals = [e.dhf for e in entries if e.dhf is not None]
    return {"n": n, "stable_rate": stable / n, "dhf_mean": float(np.mean(vals)) if vals else None, "dhf_median": float(np.median(vals)) if vals else None,
            "threshold_ev_per_atom": STABLE_DHF, "mlip": f"MACE-MP ({model_path})",
            "definition": "relaxed with MACE; formation energy per atom against elemental reference phases (meidnet.screen); stable if <= "
                          f"{STABLE_DHF} eV/atom. A proxy: not the energy above the convex hull"}


def sun(entries: list[Entry]) -> dict:
    n = len(entries)
    ok = [e for e in entries if e.stable and e.unique and e.novel_structure]
    return {"n": n, "sun": len(ok), "sun_rate": len(ok) / n, "definition": "stable and unique and novel (by structure), over all structures"}


# ───────────────────────── the conditional extension ─────────────────────────
TARGET_SUFFIXES = ("_target", "_min", "_max")


def load_targets(path: str) -> tuple[list[dict], list[str]]:
    """targets.csv: `file` + per property `<p>_target` (a point target) and/or `<p>_min` / `<p>_max` (a window, e.g. a
    bound "at most 1.0" is `<p>_max` = 1.0), optionally `<p>_value` and `source`."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or not any(c in rows[0] for c in ("file", "id", "material_id")):
        raise SystemExit(f"{path} needs a 'file' column naming each structure")
    props = sorted({c[: -len(s)] for c in rows[0] for s in TARGET_SUFFIXES if c.endswith(s) and len(c) > len(s)})
    if not props:
        raise SystemExit(f"{path} has no '<property>_target', '<property>_min' or '<property>_max' column")
    return rows, props


def _number(v) -> float | None:
    return float(v) if _is_number(v) else None


def predict_with_model(entries: list[Entry], checkpoint: str, props: list[str], log=print) -> dict[str, dict[str, float]]:
    """Encoder-side predictions of a MEIDNet checkpoint for each structure (labelled model-predicted)."""
    import torch
    from meidnet.checkpoint import load_checkpoint
    from meidnet.data import featurize
    lm = load_checkpoint(checkpoint, device="cpu")
    cols = list(lm.stats.columns)
    missing = [p for p in props if p not in cols]
    if missing:
        raise SystemExit(f"the model predicts {', '.join(cols)}, not {', '.join(missing)}")
    out = {}
    with torch.no_grad():
        for e in entries:
            try:
                x = torch.tensor(featurize(e.structure, lm.model.max_sites), dtype=torch.float32).unsqueeze(0)
                zc, _ = lm.model.encode_crystal(x)
                pred = lm.stats.denormalize_tensor(lm.model.property_decoder(zc))[0].numpy()
                out[e.name] = {c: float(v) for c, v in zip(cols, pred)}
            except Exception as ex:
                log(f"  [warn] no prediction for {e.name}: {ex}")
    return out


def conditional(entries: list[Entry], rows: list[dict], props: list[str], tolerances: dict[str, float],
                ref: Reference | None, predictions: dict[str, dict[str, float]] | None) -> dict:
    by_name = {e.name: e for e in entries}
    by_stem = {os.path.splitext(e.name)[0]: e for e in entries}
    matched, per = [], {p: {"errors": [], "hits": 0, "n": 0, "windowed": 0} for p in props}
    successes, target_keys, hit_keys, sources = [], set(), set(), Counter()
    for r in rows:
        key = str(r.get("file") or r.get("id") or r.get("material_id"))
        e = by_name.get(key) or by_stem.get(os.path.splitext(key)[0])
        if e is None:
            continue
        matched.append(e)
        tvec, all_hit, any_target = [], True, False
        for p in props:
            t, lo, hi = _number(r.get(f"{p}_target")), _number(r.get(f"{p}_min")), _number(r.get(f"{p}_max"))
            if t is None and lo is None and hi is None:
                continue
            any_target = True
            tvec.append((p, t, lo, hi))
            v = r.get(f"{p}_value")
            src = r.get("source") or ("reported" if _is_number(v) else None)
            if not _is_number(v) and predictions and e.name in predictions and p in predictions[e.name]:
                v, src = predictions[e.name][p], "model-predicted"
            if not _is_number(v):
                all_hit = False
                continue
            sources[src] += 1
            v = float(v)
            if lo is not None or hi is not None:          # a window: inside it is a success; the error is the distance outside it
                hit = (lo is None or v >= lo) and (hi is None or v <= hi)
                err = abs(v - t) if t is not None else max(0.0, (lo - v) if lo is not None else 0.0, (v - hi) if hi is not None else 0.0)
                per[p]["windowed"] += 1
            else:                                          # a point target: within the tolerance is a success
                err = abs(v - t)
                hit = err <= tolerances[p]
            per[p]["errors"].append(err); per[p]["n"] += 1
            per[p]["hits"] += hit
            all_hit &= hit
        if any_target:
            tkey = tuple(tvec)
            target_keys.add(tkey)
            if all_hit and tvec:
                successes.append(e)
                hit_keys.add(tkey)
    n = len(matched)
    out = {"n_structures_with_targets": n, "n_distinct_targets": len(target_keys), "tolerances": tolerances, "value_sources": dict(sources),
           "per_property": {p: {"target_success_rate": (d["hits"] / d["n"]) if d["n"] else None, "target_error_mean": (float(np.mean(d["errors"])) if d["errors"] else None),
                                "n": d["n"], "n_windowed": d["windowed"]} for p, d in per.items()},
           "multi_success_rate": (len(successes) / n) if n else None,
           "constraint_success_rate": (sum(e.valid for e in successes) / len(successes)) if successes else None,
           "conditional_diversity": (len({e.formula for e in successes}) / len(successes)) if successes else None,
           "target_coverage": (len(hit_keys) / len(target_keys)) if target_keys else None,
           "definition": "target success: the value lies inside the window <p>_min..<p>_max when one is given, else |value - target| <= tolerance; "
                         "target error: |value - target|, or the distance outside the window when there is no point target; multi-property "
                         "success: every targeted property a success; constraint success: valid structures among the successes; conditional "
                         "diversity: distinct compositions among the successes; target coverage: distinct targets with at least one success"}
    if ref and ref.properties:
        inside = total = 0
        ranges = {p: ref.property_range(p) for p in props if p in ref.properties}
        for tkey in target_keys:
            for p, t, lo, hi in tkey:
                anchor = t if t is not None else ((lo + hi) / 2 if lo is not None and hi is not None else (lo if lo is not None else hi))
                if ranges.get(p):
                    total += 1
                    inside += ranges[p][0] <= anchor <= ranges[p][1]
        out["interpolation_share"] = (inside / total) if total else None
        out["reference_property_ranges"] = {p: list(r) for p, r in ranges.items() if r}
    return out


# ───────────────────────── the report ─────────────────────────
def score(structures: str, reference: str | None = None, targets: str | None = None, tolerances: dict[str, float] | None = None,
          model: str | None = None, mlip: bool = False, mlip_model: str = "medium", device: str = "auto",
          limit: int | None = None, log=print) -> dict:
    import meidnet
    log(f"reading {structures} ...")
    entries = load_structures(structures, limit, log)
    log(f"  {len(entries):,} structures")
    report = {"meidnet_version": meidnet.__version__, "structures": structures, "n": len(entries), "not_computed": {}, "families": {}}
    fam = report["families"]
    fam["validity"] = validity(entries)
    fam["uniqueness"] = uniqueness(entries)
    fam["diversity"] = diversity(entries)
    ref = None
    if reference:
        ref = Reference(reference, log)
        fam["novelty"] = novelty(entries, ref)
        if not ref.has_cif:
            report["not_computed"]["novelty.structure"] = "the reference has no 'cif' column: novelty is by composition only"
        fam["distribution"] = distribution(entries, ref)
    else:
        report["not_computed"]["novelty"] = "no --reference given"
        report["not_computed"]["distribution"] = "no --reference given"
    report["not_computed"]["distribution.embeddings"] = "Frechet distances of MLIP embeddings and MMD are not computed here"
    report["not_computed"]["hhi"] = "supply-risk indices are not computed here"
    if mlip:
        log("relaxing with MACE ...")
        fam["stability"] = stability(entries, mlip_model, device, log=log)
        fam["sun"] = sun(entries) if ref and ref.has_cif else {"n": len(entries), "sun": None, "sun_rate": None}
        if not (ref and ref.has_cif):
            report["not_computed"]["sun"] = "needs structure novelty, i.e. a reference with a 'cif' column"
        fam["stability"]["note"] = "formation energy against elemental references, not the energy above the convex hull"
    else:
        report["not_computed"]["stability"] = "pass --mlip to relax with MACE (pip install 'meidnet[stability]')"
        report["not_computed"]["sun"] = "needs --mlip"
    if targets:
        rows, props = load_targets(targets)
        tol = dict(tolerances or {})
        for p in props:
            if p not in tol:
                r = ref.property_range(p) if (ref and p in ref.properties) else None
                tol[p] = 0.05 * (r[1] - r[0]) if r else 0.1
        preds = predict_with_model(entries, model, props, log) if model else None
        fam["conditional"] = conditional(entries, rows, props, tol, ref, preds)
        if preds:
            fam["conditional"]["predictions"] = "model-predicted values from the MEIDNet checkpoint where targets.csv gave none"
    else:
        report["not_computed"]["conditional"] = "no --targets given"
    report["entries"] = [{"name": e.name, "formula": e.formula, "n_sites": e.n_sites, "valid": e.valid, **e.checks, "space_group": e.space_group,
                          "density": e.density, "unique": e.unique, "novel_composition": e.novel_composition, "novel_structure": e.novel_structure,
                          "dhf": e.dhf, "stable": e.stable} for e in entries]
    return report


def format_report(report: dict) -> str:
    f = report["families"]
    pct = lambda v: "-" if v is None else f"{100 * v:5.1f} %"  # noqa: E731
    lines = [f"# Structure generation report ({report['n']} structures, meidnet {report['meidnet_version']})", "",
             "| family | metric | value |", "|---|---|---|"]
    v = f["validity"]
    lines += [f"| validity | valid (all checks) | {pct(v['valid_rate'])} |", f"| validity | charge neutral | {pct(v['charge_neutral_rate'])} |",
              f"| validity | minimum distance | {pct(v['min_distance_rate'])} |", f"| validity | physically plausible | {pct(v['plausible_rate'])} |"]
    u = f["uniqueness"]
    lines += [f"| uniqueness | unique structures | {u['unique']} of {u['n']} ({pct(u['unique_rate'])}) |"]
    if "novelty" in f:
        n = f["novelty"]
        lines += [f"| novelty | new compositions vs {n['reference']} | {pct(n['novel_composition_rate'])} |"]
        if "novel_structure_rate" in n:
            lines += [f"| novelty | new structures vs {n['reference']} | {pct(n['novel_structure_rate'])} |"]
    d = f["diversity"]
    lines += [f"| diversity | elements (entropy) | {d['elements']} ({d['element_entropy_bits']:.2f} bits) |",
              f"| diversity | space groups (entropy) | {d['space_groups']} ({d['space_group_entropy_bits']:.2f} bits) |",
              f"| diversity | compositions | {d['compositions']} |"]
    if "distribution" in f:
        lines += [f"| distribution | element JSD vs reference | {f['distribution']['element_jsd']:.3f} |",
                  f"| distribution | site-number JSD vs reference | {f['distribution']['site_number_jsd']:.3f} |"]
    if "stability" in f:
        s = f["stability"]
        lines += [f"| stability | stable (formation energy <= {s['threshold_ev_per_atom']} eV/atom, {s['mlip']}) | {pct(s['stable_rate'])} |"]
    if "sun" in f and f["sun"].get("sun_rate") is not None:
        lines += [f"| sun | stable, unique and novel | {pct(f['sun']['sun_rate'])} |"]
    if "conditional" in f:
        c = f["conditional"]
        for p, m in c["per_property"].items():
            err = m["target_error_mean"]
            err_text = "-" if err is None else f"{err:.3g}"
            how = ("inside the window" if m.get("n_windowed") == m["n"] and m["n"] else
                   f"within {c['tolerances'][p]:g} of the target" if not m.get("n_windowed") else
                   f"window, or within {c['tolerances'][p]:g} of the target")
            lines += [f"| conditional | {p}: target success ({how}) | {pct(m['target_success_rate'])} |",
                      f"| conditional | {p}: mean target error | {err_text} |"]
        lines += [f"| conditional | multi-property success | {pct(c['multi_success_rate'])} |",
                  f"| conditional | constraint success | {pct(c['constraint_success_rate'])} |",
                  f"| conditional | conditional diversity | {pct(c['conditional_diversity'])} |",
                  f"| conditional | target coverage | {pct(c['target_coverage'])} |"]
        if "interpolation_share" in c:
            lines += [f"| conditional | targets inside the reference range | {pct(c['interpolation_share'])} |"]
    if report["not_computed"]:
        lines += ["", "Not computed: " + "; ".join(f"{k} ({v})" for k, v in report["not_computed"].items())]
    return "\n".join(lines)
