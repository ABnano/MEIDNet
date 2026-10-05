"""
MEIDNet Studio backend, driven through the Studio class (no HTTP server, no network).

Covers one browser tab's journey (upload -> check -> train -> switch model -> export), stopping
jobs, config validation, the chemiscope datasets, public-mode guards (budgets, job limit, paths),
session clean-up and the small helpers the server relies on.  Every test runs in an empty temporary
working directory, so the gitignored data/perov5 folder is never seen.  Session ids follow the
server's rule: 4-64 characters of [A-Za-z0-9_-] (so the tab ids are "tab-...", not "t1").
"""
import base64
import io
import json
import math
import os
import shutil
import sys
import time
import zipfile

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
MINI = os.path.join(ROOT, "tests", "data", "perov5_mini.csv")
CKPT = os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")

from meidnet.studio.server import EMPTY_STATUS, PUBLIC_LIMITS, Job, Studio, _finite  # noqa: E402

SID = "tab-t1"          # the tab that uploads, checks and trains
CHECK = {"id_column": "material_id", "cif_column": "cif",
         "properties": [{"column": "heat_all", "unit": "eV/atom"}, {"column": "dir_gap", "unit": "eV"}],
         "family": "perovskite_abx3", "variant": "halide", "align_to_prototype": True, "prototype_tolerance": 0.25}
# a search ends as soon as per_target candidates are saved, so rounds 2-3 only run if round 1 saved nothing
TINY_SEARCH = {"targets": [{"dir_gap": 2.0, "heat_all": -0.1}], "per_target": 1, "population": 8, "rounds": 3,
               "steps": 20}


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def mini_upload(sid: str) -> dict:
    with open(MINI, "rb") as f:
        return {"session": sid, "files": [{"name": "materials.csv", "b64": b64(f.read())}]}


def wait_done(studio, sid, kind, timeout=300):
    deadline = time.time() + timeout
    while True:
        snap = studio.status(sid, kind)
        if snap["done"]:
            return snap
        assert time.time() < deadline, f"{kind} job of {sid} still running after {timeout} s: {snap['log'][-5:]}"
        time.sleep(0.2)


def single_type(values) -> bool:
    return len({type(v) for v in values}) == 1


# ───────────────────────── fixtures ─────────────────────────
@pytest.fixture(scope="module", autouse=True)
def workdir(tmp_path_factory):
    """An empty working directory for the whole module (the Studio looks for data/perov5 relative to it)."""
    d = tmp_path_factory.mktemp("studio_cwd")
    with pytest.MonkeyPatch.context() as mp:
        mp.chdir(d)
        yield d


@pytest.fixture(scope="module")
def studio(workdir):
    return Studio(None, model_path=CKPT, run_root=str(workdir / "runs"))


@pytest.fixture(scope="module")
def public_studio(workdir):
    return Studio(None, model_path=CKPT, public=True, run_root=str(workdir / "runs_public"))


@pytest.fixture(scope="module")
def uploaded(studio):
    return studio.upload(mini_upload(SID))


@pytest.fixture(scope="module")
def checked(studio, uploaded):
    return studio.check_data(dict(CHECK, session=SID))


@pytest.fixture(scope="module")
def trained(studio, checked):
    assert studio.start_train({"session": SID, "epochs": 2, "batch_size": 8}) == {"ok": True, "epochs": 2}
    return wait_done(studio, SID, "train")


# ───────────────────────── 1. upload ─────────────────────────
def test_http_routes_landing_and_studio(studio, tmp_path):
    """Platform mode (a docs folder is served): / is the landing page, /studio/ the workbench, deep links redirect.
    Without a docs folder, / is the workbench itself."""
    import http.client
    import threading
    from meidnet.studio.server import ASK_PRISM_TAG, Handler, _Server
    docs = tmp_path / "site"
    docs.mkdir()
    (docs / "index.html").write_text("<h1>docs</h1>", encoding="utf-8")

    def serve(st):
        Handler.studio = st
        srv = _Server(("127.0.0.1", 0), Handler)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        return srv

    def get(srv, path):
        c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
        c.request("GET", path)
        r = c.getresponse()
        body = r.read().decode("utf-8", "replace")
        c.close()
        return r.status, dict(r.getheaders()), body

    old = Handler.studio
    try:
        studio.docs_dir = str(docs)
        srv = serve(studio)
        try:
            st, _, body = get(srv, "/")
            assert st == 200 and "MEIDNet Prism" in body and "Try MEIDNet" in body and "/docs/learn/index.html" in body
            st, _, body = get(srv, "/studio/")
            assert st == 200 and "MEIDNet Studio" in body and "Researcher mode" in body
            assert all(ASK_PRISM_TAG in get(srv, p)[2] for p in ("/", "/studio/"))   # the help panel on both pages
            assert all(get(srv, p)[1]["Cache-Control"] == "no-cache" for p in ("/", "/studio/", "/docs/"))   # a deploy shows at once
            st, h, body = get(srv, "/ask-prism.js")
            assert st == 200 and h["Content-Type"].startswith("text/javascript") and "Ask PRISM" in body
            st, _, body = get(srv, "/health")
            assert st == 200 and json.loads(body)["status"] == "ok"                 # uptime checks, no session needed
            st, h, _ = get(srv, "/?panel=rules&session=tab-route")
            assert st == 302 and h["Location"] == "/studio/?panel=rules&session=tab-route"
            st, _, body = get(srv, "/docs/")
            assert st == 200 and "<h1>docs</h1>" in body
            c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
            c.request("HEAD", "/studio/")
            r = c.getresponse()
            assert r.status == 200 and int(r.getheader("Content-Length")) > 1000 and r.read() == b""   # HEAD: headers only
            c.close()
            st, _, body = get(srv, "/api/state?session=tab-route")
            assert st == 200 and json.loads(body)["home_url"] == "/"
            # byte ranges: browsers stream and seek the tour video this way; Safari plays nothing without them
            clip = bytes(range(256)) * 4
            (docs / "clip.webm").write_bytes(clip)

            def raw(path, rng=None):
                c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
                c.request("GET", path, headers={"Range": rng} if rng else {})
                r = c.getresponse()
                out = r.status, dict(r.getheaders()), r.read()
                c.close()
                return out
            st, h, b = raw("/docs/clip.webm")
            assert st == 200 and b == clip and h["Accept-Ranges"] == "bytes" and h["Content-Type"] == "video/webm"
            st, h, b = raw("/docs/clip.webm", "bytes=10-19")
            assert st == 206 and b == clip[10:20] and h["Content-Range"] == "bytes 10-19/1024"
            st, h, b = raw("/docs/clip.webm", "bytes=1000-")
            assert st == 206 and b == clip[1000:] and h["Content-Range"] == "bytes 1000-1023/1024"
            st, h, b = raw("/docs/clip.webm", "bytes=-4")
            assert st == 206 and b == clip[-4:]
            st, h, _ = raw("/docs/clip.webm", "bytes=5000-")
            assert st == 416 and h["Content-Range"] == "bytes */1024"
        finally:
            srv.shutdown()
            srv.server_close()
        studio.docs_dir = None
        srv = serve(studio)
        try:
            st, _, body = get(srv, "/")
            assert st == 200 and "MEIDNet Studio" in body          # no docs folder: the workbench is the front page
            assert json.loads(get(srv, "/api/state?session=tab-route")[2])["home_url"] is None
            assert get(srv, "/ask-prism.js")[0] == 200                 # local Studio: the panel works without docs
        finally:
            srv.shutdown()
            srv.server_close()
    finally:
        Handler.studio = old


def test_ask_prism_static_copy_and_issue_form():
    """The static Studio carries the panel inside the file, and the GitHub form has the fields the panel fills in."""
    import re
    from meidnet.studio.server import ASK_PRISM_TAG, HERE, inline_ask_prism
    with open(os.path.join(HERE, "studio.html"), encoding="utf-8") as f:
        page = f.read()
    out = inline_ask_prism(page)
    assert ASK_PRISM_TAG in page and "/ask-prism.js" not in out and "Ask PRISM" in out
    with open(os.path.join(HERE, "ask_prism.js"), encoding="utf-8") as f:
        js = f.read()
    with open(os.path.join(os.path.dirname(__file__), "..", ".github", "ISSUE_TEMPLATE", "bug_report.yml"), encoding="utf-8") as f:
        ids = set(re.findall(r"^\s+id: (\w+)$", f.read(), re.M))
    gh = js[js.index("function ghBugUrl"):js.index("function copy")]
    used = set(re.findall(r'"&(\w+)=" \+ encodeURIComponent', gh)) - {"body"}   # body: the fallback without the form
    assert "template=bug_report.yml" in js and used and used <= ids, (used, ids)


def test_doped_cif_is_skipped_not_fatal(studio):
    """A partially occupied (doped) structure is reported as a skip reason; the rest of the table is still checked."""
    df = pd.read_csv(MINI).head(6)
    lines = df.loc[0, "cif"].splitlines()          # the last column of a site line is its occupancy: make one 0.5
    i = next(k for k, line in enumerate(lines) if line.split()[-1:] == ["1"] and len(line.split()) == 7)
    lines[i] = lines[i].rsplit(" ", 1)[0] + " 0.5"
    df.loc[0, "cif"] = "\n".join(lines)
    sid = "tab-doped"
    studio.upload({"session": sid, "files": [{"name": "doped.csv", "b64": b64(df.to_csv(index=False).encode())}]})
    checked = studio.check_data(dict(CHECK, session=sid))
    assert checked["available"] and checked["rows"] == 6
    assert any("partially occupied" in reason for reason in checked["skipped"]), checked["skipped"]
    assert checked["kept"] >= 1


def test_upload_suggests_columns(studio, uploaded):
    assert uploaded["rows"] == 64 and uploaded["n_cifs"] == 0 and uploaded["truncated"] is False
    sug = uploaded["suggest"]
    assert sug["cif_column"] == "cif"
    assert sug["id_column"] == "material_id"
    assert "heat_all" in sug["properties"] and "dir_gap" in sug["properties"]
    assert "Unnamed: 0" not in sug["properties"]        # a saved DataFrame index is not a property
    assert "material_id" not in sug["properties"]
    ses = studio.state(SID)["session"]
    assert ses["has_upload"] and ses["n_rows"] == 64 and ses["source"] == "materials.csv"
    assert "Unnamed: 0" in ses["columns"]               # ... but it is still listed as a column
    # an unsupported file is refused (in another tab: a failed upload clears that tab's data)
    with pytest.raises(ValueError, match="unsupported file type"):
        studio.upload({"session": "tab-badfile", "files": [{"name": "notes.txt", "b64": b64(b"just notes")}]})


def test_upload_rejects_requests_without_a_table(studio):
    with pytest.raises(ValueError, match="no files"):
        studio.upload({"session": "tab-nofiles", "files": []})
    cif = pd.read_csv(MINI)["cif"].iloc[0].encode()
    with pytest.raises(ValueError, match="table"):
        studio.upload({"session": "tab-nofiles", "files": [{"name": "6334.cif", "b64": b64(cif)}]})


def test_upload_zip_of_cifs_feeds_check(studio):
    df = pd.read_csv(MINI)
    first, second, third = (str(m) for m in df["material_id"].iloc[:3])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{first}.cif", df["cif"].iloc[0])
        z.writestr("nested/", "")                              # a folder entry: ignored
        z.writestr(f"nested/{second}.cif", df["cif"].iloc[1])  # kept under its base name
        z.writestr("../../escape.cif", df["cif"].iloc[2])      # must not leave the session folder
        z.writestr("readme.txt", "not a structure")
    sid = "tab-zipped"
    with open(MINI, "rb") as f:
        up = studio.upload({"session": sid, "files": [{"name": "structures.zip", "b64": b64(buf.getvalue())},
                                                      {"name": "materials.csv", "b64": b64(f.read())}]})
    assert up["n_cifs"] == 3
    s = studio.session(sid)
    assert sorted(os.listdir(s.structures_dir)) == sorted([f"{first}.cif", f"{second}.cif", "escape.cif"])
    found = [os.path.join(d, f) for d, _, files in os.walk(studio.run_root) for f in files if f == "escape.cif"]
    assert found == [os.path.join(s.structures_dir, "escape.cif")]
    # structures come from the files (no CIF column): only the two ids with a file are usable
    summary = studio.check_data({"session": sid, "id_column": "material_id", "cif_column": None,
                                 "properties": [{"column": "heat_all", "unit": "eV/atom"}],
                                 "family": "perovskite_abx3", "variant": "halide", "prototype_tolerance": 0.25})
    assert summary["rows"] == 64 and summary["kept"] == 2
    assert summary["skipped"] == {"no CIF file for this id": 62}
    assert s.cfg.data.cif_column is None and s.cfg.data.structures_dir == s.structures_dir


# ───────────────────────── 2. check ─────────────────────────
def test_check_builds_session_config(studio, checked):
    assert checked["available"] and checked["rows"] == 64 and checked["source"] == "materials.csv"
    assert checked["kept"] > 30
    assert checked["rows"] - checked["kept"] == sum(checked["skipped"].values())
    assert checked["aligned"] == checked["kept"]        # every kept structure was aligned to the prototype
    assert checked["family"] == "perovskite_abx3" and checked["site_counts"] == {"5": 64}
    assert {"heat_all", "dir_gap", "elements"} <= set(checked["charts"])
    for col in ("heat_all", "dir_gap"):
        st = checked["stats"][col]
        assert all(math.isfinite(st[k]) for k in ("min", "median", "max")), st
        assert st["min"] <= st["median"] <= st["max"]
    assert studio.state(SID)["session"]["checked"] is True
    assert studio.data(SID) == checked                  # /api/data now describes this tab's upload
    cfg = studio.session(SID).cfg
    medians = {col: round(checked["stats"][col]["median"], 3) for col in ("heat_all", "dir_gap")}
    assert cfg.generation.targets == [medians]
    assert (cfg.family, cfg.generation.family, cfg.generation.variant) == ("perovskite_abx3", "perovskite_abx3", "halide")
    assert [p.property for p in cfg.generation.objectives] == ["heat_all", "dir_gap"]
    assert [(p.column, p.unit) for p in cfg.data.properties] == [("heat_all", "eV/atom"), ("dir_gap", "eV")]
    assert cfg.data.align_to_prototype and cfg.data.prototype_tolerance == 0.25


def test_check_and_train_need_data_first(studio):
    with pytest.raises(ValueError, match="upload a table first"):
        studio.check_data({"session": "tab-empty", "properties": [{"column": "heat_all"}]})
    assert studio.start_train({"session": "tab-empty", "epochs": 1}) == {"ok": False, "error": "check your data first"}
    studio.upload(mini_upload("tab-noprops"))
    with pytest.raises(ValueError, match="at least one property"):
        studio.check_data({"session": "tab-noprops", "cif_column": "cif", "properties": []})
    with pytest.raises(ValueError, match="band_gap"):        # a column the table does not have
        studio.check_data({"session": "tab-noprops", "cif_column": "cif", "properties": [{"column": "band_gap"}]})


# ───────────────────────── 3. train + model switch ─────────────────────────
def test_train_updates_session_model(studio, checked, trained, workdir):
    assert trained["error"] is None, trained["error"]
    prog = trained["progress"]
    assert len(prog["curve"]) == 2 and prog["epochs"] == 2
    assert prog["n_train"] + prog["n_val"] == checked["kept"]
    assert set(prog["val"]["mae"]) == {"heat_all", "dir_gap"}
    assert all(math.isfinite(v) for v in prog["val"]["mae"].values())
    assert trained["report"] and studio.resolve_file(trained["report"])
    st = studio.state(SID)
    assert st["model"]["own"] is True and st["session"]["using_own"] and st["session"]["has_model"]
    assert [p["column"] for p in st["model"]["properties"]] == ["heat_all", "dir_gap"]
    assert st["config"]["name"] == "your_data"           # the state now shows this tab's configuration

    fam = studio.family({"session": SID, "family": "perovskite_abx3", "variant": "halide"})
    assert fam["model_own"] is True and fam["space"]["columns"] == ["heat_all", "dir_gap"]

    text = studio.export({"session": SID, "generation": {}})
    assert "model_path: model.pt" in text
    doc = yaml.safe_load(text)
    assert doc["data"]["table"] == "materials.csv" and doc["output_dir"] == "runs/{name}"   # the user's file name
    assert doc["generation"]["targets"] == studio.session(SID).cfg.generation.targets
    assert os.path.basename(str(workdir)) not in text    # no server paths in the exported file
    from meidnet.config import MEIDNetConfig
    MEIDNetConfig.model_validate(doc)                    # the export is a valid meidnet.yaml
    v = studio.validate({"session": SID, "generation": {}})          # the tab's own settings are the base
    assert v["ok"] and v["generation"]["targets"] == studio.session(SID).cfg.generation.targets
    assert [o["property"] for o in v["generation"]["objectives"]] == ["heat_all", "dir_gap"]

    assert studio.select_model(SID, "published") == {"ok": True, "using_own": False}
    assert studio.state(SID)["model"]["own"] is False
    assert studio.family({"session": SID, "family": "perovskite_abx3", "variant": "halide"})["model_own"] is False
    assert studio.select_model(SID, "own") == {"ok": True, "using_own": True}
    assert studio.state(SID)["model"]["own"] is True
    with pytest.raises(ValueError):
        studio.select_model("tab-nomodel", "own")        # nothing trained in this tab
    with pytest.raises(ValueError):
        studio.select_model(SID, "somebody-elses")


def test_chemiscope_space_uses_the_session_model(studio, trained):
    from meidnet.studio.chemiscope import select_rows
    assert studio.select_model(SID, "own")["using_own"]
    rows = studio.family({"session": SID, "family": "perovskite_abx3", "variant": "halide"})["space"]["rows"]
    own = studio.chemiscope(SID, "space", "perovskite_abx3", "halide")
    idx = select_rows(rows, len(own["structures"]))
    assert len(idx) == len(rows)                                        # the whole halide space fits the cap
    assert own["properties"]["pred_dir_gap"]["values"] == [float(rows[i]["p"]["dir_gap"]) for i in idx]
    assert own["properties"]["formula"]["values"] == [rows[i]["f"] for i in idx]
    pub = studio.chemiscope("tab-other", "space", "perovskite_abx3", "halide")   # another tab: published model
    assert pub["properties"]["formula"]["values"] == own["properties"]["formula"]["values"]
    assert pub["properties"]["pred_dir_gap"]["values"] != own["properties"]["pred_dir_gap"]["values"]


def test_stop_ends_jobs_early(studio):
    sid = "tab-stop"
    # per_target above the population: one round can never finish the search, so only stop() ends it early
    assert studio.start_search({"session": sid, "generation": dict(TINY_SEARCH, per_target=20, rounds=50)})["ok"]
    studio.stop(sid)                                                    # read before every round
    snap = wait_done(studio, sid, "search", timeout=120)
    assert snap["error"] is None and snap["progress"]["round"] <= 1, snap["progress"]
    assert any("stopped by user" in line for line in snap["log"]), snap["log"][-5:]

    studio.upload(mini_upload(sid))
    studio.check_data(dict(CHECK, session=sid))
    assert studio.start_train({"session": sid, "epochs": 50, "batch_size": 8}) == {"ok": True, "epochs": 50}
    studio.stop(sid)                                                    # read after every epoch
    snap = wait_done(studio, sid, "train", timeout=120)
    assert snap["error"] is None and len(snap["progress"]["curve"]) == 1, snap["progress"]
    assert any("stopped by user" in line for line in snap["log"]), snap["log"][-5:]
    assert studio.state(sid)["model"]["own"] is True                    # the model is kept as it is
    model = studio.state(sid)["model"]                                  # ... with the history of its epoch
    assert len(model["history"]["train"]) == 1 and model["validation"] is not None, model["history"]

    studio.check_data(dict(CHECK, session=sid))                         # a new check discards that model
    assert studio.state(sid)["model"]["own"] is False and studio.state(sid)["session"]["has_model"] is False
    with pytest.raises(ValueError):
        studio.select_model(sid, "own")
    studio.upload(mini_upload(sid))                                     # and new data discard the check
    assert studio.state(sid)["session"]["checked"] is False
    assert studio.start_train({"session": sid, "epochs": 1}) == {"ok": False, "error": "check your data first"}


# ───────────────────────── 4. validation ─────────────────────────
GOOD_YAML = """\
generation:
  family: perovskite_abx3
  variant: oxide
  rounds: 2
  extra_constraints:
    - {name: property_window, property: dir_gap, min: 1.0, max: 3.0}
"""


def test_validate_yaml_and_errors(studio, public_studio):
    r = studio.validate({"yaml": GOOD_YAML})
    assert r["ok"], r
    g = r["generation"]
    assert g["variant"] == "oxide" and g["rounds"] == 2 and r["notes"] == []
    assert g["extra_constraints"] == [{"name": "property_window", "property": "dir_gap", "min": 1.0, "max": 3.0}]
    assert g["per_target"] == studio.cfg.generation.per_target   # unspecified settings come from the Studio
    assert studio.validate({"generation": yaml.safe_load(GOOD_YAML)["generation"]})["generation"] == g

    bad = studio.validate({"yaml": "steps: -1\n"})
    assert not bad["ok"] and any("steps" in e for e in bad["errors"]), bad

    broken = studio.validate({"yaml": "generation: [unclosed\n"})
    assert not broken["ok"] and broken["errors"][0].startswith("YAML syntax"), broken

    capped = public_studio.validate({"yaml": "rounds: 99\n"})
    assert capped["ok"], capped
    assert capped["generation"]["rounds"] == PUBLIC_LIMITS["rounds"]
    assert any("rounds" in n and "99" in n for n in capped["notes"]), capped["notes"]
    assert studio.validate({"yaml": "rounds: 99\n"})["generation"]["rounds"] == 99   # no cap locally


def test_public_validate_reports_wrong_values_before_capping(public_studio):
    zero = public_studio.validate({"yaml": "rounds: 0\n"})          # wrong, not silently raised to 1
    assert not zero["ok"] and any("rounds" in e for e in zero["errors"])
    many = public_studio.validate({"generation": {"targets": [{"dir_gap": v, "heat_all": 0.0} for v in (1, 2, 3)]}})
    assert many["ok"] and len(many["generation"]["targets"]) == PUBLIC_LIMITS["targets"]
    assert any("targets" in n for n in many["notes"])
    custom = public_studio.validate({"yaml": "family: /somewhere/my_family.yaml\n"})
    assert not custom["ok"] and "built-in" in custom["errors"][0]


# ───────────────────────── 5./6. chemiscope ─────────────────────────
def test_chemiscope_space_dataset_shape(studio):
    from meidnet.family import load_family
    from meidnet.studio.chemiscope import space_dataset
    fam = load_family("perovskite_abx3", variant="halide")
    space = studio.family({"family": "perovskite_abx3", "variant": "halide"})["space"]   # published model
    ds = space_dataset(fam, space, studio.lm, max_structures=100)
    assert len(ds["structures"]) == 100
    for s in ds["structures"]:
        assert s["size"] == 5 and len(s["names"]) == len(s["x"]) == len(s["y"]) == len(s["z"]) == 5
        assert len(s["cell"]) == 9 and all(math.isfinite(v) for v in s["cell"] + s["x"] + s["y"] + s["z"])
    props = ds["properties"]
    for name, p in props.items():
        assert p["target"] == "structure" and len(p["values"]) == 100, name
        assert single_type(p["values"]), name
    assert props["pred_dir_gap"]["units"] == "eV" and props["pred_heat_all"]["units"] == "eV/atom"
    passes = props["passes_all"]["values"]
    assert set(passes) <= {0, 1}
    assert passes == sorted(passes, reverse=True)                   # compositions passing every rule first
    n_ok = sum(all(r["ok"].values()) for r in space["rows"])
    assert sum(passes) == min(100, n_ok) and 0 < n_ok < 100         # both kinds are shown
    assert [v == "pass" for v in props["verdict"]["values"]] == [p == 1 for p in passes]
    for i, s in enumerate(ds["structures"]):                        # structures and table rows line up
        assert s["names"] == [props["site_A"]["values"][i], props["site_B"]["values"][i]] + [props["site_X"]["values"][i]] * 3
        assert abs(s["cell"][0] - props["lattice_a"]["values"][i]) < 1e-3
    assert ds["settings"]["map"]["x"]["property"] == "pred_heat_all"
    assert ds["settings"]["map"]["y"]["property"] == "pred_dir_gap"
    assert ds["settings"]["map"]["color"]["property"] in props
    assert ds["meta"]["authors"] == ["Anand Babu"]
    json.dumps(ds, allow_nan=False)                                 # chemiscope rejects NaN/Infinity


def test_select_rows_puts_passing_rows_first():
    from meidnet.studio.chemiscope import select_rows
    rows = [{"ok": {"a": i % 3 == 0, "b": True}} for i in range(30)]      # rows 0, 3, ..., 27 pass
    passing = list(range(0, 30, 3))
    idx = select_rows(rows, 15)
    assert idx[:10] == passing and len(set(idx)) == 15
    assert idx[10:] == sorted(idx[10:]) and all(i % 3 for i in idx[10:])
    assert select_rows(rows, 15) == idx                                  # seeded sample
    assert select_rows(rows, 4) == passing[:4]
    assert select_rows(rows, 100) == passing + [i for i in range(30) if i % 3]


def test_chemiscope_endpoint_data_and_candidates(studio, checked):
    data = studio.chemiscope(SID, "data")
    assert len(data["structures"]) == checked["kept"]
    heat = data["properties"]["heat_all"]
    assert heat["units"] == "eV/atom" and len(heat["values"]) == checked["kept"]
    truth = {str(m): v for m, v in zip(pd.read_csv(MINI)["material_id"], pd.read_csv(MINI)["heat_all"])}
    assert heat["values"] == [truth[m] for m in data["properties"]["material_id"]["values"]]
    assert studio.chemiscope(SID, "data") is data                    # cached per tab

    sid = "tab-search"
    assert studio.chemiscope(sid, "candidates")["available"] is False   # nothing searched yet
    r = studio.start_search({"session": sid, "generation": dict(TINY_SEARCH)})
    assert r["ok"], r
    snap = wait_done(studio, sid, "search")
    assert snap["error"] is None, snap["error"]
    assert snap["report"] and studio.resolve_file(snap["report"])
    cands = snap["candidates"]
    assert cands, f"the tiny search saved no candidate: {snap['log'][-6:]}"
    ds = studio.chemiscope(sid, "candidates")
    assert len(ds["structures"]) == len(cands)
    assert ds["properties"]["formula"]["values"] == [c["formula"] for c in cands]
    assert all(len(p["values"]) == len(cands) and single_type(p["values"]) for p in ds["properties"].values())
    assert ds["properties"]["target_dir_gap"]["values"] == [2.0] * len(cands)
    for s, c in zip(ds["structures"], cands):        # the saved CIFs, one element per prototype site
        assert sorted(set(s["names"])) == sorted(set(c["elements"].values()))
    json.dumps(ds, allow_nan=False)

    space = studio.chemiscope(sid, "space", "perovskite_abx3", "halide")
    rows = studio.family({"family": "perovskite_abx3", "variant": "halide"})["space"]["rows"]
    assert len(space["structures"]) == len(rows)                     # the whole halide space fits the cap
    assert studio.chemiscope(sid, "space", "perovskite_abx3", "halide") is space
    with pytest.raises(ValueError):
        studio.chemiscope(sid, "bogus")


def test_candidates_dataset_reads_cifs_or_rebuilds(tmp_path, studio):
    from pymatgen.io.cif import CifWriter
    from meidnet.constraints import build_candidate, evaluate
    from meidnet.family import load_family
    from meidnet.studio.chemiscope import candidates_dataset
    fam = load_family("perovskite_abx3", variant="halide")
    cands = []
    for i, els in enumerate(({"A": "Rb", "B": "Mn", "X": "I"}, {"A": "Cs", "B": "Pb", "X": "I"}), start=1):
        c = evaluate(build_candidate(fam, els), fam.constraints)
        cands.append({"file": f"cifs/cand_{i}.cif", "elements": els, "formula": c.formula(), "score": 0.1 * i,
                      "round": 1, "target_index": 1, "predictions": {"heat_all": -0.1, "dir_gap": 2.0 + i},
                      "target_values": {"dir_gap": 2.0, "heat_all": -0.1},
                      "constraint_results": [r.to_dict() for r in c.results]})
    os.makedirs(tmp_path / "generation" / "cifs")
    sc = build_candidate(fam, cands[0]["elements"]).raw * (2, 1, 1)       # only the first CIF exists (10 atoms)
    CifWriter(sc).write_file(str(tmp_path / "generation" / "cifs" / "cand_1.cif"))
    ds = candidates_dataset(cands, fam, run_dir=str(tmp_path))
    assert [s["size"] for s in ds["structures"]] == [10, 5]               # read from disk / rebuilt on the prototype
    props = ds["properties"]
    assert props["pred_dir_gap"]["description"] == "predicted dir_gap" and props["pred_dir_gap"]["units"] == ""
    lm = studio.lm                                                        # with the model: units and property names
    named = candidates_dataset(cands, fam, run_dir=str(tmp_path), lm=lm)["properties"]
    j = list(lm.stats.columns).index("dir_gap")
    assert named["pred_dir_gap"]["units"] == lm.stats.units[j] != ""
    assert named["target_dir_gap"]["description"] == f"target {lm.stats.labels[j]}"
    assert props["formula"]["values"] == ["RbMnI3", "CsPbI3"]
    assert props["pred_dir_gap"]["values"] == [3.0, 4.0] and props["target_dir_gap"]["values"] == [2.0, 2.0]
    assert "rule_tolerance_factor" in props and "rule_symmetry_refinement" not in props   # rules without a value
    assert all(len(p["values"]) == 2 and single_type(p["values"]) for p in props.values())
    assert ds["settings"]["map"]["x"]["property"] == "pred_heat_all"
    json.dumps(ds, allow_nan=False)


def test_published_data_dataset_is_cached(tmp_path):
    from meidnet.studio.chemiscope import published_data_dataset
    cache = tmp_path / "cache" / "perov5.json"
    ds = published_data_dataset(MINI, cache_path=str(cache), max_structures=10)
    assert len(ds["structures"]) == 10 and cache.exists()
    assert ds["properties"]["heat_all"]["units"] == "eV/atom" and ds["properties"]["dir_gap"]["units"] == "eV"
    again = published_data_dataset(str(tmp_path / "not-read.csv"), cache_path=str(cache))
    assert again == json.loads(json.dumps(ds))                            # served from the cache


def test_data_views_without_perov5(studio):
    """In a folder without data/perov5 the published-data views say so instead of failing."""
    assert studio.data("tab-fresh")["available"] is False
    assert studio.chemiscope("tab-fresh", "data")["available"] is False


def test_data_views_with_perov5_in_the_working_directory(tmp_path, monkeypatch):
    os.makedirs(tmp_path / "data" / "perov5")
    shutil.copy(MINI, tmp_path / "data" / "perov5" / "train.csv")       # stands in for the real split
    monkeypatch.chdir(tmp_path)
    st = Studio(None, model_path=CKPT, run_root=str(tmp_path / "runs"))
    summary = st.data("tab-local")
    assert summary["available"] and summary["rows"] == 64
    assert summary["stats"]["dir_gap"]["max"] == pytest.approx(3.5)
    ds = st.chemiscope("tab-local", "data")
    assert len(ds["structures"]) == 64
    assert (tmp_path / "runs" / "cache" / "perov5_chemiscope.json").exists()


# ───────────────────────── 7.-9. data, JSON, families ─────────────────────────
def test_records_keep_structures():
    from pymatgen.core import Structure
    from meidnet.config import DataSection
    from meidnet.data import featurize, load_records
    from meidnet.family import load_family
    df = pd.read_csv(MINI).head(8)
    dcfg = DataSection(table="materials.csv", properties=[{"column": "heat_all"}, {"column": "dir_gap"}],
                       prototype_tolerance=0.25)
    plain, _ = load_records(df, dcfg, lambda p: p)
    kept, rep = load_records(df, dcfg, lambda p: p, keep_structures=True)
    assert len(plain) == len(kept) == rep.kept == 8
    assert all(r.structure is None for r in plain)
    assert all(isinstance(r.structure, Structure) for r in kept)
    for a, b in zip(plain, kept):
        assert a.material_id == b.material_id and np.array_equal(a.dense, b.dense)
        assert b.structure.composition.reduced_formula == b.formula
    # with alignment the kept structure is the re-ordered one that was featurised
    fam = load_family("perovskite_abx3", default_variant=True)
    aligned, rep = load_records(df, dcfg, lambda p: p, family=fam, keep_structures=True)
    assert aligned and rep.aligned == len(aligned)
    for r in aligned:
        assert np.array_equal(featurize(r.structure, dcfg.max_sites, dcfg.neighbor_cutoff), r.dense)


def test_finite_json():
    src = {"a": float("nan"), "b": [1.5, float("inf"), {"c": float("-inf"), "d": "text"}],
           "e": np.float64("nan"), "f": np.float32(2.5), "g": (1, np.int64(7), None, True),
           "h": {"deep": [[np.float64("inf"), np.float64(0.25)]]}}
    out = _finite(src)
    assert out == {"a": None, "b": [1.5, None, {"c": None, "d": "text"}], "e": None, "f": 2.5,
                   "g": [1, 7, None, True], "h": {"deep": [[None, 0.25]]}}
    assert type(out["f"]) is float and type(out["g"][1]) is int     # numpy scalars become plain numbers
    json.dumps(out, allow_nan=False)
    assert _finite(-0.5) == -0.5 and _finite(3) == 3 and _finite("nan") == "nan" and _finite(None) is None


def test_family_for_prefers_generation_family():
    from meidnet.config import config_from_dict
    from meidnet.constraints import build_candidate, evaluate
    from meidnet.family import load_family
    from meidnet.pipeline import family_for
    rule = {"name": "property_window", "property": "dir_gap", "min": 1.0, "max": 3.0}
    cfg = config_from_dict({"family": "perovskite_abx3",
                            "generation": {"family": "double_perovskite_a2bbx6", "variant": "halide",
                                           "objectives": [{"property": "dir_gap"}], "targets": [{"dir_gap": 2.0}],
                                           "extra_constraints": [rule]}})
    fam = family_for(cfg, need_variant=True)
    assert fam.name == "double_perovskite_a2bbx6" and fam.variant == "halide"
    assert fam.constraints == load_family("double_perovskite_a2bbx6", variant="halide").constraints + [rule]
    assert family_for(cfg).name == "perovskite_abx3"     # the top-level family still aligns training data
    fam.constraints[-1]["max"] = 9.0                     # the family holds a copy of the rule
    assert cfg.generation.extra_constraints[0]["max"] == 3.0
    fam.constraints[-1]["max"] = 3.0
    # the appended rule is enforced by the same evaluate() the search uses
    for gap, ok in ((2.0, True), (5.0, False)):
        cand = build_candidate(fam, {"A": "Cs", "B1": "Ag", "B2": "Bi", "X": "I"})
        cand.predictions = {"dir_gap": gap}
        evaluate(cand, fam.constraints)
        assert cand.passed is ok and (ok or cand.first_failure == "property_window")


# ───────────────────────── 10. sessions ─────────────────────────
def test_reset_session_and_session_ids(studio):
    sid = "tab-reset"
    studio.upload(mini_upload(sid))
    s = studio.session(sid)
    assert os.path.isdir(s.dir) and os.path.isfile(s.table_path)
    assert studio.reset_session(sid) == {"ok": True}
    assert not os.path.exists(s.dir) and sid not in studio.sessions
    assert studio.state(sid)["session"]["has_upload"] is False       # the tab starts again empty
    for bad in ("../x", "..\\x", "a/b/c", "tab 1", "ab", "x" * 65):
        with pytest.raises(ValueError):
            studio.session(bad)
    with pytest.raises(ValueError):
        studio.reset_session("../x")
    with pytest.raises(ValueError):
        studio.status("../x")
    assert not os.path.exists(os.path.join(studio.run_root, "x"))


def test_busy_session_is_not_reset(studio):
    s = studio.session("tab-busy")
    s.train = Job("train")                                           # still running
    studio.reset_session("tab-busy")
    assert os.path.isdir(s.dir) and "tab-busy" in studio.sessions
    s.train.running = False
    studio.reset_session("tab-busy")
    assert not os.path.exists(s.dir) and "tab-busy" not in studio.sessions


def test_idle_sessions_are_cleaned_up(studio, public_studio):
    from meidnet.studio.server import SESSION_TTL
    idle, busy, recent = (public_studio.session(f"tab-{k}") for k in ("idle", "idle-busy", "recent"))
    busy.train = Job("train")                                        # still running
    for s in (idle, busy):
        s.touched = time.time() - SESSION_TTL - 1
    try:
        public_studio._cleanup()
        assert "tab-idle" not in public_studio.sessions and not os.path.exists(idle.dir)
        assert "tab-idle-busy" in public_studio.sessions and os.path.isdir(busy.dir)   # a running job keeps its tab
        assert "tab-recent" in public_studio.sessions and os.path.isdir(recent.dir)
    finally:
        busy.train.running = False
        public_studio.reset_session("tab-idle-busy")
    local = studio.session("tab-local-idle")                         # a local Studio keeps the user's files
    local.touched = time.time() - SESSION_TTL - 1
    studio._cleanup()
    assert "tab-local-idle" in studio.sessions and os.path.isdir(local.dir)
    studio.reset_session("tab-local-idle")


def test_resolve_file_serves_the_docs_folder(studio, tmp_path, monkeypatch):
    docs = tmp_path / "site"
    (docs / "guide").mkdir(parents=True)
    (docs / "index.html").write_text("<html>home</html>", encoding="utf-8")
    (docs / "guide" / "index.html").write_text("<html>guide</html>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    assert studio.resolve_file("docs/index.html") is None             # no documentation folder configured
    monkeypatch.setattr(studio, "docs_dir", str(docs))
    assert studio.state("tab-docs")["docs_url"] == "/docs/"
    assert studio.resolve_file("docs/") == os.path.join(str(docs), "index.html")
    assert studio.resolve_file("docs/guide") == os.path.join(str(docs), "guide", "index.html")
    assert studio.resolve_file("docs/guide/index.html") == os.path.join(str(docs), "guide", "index.html")
    for rel in ("docs/../secret.txt", "docs/..%2Fsecret.txt", "docs/..\\secret.txt", "docs/missing.html"):
        assert studio.resolve_file(rel) is None, rel


def test_status_of_an_unknown_tab(studio):
    assert studio.status("tab-never-seen", "search") == EMPTY_STATUS
    assert studio.status("tab-never-seen", "train") == EMPTY_STATUS
    assert "tab-never-seen" not in studio.sessions                   # polling does not create sessions


def test_resolve_file_stays_inside_run_root(studio, workdir):
    inside = os.path.join(studio.run_root, "sessions", "tab-files", "report.html")
    os.makedirs(os.path.dirname(inside), exist_ok=True)
    with open(inside, "w", encoding="utf-8") as f:
        f.write("<html></html>")
    (workdir / "outside.txt").write_text("secret")
    os.makedirs(workdir / "runs_evil", exist_ok=True)
    (workdir / "runs_evil" / "x.txt").write_text("secret")
    assert studio.resolve_file("sessions/tab-files/report.html") == inside
    assert studio.resolve_file("sessions%2Ftab-files%2Freport.html") == inside
    for rel in ("../outside.txt", "..\\outside.txt", "%2e%2e/outside.txt", "../runs_evil/x.txt",
                str(workdir / "outside.txt"), "docs/index.html", "sessions/tab-files/missing.html"):
        assert studio.resolve_file(rel) is None, rel


# ───────────────────────── public mode ─────────────────────────
def test_public_mode_guards(public_studio, workdir):
    st = public_studio.state("tab-public")
    assert st["public"] and st["limits"] == PUBLIC_LIMITS
    assert st["model"]["path"] == os.path.basename(CKPT)              # no server paths for visitors
    assert os.path.dirname(CKPT) not in st["model"]["description"]
    with pytest.raises(ValueError):
        public_studio.family({"session": "tab-public",
                              "family": os.path.join(ROOT, "meidnet", "families", "perovskite_abx3.yaml")})
    public_studio.upload(mini_upload("tab-public"))
    with pytest.raises(ValueError, match="built-in"):
        public_studio.check_data(dict(CHECK, session="tab-public", family="/somewhere/my_family.yaml"))
    text = public_studio.export({"session": "tab-public", "generation": {}})
    assert "<path to the model file>" in text and os.path.basename(str(workdir)) not in text
    big = b"x" * (PUBLIC_LIMITS["upload_mb"] * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="too large"):
        public_studio.upload({"session": "tab-public", "files": [{"name": "big.csv", "b64": b64(big)}]})


def test_public_server_runs_a_limited_number_of_jobs(public_studio):
    from meidnet.studio.server import MAX_RUNNING
    sid = "tab-queued"
    public_studio.upload(mini_upload(sid))
    public_studio.check_data(dict(CHECK, session=sid))
    others = [public_studio.session(f"tab-running{i}") for i in range(MAX_RUNNING)]
    try:
        for s in others:
            s.search = Job("search")                                 # jobs of other visitors, still running
        r = public_studio.start_search({"session": sid, "generation": dict(TINY_SEARCH)})
        assert r["ok"] is False and r["busy"] is True, r
        r = public_studio.start_train({"session": sid, "epochs": 1})
        assert r["ok"] is False and r["busy"] is True, r
        assert public_studio.status(sid, "search") == EMPTY_STATUS == public_studio.status(sid, "train")
        r = public_studio.start_search({"session": "tab-running0", "generation": {}})
        assert r == {"ok": False, "error": "this session is already running a job"}
    finally:
        for s in others:
            s.search.running = False
            public_studio.reset_session(s.sid)
    # once they have finished the tab may train, with the epochs capped for visitors
    assert public_studio.start_train({"session": sid, "epochs": 10_000, "batch_size": 8}) == \
        {"ok": True, "epochs": PUBLIC_LIMITS["epochs"]}
    public_studio.stop(sid)
    snap = wait_done(public_studio, sid, "train", timeout=120)
    assert snap["error"] is None and snap["progress"]["epochs"] == PUBLIC_LIMITS["epochs"]
    assert len(snap["progress"]["curve"]) == 1


def test_public_upload_is_truncated_to_the_row_limit(public_studio):
    n = PUBLIC_LIMITS["rows"] + 100
    csv = "material_id,band_gap\n" + "".join(f"m{i},{i * 0.001:.3f}\n" for i in range(n))
    up = public_studio.upload({"session": "tab-many", "files": [{"name": "t.csv", "b64": b64(csv.encode())}]})
    assert up["rows"] == PUBLIC_LIMITS["rows"] and up["truncated"] is True
    assert len(pd.read_csv(public_studio.session("tab-many").table_path)) == PUBLIC_LIMITS["rows"]
    assert up["suggest"]["id_column"] == "material_id" and up["suggest"]["properties"] == ["band_gap"]
    assert up["suggest"]["cif_column"] is None
    exact = csv.splitlines(keepends=True)[:PUBLIC_LIMITS["rows"] + 1]   # header + exactly the limit: nothing cut
    up = public_studio.upload({"session": "tab-exact", "files": [{"name": "t.csv", "b64": b64("".join(exact).encode())}]})
    assert up["rows"] == PUBLIC_LIMITS["rows"] and up["truncated"] is False


def _strings(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)
    elif isinstance(x, str):
        yield x


def test_public_state_shows_no_server_paths(public_studio):
    sid = "tab-paths"
    public_studio.upload(mini_upload(sid))
    public_studio.check_data(dict(CHECK, session=sid))
    s = public_studio.session(sid)
    assert public_studio.state(sid)["config"]["model_path"] == os.path.basename(CKPT)   # the published config
    s.lm = public_studio.lm                                   # as if this tab had trained: its own config is shown
    try:
        cfg = public_studio.state(sid)["config"]
        assert cfg["name"] == "your_data" and cfg["data"]["table"] == "table.csv"
        assert [v for v in _strings(cfg) if os.path.isabs(v)] == []
    finally:
        s.lm = None


# ───────────────────────── errors reach the page ─────────────────────────
def test_validate_rejects_text_that_is_not_settings(studio):
    for text in ("- rounds: 2\n", "just some words\n", "42\n"):
        r = studio.validate({"yaml": text})
        assert not r["ok"] and "key: value" in r["errors"][0], (text, r)
    assert studio.validate({"yaml": ""})["ok"]                  # empty text: nothing changes
    assert studio.validate({"yaml": "generation:\n"})["ok"]


def test_unknown_variant_is_reported_not_silent(studio):
    r = studio.validate({"generation": {"variant": "bogus"}})
    assert not r["ok"] and "bogus" in r["errors"][0], r
    sid = "tab-badvariant"
    studio.upload(mini_upload(sid))
    with pytest.raises(ValueError, match="bogus"):
        studio.check_data(dict(CHECK, session=sid, variant="bogus"))
    studio.check_data(dict(CHECK, session=sid, variant=None))   # no variant named: the family's first, so a
    from meidnet.family import load_family                       # later search has one
    assert studio.session(sid).cfg.generation.variant == load_family("perovskite_abx3", default_variant=True).variant
    # a search with a wrong variant, or a window on a property the model does not predict, is refused at once
    r = studio.start_search({"session": "tab-badsearch", "generation": dict(TINY_SEARCH, variant="bogus")})
    assert r["ok"] is False and "bogus" in r["error"], r
    window = {"name": "property_window", "property": "no_such_prop", "min": 0.0}
    r = studio.start_search({"session": "tab-badsearch", "generation": dict(TINY_SEARCH, extra_constraints=[window])})
    assert r["ok"] is False and "no_such_prop: not predicted by this model" in r["error"], r
    assert studio.status("tab-badsearch", "search") == EMPTY_STATUS                # no job was started


def test_busy_session_refuses_new_data(studio):
    sid = "tab-busydata"
    studio.upload(mini_upload(sid))
    s = studio.session(sid)
    s.train = Job("train")                                      # still running
    try:
        with pytest.raises(ValueError, match="stop it"):
            studio.upload(mini_upload(sid))
        with pytest.raises(ValueError, match="stop it"):
            studio.check_data(dict(CHECK, session=sid))
    finally:
        s.train.running = False


def test_upload_counts_and_id_guess(studio):
    sid = "tab-recount"
    cif = b64(pd.read_csv(MINI)["cif"].iloc[0].encode())
    with open(MINI, "rb") as f:
        table = b64(f.read())
    up = studio.upload({"session": sid, "files": [{"name": "materials.csv", "b64": table},
                                                  {"name": "a.cif", "b64": cif}, {"name": "b.cif", "b64": cif}]})
    assert up["n_cifs"] == 2
    assert studio.upload(mini_upload(sid))["n_cifs"] == 0       # a new upload starts from scratch
    csv = "formula,is_hybrid,material_id,band_gap\n" + "".join(f"CsPbI3,0,m{i},{1 + i * 0.01:.2f}\n" for i in range(8))
    up = studio.upload({"session": "tab-idguess", "files": [{"name": "t.csv", "b64": b64(csv.encode())}]})
    assert up["suggest"]["id_column"] == "material_id"            # not "is_hybrid", which merely contains "id"


def test_upload_reads_excel_and_explains_missing_readers(studio, tmp_path):
    pytest.importorskip("openpyxl")
    xlsx = tmp_path / "materials.xlsx"
    pd.read_csv(MINI).to_excel(xlsx, index=False)
    up = studio.upload({"session": "tab-excel", "files": [{"name": "materials.xlsx", "b64": b64(xlsx.read_bytes())}]})
    assert up["rows"] == 64 and up["suggest"]["cif_column"] == "cif" and up["suggest"]["id_column"] == "material_id"
    try:
        import pyarrow  # noqa: F401
    except ImportError:                                           # without pyarrow: a message, not a crash
        with pytest.raises(ValueError, match="pyarrow"):
            studio.upload({"session": "tab-parquet", "files": [{"name": "t.parquet", "b64": b64(b"PAR1")}]})


def test_search_stops_inside_a_round(tmp_path):
    from meidnet.checkpoint import load_checkpoint
    from meidnet.config import GenerationSection
    from meidnet.family import load_family
    from meidnet.generate import Designer
    g = GenerationSection(family="perovskite_abx3", variant="halide", objectives=[{"property": "dir_gap"}],
                          targets=[{"dir_gap": 2.0}], per_target=1, population=8, rounds=3, steps=5000)
    steps = []
    designer = Designer(load_checkpoint(CKPT), load_family("perovskite_abx3", variant="halide"), g,
                        log=lambda *a: None, on_step=lambda step, n, loss: steps.append(step),
                        should_stop=lambda: bool(steps))           # "Stop" pressed during the first round
    res = designer.run(str(tmp_path / "out"))
    assert steps == [0] and res.saved == [] and res.targets[0].rounds_used == 0


# ───────────────────────── a public host protects itself and its visitors ─────────────────────────
def _zip(members: dict) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return b64(buf.getvalue())


def test_public_zip_uploads_are_bounded(public_studio):
    from meidnet.studio.server import CIF_MAX_KB
    with open(MINI, "rb") as f:
        table = {"name": "materials.csv", "b64": b64(f.read())}
    big = _zip({"huge.cif": b"0" * (CIF_MAX_KB * 1024 + 10)})            # compresses to a few bytes
    with pytest.raises(ValueError, match="really a CIF"):
        public_studio.upload({"session": "tab-zipbomb", "files": [table, {"name": "s.zip", "b64": big}]})
    many = _zip({f"m{i}.cif": b"data_x\n" for i in range(PUBLIC_LIMITS["rows"] + 1)})
    with pytest.raises(ValueError, match="at most"):
        public_studio.upload({"session": "tab-zipbomb", "files": [table, {"name": "s.zip", "b64": many}]})
    assert len(os.listdir(os.path.join(public_studio.session("tab-zipbomb").data_dir))) <= 2   # nothing unpacked


def test_yaml_aliases_are_refused(studio):
    bomb = "a: &a [1, 1, 1]\nb: &b [*a, *a, *a]\ngeneration:\n  overrides: {tolerance_factor: {max: 1.0, x: *b}}\n"
    r = studio.validate({"yaml": bomb})
    assert not r["ok"] and "aliases" in r["errors"][0], r


def test_public_search_settings_are_allow_listed(public_studio):
    gen = {"decode_tries": 10 ** 9, "rff_frequencies": 6_000_000, "output_prefix": "x",
           "overrides": {"bond_window": {"cutoff": 1000.0, "low": 0.7, "from": "A"}},
           "extra_constraints": [{"name": "bond_window", "from": "X", "to": "B", "cutoff": 1000.0},
                                 {"name": "property_window", "property": "dir_gap", "min": 1.0, "evil": "x"}]}
    r = public_studio.validate({"generation": gen})
    assert r["ok"], r
    g = r["generation"]
    defaults = public_studio.cfg.generation
    assert g["decode_tries"] == defaults.decode_tries and g["rff_frequencies"] == defaults.rff_frequencies
    assert g["output_prefix"] == defaults.output_prefix
    assert g["overrides"] == {"bond_window": {"cutoff": 8.0, "low": 0.7}}
    assert g["extra_constraints"] == [{"name": "property_window", "property": "dir_gap", "min": 1.0}]
    assert any("decode_tries" in n for n in r["notes"]) and any("windows" in n for n in r["notes"])


def test_property_windows_must_name_a_model_property(studio):
    r = studio.validate({"generation": {"extra_constraints": [{"name": "property_window", "property": "band_gap",
                                                               "min": 1.0}]}})
    assert not r["ok"] and "band_gap" in r["errors"][0], r


def test_public_files_serve_only_run_outputs(public_studio):
    sid = "tab-filesafe"
    public_studio.upload(mini_upload(sid))
    s = public_studio.session(sid)
    rel_upload = os.path.relpath(s.table_path, public_studio.run_root).replace(os.sep, "/")
    assert public_studio.resolve_file(rel_upload) is None                 # the visitor's data is never served
    os.makedirs(s.share_dir, exist_ok=True)
    report = os.path.join(s.share_dir, "generation_report.html")
    with open(report, "w", encoding="utf-8") as f:
        f.write("<html></html>")
    rel = os.path.relpath(report, public_studio.run_root).replace(os.sep, "/")
    assert rel.startswith("shared/") and sid not in rel                   # a shared link hides the session id
    assert public_studio.resolve_file(rel) == report
    assert public_studio.resolve_file("shared/../sessions/" + sid + "/data/table.csv") is None


def test_public_reserved_sessions_and_shared_cache(public_studio):
    with pytest.raises(ValueError, match="own session"):
        public_studio.upload(mini_upload("localtab"))
    assert public_studio.state("local")["public"]                          # read-only views still work
    small = public_studio.family({"family": "perovskite_abx3", "variant": "oxide", "max_compositions": 1})
    assert len(small["space"]["rows"]) == 21 * 23                          # visitors cannot shrink the shared cache
