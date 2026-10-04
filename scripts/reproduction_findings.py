"""
Condense the analysis data of the Perov-5 alignment runs into the small files the documentation is generated from.

    python scripts/reproduction_findings.py <analysis folder>     # the unpacked analysis archive of the runs

Reads   <folder>/results/final_results_all_runs.csv, results/snapshots_during_training_seed6.csv and
        <folder>/analysis_data/ (per-material tables, latents, decoded crystals, training curves, dataset table).
Writes  benchmarks/reproduction/perov5/findings.json            every number the pages quote
        benchmarks/reproduction/perov5/runs.csv                  one row per run
        benchmarks/reproduction/perov5/snapshots_seed6.csv       seed 6 during training, with and without the curriculum
        benchmarks/reproduction/perov5/per_material_7seeds.csv.gz   per material and seed: matched or not, cosine

The seven runs are seeds 0 to 6 of the alignment training script (2,200 epochs, all 18,928 materials). Other runs:
without the curriculum (3 seeds), and trained on 80 % of the materials with 20 % held out (3 seeds).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "benchmarks", "reproduction", "perov5")
SEVEN = [f"B_seed{i}" for i in range(6)] + ["instrumented_seed6"]
SITES = ["A", "B", "X1", "X2", "X3"]


def stats(x) -> dict:
    x = np.asarray(x, dtype=float)
    return {"mean": float(x.mean()), "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0, "min": float(x.min()), "max": float(x.max()), "n": int(len(x))}


def auc(y, score) -> float:
    """Area under the ROC curve (probability that a matched material has the higher score), ties counted half."""
    y = np.asarray(y).astype(bool)
    r = pd.Series(score).rank().to_numpy()
    n1, n0 = int(y.sum()), int((~y).sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def participation_ratio(x) -> float:
    x = np.asarray(x, dtype=np.float64)
    sv = np.linalg.svd(x - x.mean(0), compute_uv=False) ** 2
    return float(sv.sum() ** 2 / (sv ** 2).sum())


def main(folder: str):
    from meidnet import benchmark as B
    A = os.path.join(folder, "analysis_data")
    res = pd.read_csv(os.path.join(folder, "results", "final_results_all_runs.csv"))
    snaps = pd.read_csv(os.path.join(folder, "results", "snapshots_during_training_seed6.csv"))
    table = pd.read_csv(os.path.join(A, "dataset", "dataset_table.csv"))
    curves = pd.read_csv(os.path.join(A, "training_curves.csv"))

    def per_material(run):
        p = pd.read_csv(os.path.join(A, "runs", run, "per_material.csv.gz"))
        p["material_id"] = p.material_id.astype(str)
        st, sp = p.species_true.str.split(" ", expand=True), p.species_pred.str.split(" ", expand=True)
        p["A"], p["B"] = st[0], st[1]
        p["anion"] = st[[2, 3, 4]].apply(lambda r: "".join(sorted(r)), axis=1)
        for k, name in enumerate(SITES):
            p["ok_" + name] = (st[k] == sp[k]).astype(int)
        return p

    def decoded(run, ids):
        d = np.load(os.path.join(A, "runs", run, "decoded.npz"))
        order = pd.Series(np.arange(len(d["material_id"])), index=d["material_id"].astype(str)).loc[ids].to_numpy()
        return {k: d[k][order] for k in ("species_top5_idx", "species_top5_prob", "species_pred_idx")}

    def latents(run, ids):
        e = np.load(os.path.join(A, "runs", run, "embeddings.npz"))
        order = pd.Series(np.arange(len(e["material_id"])), index=e["material_id"].astype(str)).loc[ids].to_numpy()
        return {k: e[k][order].astype(np.float64) for k in ("z_crystal", "z_property", "z_joint")}

    P = {r: per_material(r) for r in SEVEN}
    ids = P[SEVEN[0]].material_id.to_numpy()
    for r in SEVEN:
        P[r] = P[r].set_index("material_id").loc[ids].reset_index()
    pooled = pd.concat([P[r].assign(run=r) for r in SEVEN], ignore_index=True)
    F: dict = {"dataset": "perov5", "n_materials": int(len(ids)),
               "training": {"epochs": 2200, "batch": 16, "optimizer": "Adam, learning rate 1e-3", "contrastive_weight": 5, "warmup_epochs": 1500, "temperature": 0.01}}

    # ── the seven seeds ──
    seven = res[res.run.isin(SEVEN)].copy()
    seven["seed"] = seven.seed.astype(int)
    cols = {"cosine": "cosine_before_projection", "l2": "l2_before_projection", "sm_sampled": "structure_matching_sampled_in_run_pct",
            "sm_likely": "structure_matching_most_likely_pct", "cosine_after_projection": "cosine_after_projection",
            "recall_at_1": "recall_at_1_crystal_to_property", "recall_at_10": "recall_at_10_crystal_to_property",
            "median_rank": "median_rank_crystal_to_property", "site_accuracy": "site_species_accuracy_pct",
            "composition_exact": "composition_exact_pct", "lattice_mae": "lattice_length_mae_angstrom", "coord_mae": "frac_coord_mae",
            "r2_heat_all": "r2_heat_all", "r2_dir_gap": "r2_dir_gap", "hours": "training_hours"}
    F["runs"] = [{"seed": int(r.seed), **{k: float(r[c]) for k, c in cols.items()}} for _, r in seven.sort_values("seed").iterrows()]
    F["summary"] = {k: stats(seven[c]) for k, c in cols.items()}
    a, b = res[res.run.str.match(r"A_seed[012]$")].sort_values("seed"), res[res.run.str.match(r"B_seed[012]$")].sort_values("seed")
    same = [c for c in res.columns if c not in ("run", "what", "training_hours")]
    F["determinism"] = {"identical": bool((a[same].astype(str).to_numpy() == b[same].astype(str).to_numpy()).all()), "seeds": [0, 1, 2],
                        "setups": ["torch 2.6.0, pymatgen 2024.11.13, NVIDIA A100 40 GB", "torch 2.8.0, pymatgen 2025.10.7, NVIDIA A100 80 GB"]}
    F["correlation_cosine_vs_matching"] = {"sampled": float(np.corrcoef(seven[cols["cosine"]], seven[cols["sm_sampled"]])[0, 1]),
                                           "most_likely": float(np.corrcoef(seven[cols["cosine"]], seven[cols["sm_likely"]])[0, 1])}

    # ── without the curriculum; held out ──
    no = res[res.run.str.startswith("noCL_seed")]
    F["no_curriculum"] = {"epochs": 2500, "summary": {k: stats(no[cols[k]]) for k in ("cosine", "l2", "sm_sampled", "sm_likely")},
                          "runs": [{"seed": int(r.seed), "cosine": float(r[cols["cosine"]]), "l2": float(r[cols["l2"]]), "sm_sampled": float(r[cols["sm_sampled"]])} for _, r in no.iterrows()]}
    ho = res[res.run.str.startswith("heldout")]
    F["heldout"] = {"n_train": int(ho[ho.scored_on == "train80"].n.iloc[0]), "n_test": int(ho[ho.scored_on == "test20"].n.iloc[0])}
    for split, key in (("test20", "unseen"), ("train80", "seen")):
        g = ho[ho.scored_on == split]
        F["heldout"][key] = {k: stats(g[cols[k]]) for k in ("cosine", "l2", "sm_sampled", "sm_likely", "recall_at_1")}

    # ── during training: seed 6 ──
    snap_cols = ["epoch", "cosine_before_projection", "structure_matching_most_likely_pct", "composition_exact_pct", "recall_at_1_crystal_to_property"]
    F["snapshots"] = {name: [{"epoch": int(r.epoch), "cosine": float(r.cosine_before_projection), "sm": float(r.structure_matching_most_likely_pct),
                              "composition": float(r.composition_exact_pct)} for _, r in snaps[snaps.curriculum == flag].sort_values("epoch").iterrows()]
                      for name, flag in (("curriculum", True), ("no_curriculum", False))}
    cur = snaps[snaps.curriculum].sort_values("epoch")
    late = cur[cur.epoch >= 300]
    pk = cur.loc[cur.structure_matching_most_likely_pct.idxmax()]
    F["snapshots"]["peak"] = {"epoch": int(pk.epoch), "sm": float(pk.structure_matching_most_likely_pct), "cosine": float(pk.cosine_before_projection)}
    F["snapshots"]["final"] = {"epoch": int(cur.iloc[-1].epoch), "sm": float(cur.iloc[-1].structure_matching_most_likely_pct), "cosine": float(cur.iloc[-1].cosine_before_projection)}
    F["snapshots"]["after_300"] = {"min": float(late.structure_matching_most_likely_pct.min()), "max": float(late.structure_matching_most_likely_pct.max())}
    c7 = curves[curves.run.isin(SEVEN)].pivot(index="epoch", columns="run", values="cosine_train_batches")[SEVEN]
    marks = [10, 25, 50, 100, 200, 400, 800, 1500, 2200]
    F["seed_spread"] = {"epochs": marks, "min": [float(c7.loc[e].min()) for e in marks], "max": [float(c7.loc[e].max()) for e in marks],
                        "rank_correlation_with_final": {str(e): float(c7.loc[e].rank().corr(c7.loc[2200].rank())) for e in (100, 400, 800)}}
    grid = sorted(set(list(range(1, 50, 2)) + list(range(50, 400, 10)) + list(range(400, 2201, 50)) + [2200]))
    F["seed_curves"] = {"epochs": grid, "cosine": {str(i): [round(float(c7.loc[e, r]), 4) for e in grid] for i, r in enumerate(SEVEN)}}

    # ── which materials fail, and why ──
    M = np.stack([P[r].match_most_likely_element.to_numpy() for r in SEVEN], 1)
    k = M.sum(1)
    C = np.stack([P[r].cosine_before_projection.to_numpy() for r in SEVEN], 1)
    iu = np.triu_indices(7, 1)
    F["consistency"] = {"matched_in_k_seeds": {str(i): int((k == i).sum()) for i in range(8)},
                        "always_pct": float(100 * (k == 7).mean()), "never_pct": float(100 * (k == 0).mean()), "any_pct": float(100 * (k > 0).mean()),
                        "never_n": int((k == 0).sum()),
                        "correlation_match": float(np.corrcoef(M.T)[iu].mean()), "correlation_cosine": float(np.corrcoef(C.T)[iu].mean())}
    fail, wrong = pooled[pooled.match_most_likely_element == 0], pooled[pooled.composition_exact == 0]
    right = pooled[pooled.composition_exact == 1]
    F["failures"] = {"share_pct": float(100 * len(fail) / len(pooled)), "wrong_composition_pct": float(100 * (fail.composition_exact == 0).mean()),
                     "site_accuracy_pct": {s: float(100 * pooled["ok_" + s].mean()) for s in SITES},
                     "wrong_site_pct": {s: float(100 * (1 - wrong["ok_" + s].mean())) for s in SITES},
                     "match_given_right_composition_pct": float(100 * right.match_most_likely_element.mean()),
                     "match_given_wrong_composition_pct": float(100 * wrong.match_most_likely_element.mean()),
                     "lattice_mae": float(np.abs(pooled.a_pred - pooled.a_true).mean())}
    F["most_likely_gain"] = {"per_seed": [float(100 * (P[r].match_most_likely_element.mean() - P[r].match_sampled_element_in_run_evaluation.mean())) for r in SEVEN]}
    F["most_likely_gain"]["mean"] = float(np.mean(F["most_likely_gain"]["per_seed"]))

    # ── chemistry ──
    g = pooled.groupby("anion").agg(n=("material_id", lambda x: len(x) // 7), sm=("match_most_likely_element", "mean"), comp=("composition_exact", "mean"))
    F["by_anion"] = [{"anions": i, "n": int(r.n), "sm": float(100 * r.sm), "composition": float(100 * r.comp)} for i, r in g.sort_values("sm", ascending=False).iterrows()]
    F["by_cation"] = {}
    for site in ("A", "B"):
        e = pooled.groupby(site).agg(n=("material_id", lambda x: len(x) // 7), sm=("match_most_likely_element", "mean")).query("n >= 100").sort_values("sm")
        F["by_cation"][site] = {"lowest": [{"element": i, "sm": float(100 * r.sm), "n": int(r.n)} for i, r in e.head(6).iterrows()],
                                "highest": [{"element": i, "sm": float(100 * r.sm), "n": int(r.n)} for i, r in e.tail(4).iloc[::-1].iterrows()],
                                "n_elements": int(len(e))}

    # ── the decoder's confidence (no ground truth needed): the lowest top-1 probability over the five sites ──
    def confidence_table(frames):
        y = np.concatenate([f[0] for f in frames]); c = np.concatenate([f[1] for f in frames])
        rows = []
        for lo, hi in ((0.9, 1.01), (0.6, 0.9), (0.0, 0.6)):
            m = (c >= lo) & (c < hi)
            rows.append({"from": lo, "to": min(hi, 1.0), "share_pct": float(100 * m.mean()), "match_pct": float(100 * y[m].mean())})
        return {"auc": float(np.mean([auc(f[0], f[1]) for f in frames])), "bins": rows, "overall_match_pct": float(100 * y.mean())}
    seen = [(P[r].match_most_likely_element.to_numpy(), decoded(r, ids)["species_top5_prob"][:, :, 0].min(1)) for r in SEVEN]
    unseen, HP = [], {}
    for i in range(3):
        hp = per_material(f"heldout_seed{i}"); HP[i] = hp
        te = (hp.heldout_split == "test20").to_numpy()
        conf = decoded(f"heldout_seed{i}", hp.material_id.to_numpy())["species_top5_prob"][:, :, 0].min(1)
        unseen.append((hp.match_most_likely_element.to_numpy()[te], conf[te]))
    F["confidence"] = {"seen": confidence_table(seen), "unseen": confidence_table(unseen)}

    # ── combining seeds: add the element probabilities of several seeds, site by site ──
    true_idx = np.load(os.path.join(A, "dataset", "dataset_encoding.npz"))
    order = pd.Series(np.arange(len(true_idx["species_idx"])), index=pd.read_csv(os.path.join(A, "dataset", "dataset_table.csv")).material_id.astype(str)).loc[ids].to_numpy()
    truth = true_idx["species_idx"][order][:, :5]
    D = [decoded(r, ids) for r in SEVEN]
    single = [float(100 * (d["species_pred_idx"][:, :5] == truth).all(1).mean()) for d in D]

    def vote(members):
        acc = np.zeros((len(ids), 5, 119), dtype=np.float32)
        for m in members:
            np.add.at(acc, (np.arange(len(ids))[:, None, None], np.arange(5)[None, :, None], D[m]["species_top5_idx"]), D[m]["species_top5_prob"])
        return float(100 * (acc.argmax(-1) == truth).all(1).mean())
    F["ensemble"] = {"single_composition_exact": stats(single), "three_seeds": vote([0, 1, 2]), "five_seeds": vote([0, 1, 2, 3, 4]), "seven_seeds": vote(range(7))}

    # ── what the latents contain ──
    pr = {"z_crystal": [], "z_property": [], "z_joint": []}
    for r in SEVEN:
        z = latents(r, ids)
        for name in pr:
            pr[name].append(participation_ratio(z[name]))
    F["latent_dimensions"] = {name: stats(v) for name, v in pr.items()}
    F["latent_dimensions"]["of"] = 128
    F["encoder_output_length"] = {"crystal_median": float(pooled.encoder_norm_crystal.median()), "property_median": float(pooled.encoder_norm_property.median())}
    grp = table.groupby(["heat_all", "dir_gap"]).size()
    size_of_own = table.merge(grp.rename("m").reset_index(), on=["heat_all", "dir_gap"]).m
    F["properties"] = {"gap_zero_pct": float(100 * (table.dir_gap == 0).mean()), "gap_zero_n": int((table.dir_gap == 0).sum()), "profiles": int(len(grp)),
                       "largest_group": int(grp.max()), "share_with_10_or_more_pct": float(100 * (size_of_own >= 11).mean()), "unique_profile_n": int((grp == 1).sum()),
                       "heat_all_range": [float(table.heat_all.min()), float(table.heat_all.max())], "dir_gap_range": [float(table.dir_gap.min()), float(table.dir_gap.max())]}
    z0 = pooled.dir_gap_true == 0
    F["retrieval"] = {"structure_to_property_r1": float((pooled.rank_crystal_to_property == 1).mean()), "property_to_structure_r1": float((pooled.rank_property_to_crystal == 1).mean()),
                      "structure_to_property_median_rank": float(pooled.rank_crystal_to_property.median()), "property_to_structure_median_rank": float(pooled.rank_property_to_crystal.median()),
                      "gap_zero": {"r1": float((pooled[z0].rank_crystal_to_property == 1).mean()), "median_rank": float(pooled[z0].rank_crystal_to_property.median()), "cosine": float(pooled[z0].cosine_before_projection.mean())},
                      "gap_positive": {"r1": float((pooled[~z0].rank_crystal_to_property == 1).mean()), "median_rank": float(pooled[~z0].rank_crystal_to_property.median()), "cosine": float(pooled[~z0].cosine_before_projection.mean()), "n": int((~z0).sum() // 7)}}
    q = pd.qcut(pooled.heat_all_true, 5)
    gq = pooled.groupby(q, observed=True)
    F["by_formation_enthalpy"] = {"quintile_upper_edges": [float(i.right) for i in gq.size().index], "cosine": [float(v) for v in gq.cosine_before_projection.mean()],
                                  "sm": [float(100 * v) for v in gq.match_most_likely_element.mean()],
                                  "correlation_cosine": stats([np.corrcoef(P[r].cosine_before_projection, P[r].heat_all_true)[0, 1] for r in SEVEN])}

    # ── prediction on unseen materials, from the structure alone ──
    pred = {k: {"heat_all": [], "dir_gap": []} for k in ("knn5", "linear", "retrieval", "training_mean", "decoded_joint")}
    anatomy = {"seen": [], "unseen": []}
    for i in range(3):
        hp = HP[i]
        z = latents(f"heldout_seed{i}", hp.material_id.to_numpy())
        tr, te = (hp.heldout_split == "train80").to_numpy(), (hp.heldout_split == "test20").to_numpy()
        zc, zp = z["z_crystal"], z["z_property"]
        Y = hp[["heat_all_true", "dir_gap_true"]].to_numpy()
        knn = B.knn_predict(zc[tr], Y[tr], zc[te], k=5, metric="cosine")
        Xtr, Xte = np.c_[zc[tr], np.ones(tr.sum())], np.c_[zc[te], np.ones(te.sum())]
        lin = Xte @ np.linalg.solve(Xtr.T @ Xtr + 1e-3 * np.eye(Xtr.shape[1]), Xtr.T @ Y[tr])
        nearest = (zc[te] @ zp[tr].T).argmax(1)
        for j, c in enumerate(("heat_all", "dir_gap")):
            pred["knn5"][c].append(float(np.abs(knn[:, j] - Y[te, j]).mean()))
            pred["linear"][c].append(float(np.abs(lin[:, j] - Y[te, j]).mean()))
            pred["retrieval"][c].append(float(np.abs(Y[tr][nearest, j] - Y[te, j]).mean()))
            pred["training_mean"][c].append(float(np.abs(Y[tr, j].mean() - Y[te, j]).mean()))
            pred["decoded_joint"][c].append(float(np.abs(hp[c + "_pred"].to_numpy()[te] - Y[te, j]).mean()))
        for key, m in (("seen", tr), ("unseen", te)):
            gq2 = hp[m]
            anatomy[key].append({"sm": 100 * gq2.match_most_likely_element.mean(), "composition": 100 * gq2.composition_exact.mean(),
                                 "site_A": 100 * gq2.ok_A.mean(), "site_B": 100 * gq2.ok_B.mean(), "site_X": 100 * gq2[["ok_X1", "ok_X2", "ok_X3"]].to_numpy().mean(),
                                 "lattice_mae": np.abs(gq2.a_pred - gq2.a_true).mean(), "coord_mae": gq2.frac_coord_mae.mean(),
                                 "match_given_right_composition": 100 * gq2[gq2.composition_exact == 1].match_most_likely_element.mean()})
    F["prediction_unseen"] = {k: {c: stats(v) for c, v in d.items()} for k, d in pred.items()}
    F["heldout_anatomy"] = {key: {m: float(np.mean([r[m] for r in rows])) for m in rows[0]} for key, rows in anatomy.items()}

    # ── files ──
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "findings.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(F, f, indent=1)
        f.write("\n")
    runs = res[res.run.isin(SEVEN) | res.run.str.startswith("noCL_seed") | res.run.str.startswith("heldout")].copy()
    runs["run"] = runs.run.replace({r: f"seed{i}" for i, r in enumerate(SEVEN)})
    runs["what"] = np.where(runs.run.str.startswith("seed"), "alignment training", np.where(runs.run.str.startswith("noCL"), "without the curriculum", "trained on 80 %, 20 % held out"))
    runs.to_csv(os.path.join(OUT, "runs.csv"), index=False, lineterminator="\n")
    snaps.drop(columns=["run"]).to_csv(os.path.join(OUT, "snapshots_seed6.csv"), index=False, lineterminator="\n")
    pm = pd.DataFrame({"material_id": ids, "formula": P[SEVEN[0]].formula, "heat_all": P[SEVEN[0]].heat_all_true, "dir_gap": P[SEVEN[0]].dir_gap_true})
    for i, r in enumerate(SEVEN):
        pm[f"matched_seed{i}"] = P[r].match_most_likely_element.to_numpy()
        pm[f"cosine_seed{i}"] = P[r].cosine_before_projection.round(4).to_numpy()
    pm.to_csv(os.path.join(OUT, "per_material_7seeds.csv.gz"), index=False, lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    print("wrote", os.path.relpath(OUT, ROOT), {f: os.path.getsize(os.path.join(OUT, f)) for f in sorted(os.listdir(OUT))})
    return F


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
