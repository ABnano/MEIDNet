"""The benchmark protocol and method records (scripts/benchmarks.py) and the scoring code (meidnet.benchmark):
schema rules, ordering and colours of the leaderboards, verification, and the metrics themselves."""
import importlib.util
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

spec = importlib.util.spec_from_file_location("benchmarks", os.path.join(ROOT, "scripts", "benchmarks.py"))
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

from meidnet import benchmark as B  # noqa: E402

PROTO = {"version": "t-v1", "data_dir": "data/t", "tasks": [
    {"id": "property_prediction", "name": "Property prediction", "headline": "mae_x",
     "metrics": [{"id": "mae_x", "label": "MAE x", "better": "lower", "digits": 2},
                 {"id": "r2_x", "label": "R2 x", "better": "higher", "digits": 2}]}]}


def _ds(**over):
    return bench.Dataset.model_validate({"id": "tset", "name": "T", "description": "d.", "protocol": PROTO, **over})


def _sub(**over):
    base = {"id": "t-row", "dataset": "tset", "protocol": "t-v1", "date": "2026-01-01", "submitter": {"name": "x"},
            "modalities": ["structure"], "method": {"name": "M"},
            "results": {"property_prediction": {"mae_x": 0.3, "r2_x": 0.5}}}
    base.update(over)
    return bench.Submission.model_validate(base)


def test_repository_files_validate():
    assert bench.validate() == []
    cat = bench.catalog()
    assert len(cat.databases) >= 20 and {"theoretical", "experimental"} <= {d.kind for d in cat.databases}
    assert all(d.url.startswith("http") for d in cat.databases)
    ds = bench.datasets()["perov5"]
    assert ds.protocol and {t.id for t in ds.protocol.tasks} == {"inverse_design", "property_prediction", "representation"}


def test_leaderboard_orders_rows_and_colours_cells():
    task = _ds().protocol.task("property_prediction")
    rows = [_sub(id="a-row", method={"name": "Alpha"}, results={"property_prediction": {"mae_x": 0.5, "r2_x": 0.1}}),
            _sub(id="b-row", method={"name": "Beta", "kind": "baseline"}, results={"property_prediction": {"mae_x": 0.2, "r2_x": 0.9}}),
            _sub(id="c-row", method={"name": "Gamma"}, results={"property_prediction": {"mae_x": None, "r2_x": 0.3}})]
    page = bench.leaderboard(task, rows)
    assert page.index(">Beta<") < page.index(">Alpha<") < page.index(">Gamma<")   # lower MAE first, missing last
    assert "background:#fde725" in page and "background:#440154" in page            # best yellow, weakest dark
    assert ">–<" in page and "baseline" in page and 'href="results/b-row.html"' in page
    assert bench.heat(1.0) == ("#fde725", "#111111") and bench.heat(0.0) == ("#440154", "#ffffff")


def test_rows_are_never_compared_across_datasets():
    with pytest.raises(ValueError, match="never compared across datasets"):
        bench.render_dataset(_ds(), [_sub(), _sub(id="t-other", dataset="mp20")])


def test_validate_checks_tasks_metrics_and_verification(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "BENCH", str(tmp_path))
    monkeypatch.setattr(bench, "DOCS", str(tmp_path / "docs"))
    (tmp_path / "datasets").mkdir()
    (tmp_path / "datasets" / "tset.json").write_text(json.dumps({"id": "tset", "name": "T", "description": "d.", "protocol": PROTO}), encoding="utf-8")
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "databases.json").write_text(json.dumps({"applications": [], "databases": []}), encoding="utf-8")
    sub = tmp_path / "submissions" / "tset"
    sub.mkdir(parents=True)
    row = _sub(status="meidnet_verified").model_dump()
    path = sub / "t-row.json"

    def check(r):
        path.write_text(json.dumps(r), encoding="utf-8")
        return bench.validate()
    bad = json.loads(json.dumps(row))
    bad["results"]["property_prediction"]["rmse_x"] = 1.0
    assert any("metric 'rmse_x' is not defined" in p for p in check(bad))
    bad = json.loads(json.dumps(row))
    bad["results"] = {"inverse_design": {"sun_rate": 0.1}}
    assert any("unknown task 'inverse_design'" in p for p in check(bad))
    bad = json.loads(json.dumps(row))
    del bad["results"]["property_prediction"]["mae_x"]          # the headline key is required (null = not applicable)
    assert any("headline metric 'mae_x'" in p for p in check(bad))
    assert any("without benchmarks/verified" in p for p in check(row))
    (tmp_path / "verified").mkdir()
    (tmp_path / "verified" / "t-row.json").write_text(json.dumps({"submission_sha256": bench.content_sha(str(path))}), encoding="utf-8")
    assert bench.validate() == []
    row["results"]["property_prediction"]["mae_x"] = 0.1                    # the numbers may not change after verification
    assert any("another version" in p for p in check(row))
    row["results"]["property_prediction"]["mae_x"] = 0.3
    check(row)
    written = bench.render()
    assert "benchmarks/tset.md" in written and (tmp_path / "docs" / "benchmarks" / "results" / "t-row.md").exists()
    page = (tmp_path / "docs" / "benchmarks" / "tset.md").read_text(encoding="utf-8")
    assert 'class="lb"' in page and "## Protocol" in page and "Discovery" not in page
    assert (tmp_path / "docs" / "benchmarks" / "data" / "tset-property_prediction.csv").exists()


def test_databases_page_groups_by_application():
    page = bench.render_databases(bench.catalog())
    assert "## Solar cells and photovoltaics" in page and "## All databases" in page
    assert "Perovskite Database Project" in page and "Materials Project" in page and "Discovery" not in page


def test_property_metrics_retrieval_and_knn():
    Y = np.array([[1.0, 0.0], [2.0, 2.0], [3.0, 0.0], [4.0, 1.0]])
    P = Y + np.array([0.1, -0.1, 0.1, -0.1])[:, None]
    m = B.property_metrics(["h", "g"], Y, P)
    assert m["mae_h"] == pytest.approx(0.1) and m["r2_h"] > 0.99 and m["n_evaluated"] == 4
    assert m["mae_g_nonzero"] == pytest.approx(0.1) and "mae_h_nonzero" not in m      # no zeros in h: no subset metric
    Z = np.eye(4)
    r = B.retrieval(Z, Z)
    assert r["retrieval_top1"] == 1.0 and r["cosine_matched"] == pytest.approx(1.0) and r["l2_matched"] == pytest.approx(0.0)
    # materials 0 and 1 have identical properties, hence identical property latents: one profile, not two candidates
    Zp = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    Zc = np.array([[0.6, 0.8], [0.99, 0.14], [0.0, 1.0]])
    Zc = Zc / np.linalg.norm(Zc, axis=1, keepdims=True)
    r = B.retrieval(Zc, Zp, Y=np.array([[1.0, 0.0], [1.0, 0.0], [2.0, 0.0]]))
    assert r["n_profiles"] == 2 and r["retrieval_top1"] == pytest.approx(2 / 3)    # material 0 is nearer the other profile
    tr_X = np.array([[0.0], [1.0], [10.0], [11.0]])
    tr_Y = np.array([[0.0], [2.0], [100.0], [102.0]])
    assert B.knn_predict(tr_X, tr_Y, np.array([[0.4], [10.6]]), k=2, metric="euclidean").ravel().tolist() == [1.0, 101.0]


def test_inverse_design_scoring_counts_against_the_budget():
    settings = {"variants": ["oxide"], "targets": [{"dir_gap": 2.0}], "per_target": 4, "stability_threshold": 0.1, "gap_tolerance": 0.5}
    cands = [{"id": "c1", "formula": "BaTiO3", "elements": json.dumps({"A": "Ba", "B": "Ti", "X": "O"}), "target_dir_gap": "2.0", "passes_rules": "True"},
             {"id": "c2", "formula": "SrTiO3", "elements": json.dumps({"A": "Sr", "B": "Ti", "X": "O"}), "target_dir_gap": "2.0", "passes_rules": "True"},
             {"id": "c3", "formula": "SrTiO3", "elements": json.dumps({"A": "Sr", "B": "Ti", "X": "O"}), "target_dir_gap": "2.0", "passes_rules": "True"}]
    stab = {"c1": {"dHf": -2.0, "artefact": False}, "c2": {"dHf": -1.0, "artefact": False}, "c3": {"dHf": 0.5, "artefact": False}}
    known = {"Ba|Ti|O": [4.0], "Sr|Ti|O": [2.2]}            # site-matched DFT gaps
    m, rows = B.score_inverse_design(cands, stab, settings, train_formulas={"BaTiO3"}, known=known)
    assert m["n_delivered"] == 3 and m["n_budget"] == 4
    assert m["sun_rate"] == pytest.approx(1 / 4)             # only c2: c1 is in the training set, c3 repeats c2 and is unstable
    assert m["novel_rate"] == pytest.approx(2 / 3) and m["unique_rate"] == pytest.approx(2 / 3) and m["stable_rate"] == pytest.approx(2 / 3)
    assert m["dft_known"] == 3 and m["dft_hit_rate"] == pytest.approx(2 / 3)       # SrTiO3 within 0.5 eV, BaTiO3 not
    assert [r["sun"] for r in rows] == [False, True, False]
    assert B.site_key({"A": "Ba", "B": "Ti", "X": "O"}) == "Ba|Ti|O" and B.site_key({"A": "Ba"}) is None
