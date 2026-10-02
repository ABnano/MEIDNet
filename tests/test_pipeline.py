"""End-to-end: init → check → train (3 epochs) → generate (quick) on the 64-row mini set, plus the Studio API."""
import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
MINI = os.path.join(ROOT, "tests", "data", "perov5_mini.csv")


def run(args, cwd):
    env = dict(os.environ, PYTHONPATH=ROOT, OMP_NUM_THREADS="2")
    r = subprocess.run([sys.executable, "-m", "meidnet.cli", *args], cwd=cwd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-3000:]
    return r.stdout


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    d = tmp_path_factory.mktemp("proj")
    import shutil
    shutil.copy(MINI, d / "materials.csv")
    run(["init", "--name", "t", "--table", "materials.csv", "--properties", "heat_all", "dir_gap",
         "--variant", "halide"], d)
    return d


def test_check_reports_skips(project):
    out = run(["check", "meidnet.yaml"], project)
    assert "usable" in out
    assert (project / "runs" / "t" / "check_report.html").exists()


def test_train_and_generate(project):
    out = run(["train", "meidnet.yaml", "--epochs", "3"], project)
    assert "model saved" in out
    assert (project / "runs" / "t" / "training_report.html").exists()
    info = run(["info", "runs/t/model.pt"], project)
    assert "MEIDNet 2" in info and "heat_all" in info
    out = run(["generate", "meidnet.yaml", "--quick"], project)
    assert "candidate(s) written" in out
    gen = project / "runs" / "t" / "generation"
    assert (gen / "candidates.csv").exists() and (gen / "generation.json").exists()
    assert (project / "runs" / "t" / "generation_report.html").exists()


def test_schema_and_families_commands(tmp_path):
    out = run(["schema"], tmp_path)
    assert '"GenerationSection"' in out
    out = run(["families", "perovskite_abx3", "--variant", "oxide"], tmp_path)
    assert "Goldschmidt" in out


def test_studio_backend_runs_a_search(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from meidnet.studio.server import Studio
    s = Studio(None, model_path=os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"))
    st = s.state()
    assert "perovskite_abx3" in st["families"]
    fam = s.family({"family": "perovskite_abx3", "variant": "halide"})
    assert len(fam["space"]["rows"]) == 924
    r = s.start_search({"session": "tab1", "generation": {"targets": [{"dir_gap": 2.0, "heat_all": -0.1}],
                                                            "per_target": 1, "population": 8, "rounds": 1, "steps": 20}})
    assert r["ok"]
    # a second tab may not start while the first is running (MAX_RUNNING is 2, but the same session may not double up)
    assert not s.start_search({"session": "tab1", "generation": {}})["ok"]
    for _ in range(600):
        snap = s.status("tab1")
        if snap["done"]:
            break
        time.sleep(0.5)
    assert snap["done"] and snap["error"] is None, snap["error"]
    assert snap["report"] and os.path.exists(os.path.join(s.run_root, snap["report"]))
    assert s.resolve_file(snap["report"]) and s.resolve_file("../../etc/passwd") is None
    yaml_text = s.export({"generation": {"overrides": {"tolerance_factor": {"max": 1.0}}}})
    assert "max: 1.0" in yaml_text


def test_studio_public_mode_caps_budgets_and_families(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from meidnet.studio.server import PUBLIC_LIMITS, Studio
    s = Studio(None, model_path=os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"),
               public=True, run_root=str(tmp_path / "runs"))
    assert s.state()["limits"] == PUBLIC_LIMITS
    gen = s._apply_limits({"rounds": 999, "steps": 99999, "population": 999, "per_target": 99,
                           "targets": [{"dir_gap": 1}, {"dir_gap": 2}, {"dir_gap": 3}], "family": "perovskite_abx3"})
    assert gen["rounds"] == PUBLIC_LIMITS["rounds"] and gen["steps"] == PUBLIC_LIMITS["steps"] and len(gen["targets"]) == 2
    import pytest
    with pytest.raises(ValueError):
        s._apply_limits({"family": "/etc/some_family.yaml"})
    assert "<path to the model file>" in s.export({"generation": {}})
