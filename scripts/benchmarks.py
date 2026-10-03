"""
MEIDNet Benchmarks: one JSON file per result, rendered into the docs, reproducible on request.

    python scripts/benchmarks.py validate              check every file against the schema and the rules
    python scripts/benchmarks.py render                write docs/benchmarks/** and docs/community/index.md
    python scripts/benchmarks.py reproduce <id>        re-run a submission's command and record agreement
    python scripts/benchmarks.py schema                write benchmarks/schema.json

Layout:  benchmarks/datasets/<dataset>.json       what the dataset is (one card each)
         benchmarks/submissions/<dataset>/<id>.json one result (one category each)
         benchmarks/verified/<id>.json            written by `reproduce` only: the numbers obtained here

Results are only ever compared within one dataset: `render_dataset` refuses rows of several datasets.
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator

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
# How `reproduce` reads a metric from what the code produces (representation rows from train.evaluate).
TOLERANCE = {"default_rel": 0.05, "default_abs": 0.02}


def metric_allowed(category: str, name: str) -> bool:
    for pat in METRICS[category]:
        if pat == name:
            return True
        if pat.endswith("<prop>") and name.startswith(pat[:-6]) and len(name) > len(pat) - 6:
            return True
    return False


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
        rel = os.path.relpath(path, ROOT)
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
            vp = os.path.join(BENCH, "verified", s.id + ".json")
            if not os.path.exists(vp):
                problems.append(f"{rel}: status meidnet_verified without benchmarks/verified/{s.id}.json")
            else:
                v = _read(vp)
                if v.get("submission_sha256") != sha256(path):
                    problems.append(f"{rel}: the verified record was made for another version of this file - run reproduce again")
    return problems


# ── render ───────────────────────────────────────────────────────────────────
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
    out += ["!!! note \"Read a row\"", "    Rows are compared only within this dataset and category. The ladder ●○○○○ … ●●●●● is the",
            "    evidence level (generated → ML filtered → MLIP validated → DFT validated → experimentally validated).",
            "    *Published* = taken from the paper; *MEIDNet verified* = reproduced here from the submitted configuration.", ""]
    if not rows:
        out += ["_No results yet._ [Contribute one](../community/contribute.md).", ""]
    for cat in METRICS:
        rs = [r for r in rows if r.category == cat]
        if not rs:
            continue
        rs.sort(key=lambda r: (-LEVELS.index(r.validation_level), r.date), reverse=False)
        metrics = []
        for r in rs:
            for m in r.results:
                if m not in metrics:
                    metrics.append(m)
        out += [f"## {CATEGORY_WORDS[cat]}", "", "| result | model | modalities | " + " | ".join(metrics) + " | evidence | status |",
                "|---|---|---|" + "---|" * len(metrics) + "---|---|"]
        for r in rs:
            cells = []
            for m in metrics:
                mv = r.results.get(m)
                cells.append(f"{_fmt(mv.value)}{(' ' + mv.unit) if mv and mv.unit else ''}" if mv else "–")
            out.append(f"| [{r.title}](results/{r.id}.md) | {r.model.name} | {', '.join(r.modalities)} | " + " | ".join(cells)
                       + f" | {_badge(r.validation_level)} | {_status(r)} |")
        out.append("")
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
    out += ["", "## Results", "", "| metric | value | split | note |", "|---|---|---|---|"]
    for m, mv in s.results.items():
        out.append(f"| `{m}` | {_fmt(mv.value)}{(' ' + mv.unit) if mv.unit else ''} | {mv.split} | {mv.note} |")
    out += ["", "## Validation", "", f"Evidence level: {_badge(s.validation_level)}.", ""]
    if s.evidence:
        out += ["Evidence:", ""] + [f"- <{e}>" if e.startswith("http") else f"- `{e}`" for e in s.evidence] + [""]
    if s.reproduce.command:
        out += ["## Reproduce", "", f"Configuration `{s.reproduce.config}`" + (f", seed {s.reproduce.seed}" if s.reproduce.seed is not None else "")
                + (f", split {s.reproduce.split}" if s.reproduce.split else "") + ":", "", "```", s.reproduce.command, "```", ""]
    if s.status == "meidnet_verified":
        vp = os.path.join(BENCH, "verified", s.id + ".json")
        if os.path.exists(vp):
            v = _read(vp)
            out += ["## Verified here", "", f"Reproduced on {v.get('date', '?')} with MEIDNet {v.get('meidnet_version', '?')} by {s.verified_by or v.get('by', '?')}:", "",
                    "| metric | submitted | obtained |", "|---|---|---|"]
            for m, got in v.get("obtained", {}).items():
                sub = s.results.get(m)
                out.append(f"| `{m}` | {_fmt(sub.value) if sub else '–'} | {_fmt(got)} |")
            out.append("")
    elif s.status == "published":
        out += ["", "_These numbers are quoted from the paper and have not been re-run from this repository._", ""]
    if s.notes:
        out += ["## Notes", "", s.notes, ""]
    return "\n".join(out)


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
    # the hub
    hub = ["# MEIDNet Benchmarks", "", "Reproducible results for multimodal materials representation and inverse design, **one page per dataset**.",
           "Different datasets are different tasks, so there is no leaderboard across them: compare rows only within a page.", "",
           "## The evidence ladder", "", "| level | means |", "|---|---|",
           "| ○○○○○ generated | the model produced it |",
           "| ●○○○○ ML filtered | it passed the family's rules and the model's own checks |",
           "| ●●○○○ MLIP validated | relaxed and found stable with a machine-learned potential (`meidnet screen`, MACE) |",
           "| ●●●○○ DFT validated | confirmed by density-functional calculations |",
           "| ●●●●○ experimentally validated | synthesised and measured |", "",
           "Each row also carries a status: **Published** (quoted from the paper), **Community submitted** (a pull request),",
           "**MEIDNet verified** (reproduced here from the submitted configuration). [How to contribute](../community/contribute.md).", "",
           "## Datasets", ""]
    for k, d in ds.items():
        rows = by_ds.get(k, [])
        n_ver = sum(1 for r in rows if r.status == "meidnet_verified")
        hub.append(f"- **[{d.name}]({k}.md)** — {d.role or d.description.split('.')[0]} · {len(rows)} result(s), {n_ver} verified")
    hub.append("")
    _write(os.path.join(out_dir, "index.md"), "\n".join(hub)); written.append("benchmarks/index.md")
    for k, d in ds.items():
        _write(os.path.join(out_dir, k + ".md"), render_dataset(d, by_ds.get(k, []))); written.append(f"benchmarks/{k}.md")
    for _, s in subs:
        _write(os.path.join(out_dir, "results", s.id + ".md"), render_result(s, ds.get(s.dataset))); written.append(f"benchmarks/results/{s.id}.md")
    # the community list
    com = ["# Community results", "", "Every submitted result, newest first. [Contribute yours](contribute.md).", "",
           "| date | result | dataset | category | evidence | status |", "|---|---|---|---|---|---|"]
    for _, s in sorted(subs, key=lambda x: x[1].date, reverse=True):
        com.append(f"| {s.date} | [{s.title}](../benchmarks/results/{s.id}.md) | [{ds[s.dataset].name if s.dataset in ds else s.dataset}](../benchmarks/{s.dataset}.md) | {CATEGORY_WORDS[s.category]} | {_badge(s.validation_level)} | {_status(s)} |")
    com.append("")
    os.makedirs(os.path.join(DOCS, "community"), exist_ok=True)
    _write(os.path.join(DOCS, "community", "index.md"), "\n".join(com)); written.append("community/index.md")
    return written


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ── reproduce ────────────────────────────────────────────────────────────────
def reproduce(sid: str, by: str = "maintainer") -> dict:
    """Re-run a submission here. representation_quality rows: train.evaluate of the stated checkpoint on the stated
    split of the dataset in data/<dataset>/; validation rows: `meidnet screen` on the stated CIF folder. Other
    categories must give a `reproduce.command` whose last line prints a JSON object of metric values."""
    match = [(p, s) for p, s in submissions() if s.id == sid]
    if not match:
        raise SystemExit(f"no submission with id {sid}")
    path, s = match[0]
    obtained: dict[str, float] = {}
    if s.category == "representation_quality" and s.model.checkpoint_url and s.dataset == "perov5":
        from meidnet.checkpoint import load_checkpoint
        from meidnet.data import MaterialsDataset, load_records, read_table
        from meidnet.train import evaluate
        from meidnet.config import DataSection, PropertyColumn
        ck = s.model.checkpoint_url if os.path.exists(s.model.checkpoint_url) else os.path.join(ROOT, s.model.checkpoint_url)
        lm = load_checkpoint(ck)
        split = s.reproduce.split or "val"
        table = os.path.join(ROOT, "data", "perov5", f"{split}.csv")
        if not os.path.exists(table):
            raise SystemExit(f"{table} is missing: run `meidnet download-data` first")
        props = [PropertyColumn(column=c) for c in lm.stats.columns]
        dcfg = DataSection(table=table, id_column="material_id", cif_column="cif", properties=props, align_to_prototype=False,
                           max_sites=lm.max_sites)
        recs, rep = load_records(read_table(table), dcfg, lambda p: p, None, source=f"perov5 {split}")
        res = evaluate(lm.model, MaterialsDataset(recs, lm.stats), lm.stats)
        for c in lm.stats.columns:
            obtained[f"mae_{c}"] = res["mae"][c]
            obtained[f"r2_{c}"] = res["r2_structure_only"][c]
        obtained["retrieval_top1"] = res["retrieval_top1"]
        obtained["retrieval_top5"] = res["retrieval_top5"]
        obtained["cosine_matched"] = res["cosine_matched"]
        obtained["n_evaluated"] = float(res["n"])
    elif s.category == "validation" and s.reproduce.command.startswith("meidnet screen"):
        import pandas as pd
        from meidnet.screen import screen
        parts = s.reproduce.command.split()
        folder = os.path.join(ROOT, parts[2])
        train_csv = None
        if "--train-csv" in parts:
            train_csv = os.path.join(ROOT, parts[parts.index("--train-csv") + 1])
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
    rec = {"id": s.id, "submission_sha256": sha256(path), "date": _dt.date.today().isoformat(), "by": by,
           "meidnet_version": ver, "agree": agree, "obtained": obtained, "compared": detail}
    os.makedirs(os.path.join(BENCH, "verified"), exist_ok=True)
    if agree:
        _write(os.path.join(BENCH, "verified", s.id + ".json"), json.dumps(rec, indent=1))
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
        print(f"ok: {len(submissions())} submission(s), {len(datasets())} dataset(s)")
        return 0
    if a.cmd == "render":
        for w in render():
            print("wrote docs/" + w)
        return 0
    if a.cmd == "schema":
        print("wrote", os.path.relpath(write_schema(), ROOT))
        return 0
    rec = reproduce(a.id, a.by)
    print(json.dumps(rec, indent=1))
    if rec["agree"]:
        print(f"agreed: set \"status\": \"meidnet_verified\" and \"verified_by\" in the submission and commit benchmarks/verified/{a.id}.json")
    else:
        print("the numbers do not agree within the tolerances; nothing was written")
    return 0 if rec["agree"] else 2


if __name__ == "__main__":
    sys.exit(main())
