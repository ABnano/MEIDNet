"""`meidnet score`: the LeMat-GenBench metric families and the conditional extension on the paper's 26 CIFs."""
import csv
import json
import os

import pytest

pytest.importorskip("pymatgen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIFS = os.path.join(ROOT, "examples", "perov5", "paper_results")
MINI = os.path.join(ROOT, "tests", "data", "perov5_mini.csv")
QUIET = {"log": lambda *a, **k: None}


@pytest.fixture(scope="module")
def report():
    from meidnet.genbench import score
    return score(CIFS, reference=MINI, **QUIET)


def _rate(v):
    assert v is not None and 0.0 <= v <= 1.0, v


def test_reads_every_cif_recursively(report):
    n_files = sum(f.lower().endswith(".cif") for _, _, fs in os.walk(CIFS) for f in fs)
    assert report["n"] == n_files == len(report["entries"]) > 20


def test_metric_families(report):
    fam = report["families"]
    assert set(fam) >= {"validity", "uniqueness", "novelty", "diversity", "distribution"}
    v = fam["validity"]
    for k in ("valid_rate", "charge_neutral_rate", "min_distance_rate", "plausible_rate"):
        _rate(v[k])
    assert v["valid_rate"] <= min(v["charge_neutral_rate"], v["min_distance_rate"], v["plausible_rate"])
    u = fam["uniqueness"]
    assert u["unique"] + u["duplicates"] == u["n"] and u["unique"] >= 1
    d = fam["diversity"]
    assert d["elements"] >= 3 and d["element_entropy_bits"] > 0 and d["compositions"] >= 1
    assert d["site_numbers"] >= 1 and d["density_mean"] > 0


def test_novelty_and_distribution_against_the_reference(report):
    n = report["families"]["novelty"]
    assert n["reference"] == "perov5_mini.csv" and n["reference_entries"] > 0
    _rate(n["novel_composition_rate"])
    _rate(n["novel_structure_rate"])                     # the mini CSV has a cif column
    assert n["novel_structure_rate"] >= n["novel_composition_rate"] - 1e-9
    assert all(e["novel_structure"] is not None for e in report["entries"])
    dist = report["families"]["distribution"]
    assert 0.0 <= dist["element_jsd"] <= 1.0 and 0.0 <= dist["site_number_jsd"] <= 1.0
    assert "novelty.structure" not in report["not_computed"]


def test_what_is_not_computed_is_named(report):
    nc = report["not_computed"]
    assert "stability" in nc and "sun" in nc and "conditional" in nc and "hhi" in nc
    assert "--mlip" in nc["stability"]


def test_without_reference_novelty_is_not_computed():
    from meidnet.genbench import score
    r = score(CIFS, limit=4, **QUIET)
    assert r["n"] == 4 and "novelty" not in r["families"] and "novelty" in r["not_computed"]


def test_conditional_extension(tmp_path, report):
    from meidnet.genbench import score
    names = [e["name"] for e in report["entries"][:4]]
    rows = [{"file": names[0], "dir_gap_target": 2.0, "dir_gap_value": 2.0, "source": "dft"},
            {"file": names[1], "dir_gap_target": 2.0, "dir_gap_value": 2.2, "source": "dft"},
            {"file": names[2], "dir_gap_target": 2.0, "dir_gap_value": 5.0, "source": "dft"},
            {"file": names[3], "dir_gap_target": 2.0, "dir_gap_value": "", "source": ""}]
    targets = tmp_path / "targets.csv"
    with open(targets, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    r = score(CIFS, reference=MINI, targets=str(targets), tolerances={"dir_gap": 0.3}, **QUIET)
    c = r["families"]["conditional"]
    assert c["n_structures_with_targets"] == 4 and c["n_distinct_targets"] == 1
    p = c["per_property"]["dir_gap"]
    assert p["n"] == 3 and p["target_success_rate"] == pytest.approx(2 / 3)
    assert p["target_error_mean"] == pytest.approx((0.0 + 0.2 + 3.0) / 3)
    assert c["multi_success_rate"] == pytest.approx(0.5)      # the row without a value is not a success
    assert c["target_coverage"] == 1.0
    _rate(c["constraint_success_rate"])
    _rate(c["conditional_diversity"])
    assert c["interpolation_share"] == 1.0                     # 2.0 eV lies inside the reference's dir_gap range
    assert c["value_sources"] == {"dft": 3}
    assert c["tolerances"] == {"dir_gap": 0.3}


def test_windows_and_bounds(tmp_path, report):
    """A bound ("at most 1.0") is a window, not a point target: a value far below it is a success with no error."""
    from meidnet.genbench import format_report, load_targets, score
    names = [e["name"] for e in report["entries"][:3]]
    targets = tmp_path / "bounds.csv"
    targets.write_text("file,heat_all_max,heat_all_value,dir_gap_target,dir_gap_min,dir_gap_max,dir_gap_value\n"
                       f"{names[0]},1.0,-2.2,1.5,1.2,1.8,1.5\n"
                       f"{names[1]},1.0,1.4,1.5,1.2,1.8,1.9\n"
                       f"{names[2]},1.0,0.9,,1.2,1.8,1.0\n", encoding="utf-8")
    assert load_targets(str(targets))[1] == ["dir_gap", "heat_all"]
    r = score(CIFS, reference=MINI, targets=str(targets), tolerances={"dir_gap": 5.0}, **QUIET)   # a window overrides the tolerance
    c = r["families"]["conditional"]
    h, g = c["per_property"]["heat_all"], c["per_property"]["dir_gap"]
    assert h["n"] == 3 and h["n_windowed"] == 3 and h["target_success_rate"] == pytest.approx(2 / 3)
    assert h["target_error_mean"] == pytest.approx((0.0 + 0.4 + 0.0) / 3)            # distance outside the window
    assert g["target_success_rate"] == pytest.approx(1 / 3)                            # 1.9 and 1.0 lie outside 1.2-1.8
    assert g["target_error_mean"] == pytest.approx((0.0 + 0.4 + 0.2) / 3)              # |v - t| where t is given, else distance
    assert c["multi_success_rate"] == pytest.approx(1 / 3) and c["n_distinct_targets"] == 2
    assert c["interpolation_share"] == 1.0
    text = format_report(r)
    assert "heat_all: target success (inside the window)" in text and text.isascii()


def test_default_tolerance_is_five_percent_of_the_reference_range(tmp_path, report):
    from meidnet.genbench import Reference, score
    name = report["entries"][0]["name"]
    targets = tmp_path / "t.csv"
    targets.write_text(f"file,heat_all_target,heat_all_value\n{name},0.0,0.01\n", encoding="utf-8")
    r = score(CIFS, reference=MINI, targets=str(targets), limit=3, **QUIET)
    lo, hi = Reference(MINI, **QUIET).property_range("heat_all")
    assert r["families"]["conditional"]["tolerances"]["heat_all"] == pytest.approx(0.05 * (hi - lo))


def test_targets_need_a_file_column(tmp_path):
    from meidnet.genbench import load_targets
    bad = tmp_path / "bad.csv"
    bad.write_text("name,dir_gap_target\nx.cif,2.0\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_targets(str(bad))
    bad.write_text("file,dir_gap\nx.cif,2.0\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_targets(str(bad))
    bad.write_text("file,_max\nx.cif,2.0\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_targets(str(bad))


def test_csv_with_cif_column_as_input(tmp_path):
    from meidnet.genbench import score
    with open(MINI, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))[:5]
    src = tmp_path / "gen.csv"
    with open(src, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "cif"])
        w.writeheader()
        w.writerows([{"id": r["material_id"], "cif": r["cif"]} for r in rows])
    r = score(str(src), **QUIET)
    assert r["n"] == 5 and {e["name"] for e in r["entries"]} == {r_["material_id"] for r_ in rows}


def test_format_report_is_a_table(report):
    from meidnet.genbench import format_report
    text = format_report(report)
    assert text.startswith("# Structure generation report")
    assert "| validity | valid (all checks) |" in text and "| novelty | new structures vs perov5_mini.csv |" in text
    assert "Not computed:" in text


def test_cli_score_writes_the_json_report(tmp_path, capsys):
    from meidnet.cli import main
    out = tmp_path / "sub" / "report.json"
    main(["score", CIFS, "--reference", MINI, "--limit", "5", "--tolerance", "dir_gap=0.5", "--out", str(out)])
    captured = capsys.readouterr().out
    assert "| uniqueness |" in captured and f"report -> {out}" in captured
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["n"] == 5 and r["meidnet_version"]
    with pytest.raises(SystemExit):
        main(["score", CIFS, "--limit", "2", "--tolerance", "dir_gap"])
