"""The benchmark files and their generator (scripts/benchmarks.py): schema rules, the no-cross-dataset rule,
the verified flag, and the rendered pages."""
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

spec = importlib.util.spec_from_file_location("benchmarks", os.path.join(ROOT, "scripts", "benchmarks.py"))
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def test_repository_files_validate():
    assert bench.validate() == []
    cat = bench.catalog()
    assert len(cat.databases) >= 20 and {"theoretical", "experimental"} <= {d.kind for d in cat.databases}
    assert all(d.url.startswith("http") for d in cat.databases)


def _sub(**over):
    base = {"id": "t-row", "dataset": "perov5", "title": "t", "submitter": {"name": "x"}, "date": "2026-01-01",
            "modalities": ["structure", "property:dir_gap"], "model": {"name": "m", "meidnet_version": "2.0.0"},
            "category": "representation_quality", "results": {"mae_dir_gap": {"value": 0.3, "unit": "eV"}}}
    base.update(over)
    return bench.Submission.model_validate(base)


def test_metric_names_are_checked_per_category():
    assert bench.metric_allowed("representation_quality", "mae_dir_gap")
    assert bench.metric_allowed("validation", "n_sun")
    assert not bench.metric_allowed("representation_quality", "n_sun")
    assert not bench.metric_allowed("representation_quality", "mae_")            # a property name is required
    with pytest.raises(Exception):
        _sub(modalities=["spectra"])                                            # unknown modality
    with pytest.raises(Exception):
        _sub(results={})                                                        # at least one metric
    assert bench.lower_is_better("mae_heat_all") and not bench.lower_is_better("r2_heat_all")


def test_rows_are_never_compared_across_datasets():
    ds = bench.Dataset(id="perov5", name="P", description="d.")
    with pytest.raises(ValueError, match="never compared across datasets"):
        bench.render_dataset(ds, [_sub(), _sub(id="t-other", dataset="mp20")])
    page = bench.render_dataset(ds, [_sub(), _sub(id="t-two", results={"mae_dir_gap": {"value": 0.2, "unit": "eV"}})])
    assert "**0.2**" in page and "[t](results/t-two.md" in page         # the best value is marked, rows link to their pages
    assert "lower is better" in page and "bench-chart" in page           # the bar chart for a metric shared by two rows


def test_verified_needs_a_matching_record(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "BENCH", str(tmp_path))
    monkeypatch.setattr(bench, "DOCS", str(tmp_path / "docs"))
    (tmp_path / "datasets").mkdir()
    (tmp_path / "datasets" / "perov5.json").write_text(json.dumps({"id": "perov5", "name": "P", "description": "d."}), encoding="utf-8")
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "databases.json").write_text(json.dumps({"applications": [], "databases": []}), encoding="utf-8")
    sub = tmp_path / "submissions" / "perov5"
    sub.mkdir(parents=True)
    row = _sub(status="meidnet_verified").model_dump()
    (sub / "t-row.json").write_text(json.dumps(row), encoding="utf-8")
    problems = bench.validate()
    assert any("without benchmarks/verified" in p for p in problems)
    (tmp_path / "verified").mkdir()
    (tmp_path / "verified" / "t-row.json").write_text(json.dumps({"submission_sha256": "0" * 64}), encoding="utf-8")
    assert any("another version" in p for p in bench.validate())
    (tmp_path / "verified" / "t-row.json").write_text(json.dumps({"submission_sha256": bench.content_sha(str(sub / "t-row.json"))}), encoding="utf-8")
    assert bench.validate() == []
    row["verified_by"] = "maintainer"                                     # status fields may change after reproduce ...
    (sub / "t-row.json").write_text(json.dumps(row), encoding="utf-8")
    assert bench.validate() == []
    row["results"]["mae_dir_gap"]["value"] = 0.1                          # ... the numbers may not
    (sub / "t-row.json").write_text(json.dumps(row), encoding="utf-8")
    assert any("another version" in p for p in bench.validate())
    row["results"]["mae_dir_gap"]["value"] = 0.3
    (sub / "t-row.json").write_text(json.dumps(row), encoding="utf-8")
    written = bench.render()
    assert "benchmarks/perov5.md" in written and (tmp_path / "docs" / "benchmarks" / "results" / "t-row.md").exists()
    assert "MEIDNet verified" in (tmp_path / "docs" / "benchmarks" / "perov5.md").read_text(encoding="utf-8")


def test_databases_page_groups_by_application():
    page = bench.render_databases(bench.catalog())
    assert "## Solar cells and photovoltaics" in page and "## All databases" in page
    assert "Perovskite Database Project" in page and "Materials Project" in page
