"""The scripts behind the reproduction page work after a plain `pip install meidnet` and from the downloaded data."""
import importlib.util
import os
import sys
import urllib.request

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_published_seed_checkpoint_downloads_without_the_hugging_face_library(tmp_path, monkeypatch):
    mod = _load("scripts/reproduce_alignment.py", "reproduce_alignment")
    monkeypatch.setattr(mod, "ROOT", str(tmp_path / "repo"))                  # no checkpoints/reproduction/ here
    for var in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(var, str(tmp_path / "home"))
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)                  # not a dependency of meidnet
    calls = []

    def fake_download(url, path):
        calls.append(url)
        with open(path, "wb") as f:
            f.write(b"checkpoint")

    monkeypatch.setattr(urllib.request, "urlretrieve", fake_download)
    path = mod.checkpoint_path(4)
    assert calls == ["https://huggingface.co/Babu09/MEIDNet/resolve/main/reproduction/meidnet_paper_rerun_seed4.pth"]
    assert path == os.path.join(str(tmp_path / "home"), ".meidnet", "reproduction", "meidnet_paper_rerun_seed4.pth")
    assert mod.checkpoint_path(4) == path and len(calls) == 1                  # downloaded once


def test_prepare_data_writes_the_training_input_sorted_and_inside_the_cell(tmp_path, monkeypatch):
    mini = pd.read_csv(os.path.join(ROOT, "tests", "data", "perov5_mini.csv"))
    data = tmp_path / "perov5"
    data.mkdir()
    for k, split in enumerate(("train", "val", "test")):                       # three splits, ids out of order
        mini.iloc[k::3].iloc[::-1].to_csv(data / f"{split}.csv", index=False)
    out = tmp_path / "out"
    out.mkdir()
    mod = _load("reproduction/paper_alignment/prepare_data.py", "prepare_data")
    monkeypatch.setattr(sys, "argv", ["prepare_data.py", "--data-dir", str(data), "--out", str(out)])
    mod.main()

    table = pd.read_csv(out / "train.csv")
    assert list(table.columns) == ["material_id", "heat_all", "dir_gap"]
    assert len(table) == len(mini) and table.material_id.is_monotonic_increasing
    from pymatgen.core import Structure
    for mid in table.material_id:
        s = Structure.from_file(str(out / "cif_files" / f"{mid}.cif"))
        assert ((s.frac_coords >= 0) & (s.frac_coords < 1)).all()
