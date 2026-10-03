"""
MEIDNet Benchmarks: one JSON file per result, rendered into the docs with leaderboards, plots and an analysis,
reproducible on request.

    python scripts/benchmarks.py validate              check every file against the schema and the rules
    python scripts/benchmarks.py render                write docs/benchmarks/**, docs/community/index.md, docs/explore/databases.md
    python scripts/benchmarks.py reproduce <id>        re-run a submission's recipe here and record agreement
    python scripts/benchmarks.py schema                write benchmarks/schema.json

Layout:  benchmarks/datasets/<dataset>.json         what the dataset is (one card each)
         benchmarks/submissions/<dataset>/<id>.json  one result (one category each)
         benchmarks/verified/<id>.json               written by `reproduce` only: the numbers obtained here
         benchmarks/verified/<id>.predictions.csv    per-sample predictions of a reproduced representation row
         benchmarks/catalog/databases.json           the catalogue of external databases by application

Results are only ever compared within one dataset: `render_dataset` refuses rows of several datasets.
"""
import argparse
import csv
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
BENCH = os.path.join(ROOT, "benchmarks")
DOCS = os.path.join(ROOT, "docs")

Category = Literal["representation_quality", "conditional_design", "efficiency", "validation"]
Level = Literal["generated", "ml_filtered", "mlip_validated", "dft_validated", "experimentally_validated"]
Status = Literal["community_submitted", "published", "meidnet_verified"]
LEVELS: list[str] = ["generated", "ml_filtered", "mlip_validated", "dft_validated", "experimentally_validated"]
LEVEL_WORDS = {"generated": "generated", "ml_filtered": "ML filtered", "mlip_validated": "MLIP validated",
               "dft_validated": "DFT validated", "experimentally_validated": "experimentally validated"}
CATEGORY_WORDS = {"representation_quality": "Representation quality", "conditional_design": "Conditional design",
                  "efficiency": "Computational efficiency", "validation": "Validation level"}
STATUS_WORDS = {"community_submitted": "Community submitted", "published": "Published (from the paper)",
                "meidnet_verified": "MEIDNet verified"}

# Metric names allowed per category. Fixed lists keep rows comparable; `<prop>` is a property column name.
METRICS: dict[str, list[str]] = {
    "representation_quality": ["mae_<prop>", "r2_<prop>", "retrieval_top1", "retrieval_top5", "cosine_matched",
                               "l2_matched", "structure_match_rate", "n_evaluated"],
    "conditional_design": ["n_generated", "n_pass_rules", "n_sun", "sun_rate", "target_hit_rate", "mae_to_target_<prop>",
                           "validity", "uniqueness", "novelty"],
    "efficiency": ["training_epochs", "training_time_s", "gpu_hours", "parameters", "seconds_per_candidate"],
    "validation": ["n_screened", "n_stable", "n_unique", "n_novel", "n_sun", "n_dft", "n_experimental"],
}
# which way is better, for the "best" markers and the bar charts
LOWER_IS_BETTER = ("mae_", "l2_", "seconds_", "training_", "gpu_hours", "parameters", "mae_to_target_")
# what each metric means, for the "how to read" boxes
METRIC_WORDS = {
    "mae_<prop>": "mean absolute error of the property predicted from the structure alone (physical units)",
    "r2_<prop>": "coefficient of determination of that prediction; 0 = no better than the mean, 1 = perfect",
    "retrieval_top1": "fraction of validation materials whose property latent is nearest to its own structure latent",
    "retrieval_top5": "the same within the five nearest",
    "cosine_matched": "mean cosine similarity between the structure and property latents of the same material (1 = aligned)",
    "l2_matched": "mean L2 distance between those two latents (0 = identical)",
    "structure_match_rate": "fraction of reconstructed structures that match the input (StructureMatcher)",
    "n_evaluated": "materials in the evaluation split",
    "n_generated": "candidates the search produced", "n_pass_rules": "of those, candidates passing every family rule",
    "n_sun": "stable, unique and novel candidates", "sun_rate": "n_sun / n_generated",
    "target_hit_rate": "fraction of candidates whose predicted property lies within the stated tolerance of the target",
    "mae_to_target_<prop>": "mean absolute distance between the predicted property and the target",
    "validity": "fraction of generated structures that are chemically valid", "uniqueness": "fraction of distinct structures",
    "novelty": "fraction not present in the training set",
    "training_epochs": "epochs trained", "training_time_s": "wall-clock training time", "gpu_hours": "GPU hours used",
    "parameters": "model parameters", "seconds_per_candidate": "wall-clock seconds per saved candidate",
    "n_screened": "structures relaxed with the MLIP", "n_stable": "within the stability threshold after relaxation",
    "n_unique": "no structural duplicate among them", "n_novel": "formula absent from the training table",
    "n_dft": "confirmed by DFT", "n_experimental": "synthesised and measured",
}
TOLERANCE = {"default_rel": 0.05, "default_abs": 0.02}


def metric_allowed(category: str, name: str) -> bool:
    for pat in METRICS[category]:
        if pat == name:
            return True
        if pat.endswith("<prop>") and name.startswith(pat[:-6]) and len(name) > len(pat) - 6:
            return True
    return False


def metric_word(name: str) -> str:
    if name in METRIC_WORDS:
        return METRIC_WORDS[name]
    for pat, text in METRIC_WORDS.items():
        if pat.endswith("<prop>") and name.startswith(pat[:-6]):
            return text.replace("the property", f"`{name[len(pat) - 6:]}`")
    return ""


def lower_is_better(name: str) -> bool:
    return name.startswith(LOWER_IS_BETTER)


class Submitter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    affiliation: str = ""
    github: str = ""


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    meidnet_version: str
    family: str = ""
    variant: str = ""
    config: str = Field("", description="path to the meidnet.yaml used, relative to the repository, or a URL")
    checkpoint_url: str = ""
    checkpoint_sha256: str = Field("", pattern=r"^([0-9a-f]{64})?$")
    notes: str = ""


class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float
    unit: str = ""
    split: str = ""
    note: str = ""


class Resources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hardware: str = ""
    wall_time_s: float | None = None


class Reproduce(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: str = ""
    seed: int | None = None
    command: str = ""
    split: str = ""


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,60}$")
    dataset: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,40}$")
    title: str
    submitter: Submitter
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    modalities: list[str] = Field(min_length=1)
    model: ModelInfo
    category: Category
    results: dict[str, Metric] = Field(min_length=1)
    validation_level: Level = "generated"
    evidence: list[str] = []
    resources: Resources = Resources()
    reproduce: Reproduce = Reproduce()
    status: Status = "community_submitted"
    verified_by: str = ""
    verified_on: str = ""
    notes: str = ""

    @field_validator("modalities")
    @classmethod
    def _modalities(cls, v):
        for m in v:
            if not re.fullmatch(r"(structure|property:[A-Za-z_][A-Za-z0-9_]*|xrd|dos|spectrum:[a-z_]+|text|image)", m):
                raise ValueError(f"unknown modality {m!r}: use structure, property:<column>, xrd, dos, spectrum:<kind>, text, image")
        return v


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,40}$")
    name: str
    description: str
    rows: int | None = None
    split: str = ""
    properties: list[str] = []
    source: str = ""
    citation: str = ""
    role: str = Field("", description="what the paper used it for")


# ── files ────────────────────────────────────────────────────────────────────
def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def datasets() -> dict[str, Dataset]:
    out = {}
    d = os.path.join(BENCH, "datasets")
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if fn.endswith(".json"):
            ds = Dataset.model_validate(_read(os.path.join(d, fn)))
            if ds.id != fn[:-5]:
                raise ValueError(f"{fn}: id {ds.id!r} must equal the file name")
            out[ds.id] = ds
    return out


def submissions() -> list[tuple[str, Submission]]:
    out = []
    d = os.path.join(BENCH, "submissions")
    for ds in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        dd = os.path.join(d, ds)
        if not os.path.isdir(dd):
            continue
        for fn in sorted(os.listdir(dd)):
            if fn.endswith(".json") and not fn.startswith("_"):
                path = os.path.join(dd, fn)
                out.append((path, Submission.model_validate(_read(path))))
    return out


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def content_sha(path) -> str:
    """Fingerprint of a submission without its status fields, so that flipping `status` to meidnet_verified after a
    successful `reproduce` does not invalidate the record that `reproduce` wrote."""
    d = _read(path)
    for k in ("status", "verified_by", "verified_on"):
        d.pop(k, None)
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def verified_record(sid: str) -> dict | None:
    vp = os.path.join(BENCH, "verified", sid + ".json")
    return _read(vp) if os.path.exists(vp) else None


def predictions_path(sid: str) -> str:
    return os.path.join(BENCH, "verified", sid + ".predictions.csv")


def attempt_path(sid: str) -> str:
    return os.path.join(BENCH, "verified", sid + ".attempt.json")


def attempt_record(sid: str) -> dict | None:
    return _read(attempt_path(sid)) if os.path.exists(attempt_path(sid)) else None


# ── validate ─────────────────────────────────────────────────────────────────
def validate() -> list[str]:
    problems = []
    try:
        ds = datasets()
    except (ValidationError, ValueError) as e:
        return [f"datasets: {e}"]
    try:
        subs = submissions()
    except ValidationError as e:
        return [f"submissions: {e}"]
    seen = set()
    for path, s in subs:
        try:
            rel = os.path.relpath(path, ROOT)
        except ValueError:            # another drive on Windows (tests use a temporary folder)
            rel = path
        if s.dataset not in ds:
            problems.append(f"{rel}: unknown dataset {s.dataset!r} (add benchmarks/datasets/{s.dataset}.json)")
        if os.path.basename(os.path.dirname(path)) != s.dataset or os.path.basename(path) != s.id + ".json":
            problems.append(f"{rel}: must be benchmarks/submissions/{s.dataset}/{s.id}.json")
        if s.id in seen:
            problems.append(f"{rel}: duplicate id {s.id}")
        seen.add(s.id)
        for m in s.results:
            if not metric_allowed(s.category, m):
                problems.append(f"{rel}: metric {m!r} is not allowed for {s.category} (allowed: {', '.join(METRICS[s.category])})")
        if s.validation_level in ("dft_validated", "experimentally_validated") and not s.evidence:
            problems.append(f"{rel}: {s.validation_level} needs evidence links")
        if s.status == "meidnet_verified":
            v = verified_record(s.id)
            if v is None:
                problems.append(f"{rel}: status meidnet_verified without benchmarks/verified/{s.id}.json")
            elif v.get("submission_sha256") != content_sha(path):
                problems.append(f"{rel}: the verified record was made for another version of this file - run reproduce again")
    try:
        catalog()
    except (ValidationError, ValueError, KeyError) as e:
        problems.append(f"benchmarks/catalog/databases.json: {e}")
    return problems


# ── the catalogue of external databases ──────────────────────────────────────
class Application(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    what_to_look_for: str
    meidnet_targets: str


class Database(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    kind: Literal["theoretical", "experimental", "mixed"]
    url: str
    access: str = ""
    size: str = ""
    features: str
    applications: list[str]
    licence: str = ""
    meidnet: str = ""


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    applications: list[Application]
    databases: list[Database]


def catalog() -> Catalog:
    cat = Catalog.model_validate(_read(os.path.join(BENCH, "catalog", "databases.json")))
    ids = {a.id for a in cat.applications}
    for d in cat.databases:
        unknown = set(d.applications) - ids
        if unknown:
            raise ValueError(f"database {d.id}: unknown application(s) {sorted(unknown)}")
    return cat


def render_databases(cat: Catalog) -> str:
    kind_word = {"theoretical": "computed", "experimental": "experimental", "mixed": "computed + experimental"}
    out = ["# Databases by application", "",
           "Where to find training data and realistic targets: **computed** (DFT) databases give structures with properties, "
           "**experimental** databases give measured values and refined structures. MEIDNet needs, per material, one crystal "
           "structure plus one or more scalar properties ([what data do I need?](../start/what-data.md)); the last column says "
           "how far each source is from that.", "",
           "Pick an application:", ""]
    out += [f"- [{a.name}](#{_anchor(a.name)})" for a in cat.applications]
    out += ["- [All databases](#all-databases)", ""]
    by_id = {d.id: d for d in cat.databases}
    for a in cat.applications:
        rows = [d for d in cat.databases if a.id in d.applications]
        out += [f"## {a.name}", "", f"**What to look for:** {a.what_to_look_for}", "", f"**As MEIDNet targets:** {a.meidnet_targets}", ""]
        if rows:
            out += ["| database | kind | size | features | use with MEIDNet |", "|---|---|---|---|---|"]
            for d in rows:
                out.append(f"| [{d.name}]({d.url}) | {kind_word[d.kind]} | {d.size} | {d.features} | {d.meidnet} |")
            out.append("")
    out += ["## All databases", "", "| database | kind | access | licence | applications |", "|---|---|---|---|---|"]
    names = {a.id: a.name for a in cat.applications}
    for d in cat.databases:
        out.append(f"| [{d.name}]({d.url}) | {kind_word[d.kind]} | {d.access} | {d.licence} | {', '.join(names[x] for x in d.applications)} |")
    out += ["", "Missing one you use? [Open an issue](https://github.com/ABnano/MEIDNet/issues) or edit `benchmarks/catalog/databases.json`.", ""]
    return "\n".join(out)


def _anchor(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


# ── render: pages, leaderboards, plots, analysis ─────────────────────────────
def _badge(level: str) -> str:
    i = LEVELS.index(level)
    dots = "".join("●" if k <= i else "○" for k in range(len(LEVELS)))
    return f"<span class=\"ladder\" title=\"{LEVEL_WORDS[level]}\">{dots}</span> {LEVEL_WORDS[level]}"


def _status(s: Submission) -> str:
    css = {"community_submitted": "sub", "published": "pub", "meidnet_verified": "ver"}[s.status]
    return f"<span class=\"bstatus {css}\">{STATUS_WORDS[s.status]}</span>"


def _fmt(v: float) -> str:
    if float(v).is_integer() and abs(v) < 1e7:
        return f"{int(v):,}"
    return f"{v:.3g}"


HEADLINE = ("cosine_matched", "retrieval_top1", "mae_", "structure_match_rate", "sun_rate", "target_hit_rate", "n_sun",
            "seconds_per_candidate", "parameters", "n_dft", "n_experimental")


def _headline(metric: str) -> bool:
    """Metrics worth a bar chart on the dataset page (counts such as n_evaluated are not)."""
    return metric.startswith(HEADLINE)


def _split_of(r: Submission) -> str:
    splits = {mv.split for mv in r.results.values() if mv.split}
    return next(iter(splits)) if len(splits) == 1 else (r.reproduce.split or "")


def _short(title: str, n: int = 56) -> str:
    return title if len(title) <= n else title[:n - 1].rstrip() + "…"


def _inputs(r: Submission) -> str:
    props = [m[len("property:"):] for m in r.modalities if m.startswith("property:")]
    other = [m for m in r.modalities if not m.startswith("property:")]
    parts = other + ([f"{len(props)} propert{'y' if len(props) == 1 else 'ies'}"] if props else [])
    return " + ".join(parts)


def _chart(svg_markup: str) -> str:
    return f"<div class=\"bench-chart\" markdown=\"0\">{svg_markup}</div>"


def _best(rows: list[Submission], metric: str) -> Submission | None:
    have = [r for r in rows if metric in r.results]
    if not have:
        return None
    return (min if lower_is_better(metric) else max)(have, key=lambda r: r.results[metric].value)


def _metric_chart(rows: list[Submission], metric: str):
    from meidnet import svg
    items = [(r.title[:38], r.results[metric].value) for r in rows if metric in r.results]
    if len(items) < 2:
        return ""
    direction = "lower is better" if lower_is_better(metric) else "higher is better"
    return _chart(svg.hbars(items, f"{metric} ({direction})", value_fmt="{:.3g}"))


def _funnel_chart(r: Submission):
    from meidnet import svg
    stages = []
    for key, label in (("n_generated", "generated"), ("n_pass_rules", "pass every rule"), ("n_sun", "stable, unique, novel"),
                       ("n_screened", "screened (MLIP)"), ("n_stable", "stable"), ("n_unique", "unique"), ("n_novel", "novel"),
                       ("n_dft", "confirmed by DFT"), ("n_experimental", "made and measured")):
        if key in r.results:
            stages.append((label, int(r.results[key].value), ""))
    if len(stages) < 2:
        return ""
    return _chart(svg.funnel(stages, f"{r.title}: from generated to validated"))


def _parity_charts(s: Submission) -> str:
    """Parity plots of a reproduced representation row (predictions saved by `reproduce`)."""
    from meidnet import svg
    path = predictions_path(s.id)
    if not os.path.exists(path):
        return ""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return ""
    cols = sorted({k[len("true_"):] for k in rows[0] if k.startswith("true_")})
    out = []
    for c in cols:
        x = [float(r["true_" + c]) for r in rows]
        y = [float(r["pred_" + c]) for r in rows]
        unit = s.results.get("mae_" + c).unit if s.results.get("mae_" + c) else ""
        out.append(_chart(svg.scatter(x, y, f"{c}: predicted from the structure vs. true ({len(x):,} validation materials)",
                                      f"true {c}{(' (' + unit + ')') if unit else ''}", f"predicted {c}", diagonal=True)))
    if "cos" in rows[0]:
        cos = [float(r["cos"]) for r in rows]
        out.append(_chart(svg.histogram(cos, "cosine similarity of the two latents, per material", "cosine(structure latent, property latent)",
                                        bins=40, marks={"mean": sum(cos) / len(cos)})))
    return "\n".join(out)


def _how_to_read(cat: str, metrics: list[str]) -> str:
    out = [f"??? info \"How to read the {CATEGORY_WORDS[cat].lower()} table\"", ""]
    for m in metrics:
        w = metric_word(m)
        if w:
            out.append(f"    - `{m}` — {w}{' (lower is better)' if lower_is_better(m) else ''}")
    extra = {
        "representation_quality": "    Representation rows describe how well the shared latent space holds structures and properties; they say nothing about whether a generated material is real.",
        "conditional_design": "    Design rows are funnels: every number after `n_generated` is a subset of the one before. A high SUN rate on few candidates is weaker evidence than a lower rate on many.",
        "efficiency": "    Efficiency rows are hardware-dependent: compare only rows that state the same hardware.",
        "validation": "    Validation rows count structures that survived each check. `n_stable` depends on the stability threshold used (0.10 eV/atom above the hull by default).",
    }
    out += ["", extra[cat], ""]
    return "\n".join(out)


def _insights(ds: Dataset, rows: list[Submission]) -> str:
    if not rows:
        return ""
    out = ["## Insights", ""]
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r.category, []).append(r)
    for cat, rs in by_cat.items():
        metrics = []
        for r in rs:
            for m in r.results:
                if m not in metrics:
                    metrics.append(m)
        for m in metrics:
            if m.startswith("n_") and m not in ("n_sun", "n_dft", "n_experimental"):
                continue                                                   # counts are context, not a score
            b = _best(rs, m)
            if b and len([r for r in rs if m in r.results]) > 1:
                out.append(f"- Best `{m}`: **{b.title}** ({_fmt(b.results[m].value)}{(' ' + b.results[m].unit) if b.results[m].unit else ''}), {STATUS_WORDS[b.status].lower()}.")
    levels = sorted({r.validation_level for r in rows}, key=LEVELS.index)
    out.append(f"- Evidence levels present: {', '.join(LEVEL_WORDS[l] for l in levels)}. "
               f"{sum(1 for r in rows if r.status == 'meidnet_verified')} of {len(rows)} rows have been reproduced here.")
    pub = [r for r in rows if r.status == "published"]
    if pub:
        out.append(f"- {len(pub)} row(s) are quoted from the paper; a verified re-run of the same checkpoint, where it exists, "
                   f"is the row to trust for the exact numbers of this code version.")
    for r in rows:
        att = attempt_record(r.id)
        if att and r.status != "meidnet_verified":
            dis = [f"`{m}` {_fmt(d['submitted'])} → {_fmt(d['obtained'])}" for m, d in att.get("compared", {}).items() if not d["ok"]]
            out.append(f"- **A re-run of [{r.title}](results/{r.id}.md) here did not agree** ({'; '.join(dis)}). "
                       f"The row keeps its status; see its page for the full comparison.")
    out.append("")
    return "\n".join(out)


def render_dataset(ds: Dataset, rows: list[Submission]) -> str:
    sets = {r.dataset for r in rows}
    if sets - {ds.id}:
        raise ValueError(f"render_dataset({ds.id}): rows of other datasets {sorted(sets - {ds.id})} - results are never compared across datasets")
    out = [f"# {ds.name}", "", ds.description, ""]
    meta = []
    if ds.rows:
        meta.append(f"**{ds.rows:,} rows**")
    if ds.split:
        meta.append(f"split: {ds.split}")
    if ds.properties:
        meta.append("properties: " + ", ".join(f"`{p}`" for p in ds.properties))
    if ds.role:
        meta.append(f"role in the paper: {ds.role}")
    if ds.source:
        meta.append(f"[dataset source]({ds.source})")
    if meta:
        out += [" · ".join(meta), ""]
    n_ver = sum(1 for r in rows if r.status == "meidnet_verified")
    out += ["<div class=\"bench-kpis\" markdown=\"0\">"
            f"<div><b>{len(rows)}</b><span>results</span></div>"
            f"<div><b>{n_ver}</b><span>reproduced here</span></div>"
            f"<div><b>{len({r.category for r in rows})}</b><span>categories</span></div>"
            f"<div><b>{LEVEL_WORDS[max((r.validation_level for r in rows), key=LEVELS.index)] if rows else '–'}</b><span>highest evidence</span></div>"
            "</div>", ""]
    out += ["!!! note \"Read a row\"", "    Rows are compared only within this dataset and category; click a column header to sort. The ladder ●○○○○ … ●●●●● is the",
            "    evidence level (generated → ML filtered → MLIP validated → DFT validated → experimentally validated).",
            "    *Published* = taken from the paper; *MEIDNet verified* = reproduced here from the submitted configuration.", ""]
    if not rows:
        out += ["_No results yet._ [Contribute one](../community/contribute.md).", ""]
    for cat in METRICS:
        rs = [r for r in rows if r.category == cat]
        if not rs:
            continue
        rs.sort(key=lambda r: (-LEVELS.index(r.validation_level), r.date))
        metrics = []
        for r in rs:
            for m in r.results:
                if m not in metrics:
                    metrics.append(m)
        out += [f"## {CATEGORY_WORDS[cat]}", "", "<div class=\"bench-table\" markdown=\"1\">", "",
                "| result | split | inputs | " + " | ".join(metrics) + " | evidence | status |",
                "|---|---|---|" + "---|" * len(metrics) + "---|---|"]
        for r in rs:
            cells = []
            for m in metrics:
                mv = r.results.get(m)
                best = _best(rs, m) is r and len([x for x in rs if m in x.results]) > 1
                cells.append((f"**{_fmt(mv.value)}**" if best else _fmt(mv.value)) + ((' ' + mv.unit) if mv and mv.unit else "") if mv else "–")
            splits = sorted({mv.split for mv in r.results.values() if mv.split}) or [r.reproduce.split or "–"]
            out.append(f"| [{_short(r.title)}](results/{r.id}.md \"{r.title} — {r.model.name}\") | {', '.join(splits)} | {_inputs(r)} | " + " | ".join(cells)
                       + f" | {_badge(r.validation_level)} | {_status(r)} |")
        out += ["", "</div>"]
        out += ["", _how_to_read(cat, metrics), ""]
        charts = [c for c in (_metric_chart(rs, m) for m in metrics if _headline(m)) if c]
        if cat == "conditional_design" or cat == "validation":
            charts += [c for c in (_funnel_chart(r) for r in rs) if c]
        if cat == "representation_quality":          # per-material plots of the held-out re-runs (the result pages have the rest)
            charts += [c for c in (_parity_charts(r) for r in rs if r.status == "meidnet_verified" and _split_of(r) != "train") if c]
        if charts:
            out += ["<div class=\"bench-charts\" markdown=\"0\">" + "".join(charts) + "</div>", ""]
    out.append(_insights(ds, rows))
    return "\n".join(out)


def render_result(s: Submission, ds: Dataset | None) -> str:
    out = [f"# {s.title}", "", f"{_status(s)} · {_badge(s.validation_level)}", "",
           "| | |", "|---|---|",
           f"| Dataset | [{ds.name if ds else s.dataset}](../{s.dataset}.md) |",
           f"| Modalities | {', '.join(f'`{m}`' for m in s.modalities)} |",
           f"| Model | {s.model.name} (MEIDNet {s.model.meidnet_version}{', ' + s.model.family if s.model.family else ''}{' / ' + s.model.variant if s.model.variant else ''}) |",
           f"| Category | {CATEGORY_WORDS[s.category]} |",
           f"| Submitted by | {s.submitter.name}{' (' + s.submitter.affiliation + ')' if s.submitter.affiliation else ''} on {s.date} |"]
    if s.model.config:
        out.append(f"| Configuration | `{s.model.config}` |")
    if s.model.checkpoint_url:
        url = s.model.checkpoint_url
        if not url.startswith("http"):              # a path in this repository
            url = "https://github.com/ABnano/MEIDNet/blob/main/" + url.replace(os.sep, "/")
        out.append(f"| Checkpoint | [{os.path.basename(s.model.checkpoint_url)}]({url})"
                   + (f" · sha256 `{s.model.checkpoint_sha256[:12]}…`" if s.model.checkpoint_sha256 else "") + " |")
    if s.resources.hardware or s.resources.wall_time_s:
        out.append(f"| Resources | {s.resources.hardware}{' · ' + _fmt(s.resources.wall_time_s) + ' s' if s.resources.wall_time_s else ''} |")
    if s.model.notes:
        out.append(f"| Notes on the model | {s.model.notes} |")
    out += ["", "## Results", "", "| metric | value | split | meaning | note |", "|---|---|---|---|---|"]
    for m, mv in s.results.items():
        out.append(f"| `{m}` | {_fmt(mv.value)}{(' ' + mv.unit) if mv.unit else ''} | {mv.split} | {metric_word(m)} | {mv.note} |")
    fun = _funnel_chart(s)
    if fun:
        out += ["", fun]
    out += ["", "## Validation", "", f"Evidence level: {_badge(s.validation_level)}.", ""]
    if s.evidence:
        out += ["Evidence:", ""] + [f"- <{e}>" if e.startswith("http") else f"- `{e}`" for e in s.evidence] + [""]
    if s.reproduce.command:
        out += ["## Reproduce", "", f"Configuration `{s.reproduce.config}`" + (f", seed {s.reproduce.seed}" if s.reproduce.seed is not None else "")
                + (f", split {s.reproduce.split}" if s.reproduce.split else "") + ":", "", "```", s.reproduce.command, "```", ""]
    v = verified_record(s.id)
    if s.status == "meidnet_verified" and v:
        out += ["## Verified here", "", f"Reproduced on {v.get('date', '?')} with MEIDNet {v.get('meidnet_version', '?')} by {s.verified_by or v.get('by', '?')}"
                + (f" on {v['hardware']}" if v.get("hardware") else "") + ":", "",
                "| metric | submitted | obtained here |", "|---|---|---|"]
        for m, got in v.get("obtained", {}).items():
            sub = s.results.get(m)
            out.append(f"| `{m}` | {_fmt(sub.value) if sub else '–'} | {_fmt(got)} |")
        out.append("")
        par = _parity_charts(s)
        if par:
            out += ["### Per-material analysis", "", "Every validation material, predicted from its structure alone; the dashed line is perfect agreement.", "",
                    "<div class=\"bench-charts\" markdown=\"0\">" + par + "</div>", ""]
    elif s.status == "published":
        out += ["", "_These numbers are quoted from the paper._", ""]
    att = attempt_record(s.id)
    if att and s.status != "meidnet_verified":
        out += ["## Re-run here did not agree", "",
                f"On {att.get('date', '?')} this repository's code re-ran the recipe above ({att.get('hardware', '')}, MEIDNet {att.get('meidnet_version', '?')}) "
                "and obtained different numbers. The row keeps its status; the comparison is shown so that readers can judge it. "
                "Possible reasons: a different split or protocol in the original measurement, a different definition of the metric, "
                "or a checkpoint that is not the one the numbers were measured on.", "",
                "| metric | this row | obtained here | agree |", "|---|---|---|---|"]
        for m, d in att.get("compared", {}).items():
            out.append(f"| `{m}` | {_fmt(d['submitted'])} | {_fmt(d['obtained'])} | {'yes' if d['ok'] else 'no'} |")
        extra = {m: v for m, v in att.get("obtained", {}).items() if m not in att.get("compared", {})}
        if extra:
            out += ["", "Also obtained in that run: " + ", ".join(f"`{m}` = {_fmt(v)}" for m, v in extra.items()), ""]
        out.append("")
    if s.notes:
        out += ["## Notes", "", s.notes, ""]
    return "\n".join(out)


def render_hub(ds: dict[str, Dataset], by_ds: dict[str, list[Submission]]) -> str:
    from meidnet import svg
    allrows = [r for rs in by_ds.values() for r in rs]
    hub = ["# MEIDNet Benchmarks", "",
           "Reproducible results for multimodal materials representation and inverse design, **one leaderboard per dataset**. "
           "Different datasets are different tasks, so there is no ranking across them: compare rows only within a page. "
           "The idea follows [Matbench Discovery](https://matbench-discovery.materialsproject.org): fixed data, inspectable "
           "submissions, plots and an evidence level per row.", "",
           "<div class=\"bench-kpis\" markdown=\"0\">"
           f"<div><b>{len(ds)}</b><span>datasets</span></div>"
           f"<div><b>{len(allrows)}</b><span>results</span></div>"
           f"<div><b>{sum(1 for r in allrows if r.status == 'meidnet_verified')}</b><span>reproduced here</span></div>"
           f"<div><b>{sum(1 for r in allrows if r.validation_level in ('dft_validated', 'experimentally_validated'))}</b><span>DFT or experiment</span></div>"
           "</div>", "",
           "## Datasets", "", "| dataset | role | results | reproduced | highest evidence |", "|---|---|---|---|---|"]
    for k, d in ds.items():
        rows = by_ds.get(k, [])
        top = LEVEL_WORDS[max((r.validation_level for r in rows), key=LEVELS.index)] if rows else "–"
        hub.append(f"| [{d.name}]({k}.md) | {d.role or d.description.split('.')[0]} | {len(rows)} | {sum(1 for r in rows if r.status == 'meidnet_verified')} | {top} |")
    hub += ["", "## The evidence ladder", "", "| level | means |", "|---|---|",
            "| ○○○○○ generated | the model produced it |",
            "| ●○○○○ ML filtered | it passed the family's rules and the model's own checks |",
            "| ●●○○○ MLIP validated | relaxed and found stable with a machine-learned potential (`meidnet screen`, MACE) |",
            "| ●●●○○ DFT validated | confirmed by density-functional calculations |",
            "| ●●●●○ experimentally validated | synthesised and measured |", ""]
    counts = {LEVEL_WORDS[l]: sum(1 for r in allrows if r.validation_level == l) for l in LEVELS}
    counts = {k: v for k, v in counts.items() if v}
    if counts:
        hub += [_chart(svg.hbars(list(counts.items()), "results per evidence level (all datasets)")), ""]
    hub += ["## Status of a row", "", "**Published** = quoted from the paper · **Community submitted** = a pull request, validated by CI · "
            "**MEIDNet verified** = reproduced here from the submitted configuration (`python scripts/benchmarks.py reproduce <id>`). "
            "[How to contribute](../community/contribute.md) · [Databases by application](../explore/databases.md)", "",
            "## Latest results", "", "| date | result | dataset | category | evidence | status |", "|---|---|---|---|---|---|"]
    for r in sorted(allrows, key=lambda r: r.date, reverse=True)[:12]:
        hub.append(f"| {r.date} | [{r.title}](results/{r.id}.md) | [{ds[r.dataset].name if r.dataset in ds else r.dataset}]({r.dataset}.md) | {CATEGORY_WORDS[r.category]} | {_badge(r.validation_level)} | {_status(r)} |")
    hub.append("")
    return "\n".join(hub)


def render() -> list[str]:
    problems = validate()
    if problems:
        raise SystemExit("benchmarks: fix these before rendering:\n  " + "\n  ".join(problems))
    ds = datasets()
    subs = submissions()
    by_ds: dict[str, list[Submission]] = {k: [] for k in ds}
    for _, s in subs:
        by_ds.setdefault(s.dataset, []).append(s)
    out_dir = os.path.join(DOCS, "benchmarks")
    os.makedirs(os.path.join(out_dir, "results"), exist_ok=True)
    written = []
    _write(os.path.join(out_dir, "index.md"), render_hub(ds, by_ds)); written.append("benchmarks/index.md")
    for k, d in ds.items():
        _write(os.path.join(out_dir, k + ".md"), render_dataset(d, by_ds.get(k, []))); written.append(f"benchmarks/{k}.md")
    for _, s in subs:
        _write(os.path.join(out_dir, "results", s.id + ".md"), render_result(s, ds.get(s.dataset))); written.append(f"benchmarks/results/{s.id}.md")
    com = ["# Community results", "", "Every submitted result, newest first. [Contribute yours](contribute.md).", "",
           "| date | result | dataset | category | evidence | status |", "|---|---|---|---|---|---|"]
    for _, s in sorted(subs, key=lambda x: x[1].date, reverse=True):
        com.append(f"| {s.date} | [{s.title}](../benchmarks/results/{s.id}.md) | [{ds[s.dataset].name if s.dataset in ds else s.dataset}](../benchmarks/{s.dataset}.md) | {CATEGORY_WORDS[s.category]} | {_badge(s.validation_level)} | {_status(s)} |")
    com.append("")
    _write(os.path.join(DOCS, "community", "index.md"), "\n".join(com)); written.append("community/index.md")
    _write(os.path.join(DOCS, "explore", "databases.md"), render_databases(catalog())); written.append("explore/databases.md")
    return written


# ── reproduce ────────────────────────────────────────────────────────────────
def reproduce(sid: str, by: str = "maintainer") -> dict:
    """Re-run a submission here. representation_quality rows: train.evaluate of the stated checkpoint on the stated
    split of the dataset in data/<dataset>/ (per-material predictions are kept for the parity plots); validation
    rows: `meidnet screen` on the stated CIF folder. Other categories must give a `reproduce.command` whose last
    line prints a JSON object of metric values."""
    import platform
    match = [(p, s) for p, s in submissions() if s.id == sid]
    if not match:
        raise SystemExit(f"no submission with id {sid}")
    path, s = match[0]
    obtained: dict[str, float] = {}
    hardware = f"{platform.machine()} CPU"
    if s.category == "representation_quality" and s.model.checkpoint_url and s.dataset == "perov5":
        import numpy as np
        import torch
        from torch.utils.data import DataLoader
        from meidnet.checkpoint import load_checkpoint
        from meidnet.config import DataSection, PropertyColumn
        from meidnet.data import MaterialsDataset, load_records, read_table
        from meidnet.train import evaluate
        ck = s.model.checkpoint_url if os.path.exists(s.model.checkpoint_url) else os.path.join(ROOT, s.model.checkpoint_url)
        lm = load_checkpoint(ck)
        split = s.reproduce.split or "val"
        table = os.path.join(ROOT, "data", "perov5", f"{split}.csv")
        if not os.path.exists(table):
            raise SystemExit(f"{table} is missing: run `meidnet download-data` first")
        max_sites = int(getattr(lm.model.crystal_encoder, "max_sites", 20))
        dcfg = DataSection(table=table, id_column="material_id", cif_column="cif", align_to_prototype=False, max_sites=max_sites,
                           properties=[PropertyColumn(column=c) for c in lm.stats.columns])
        recs, rep = load_records(read_table(table), dcfg, lambda p: p, None, source=f"perov5 {split}")
        dsx = MaterialsDataset(recs, lm.stats)
        res = evaluate(lm.model, dsx, lm.stats)
        for c in lm.stats.columns:
            obtained[f"mae_{c}"] = res["mae"][c]
            obtained[f"r2_{c}"] = res["r2_structure_only"][c]
        obtained["retrieval_top1"] = res["retrieval_top1"]
        obtained["retrieval_top5"] = res["retrieval_top5"]
        obtained["cosine_matched"] = res["cosine_matched"]
        obtained["n_evaluated"] = float(res["n"])
        # per-material predictions (structure only) and latent agreement, for the parity plots
        lm.model.eval()
        preds, cos = [], []
        with torch.no_grad():
            for b in DataLoader(dsx, batch_size=64, shuffle=False):
                zc, zp, *_ = lm.model.encode_modalities(b["crystal_vec"], b["props"])
                preds.append(lm.stats.denormalize_tensor(lm.model.property_decoder(zc)).cpu().numpy())
                cos.append((zc * zp).sum(1).cpu().numpy())
        P = np.concatenate(preds)
        C = np.concatenate(cos)
        obtained["l2_matched"] = float(np.sqrt(np.maximum(0.0, 2.0 - 2.0 * C)).mean())   # unit latents: |a-b|^2 = 2 - 2cos
        os.makedirs(os.path.join(BENCH, "verified"), exist_ok=True)
        with open(predictions_path(sid), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id"] + [f"true_{c}" for c in lm.stats.columns] + [f"pred_{c}" for c in lm.stats.columns] + ["cos"])
            for i, r in enumerate(recs):
                w.writerow([r.material_id] + [f"{v:.5g}" for v in r.properties] + [f"{v:.5g}" for v in P[i]] + [f"{C[i]:.4f}"])
    elif s.category == "validation" and s.reproduce.command.startswith("meidnet screen"):
        from meidnet.screen import screen
        parts = s.reproduce.command.split()
        folder = os.path.join(ROOT, parts[2])
        train_csv = os.path.join(ROOT, parts[parts.index("--train-csv") + 1]) if "--train-csv" in parts else None
        df = screen(folder, train_csv=train_csv, log=lambda *a: None)
        valid = df[~df["artefact"].fillna(False).astype(bool)] if "artefact" in df else df
        st, un = valid["stable"].fillna(False).astype(bool), valid["unique"].fillna(False).astype(bool)
        nov = valid["novel"].fillna(False).astype(bool) if train_csv else (st | True)
        obtained = {"n_screened": float(len(valid)), "n_stable": float(st.sum()), "n_unique": float(un.sum()),
                    "n_novel": float(nov.sum()) if train_csv else 0.0, "n_sun": float((st & un & nov).sum())}
    elif s.reproduce.command:
        out = subprocess.run(s.reproduce.command, shell=True, cwd=ROOT, capture_output=True, text=True, check=True).stdout
        obtained = {k: float(v) for k, v in json.loads(out.strip().splitlines()[-1]).items()}
    else:
        raise SystemExit("this submission has no reproduce.command and no automatic recipe")
    agree, detail = True, {}
    for m, mv in s.results.items():
        if m not in obtained:
            continue
        got = obtained[m]
        tol = max(TOLERANCE["default_abs"], TOLERANCE["default_rel"] * abs(mv.value))
        ok = abs(got - mv.value) <= tol
        agree &= ok
        detail[m] = {"submitted": mv.value, "obtained": got, "ok": ok}
    from meidnet import __version__ as ver
    rec = {"id": s.id, "submission_sha256": content_sha(path), "date": _dt.date.today().isoformat(), "by": by, "hardware": hardware,
           "meidnet_version": ver, "agree": agree, "obtained": obtained, "compared": detail}
    os.makedirs(os.path.join(BENCH, "verified"), exist_ok=True)
    if agree:
        _write(os.path.join(BENCH, "verified", s.id + ".json"), json.dumps(rec, indent=1))
        if os.path.exists(attempt_path(sid)):
            os.remove(attempt_path(sid))
    else:                              # a re-run that did not agree is kept and shown: that is the point of the benchmark
        _write(attempt_path(sid), json.dumps(rec, indent=1))
        if os.path.exists(predictions_path(sid)):
            os.remove(predictions_path(sid))
    return rec


def write_schema() -> str:
    path = os.path.join(BENCH, "schema.json")
    schema = Submission.model_json_schema()
    schema["$comment"] = "Allowed metric names per category: " + json.dumps(METRICS)
    _write(path, json.dumps(schema, indent=1))
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    sub.add_parser("render")
    sub.add_parser("schema")
    r = sub.add_parser("reproduce")
    r.add_argument("id")
    r.add_argument("--by", default="maintainer")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        problems = validate()
        if problems:
            print("\n".join(problems))
            return 1
        print(f"ok: {len(submissions())} submission(s), {len(datasets())} dataset(s), {len(catalog().databases)} database(s) in the catalogue")
        return 0
    if a.cmd == "render":
        for w in render():
            print("wrote docs/" + w)
        return 0
    if a.cmd == "schema":
        print("wrote", os.path.relpath(write_schema(), ROOT))
        return 0
    rec = reproduce(a.id, a.by)
    print(json.dumps({k: v for k, v in rec.items() if k != "obtained"}, indent=1))
    print("obtained:", json.dumps(rec["obtained"], indent=1))
    if rec["agree"]:
        print(f"agreed: set \"status\": \"meidnet_verified\" and \"verified_by\" in the submission and commit benchmarks/verified/{a.id}.json")
    else:
        print("the numbers do not agree within the tolerances; nothing was written")
    return 0 if rec["agree"] else 2


if __name__ == "__main__":
    sys.exit(main())
