"""
MEIDNet 2 must reproduce the published MEIDNet v1 numbers exactly.

The reference files in tests/golden/ were produced by the unmodified v1 code
(tests/legacy_v1/, byte-for-byte copies of commit ed62f6a) via
tests/legacy_v1/capture_golden.py.  If one of these tests fails, the refactor has
changed the method - not merely the code.
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GOLDEN = os.path.join(ROOT, "tests", "golden")
MINI = os.path.join(ROOT, "tests", "data", "perov5_mini.csv")
CKPT = os.path.join(ROOT, "checkpoints", "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth")

sys.path.insert(0, ROOT)
torch.set_num_threads(1)


@pytest.fixture(scope="module")
def mini():
    df = pd.read_csv(MINI)
    from meidnet.data import featurize, parse_structure
    dense = np.stack([featurize(parse_structure(cif_text=c)) for c in df.cif])
    return df, dense


def test_featurisation_matches_v1(mini):
    df, dense = mini
    g1 = np.load(os.path.join(GOLDEN, "g1_dense.npz"))
    assert list(g1["ids"]) == [str(m) for m in df.material_id]
    assert np.array_equal(dense, g1["dense"])


def test_published_checkpoint_forward_matches_v1(mini):
    from meidnet.checkpoint import load_checkpoint
    df, dense = mini
    g2 = np.load(os.path.join(GOLDEN, "g2_forward.npz"))
    lm = load_checkpoint(CKPT)
    assert lm.legacy and lm.stats.columns == ["heat_all", "dir_gap"]
    x = torch.from_numpy(dense).float()
    p = torch.tensor(np.stack([df.heat_all.values, df.dir_gap.values], 1), dtype=torch.float32)
    with torch.no_grad():
        zc, zp, lat, adj, spc, crd, prop = lm.model(x, p)
        prop_zc = lm.model.property_decoder(zc)
    for name, val in dict(zc=zc, zp=zp, lat=lat, spc=spc, crd=crd, prop=prop, prop_from_zc=prop_zc).items():
        assert np.array_equal(val.numpy(), g2[name]), name


def test_all_three_published_checkpoints_load():
    from meidnet.checkpoint import load_checkpoint
    for f in ("dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth",
              "dual_autoencoder_clip_earlyfusion_propertyaware.pth", "dual_autoencoder_clip_earlyfusion.pth"):
        lm = load_checkpoint(os.path.join(ROOT, "checkpoints", f))
        assert lm.model.n_properties == 2


def test_two_training_epochs_match_v1(mini):
    from meidnet.checkpoint import build_model
    from meidnet.config import TrainingSection
    from meidnet.data import MaterialsDataset, PropertyStats, Record
    from meidnet.train import fit, seed_everything
    import meidnet.train as T
    df, dense = mini
    meta = json.load(open(os.path.join(GOLDEN, "meta.json")))
    stats = PropertyStats.from_dict([{"column": "heat_all", "mean": 0.0, "std": 1.0},
                                     {"column": "dir_gap", "mean": 0.0, "std": 1.0}])
    by_id = {str(m): (d, h, g) for m, d, h, g in zip(df.material_id, dense, df.heat_all, df.dir_gap)}
    recs = [Record(mid, by_id[mid][0], np.array([by_id[mid][1], by_id[mid][2]]), "") for mid in meta["g3_order"]]
    seed_everything(0)
    model = build_model(2, {}, 20)
    losses = []
    orig = T.train_step

    def spy(*a, **k):
        out = orig(*a, **k)
        losses.append([v.item() for v in out[1].values()])
        return out

    T.train_step = spy
    try:
        fit(model, MaterialsDataset(recs, stats), None,
            TrainingSection(epochs=2, batch_size=16, contrastive_warmup_epochs=1200), log=lambda *a: None)
    finally:
        T.train_step = orig
    assert np.array_equal(np.array(meta["g3_losses"]), np.array(losses))
    h = hashlib.sha256()
    for k, v in sorted(model.state_dict().items()):
        h.update(k.encode())
        h.update(v.detach().numpy().tobytes())
    assert h.hexdigest() == meta["g3_state_sha256"]


@pytest.mark.slow
@pytest.mark.parametrize("case", ["halide", "oxide"])
def test_generation_matches_v1(case, tmp_path):
    """Full inverse-design run: same CIFs, same predictions, same file names as deterministic v1."""
    sys.path.insert(0, os.path.dirname(__file__))
    from compare_v1 import run_v1, run_v2
    a = run_v1(case, str(tmp_path / "v1"))
    b = run_v2(case, str(tmp_path / "v2"))
    assert len(a) == len(b) > 0
    for x, y in zip(a, b):
        assert x["file"] == y["file"]
        assert (x["A"], x["B"], x["X"]) == (y["A"], y["B"], y["X"])
        assert x["cif"] == y["cif"]
        for k in ("dir_gap", "heat_all", "a0", "t", "mu"):
            assert x[k] == y[k], k
