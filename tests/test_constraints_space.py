"""Hard constraints, candidate building, custom-rule registration and the design space."""
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from meidnet.constraints import CONSTRAINTS, build_candidate, evaluate, explain  # noqa: E402
from meidnet.designspace import enumerate_space, total_compositions  # noqa: E402
from meidnet.family import load_family  # noqa: E402


def halide():
    return load_family("perovskite_abx3", variant="halide")


def test_known_perovskite_passes_everything():
    fam = halide()
    # RbMnI3 is accepted by the published windows (CsPbBr3 is NOT: with pymatgen's averaged ionic radii its
    # octahedral factor is 0.94 > 0.90 - a property of the published method that the Studio makes visible).
    cand = evaluate(build_candidate(fam, {"A": "Rb", "B": "Mn", "X": "I"}), fam.constraints)
    assert cand.passed, [r.to_dict() for r in cand.results if not r.passed]
    assert cand.formula() == "RbMnI3"
    assert len(cand.structure) == 5
    names = [r.name for r in cand.results]
    assert names == ["min_distance", "symmetry_refinement", "charge_neutrality", "bond_window",
                     "tolerance_factor", "octahedral_factor"]


def test_charge_imbalance_is_explained():
    fam = halide()
    # Cs(+1) Sc(+3) Br(-1)x3 = +1 → not neutral
    cand = evaluate(build_candidate(fam, {"A": "Cs", "B": "Sc", "X": "Br"}), fam.constraints)
    r = next(r for r in cand.results if r.name == "charge_neutrality")
    assert not r.passed and "no combination" in r.detail
    assert cand.first_failure == "charge_neutrality"


def test_lattice_rule_is_bond_sum():
    from meidnet.chem import ionic_radius
    fam = halide()
    cand = build_candidate(fam, {"A": "Cs", "B": "Pb", "X": "I"})
    assert abs(cand.lattice_a - 2 * (ionic_radius("Pb") + ionic_radius("I"))) < 1e-9


def test_double_perovskite_candidate():
    fam = load_family("double_perovskite_a2bbx6", variant="halide")
    cand = evaluate(build_candidate(fam, {"A": "Cs", "B1": "Ag", "B2": "Bi", "X": "I"}), fam.constraints)
    assert cand.formula() == "Cs2AgBiI6"
    # built in the 10-atom fcc primitive cell (edge a/√2, 60°) ...
    assert len(cand.raw) == 10
    assert abs(cand.raw.lattice.abc[0] * np.sqrt(2) - cand.lattice_a) < 1e-6
    assert abs(cand.raw.lattice.angles[0] - 60.0) < 1e-6
    # ... and symmetry refinement returns the conventional 40-atom Fm-3m cell with edge a
    assert cand.structure.composition.reduced_formula == cand.raw.composition.reduced_formula
    assert abs(cand.structure.lattice.abc[0] - cand.lattice_a) < 1e-3
    assert cand.structure.get_space_group_info()[1] == 225
    assert cand.passed, [r.to_dict() for r in cand.results if not r.passed]


def test_custom_rule_registration_and_use():
    @CONSTRAINTS.register("no_lead_test", "Rejects lead.")
    def no_lead(cand):
        return cand.result("no_lead_test", "Pb" not in cand.elements.values())

    fam = halide()
    rules = fam.constraints + [{"name": "no_lead_test"}]
    lead = evaluate(build_candidate(fam, {"A": "Cs", "B": "Pb", "X": "Br"}), rules)
    assert not next(r for r in lead.results if r.name == "no_lead_test").passed
    assert evaluate(build_candidate(fam, {"A": "Rb", "B": "Mn", "X": "I"}), rules).passed


def test_explanations_fill_parameters():
    title, text = explain("tolerance_factor", {"min": 0.75, "max": 1.02})
    assert "0.75" in text and "Goldschmidt" in title


def test_design_space_counts_and_predictions():
    from meidnet.checkpoint import load_checkpoint
    fam = load_family("perovskite_abx3", variant="oxide")
    lm = load_checkpoint(os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"))
    space = enumerate_space(fam, lm)
    assert space["total"] == total_compositions(fam) == 21 * 23
    assert len(space["rows"]) == space["total"]
    row = next(r for r in space["rows"] if r["f"] == "BaTiO3")
    assert all(row["ok"].values())
    assert set(row["p"]) == {"heat_all", "dir_gap"}
    assert 0.5 < row["d"]["tolerance_factor"] < 1.5


def _published():
    from meidnet.checkpoint import load_checkpoint
    return load_checkpoint(os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"))


def test_rules_sharing_a_name_get_their_own_ids():
    from meidnet.constraints import assign_rule_ids, rule_key
    fam = halide()
    assert [rule_key(c) for c in fam.constraints] == [c["name"] for c in fam.constraints]   # unique: unchanged
    rules = assign_rule_ids(fam.constraints + [{"name": "property_window", "property": "dir_gap", "min": 1.0},
                                               {"name": "property_window", "property": "heat_all", "max": 0.0}])
    assert [rule_key(c) for c in rules][-2:] == ["property_window_dir_gap", "property_window_heat_all"]
    cand = build_candidate(fam, {"A": "Rb", "B": "Mn", "X": "I"})
    cand.predictions = {"dir_gap": 0.5, "heat_all": -0.2}
    names = {r.name: r.passed for r in evaluate(cand, rules).results}
    assert names["property_window_dir_gap"] is False and names["property_window_heat_all"] is True
    title, _ = explain("property_window_dir_gap", rules[-2])          # the id still finds the rule's text
    assert title == "Predicted dir_gap window"


def test_design_space_applies_property_windows():
    from meidnet.constraints import assign_rule_ids
    fam = halide()
    fam.constraints = assign_rule_ids(fam.constraints + [{"name": "property_window", "property": "dir_gap",
                                                          "min": 2.0, "max": 3.0}])
    space = enumerate_space(fam, _published())
    passing = [r for r in space["rows"] if all(r["ok"].values())]
    assert passing and all(2.0 <= r["p"]["dir_gap"] <= 3.0 for r in passing)      # the window is enforced
    assert all(r["d"]["property_window"] is not None for r in space["rows"])
    assert [r["name"] for r in space["rules"]][-1] == "property_window"


def test_family_overrides_select_a_rule_by_id(tmp_path):
    import yaml
    src = yaml.safe_load(open(os.path.join(ROOT, "meidnet", "families", "double_perovskite_a2bbx6.yaml"),
                              encoding="utf-8"))
    src["constraints"].append({"name": "bond_window", "from": "X", "to": "B2", "low": 0.75, "high": 1.35, "cutoff": 5.0})
    path = tmp_path / "two_windows.yaml"
    path.write_text(yaml.safe_dump(src), encoding="utf-8")
    fam = load_family(str(path), variant="halide", overrides={"bond_window_X_B2": {"high": 1.2}})
    windows = {c["id"]: c["high"] for c in fam.constraints if c["name"] == "bond_window"}
    assert windows == {"bond_window_X_B1": 1.35, "bond_window_X_B2": 1.2}
