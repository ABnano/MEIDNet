"""
Write the analysis pages of the Perov-5 benchmark from the result files (no number is typed by hand).

    python scripts/reproduction_pages.py          # docs/benchmarks/perov5-reproduction.md, perov5-insights.md, perov5-guide.md

Reads  benchmarks/reproduction/perov5/findings.json   (from scripts/reproduction_findings.py)
       benchmarks/reproduction/perov5/demo/           (candidates and MLIP stability of the quick-start run)
       benchmarks/submissions/perov5/*.json           (the leaderboard records)
"""
import csv
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from meidnet import svg  # noqa: E402

REP = os.path.join(ROOT, "benchmarks", "reproduction", "perov5")
DOCS = os.path.join(ROOT, "docs", "benchmarks")
HF = "https://huggingface.co/Babu09/MEIDNet/tree/main/reproduction"
GH = "https://github.com/ABnano/MEIDNet/blob/main/"
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def f(v, d=3):
    return f"{v:.{d}f}"


def pm(s, d=3):
    return f"{s['mean']:.{d}f} ± {s['sd']:.{d}f}"


def rng(s, d=3):
    return f"{s['min']:.{d}f}–{s['max']:.{d}f}"


def chart(markup, caption):
    return f'<div class="bench-chart" markdown="0"><p class="bench-cap">{caption}</p>{markup}</div>'


def charts(*items):
    return '<div class="bench-charts" markdown="0">' + "".join(items) + "</div>"


def tiles(*items):
    return '<div class="bench-kpis" markdown="0">' + "".join(f"<div><b>{v}</b><span>{k}</span></div>" for v, k in items) + "</div>"


def formula(x):
    return x.translate(SUB)


def record(mid):
    p = os.path.join(ROOT, "benchmarks", "submissions", "perov5", mid + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


GLOSSARY = """??? info "The four measures used on this page"

    - **Cosine** and **L2**: how close the structure latent and the property latent of the same material are. Both latents
      have length one; a cosine of 1 (L2 of 0) means they coincide. They are read from the normalised encoder outputs,
      before the projection heads, which is where this model's alignment loss acts.
    - **Structure matching**: the share of materials whose crystal, decoded from the joint latent, matches the input
      according to pymatgen's `StructureMatcher` (`stol` 0.5, `angle_tol` 10, `ltol` 0.3). *Sampled element* draws the
      element of each site from the decoder's probabilities, as the training script's own evaluation does; *most likely
      element* takes the highest probability and is deterministic.
    - **Retrieval, top 1**: the share of materials whose own property vector is the nearest of all property vectors to
      their structure vector.
"""


# ─────────────────────────────────────────────────────────────────────────────
def page_reproduction(F) -> str:
    S, runs, H, T = F["summary"], F["runs"], F["heldout"], F["training"]
    ep = F["seed_curves"]["epochs"]
    curves = svg.lines({f"seed {k}": (ep, v) for k, v in F["seed_curves"]["cosine"].items()},
                       "Cosine between the two latents during training, seven seeds", "epoch", "cosine (training batches)", w=640, h=300)
    out = ["# Perov-5: alignment across seeds", "",
           "The alignment model of MEIDNet learns one space for crystal structures and their properties. This page measures "
           f"how well the two modalities agree in that space, and how much the answer depends on the random seed: the same "
           f"training was run seven times, and every checkpoint is public.", "",
           tiles((pm(S["cosine"]), "cosine, 7 seeds"), (pm(S["l2"]), "L2, 7 seeds"),
                 (f"{S['sm_sampled']['mean']:.1f} ± {S['sm_sampled']['sd']:.1f} %", "structure matching"),
                 (f"{F['n_materials']:,}", "materials")), "",
           "[Results](#results) · [During training](#during-training) · [Unseen materials](#unseen-materials) · "
           "[Do it yourself](#do-it-yourself) · [What the runs show](perov5-insights.md)", "{ .lb-toolbar }", "",
           "## What was run", "",
           "| | |", "|---|---|",
           "| model | early fusion of formation enthalpy and band gap; E(n)-equivariant crystal encoder; 128-dimensional latents |",
           f"| training | {T['epochs']:,} epochs, batch {T['batch']}, {T['optimizer']}; symmetric InfoNCE with temperature {T['temperature']}; "
           f"contrastive weight raised linearly from 0 to {T['contrastive_weight']} over the first {T['warmup_epochs']:,} epochs (the curriculum) |",
           f"| data | all {F['n_materials']:,} Perov-5 materials, scored on the same materials; [unseen materials](#unseen-materials) are measured separately |",
           "| seeds | 0 to 6, one run each, about 7 hours on one NVIDIA A100 |",
           f"| script and weights | [`reproduction/paper_alignment/`]({GH}reproduction/paper_alignment) · [seven checkpoints on Hugging Face]({HF}) |", "",
           "## Results", "",
           "| seed | cosine | L2 | structure matching, sampled element | structure matching, most likely element | retrieval, top 1 |",
           "|---|---|---|---|---|---|"]
    for r in runs:
        out.append(f"| {r['seed']} | {f(r['cosine'], 4)} | {f(r['l2'], 4)} | {r['sm_sampled']:.2f} % | {r['sm_likely']:.2f} % | {f(r['recall_at_1'])} |")
    out += [f"| **mean ± s.d.** | **{pm(S['cosine'])}** | **{pm(S['l2'])}** | **{S['sm_sampled']['mean']:.1f} ± {S['sm_sampled']['sd']:.1f} %** | "
            f"**{S['sm_likely']['mean']:.1f} ± {S['sm_likely']['sd']:.1f} %** | **{pm(S['recall_at_1'])}** |",
            f"| range | {rng(S['cosine'])} | {rng(S['l2'])} | {S['sm_sampled']['min']:.1f}–{S['sm_sampled']['max']:.1f} % | "
            f"{S['sm_likely']['min']:.1f}–{S['sm_likely']['max']:.1f} % | {rng(S['recall_at_1'])} |", "",
            GLOSSARY,
            '!!! key "A seed fixes the result"',
            f"    Seeds {', '.join(str(s) for s in F['determinism']['seeds'])} were trained twice, on different hardware and library versions "
            f"({F['determinism']['setups'][0]}; {F['determinism']['setups'][1]}). Every number of the two sets is identical. "
            "The differences between the rows above therefore come from the seed alone: quote a result with its seed, or as a mean over seeds.", "",
            "## During training", "",
            charts(chart(curves, "Cosine between the structure and property latents, per epoch, for the seven seeds")), "",
            "The seeds differ most early in training and converge later:", "",
            "| epoch | lowest seed | highest seed | spread |", "|---|---|---|---|",
            *(f"| {e:,} | {f(lo)} | {f(hi)} | {f(hi - lo)} |" for e, lo, hi in zip(F["seed_spread"]["epochs"], F["seed_spread"]["min"], F["seed_spread"]["max"])), "",
            "## Unseen materials", "",
            f"The runs above score the materials the model was trained on. To measure materials it has never seen, the same training "
            f"was repeated on {H['n_train']:,} materials (80 %) with {H['n_test']:,} (20 %) held out, with three seeds.", "",
            "| | cosine | L2 | structure matching, sampled | structure matching, most likely | retrieval, top 1 |", "|---|---|---|---|---|---|",
            *(f"| {label} | {pm(H[k]['cosine'])} | {pm(H[k]['l2'])} | {H[k]['sm_sampled']['mean']:.1f} ± {H[k]['sm_sampled']['sd']:.1f} % | "
              f"{H[k]['sm_likely']['mean']:.1f} ± {H[k]['sm_likely']['sd']:.1f} % | {rng(H[k]['recall_at_1'])} |"
              for label, k in ((f"held-out {H['n_test']:,} materials", "unseen"), (f"the {H['n_train']:,} trained on", "seen"))), "",
            "The alignment carries over to unseen materials with a small loss; the reconstruction of the crystal loses about twenty "
            "points. [What the runs show](perov5-insights.md#unseen) traces that loss to one cause.", "",
            "## Do it yourself", "",
            '=== "1 · In the browser"', "",
            "    Nothing to install. The seven models are compared with the other methods on the [Perov-5 leaderboard](perov5.md#representation), "
            "and the [insights page](perov5-insights.md) has the figures behind every statement here.", "",
            '=== "2 · On a laptop, about a minute"', "",
            "    Recompute the cosine and L2 of any seed on a CPU. The checkpoint is downloaded from Hugging Face.", "",
            "    ```bash", "    pip install git+https://github.com/ABnano/MEIDNet.git", "    git clone https://github.com/ABnano/MEIDNet.git && cd MEIDNet",
            "    meidnet download-data                                   # Perov-5 into data/perov5/",
            "    python scripts/reproduce_alignment.py --seed 4          # prints cosine and L2",
            "    python scripts/reproduce_alignment.py --seed 4 --structure-matching   # also rebuilds every crystal: a few minutes", "    ```", "",
            f"    Expected for seed 4: cosine {f(runs[4]['cosine'], 4)}, L2 {f(runs[4]['l2'], 4)}, structure matching {runs[4]['sm_likely']:.2f} % (most likely element). "
            f"The values of every seed are in [`runs.csv`]({GH}benchmarks/reproduction/perov5/runs.csv).", "",
            '=== "3 · Full training, one GPU, about 7 hours"', "",
            f"    The training script, the wrapper and the job files are in [`reproduction/paper_alignment/`]({GH}reproduction/paper_alignment).", "",
            "    ```bash", "    cd reproduction/paper_alignment",
            "    python -u retrain_alignment.py --seed 4 --epochs 2200           # trains, then prints cosine, L2 and structure matching",
            "    python -u retrain_alignment.py --ckpt path/to/checkpoint.pth    # evaluation only", "    ```", "",
            "    The same seed gives the same numbers as in the table above, on any GPU.", "",
            "## Files", "",
            f"- [`findings.json`]({GH}benchmarks/reproduction/perov5/findings.json): every number on this page and the next, generated by `scripts/reproduction_findings.py`.",
            f"- [`runs.csv`]({GH}benchmarks/reproduction/perov5/runs.csv): one row per run. "
            f"[`snapshots_seed6.csv`]({GH}benchmarks/reproduction/perov5/snapshots_seed6.csv): seed 6 at 29 points of training.",
            f"- [`per_material_7seeds.csv.gz`]({GH}benchmarks/reproduction/perov5/per_material_7seeds.csv.gz): for each of the {F['n_materials']:,} materials and each seed, matched or not, and the cosine.",
            f"- [Checkpoints]({HF}) with checksums.", ""]
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
def page_insights(F) -> str:
    S, C, FA, HA, E = F["summary"], F["consistency"], F["failures"], F["heldout_anatomy"], F["ensemble"]
    sn, NC, CF, LD, PR, RT, PU, BE = F["snapshots"], F["no_curriculum"], F["confidence"], F["latent_dimensions"], F["properties"], F["retrieval"], F["prediction_unseen"], F["by_formation_enthalpy"]
    cur, noc = sn["curriculum"], sn["no_curriculum"]
    c_sm = svg.lines({"with the curriculum": ([r["epoch"] for r in cur if r["epoch"] <= 300], [r["sm"] for r in cur if r["epoch"] <= 300]),
                      "without": ([r["epoch"] for r in noc], [r["sm"] for r in noc])},
                     "Structure matching during the first 300 epochs, with and without the curriculum", "epoch", "structure matching (%)", w=460, h=280)
    c_cos = svg.lines({"with the curriculum": ([r["epoch"] for r in cur if r["epoch"] <= 300], [r["cosine"] for r in cur if r["epoch"] <= 300]),
                       "without": ([r["epoch"] for r in noc], [r["cosine"] for r in noc])},
                      "Cosine during the first 300 epochs, with and without the curriculum", "epoch", "cosine", w=460, h=280)
    c_full = svg.lines({"structure matching (%)": ([r["epoch"] for r in cur], [r["sm"] for r in cur]),
                        "cosine × 100": ([r["epoch"] for r in cur], [100 * r["cosine"] for r in cur])},
                       "Structure matching and cosine over the whole training, seed 6", "epoch", "", w=640, h=280)
    k = C["matched_in_k_seeds"]
    c_k = svg.hbars([(f"{i} of 7 seeds", k[str(i)]) for i in range(7, -1, -1)], "Materials reconstructed by k of the seven seeds", w=460, max_items=8)
    c_site = svg.hbars([(f"site {s}", round(FA["site_accuracy_pct"][s], 2)) for s in ("A", "B", "X1", "X2", "X3")],
                       "Share of materials with the right element on each site", value_fmt="{:.2f} %", w=460)
    e50 = next(r for r in cur if r["epoch"] == 50)
    n50 = next(r for r in noc if r["epoch"] == 50)
    n10 = next(r for r in noc if r["epoch"] == 10)
    c10 = next(r for r in cur if r["epoch"] == 10)
    n300 = noc[-1]
    sp = F["seed_spread"]
    out = ["# Perov-5: what the runs show", "",
           f"Seven training runs of the alignment model, three without the curriculum and three with materials held out give "
           f"more than one number per model. This page reads them for what they say about training, about failures and about "
           f"the shared space, and turns each result into something you can use. Every number is generated from "
           f"[`findings.json`]({GH}benchmarks/reproduction/perov5/findings.json); the runs are described on [Alignment across seeds](perov5-reproduction.md).", "",
           "[How the model learns](#how-the-model-learns) · [Where it fails](#where-it-fails) · [What the shared space contains](#what-the-shared-space-contains) · "
           "[In practice](#in-practice)", "{ .lb-toolbar }", "",

           "## How the model learns", "",
           "### The curriculum builds the structures first", "",
           f"With the curriculum, the contrastive weight starts at zero and grows over the first 1,500 epochs. In a paired run (seed 6, "
           f"the same starting weights and data order), structure matching reaches **{e50['sm']:.1f} %** at epoch 50 with the curriculum and "
           f"**{n50['sm']:.1f} %** without it; without the curriculum it is still {n300['sm']:.1f} % at epoch {n300['epoch']}. The alignment behaves the other "
           f"way round: without the curriculum the cosine is already {f(n10['cosine'], 2)} at epoch 10, against {f(c10['cosine'], 2)} with it.", "",
           charts(chart(c_sm, "Structure matching (most likely element), seed 6"), chart(c_cos, "Cosine between the two latents, seed 6")), "",
           "After the full training, over three and seven seeds:", "",
           "| | cosine | L2 | structure matching, sampled element |", "|---|---|---|---|",
           f"| with the curriculum (7 seeds, 2,200 epochs) | {pm(S['cosine'])} | {pm(S['l2'])} | {S['sm_sampled']['mean']:.1f} ± {S['sm_sampled']['sd']:.1f} % |",
           f"| without (3 seeds, {NC['epochs']:,} epochs) | {pm(NC['summary']['cosine'])} | {pm(NC['summary']['l2'])} | {NC['summary']['sm_sampled']['mean']:.1f} ± {NC['summary']['sm_sampled']['sd']:.1f} % |", "",
           '!!! key "What this means for you"',
           "    The curriculum does not change how well the modalities align in the end. It decides whether the model also learns to rebuild "
           "crystals. Keep `training.contrastive_warmup_epochs` on when you train on your own data.", "",

           "### Reconstruction peaks early, then swings", "",
           f"In the seed-6 run, structure matching is highest at epoch {sn['peak']['epoch']} ({sn['peak']['sm']:.1f} %), when the cosine is only {f(sn['peak']['cosine'], 2)}. "
           f"From there to the end it moves between {sn['after_300']['min']:.1f} % and {sn['after_300']['max']:.1f} % from one snapshot to the next, "
           f"and ends at {sn['final']['sm']:.1f} % (cosine {f(sn['final']['cosine'], 2)}).", "",
           charts(chart(c_full, "Structure matching and cosine over 2,200 epochs, seed 6 (29 snapshots)")), "",
           '!!! key "What this means for you"',
           "    The last epoch is not the best checkpoint for reconstruction. Save checkpoints during training and choose one on a validation "
           "measure. This is one seed; the swings may differ for others.", "",

           "### Early alignment does not predict the final one", "",
           f"At epoch {sp['epochs'][2]} the cosine of the seven seeds ranges from {f(sp['min'][2], 2)} to {f(sp['max'][2], 2)}; at the end from "
           f"{f(sp['min'][-1], 2)} to {f(sp['max'][-1], 2)}. The order of the seeds at epoch 100 has a rank correlation of only "
           f"{f(sp['rank_correlation_with_final']['100'], 2)} with their final order (figure on [Alignment across seeds](perov5-reproduction.md#during-training)).", "",
           '!!! key "What this means for you"',
           "    Do not judge a model, or stop a run, on its alignment after a few dozen epochs. A short training, such as the 30 epochs of the "
           "hosted Studio, gives a rough model whose quality depends on the seed.", "",

           "### Alignment and reconstruction are independent", "",
           f"Across the seven seeds, the correlation between the final cosine and structure matching is {f(F['correlation_cosine_vs_matching']['sampled'], 2)} "
           f"(sampled element) and {f(F['correlation_cosine_vs_matching']['most_likely'], 2)} (most likely element). "
           f"The seed with the highest cosine ({f(max(r['cosine'] for r in F['runs']), 3)}) has the lowest structure matching "
           f"({min(F['runs'], key=lambda r: r['sm_sampled'])['sm_sampled']:.1f} %).", "",
           '!!! key "What this means for you"', "    Report both. A high cosine says nothing about how well crystals are rebuilt.", "",

           "## Where it fails", "",
           "### Failures are seed noise, not hard materials", "",
           f"Of the {F['n_materials']:,} materials, **{C['any_pct']:.2f} %** are reconstructed by at least one of the seven seeds and {C['always_pct']:.1f} % by all seven; "
           f"only {C['never_n']} are missed by every seed. Whether one seed fails on a material says almost nothing about another seed "
           f"(correlation {f(C['correlation_match'], 2)}).", "",
           charts(chart(c_k, "Number of materials reconstructed by k of the seven seeds"),
                  chart(c_site, "Right element per site, seven seeds pooled (A and B: cations; X: anions)")), "",
           f"So several seeds can be combined. Adding the element probabilities of the seeds, site by site, and taking the most likely element "
           f"gives the exact composition for **{E['three_seeds']:.2f} %** of the materials with three seeds and {E['seven_seeds']:.2f} % with seven, "
           f"against {E['single_composition_exact']['mean']:.1f} % for one seed on average ({E['single_composition_exact']['min']:.1f}–{E['single_composition_exact']['max']:.1f} %).", "",
           '!!! key "What this means for you"',
           "    Three models trained with different seeds, with their element probabilities added, remove almost all composition errors on the "
           "training materials. It costs three trainings and no change to the model.", "",

           "### The bottleneck is naming the cation", "",
           f"{FA['wrong_composition_pct']:.0f} % of the failed reconstructions have a wrong element, and almost always on a cation site: the A site is right for "
           f"{FA['site_accuracy_pct']['A']:.1f} % of the materials and the B site for {FA['site_accuracy_pct']['B']:.1f} %, the three anion sites for "
           f"{min(FA['site_accuracy_pct'][s] for s in ('X1', 'X2', 'X3')):.1f} % or more. When the composition is right, {FA['match_given_right_composition_pct']:.1f} % "
           f"of the crystals match; the lattice length is off by {FA['lattice_mae']:.2f} Å on average.", "",
           '### On unseen materials the whole loss is the cation { #unseen }', "",
           "| trained on 80 %, three seeds | A site right | B site right | anion sites right | match when the composition is right | lattice error |",
           "|---|---|---|---|---|---|",
           *(f"| {label} | {HA[key]['site_A']:.1f} % | {HA[key]['site_B']:.1f} % | {HA[key]['site_X']:.1f} % | {HA[key]['match_given_right_composition']:.1f} % | {HA[key]['lattice_mae']:.3f} Å |"
             for label, key in (("materials seen in training", "seen"), ("held-out materials", "unseen"))), "",
           '!!! key "What this means for you"',
           "    The geometry generalises: lattice and positions are as good on unseen materials as on seen ones. What does not generalise is "
           "choosing the A and B elements. Work on the model should go there first; candidates should have their composition checked first.", "",

           "### Take the most likely element", "",
           f"The training script's evaluation samples the element of each site. Taking the most likely element instead raises structure matching "
           f"by {F['most_likely_gain']['mean']:.1f} points on average ({min(F['most_likely_gain']['per_seed']):.1f} to {max(F['most_likely_gain']['per_seed']):.1f} over the seven seeds).", "",
           "### The decoder knows when it is unsure", "",
           "Take the lowest of the five top probabilities of a decoded crystal (one per site) as its confidence. It needs no reference structure.", "",
           "| confidence | share of materials (seen) | reconstructed correctly (seen) | share (held-out) | reconstructed correctly (held-out) |", "|---|---|---|---|---|",
           *(f"| {'≥ 0.9' if b['from'] >= 0.9 else ('0.6 to 0.9' if b['from'] >= 0.6 else '< 0.6')} | {b['share_pct']:.1f} % | {b['match_pct']:.1f} % | {u['share_pct']:.1f} % | {u['match_pct']:.1f} % |"
             for b, u in zip(CF["seen"]["bins"], CF["unseen"]["bins"])),
           f"| all | 100 % | {CF['seen']['overall_match_pct']:.1f} % | 100 % | {CF['unseen']['overall_match_pct']:.1f} % |", "",
           f"Area under the ROC curve: {f(CF['seen']['auc'], 2)} on seen materials (seven seeds), {f(CF['unseen']['auc'], 2)} on held-out materials (three seeds).", "",
           '!!! key "What this means for you"', "    Rank or filter decoded crystals by this confidence before spending computing time on them.", "",

           "### Chemistry matters little, some cations more", "",
           "Structure matching by anion set, seven seeds pooled:", "",
           "| anions | " + " | ".join(formula(r["anions"].replace("OOO", "O3").replace("NNN", "N3").replace("NNO", "ON2").replace("NOO", "O2N").replace("FOO", "O2F").replace("OOS", "O2S").replace("FNO", "ONF")) for r in F["by_anion"]) + " |",
           "|---|" + "---|" * len(F["by_anion"]),
           "| structure matching | " + " | ".join(f"{r['sm']:.1f} %" for r in F["by_anion"]) + " |", "",
           "The cations with the lowest structure matching (elements with at least 100 materials):", "",
           "| site | lowest | highest |", "|---|---|---|",
           *(f"| {site} | " + ", ".join(f"{x['element']} {x['sm']:.0f} %" for x in F["by_cation"][site]["lowest"]) + " | "
             + ", ".join(f"{x['element']} {x['sm']:.0f} %" for x in F["by_cation"][site]["highest"]) + " |" for site in ("A", "B")), "",

           "## What the shared space contains", "",
           "### The modalities are aligned before the projection heads", "",
           f"The contrastive loss of this model acts on the normalised encoder outputs. There the cosine is {pm(S['cosine'])}. After the projection heads, "
           f"which feed the decoder, the same pairs have a cosine of {pm(S['cosine_after_projection'])}: the two projected vectors point in "
           "nearly opposite directions, and the decoder reads their mean.", "",
           '!!! meidnet "In the benchmark"',
           "    The [representation task](perov5.md#representation) compares the two latents in the space where each model aligns them, declared per "
           "method. The cosine in both spaces is recorded on each method's page.", "",

           "### The 128-number latents use about two directions", "",
           f"The participation ratio, the effective number of directions a set of vectors uses, is {pm(LD['z_crystal'], 1)} for the structure latents and "
           f"{pm(LD['z_property'], 1)} for the property latents, out of {LD['of']}; the joint latent that the decoder reads uses {pm(LD['z_joint'], 1)}.", "",
           '!!! key "What this means for you"',
           "    Two scalar properties can organise two directions, and the alignment pulls the structure latent onto them. A richer second "
           "modality, such as a diffraction pattern or a density of states, is the way to a richer shared space ([roadmap](../understand/limits.md)).", "",

           "### The property modality of Perov-5 is thin", "",
           f"{PR['gap_zero_pct']:.1f} % of the materials ({PR['gap_zero_n']:,}) have a direct band gap of 0, and the {F['n_materials']:,} materials share only "
           f"{PR['profiles']} distinct pairs of (formation enthalpy, band gap). {PR['share_with_10_or_more_pct']:.0f} % of the materials have the same pair as at "
           f"least ten others; the largest group has {PR['largest_group']}.", "",
           "### Retrieval works in one direction", "",
           "| | top 1 | median rank |", "|---|---|---|",
           f"| from a structure, find its properties | {f(RT['structure_to_property_r1'])} | {RT['structure_to_property_median_rank']:.0f} |",
           f"| from the properties, find the structure | {f(RT['property_to_structure_r1'])} | {RT['property_to_structure_median_rank']:.0f} |", "",
           "Ranks are among all 18,928 materials; a material sharing its properties with others is not counted against. From properties to a "
           "structure, many crystals are equally right answers.", "",
           '!!! key "What this means for you"',
           "    This is why inverse design in MEIDNet is a search and not a lookup: a material family fixes the sites, rules remove impossible "
           "compositions, and the search moves through the latent space ([How MEIDNet works](../understand/how-it-works.md)).", "",

           "### Less stable materials align better and reconstruct worse", "",
           "By fifths of the formation enthalpy, from the lowest to the highest:", "",
           "| formation enthalpy up to (eV/atom) | " + " | ".join(f(v, 2) for v in BE["quintile_upper_edges"]) + " |",
           "|---|" + "---|" * 5,
           "| cosine | " + " | ".join(f(v) for v in BE["cosine"]) + " |",
           "| structure matching | " + " | ".join(f"{v:.1f} %" for v in BE["sm"]) + " |", "",
           f"The correlation between a material's cosine and its formation enthalpy is {pm(BE['correlation_cosine'], 2)} over the seven seeds.", "",

           "### What a structure alone predicts", "",
           f"On the {F['heldout']['n_test']:,} held-out materials, with the property of the five nearest training materials in the structure latent (three seeds):", "",
           "| | formation enthalpy (eV/atom) | direct band gap (eV) |", "|---|---|---|",
           f"| five nearest neighbours in the structure latent | {pm(PU['knn5']['heat_all'])} | {pm(PU['knn5']['dir_gap'])} |",
           f"| nearest property latent (cross-modal) | {pm(PU['retrieval']['heat_all'])} | {pm(PU['retrieval']['dir_gap'])} |",
           f"| linear model on the structure latent | {pm(PU['linear']['heat_all'])} | {pm(PU['linear']['dir_gap'])} |",
           f"| mean of the training materials | {f(PU['training_mean']['heat_all']['mean'])} | {f(PU['training_mean']['dir_gap']['mean'])} |", "",
           "Mean absolute errors. The band-gap numbers are small because most gaps are zero.", "",
           '!!! key "What this means for you"',
           f"    The properties decoded from the joint latent have an error of only {f(PU['decoded_joint']['heat_all']['mean'])} eV/atom, but the joint latent contains the "
           f"true properties: that is a reconstruction. The error to expect for a new structure is the first row, about {f(PU['knn5']['heat_all']['mean'], 2)} eV/atom.", "",

           "## In practice", "",
           "What the results above suggest for anyone training or using such a model:", "",
           '<div class="psteps" markdown>', "",
           "1. **Keep the curriculum.** It is what teaches the model to rebuild crystals.",
           "2. **Train three seeds, not one.** Results differ between seeds, and their errors are independent.",
           "3. **Choose the checkpoint on a validation measure**, not at the last epoch.",
           "4. **Decode with the most likely element**, and add the probabilities of the seeds when you have several.",
           "5. **Rank the decoded crystals by confidence** (the lowest top probability over the sites) and check the composition first.",
           "6. **Confirm with an MLIP, then DFT.** The [guide](perov5-guide.md) runs the first of these steps.", "", "</div>", "",
           "Steps 2, 4 and 5 are measured here on reconstruction, with the alignment model. They are not yet options of `meidnet generate`.", ""]
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
def page_guide(F) -> str:
    recs = {m: record(m) for m in ("meidnet-2k", "meidnet-propertyaware", "meidnet-earlyfusion", "meidnet-alignment", "meidnet-alignment-seed3",
                                   "baseline-screening", "baseline-random")}
    with open(os.path.join(REP, "demo", "candidates.csv"), newline="", encoding="utf-8") as fh:
        cands = list(csv.DictReader(fh))
    with open(os.path.join(REP, "demo", "stability.csv"), newline="", encoding="utf-8") as fh:
        stab = {r["formula"]: r for r in csv.DictReader(fh)}

    def inv(m, k, d=3):
        r = recs.get(m)
        v = r and r["results"].get("inverse_design", {}).get(k)
        return "–" if v is None else (f"{int(v)}" if d == 0 else f"{v:.{d}f}")

    def rep(m, k, d=3):
        r = recs.get(m)
        v = r and r["results"].get("representation", {}).get(k)
        if v is None:
            return "–"
        sd = r.get("spread", {}).get("representation", {}).get(k)
        return f"{v:.{d}f}" + (f" ± {sd:.{d}f}" if sd else "")

    rows = [("meidnet-2k", "`dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth`"), ("meidnet-propertyaware", "`…_propertyaware.pth`"),
            ("meidnet-earlyfusion", "`dual_autoencoder_clip_earlyfusion.pth`"), ("meidnet-alignment-seed3", "`reproduction/meidnet_paper_rerun_seed3.pth`")]
    out = ["# Perov-5: choose a model and generate", "",
           "From nothing installed to candidate materials checked with a machine-learned interatomic potential (MLIP), with the commands "
           "that were run for this page and what they printed. Then: which of the public checkpoints to use for what.", "",
           "[Quick start](#quick-start) · [Which model](#which-model) · [Your own targets](#your-own-targets) · [Your own data](#your-own-data)", "{ .lb-toolbar }", "",
           "## Quick start", "",
           "Three candidates for a direct band gap of 2 eV, generated and screened. Run on a laptop for this page: 29 seconds to generate, "
           "under 2 minutes to screen.", "",
           '<div class="psteps" markdown>', "",
           "1. **Install.**", "",
           "    ```bash", '    pip install "meidnet[stability] @ git+https://github.com/ABnano/MEIDNet.git"', "    ```", "",
           "    `[stability]` adds the MACE potential for step 3. Without it, steps 1 and 2 work the same.", "",
           "2. **Generate.** The demo uses the published model and the cubic halide perovskite family.", "",
           "    ```bash", "    meidnet demo --family halide --band-gap 2.0 --enthalpy -0.10 -n 3 --out runs/demo", "    ```", "",
           "    It printed:", "", "    | candidate | predicted band gap (eV) | predicted formation enthalpy (eV/atom) | note |", "    |---|---|---|---|"]
    for c in cands:
        note = "extrapolating: outside the range of the training data" if c.get("warnings") else ""
        out.append(f"    | {formula(c['formula'])} | {float(c['pred_dir_gap']):.2f} | {float(c['pred_heat_all']):.2f} | {note} |")
    out += ["", "    Each candidate is a CIF file in `runs/demo/generation/cifs/`; `runs/demo/generation_report.html` shows every rule each one passed.", "",
            "3. **Screen with the MLIP.** MACE-MP-0 relaxes each crystal and computes its formation energy.", "",
            "    ```bash", "    meidnet screen runs/demo/generation/cifs --train-csv data/perov5/train.csv", "    ```", "",
            "    It printed:", "", "    | candidate | MACE formation energy (eV/atom) | stable | unique | novel |", "    |---|---|---|---|---|"]
    for c in cands:
        s = stab[c["formula"]]
        yn = lambda v: "yes" if v == "True" else "no"   # noqa: E731
        out.append(f"    | {formula(c['formula'])} | {float(s['dHf']):.2f} | {yn(s['stable'])} | {yn(s['unique'])} | {yn(s['novel'])} |")
    n_sun = sum(1 for s in stab.values() if s["stable"] == s["unique"] == s["novel"] == "True")
    out += ["", f"    {n_sun} of {len(cands)} are stable (formation energy at most 0.10 eV/atom), unique and novel. `--train-csv` needs "
            "`meidnet download-data` once; without it, novelty is skipped.", "",
            "4. **Confirm.** An MLIP is a first filter. Before any claim about a candidate, confirm its stability and its band gap with DFT.", "",
            "</div>", "",
            f"The outputs of this run are kept in [`benchmarks/reproduction/perov5/demo/`]({GH}benchmarks/reproduction/perov5/demo). "
            "No installation: the same search runs in the [Studio](https://babu09-meidnet.hf.space/studio/?panel=targets).", "",
            "## Which model", "",
            "All public checkpoints, measured under the same protocol ([leaderboard](perov5.md)): 54 candidates for three band-gap targets "
            "in three chemical families, screened with MACE-MP-0.", "",
            "| model | stable, unique, novel (of 54) | stable (share) | band-gap target met, of candidates with a DFT value | alignment (cosine) | retrieval, top 1 |", "|---|---|---|---|---|---|"]
    for m, name in rows:
        if recs.get(m) is None or "inverse_design" not in recs[m]["results"]:
            continue
        r = "meidnet-alignment" if m == "meidnet-alignment-seed3" else m
        hits = f"{round(float(inv(m, 'dft_hit_rate', 4)) * float(inv(m, 'dft_known', 0)))} of {inv(m, 'dft_known', 0)}" if inv(m, 'dft_hit_rate') != "–" else "–"
        out.append(f"| [{recs[m]['method']['name']}](results/{m}.md) | {inv(m, 'n_sun', 0)} | {inv(m, 'stable_rate', 2)} | "
                   f"{hits} | {rep(r, 'cosine_matched')} | {rep(r, 'retrieval_top1')} |")
    files = "; ".join(f"{recs[m]['method']['name']}: {name}" for m, name in rows if recs.get(m) and "inverse_design" in recs[m]["results"])
    for m in ("baseline-screening", "baseline-random"):
        k = inv(m, 'dft_known', 0)
        hits = f"{round(float(inv(m, 'dft_hit_rate', 4)) * float(k))} of {k}" if inv(m, 'dft_hit_rate') != "–" else "–"
        out.append(f"| [{recs[m]['method']['name']}](results/{m}.md) (baseline) | {inv(m, 'n_sun', 0)} | {inv(m, 'stable_rate', 2)} | {hits} | – | – |")
    seed3 = " The alignment columns of the seed-3 row are the mean of the seven alignment models." if recs.get("meidnet-alignment-seed3") else ""
    out += ["", f"Checkpoint files: {files}.{seed3}", "",
            "@GUIDE_READING@", "",
            "## Your own targets", "",
            "Targets, families, elements and rules are settings of one file, `meidnet.yaml`.", "",
            "```bash",
            "meidnet init --template perov5 -o meidnet.yaml       # a starting file",
            "# edit generation.targets, generation.variant, generation.exclude_elements …",
            "meidnet generate meidnet.yaml --model checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth",
            "meidnet screen runs/perov5/generation/cifs --train-csv data/perov5/train.csv",
            "```", "",
            "[Change the target properties](../recipes/change-targets.md) · [Exclude or restrict elements](../recipes/elements.md) · "
            "[Change the material family](../recipes/change-family.md) · [Add a rule](../recipes/add-constraint.md)", "",
            "## Your own data", "",
            "A table with one row per material, a CIF for each row and one numeric column per property is enough to train your own model: "
            "[Bring your own dataset](../use/your-data.md). When you train:", "",
            "- keep the contrastive warm-up, train more than one seed and choose the checkpoint on the validation split "
            "([why](perov5-insights.md#how-the-model-learns));",
            "- expect the alignment of a short training to depend on the seed ([figure](perov5-reproduction.md#during-training));",
            "- hold materials out, and report the scores on them ([what to expect](perov5-reproduction.md#unseen-materials)).", ""]
    return "\n".join(out)


def guide_reading() -> str:
    """The paragraph under the model table, written from the records: no model is called best unless the numbers say so."""
    def g(m, k):
        return (record(m) or {}).get("results", {}).get("inverse_design", {}).get(k)
    models = [m for m in ("meidnet-2k", "meidnet-propertyaware", "meidnet-earlyfusion", "meidnet-alignment-seed3") if g(m, "n_sun") is not None]
    sun = {m: int(g(m, "n_sun")) for m in models}
    scr, rnd = int(g("baseline-screening", "n_sun")), int(g("baseline-random", "n_sun"))
    lo, hi = min(sun.values()), max(sun.values())
    known = {m: int(g(m, "dft_known") or 0) for m in models}
    al = record("meidnet-alignment")["results"]["representation"]
    two = record("meidnet-2k")["results"]["representation"]
    lines = ['!!! key "How to read this table, and what to start with"',
             f"    - **The checkpoints are close on stability.** They deliver between {lo} and {hi} stable, unique and novel candidates of 54. Each is a "
             f"single run; how much this count changes with the seed has not been measured.",
             f"    - **Stable, unique and novel is not the design goal.** The two baselines score higher on it ({scr} and {rnd} of 54), in part because they "
             f"rarely return a material of the data set. Whether the band-gap target is met is only known where a DFT value exists: "
             f"{min(known.values())} to {max(known.values())} candidates per model, too few to rank the models.",
             "    - **To generate, start with the published model**: it is the model of `meidnet demo` and of the Studio, and its decoder (like that of the "
             "shorter training) was trained to rebuild a crystal from the property latent alone, which is what inverse design asks of it. Compare its "
             "candidates with the encoder screening of the same family (`meidnet space`), which needs no search.",
             f"    - **To study the shared space, use the seven alignment models**: their modalities agree most closely (cosine {al['cosine_matched']:.2f} against "
             f"{two['cosine_matched']:.2f} for the published model), and seven seeds show how much a result depends on the seed. They were not trained to "
             "decode from properties alone."]
    return "\n".join(lines)


def main():
    F = json.load(open(os.path.join(REP, "findings.json"), encoding="utf-8"))
    pages = {"perov5-reproduction.md": page_reproduction(F), "perov5-insights.md": page_insights(F),
             "perov5-guide.md": page_guide(F).replace("@GUIDE_READING@", guide_reading())}
    for name, text in pages.items():
        with open(os.path.join(DOCS, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.rstrip("\n") + "\n")
    print("wrote", ", ".join(f"docs/benchmarks/{n}" for n in pages))
    return list(pages)


if __name__ == "__main__":
    main()
