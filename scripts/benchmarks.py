"""
MEIDNet Benchmarks: fixed protocols per dataset, one record per method, leaderboards rendered into the docs.

    python scripts/benchmarks.py validate                       check every file against the schema and the protocol
    python scripts/benchmarks.py render                         write docs/benchmarks/**, docs/community/index.md, docs/explore/databases.md
    python scripts/benchmarks.py run <dataset> --method <id>    evaluate a built-in method under the protocol (writes its record)
    python scripts/benchmarks.py score <dataset> --task <task> --predictions file.csv | --candidates file.csv
                                                                score the outputs of any model under the protocol
    python scripts/benchmarks.py paper-candidates <dataset>     screen the candidates shipped with the paper
    python scripts/benchmarks.py schema                         write benchmarks/schema.json

Layout:  benchmarks/datasets/<dataset>.json         the dataset and its protocol (tasks, settings, metrics)
         benchmarks/submissions/<dataset>/<id>.json  one method: its description and its results per task
         benchmarks/verified/<id>.json               written by `run` and `score`: the numbers obtained here
         benchmarks/runs/<dataset>/<method>/         the outputs behind a record (predictions, candidates, stability)
         benchmarks/catalog/databases.json           the catalogue of external databases by application

Results are only compared within one dataset and one protocol version.
Stability uses an MLIP (MACE-MP-0) through scripts/mlip_stability.py; point --mlip-python (or the environment
variable MEIDNET_MLIP_PYTHON) to a Python that has mace-torch if it is not installed next to MEIDNet.
"""
import argparse
import csv
import datetime as _dt
import hashlib
import html
import json
import math
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

Level = Literal["generated", "ml_filtered", "mlip_validated", "dft_validated", "experimentally_validated"]
Status = Literal["community_submitted", "published", "meidnet_verified"]
LEVELS: list[str] = ["generated", "ml_filtered", "mlip_validated", "dft_validated", "experimentally_validated"]
LEVEL_WORDS = {"generated": "generated", "ml_filtered": "ML filtered", "mlip_validated": "MLIP validated",
               "dft_validated": "DFT validated", "experimentally_validated": "experimentally validated"}
STATUS_WORDS = {"community_submitted": "Submitted", "published": "Reported in the paper", "meidnet_verified": "Computed here"}
PAPER_URL = "https://doi.org/10.1038/s41524-026-02153-3"
CODE_URL = "https://github.com/ABnano/MEIDNet"
WEIGHTS_URL = "https://huggingface.co/Babu09/MEIDNet/blob/main/"


# ── the protocol ─────────────────────────────────────────────────────────────
class MetricDef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    unit: str = ""
    better: Literal["higher", "lower", "none"] = "higher"
    digits: int = 3
    show: bool = True
    definition: str = ""


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    summary: str = ""
    split: str = ""
    headline: str
    settings: dict = {}
    notes: str = Field("", description="context for reading the results, shown under the table")
    metrics: list[MetricDef]

    def metric(self, mid: str) -> MetricDef | None:
        return next((m for m in self.metrics if m.id == mid), None)


class Protocol(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    data_dir: str = ""
    reference_model: str = ""
    tasks: list[Task]

    def task(self, tid: str) -> Task | None:
        return next((t for t in self.tasks if t.id == tid), None)


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
    role: str = ""
    protocol: Protocol | None = None


# ── a submission: one method and its results per task ───────────────────────
class Submitter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    affiliation: str = ""
    github: str = ""


class Links(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper: str = ""
    code: str = ""
    weights: str = ""


class Method(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    kind: Literal["model", "baseline"] = "model"
    description: str = ""
    meidnet_version: str = ""
    parameters: int | None = None
    training_data: str = ""
    checkpoint: str = ""
    checkpoint_sha256: str = Field("", pattern=r"^([0-9a-f]{64})?$")
    links: Links = Links()


class Reproduce(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = ""
    hardware: str = ""
    wall_time_s: float | None = None


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,60}$")
    dataset: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,40}$")
    protocol: str = Field(description="the protocol version the results follow, or 'paper' for numbers quoted from the paper")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    submitter: Submitter
    modalities: list[str] = Field(min_length=1)
    method: Method
    results: dict[str, dict[str, float | None]] = Field(min_length=1, description="task id -> metric id -> value")
    validation_level: Level = "generated"
    evidence: list[str] = []
    artifacts: dict[str, str] = Field({}, description="task id -> folder with the outputs behind the numbers")
    reproduce: Reproduce = Reproduce()
    status: Status = "community_submitted"
    verified_by: str = ""
    verified_on: str = ""
    notes: str = ""

    @field_validator("modalities")
    @classmethod
    def _modalities(cls, v):
        for m in v:
            if not re.fullmatch(r"(structure|composition|property:[A-Za-z_][A-Za-z0-9_]*|xrd|dos|spectrum:[a-z_]+|text|image)", m):
                raise ValueError(f"unknown modality {m!r}: use structure, composition, property:<column>, xrd, dos, spectrum:<kind>, text, image")
        return v


# ── files ────────────────────────────────────────────────────────────────────
def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _clean(v):
    """JSON has no NaN: missing values are stored as null."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


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
    """Fingerprint of a submission without its status fields."""
    d = _read(path)
    for k in ("status", "verified_by", "verified_on"):
        d.pop(k, None)
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def verified_record(sid: str) -> dict | None:
    vp = os.path.join(BENCH, "verified", sid + ".json")
    return _read(vp) if os.path.exists(vp) else None


def attempt_record(sid: str) -> dict | None:
    p = os.path.join(BENCH, "verified", sid + ".attempt.json")
    return _read(p) if os.path.exists(p) else None


# ── validate ─────────────────────────────────────────────────────────────────
def validate() -> list[str]:
    problems = []
    try:
        ds = datasets()
    except (ValidationError, ValueError) as e:
        return [f"datasets: {e}"]
    for d in ds.values():
        if d.protocol:
            for t in d.protocol.tasks:
                if not t.metric(t.headline):
                    problems.append(f"datasets/{d.id}.json: task {t.id} has headline {t.headline!r}, which is not one of its metrics")
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
        d = ds.get(s.dataset)
        if d is None:
            problems.append(f"{rel}: unknown dataset {s.dataset!r} (add benchmarks/datasets/{s.dataset}.json)")
            continue
        if os.path.basename(os.path.dirname(path)) != s.dataset or os.path.basename(path) != s.id + ".json":
            problems.append(f"{rel}: must be benchmarks/submissions/{s.dataset}/{s.id}.json")
        if s.id in seen:
            problems.append(f"{rel}: duplicate id {s.id}")
        seen.add(s.id)
        if d.protocol is None:
            problems.append(f"{rel}: dataset {s.dataset} has no protocol yet")
            continue
        if s.protocol not in (d.protocol.version, "paper"):
            problems.append(f"{rel}: protocol {s.protocol!r} is neither {d.protocol.version!r} nor 'paper'")
        for tid, res in s.results.items():
            t = d.protocol.task(tid)
            if t is None:
                problems.append(f"{rel}: unknown task {tid!r} (tasks: {', '.join(x.id for x in d.protocol.tasks)})")
                continue
            for m in res:
                if not t.metric(m):
                    problems.append(f"{rel}: metric {m!r} is not defined for task {tid} (metrics: {', '.join(x.id for x in t.metrics)})")
            if s.protocol == d.protocol.version and t.headline not in res:
                problems.append(f"{rel}: task {tid} needs its headline metric {t.headline!r} (null if it does not apply)")
        if s.validation_level in ("dft_validated", "experimentally_validated") and not s.evidence:
            problems.append(f"{rel}: {s.validation_level} needs evidence links")
        if s.status == "meidnet_verified":
            v = verified_record(s.id)
            if v is None:
                problems.append(f"{rel}: status meidnet_verified without benchmarks/verified/{s.id}.json")
            elif v.get("submission_sha256") != content_sha(path):
                problems.append(f"{rel}: the verified record was made for another version of this file - run it again")
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


# ── render: leaderboards ─────────────────────────────────────────────────────
VIRIDIS = ["#440154", "#482878", "#3e4a89", "#31688e", "#26828e", "#1f9e89", "#35b779", "#6ece58", "#b5de2b", "#fde725"]


def _mix(c1: str, c2: str, f: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(a, b))


def heat(t: float) -> tuple[str, str]:
    """Background and text colour for a score t in [0, 1] (1 = best), on the viridis scale."""
    t = min(1.0, max(0.0, t))
    x = t * (len(VIRIDIS) - 1)
    i = min(int(x), len(VIRIDIS) - 2)
    bg = _mix(VIRIDIS[i], VIRIDIS[i + 1], x - i)
    return bg, ("#111111" if t >= 0.55 else "#ffffff")


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _fmt(v, digits: int = 3) -> str:
    if not _num(v):
        return "–"
    if digits == 0:
        return f"{int(round(v)):,}"
    return f"{v:.{digits}f}"


def _params(p) -> str:
    if not p:
        return "–"
    return f"{p / 1e6:.2f} M" if p >= 1e5 else f"{p:,}"


def _sorted_rows(task: Task, rows: list[Submission]) -> list[Submission]:
    hm = task.metric(task.headline)
    def key(r):
        v = r.results.get(task.id, {}).get(task.headline)
        if not _num(v):
            return (1, 0.0)
        return (0, -v if hm.better == "higher" else v)
    return sorted(rows, key=key)


def _scale(task: Task, rows: list[Submission], m: MetricDef):
    """Colour position of a value within its column, by rank (1 = best): one outlier cannot flatten the others, and
    equal values share a colour."""
    vals = sorted({round(v, 9) for v in (r.results.get(task.id, {}).get(m.id) for r in rows) if _num(v)},
                  reverse=(m.better == "higher"))
    if not vals or m.better == "none":
        return None
    pos = {v: i for i, v in enumerate(vals)}
    def t(v):
        if not _num(v):
            return None
        if len(vals) == 1:
            return 1.0
        return 1.0 - pos[round(v, 9)] / (len(vals) - 1)
    return t


def _links(s: Submission) -> str:
    out = []
    for label, url in (("paper", s.method.links.paper), ("code", s.method.links.code), ("weights", s.method.links.weights)):
        if url:
            out.append(f'<a href="{html.escape(url)}" title="{label}">{label}</a>')
    return " · ".join(out) or "–"


def leaderboard(task: Task, rows: list[Submission], page_prefix: str = "results/") -> str:
    """One task as a sortable table: one row per method, one colour-scaled column per metric."""
    rows = _sorted_rows(task, [r for r in rows if task.id in r.results])
    cols = [m for m in task.metrics if m.show]
    scales = {m.id: _scale(task, rows, m) for m in cols}
    h = [f'<div class="lb-wrap" markdown="0"><table class="lb" id="lb-{task.id}">', "<thead><tr>",
         '<th class="no-sort lb-rank">#</th><th class="lb-model">Method</th>']
    for m in cols:
        arrow = " ↑" if m.better == "higher" else (" ↓" if m.better == "lower" else "")
        unit = f" ({m.unit})" if m.unit else ""
        h.append(f'<th data-sort-method="number" title="{html.escape(m.definition + unit)}">{m.label}{arrow}</th>')
    h.append('<th data-sort-method="number" title="trainable parameters">Params</th><th>Training data</th>'
             '<th>Added</th><th class="no-sort">Links</th></tr></thead><tbody>')
    for i, r in enumerate(rows, start=1):
        res = r.results[task.id]
        kind = '<span class="lb-kind">baseline</span>' if r.method.kind == "baseline" else ""
        h.append(f'<tr><td class="lb-rank">{i}</td><td class="lb-model"><a href="{page_prefix}{r.id}.html">{html.escape(r.method.name)}</a>{kind}</td>')
        for m in cols:
            v = res.get(m.id)
            sc = scales[m.id]
            t = sc(v) if sc else None
            style = ""
            if t is not None:
                bg, fg = heat(t)
                style = f' style="background:{bg};color:{fg}"'
            sort = f' data-sort="{v:.6g}"' if _num(v) else ' data-sort=""'
            h.append(f'<td class="lb-num"{sort}{style}>{_fmt(v, m.digits)}</td>')
        p = r.method.parameters
        h.append(f'<td class="lb-num" data-sort="{p or 0}">{_params(p)}</td><td>{html.escape(r.method.training_data or "–")}</td>'
                 f'<td>{r.date}</td><td class="lb-links">{_links(r)}</td></tr>')
    h.append("</tbody></table></div>")
    return "".join(h)


def _how_to_read(task: Task) -> str:
    out = [f'??? info "How to read the {task.name.lower()} table"', "",
           "    Rows are sorted by the first metric column; click any header to sort by another. Colours show the rank within "
           "each column, from dark (last) to yellow (first); ↑ marks metrics where higher is better, ↓ where lower is better. "
           "Hover a header for its definition.", ""]
    for m in task.metrics:
        unit = f" ({m.unit})" if m.unit else ""
        hidden = "" if m.show else " Listed on each method's page."
        out.append(f"    - **{re.sub('<[^>]+>', '', m.label)}**{unit}: {m.definition}.{hidden}")
    out.append("")
    return "\n".join(out)


def _artifact(s: Submission, task: str, name: str) -> str | None:
    folder = s.artifacts.get(task)
    if not folder:
        return None
    p = os.path.join(ROOT, folder, name)
    return p if os.path.exists(p) else None


def _scored_rows(s: Submission) -> list[dict]:
    p = _artifact(s, "inverse_design", "scored.csv")
    if not p:
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _by_variant(task: Task, rows: list[Submission]) -> str:
    """SUN rate per chemical family: where the methods differ."""
    variants = task.settings.get("variants", [])
    if not variants:
        return ""
    per = task.settings["per_target"] * len(task.settings["targets"])
    table = []
    for r in _sorted_rows(task, [x for x in rows if task.id in x.results]):
        sr = _scored_rows(r)
        if not sr:
            continue
        cells = []
        for v in variants:
            vr = [x for x in sr if x["variant"] == v]
            sun = sum(1 for x in vr if x["sun"] == "True")
            nov = sum(1 for x in vr if x["novel"] == "True")
            cells.append((sun / per, f"{sun}/{per}", f"{nov} novel of {len(vr)} delivered"))
        table.append((r, cells))
    if not table:
        return ""
    h = ['<div class="lb-wrap" markdown="0"><table class="lb lb-small"><thead><tr><th class="lb-model">Method</th>']
    h += [f'<th data-sort-method="number">{html.escape(v)}</th>' for v in variants]
    h.append("</tr></thead><tbody>")
    for r, cells in table:
        h.append(f'<tr><td class="lb-model"><a href="results/{r.id}.html">{html.escape(r.method.name)}</a></td>')
        for t, label, title in cells:
            bg, fg = heat(t)
            h.append(f'<td class="lb-num" data-sort="{t:.4f}" style="background:{bg};color:{fg}" title="{html.escape(title)}">{label}</td>')
        h.append("</tr>")
    h.append("</tbody></table></div>")
    return "".join(h)


def _chart(svg_markup: str, caption: str = "") -> str:
    cap = f'<p class="bench-cap">{html.escape(caption)}</p>' if caption else ""
    return f'<div class="bench-chart" markdown="0">{cap}{svg_markup}</div>'


def _parity(s: Submission, column: str, label: str) -> str:
    from meidnet import svg
    p = _artifact(s, "property_prediction", "predictions.csv")
    if not p:
        return ""
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows or f"true_{column}" not in rows[0]:
        return ""
    x = [float(r[f"true_{column}"]) for r in rows]
    y = [float(r[f"pred_{column}"]) for r in rows]
    return _chart(svg.scatter(x, y, f"{s.method.name}: {label}, predicted vs. DFT ({len(x):,} test materials)",
                              f"DFT {label}", f"predicted {label}", diagonal=True),
                  caption=f"{s.method.name}: {label.split(' (')[0]}, predicted vs. DFT")


def export_task(ds: Dataset, task: Task, rows: list[Submission]) -> tuple[str, str]:
    """CSV and JSON of a leaderboard, written next to the page (the Export links)."""
    rows = _sorted_rows(task, [r for r in rows if task.id in r.results])
    cols = [m.id for m in task.metrics]
    data_dir = os.path.join(DOCS, "benchmarks", "data")
    base = f"{ds.id}-{task.id}"
    lines = [["rank", "id", "method", "kind", *cols, "parameters", "training_data", "date", "paper", "code", "weights"]]
    recs = []
    for i, r in enumerate(rows, start=1):
        res = r.results[task.id]
        lines.append([i, r.id, r.method.name, r.method.kind, *[("" if not _num(res.get(c)) else res.get(c)) for c in cols],
                      r.method.parameters or "", r.method.training_data, r.date, r.method.links.paper, r.method.links.code,
                      r.method.links.weights])
        recs.append({"rank": i, "id": r.id, "method": r.method.name, "kind": r.method.kind,
                     "metrics": {c: _clean(res.get(c)) for c in cols if c in res}, "parameters": r.method.parameters,
                     "training_data": r.method.training_data, "date": r.date, "links": r.method.links.model_dump()})
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, base + ".csv"), "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(lines)
    _write(os.path.join(data_dir, base + ".json"), json.dumps(
        {"dataset": ds.id, "protocol": ds.protocol.version, "task": task.id, "headline": task.headline,
         "metrics": [m.model_dump() for m in task.metrics], "rows": recs}, indent=1, ensure_ascii=False))
    return f"data/{base}.csv", f"data/{base}.json"


def _protocol_section(ds: Dataset) -> list[str]:
    p = ds.protocol
    out = ["## Protocol", "", f"Version **{p.version}**. Data: `{p.data_dir}` (`meidnet download-data`), split {ds.split}.", ""]
    for t in p.tasks:
        out += [f"### {t.name}", "", t.summary, ""]
        st = t.settings
        if t.id == "inverse_design":
            tg = "; ".join(", ".join(f"{k} {v:g}" for k, v in x.items()) for x in st.get("targets", []))
            out += ["| setting | value |", "|---|---|",
                    f"| family | `{st.get('family')}`, variants {', '.join(f'`{v}`' for v in st.get('variants', []))} |",
                    f"| targets | {tg} |",
                    f"| budget | {st.get('per_target')} candidates per target and variant "
                    f"({st.get('per_target', 0) * len(st.get('targets', [])) * len(st.get('variants', []))} in total), each passing the family's rules |",
                    f"| MEIDNet search | the generation settings of `{st.get('generation_config')}`, at most {st.get('max_rounds')} rounds per target |",
                    f"| stability | {st.get('mlip')}; formation energy against elemental phases at most {st.get('stability_threshold')} eV/atom |",
                    f"| novelty | composition absent from the training split |",
                    f"| DFT check | Perov-5 entries with the same A, B and X sites; hit within {st.get('gap_tolerance')} eV of the target band gap |", ""]
        else:
            out += [f"Split: `{t.split}`. Reference implementation: `meidnet.benchmark`.", ""]
    out += ["Run the protocol for a MEIDNet checkpoint, or score the outputs of any other model:", "",
            "```bash",
            f"python scripts/benchmarks.py run {ds.id} --method meidnet-2k            # a built-in method, every task",
            f"python scripts/benchmarks.py score {ds.id} --task property_prediction --predictions preds.csv",
            f"python scripts/benchmarks.py score {ds.id} --task inverse_design --candidates candidates.csv",
            "```", "",
            "`preds.csv` has one row per test material: `id` (the dataset's `material_id`) and `pred_<property>` for each "
            "property. `candidates.csv` has `id`, `variant`, `target` (1, 2, 3), `formula`, `elements` (JSON of the sites, "
            "e.g. `{\"A\": \"Ba\", \"B\": \"Ti\", \"X\": \"O\"}`) and `cif` (path of the structure). Stability needs MACE: "
            "set `--mlip-python` or `MEIDNET_MLIP_PYTHON` if it lives in another environment.", ""]
    return out


def render_dataset(ds: Dataset, rows: list[Submission]) -> str:
    sets = {r.dataset for r in rows}
    if sets - {ds.id}:
        raise ValueError(f"render_dataset({ds.id}): rows of other datasets {sorted(sets - {ds.id})} - results are never compared across datasets")
    out = (["---", "hide:", "  - toc", "---", ""] if ds.protocol else []) + [f"# {ds.name}", "", ds.description, ""]
    meta = []
    if ds.rows:
        meta.append(f"**{ds.rows:,} materials**")
    if ds.split:
        meta.append(f"split: {ds.split}")
    if ds.properties:
        meta.append("properties: " + ", ".join(f"`{p}`" for p in ds.properties))
    if ds.source:
        meta.append(f"[dataset source]({ds.source})")
    if meta:
        out += [" · ".join(meta), ""]
    if ds.protocol is None:
        out += ["## No protocol yet", "",
                "The paper uses this dataset for structure-representation results; no benchmark protocol has been defined "
                "for it yet. A protocol is a `protocol` section in `benchmarks/datasets/" + ds.id + ".json` with its tasks, "
                "settings and metrics: [Perov-5](perov5.md) is the template ([how to add a dataset](../community/contribute.md#add-a-dataset)).", ""]
        return "\n".join(out)
    p = ds.protocol
    lb = [r for r in rows if r.protocol == p.version]
    paper = [r for r in rows if r.protocol == "paper"]
    tiles = [f"<div><b>{p.version}</b><span>protocol</span></div>",
             f"<div><b>{len(p.tasks)}</b><span>tasks</span></div>",
             f"<div><b>{len({r.id for r in lb if r.method.kind == 'model'})}</b><span>models</span></div>",
             f"<div><b>{len({r.id for r in lb if r.method.kind == 'baseline'})}</b><span>baselines</span></div>"]
    idt = p.task("inverse_design")
    if idt and idt.settings.get("per_target"):
        st = idt.settings
        tiles.append(f"<div><b>{st['per_target'] * len(st['targets']) * len(st['variants'])}</b><span>candidates per method</span></div>")
    out += ['<div class="bench-kpis" markdown="0">' + "".join(tiles) + "</div>", ""]
    nav = " · ".join([f"[{t.name}](#{_anchor(t.name)})" for t in p.tasks] + ["[Protocol](#protocol)", "[Reported in the paper](#reported-in-the-paper)",
                                                                             "[Submit a method](../community/contribute.md)"])
    out += [nav, "{ .lb-toolbar }", ""]
    from meidnet import svg
    for t in p.tasks:
        trows = [r for r in lb if t.id in r.results]
        csv_link, json_link = export_task(ds, t, trows)
        out += [f"## {t.name}", "", t.summary + f" Export: [CSV]({csv_link}) · [JSON]({json_link}).", ""]
        if not trows:
            out += ["_No results yet._", ""]
            continue
        out += [leaderboard(t, trows), "", _how_to_read(t)]
        if t.notes:
            out += [t.notes, ""]
        if t.id == "inverse_design":
            bv = _by_variant(t, trows)
            if bv:
                out += ["**SUN by chemical family.** Stable, unique and novel candidates out of the budget of each family; "
                        "hover a cell for the number of novel candidates.", "", bv, ""]
        if t.id == "property_prediction":
            charts = []
            for r in _sorted_rows(t, trows):
                if r.method.kind == "model":
                    charts += [_parity(r, "heat_all", "formation enthalpy (eV/atom)"), _parity(r, "dir_gap", "direct band gap (eV)")]
                    break
            knn = next((r for r in trows if r.id == "baseline-composition-knn"), None)
            if knn:
                charts.append(_parity(knn, "heat_all", "formation enthalpy (eV/atom)"))
            charts = [c for c in charts if c]
            if charts:
                out += ['<div class="bench-charts" markdown="0">' + "".join(charts) + "</div>", ""]
    out += _protocol_section(ds)
    out += ["## Reported in the paper", "",
            "Numbers quoted from the paper use the paper's own settings (other targets, budget and splits), so they are "
            "listed here rather than ranked above.", ""]
    if paper:
        out += ["| record | task | values | status |", "|---|---|---|---|"]
        for r in paper:
            for tid, res in r.results.items():
                t = p.task(tid)
                vals = ", ".join(f"{re.sub('<[^>]+>', '', t.metric(m).label)} {_fmt(v, t.metric(m).digits)}" for m, v in res.items() if t and t.metric(m))
                out.append(f"| [{r.method.name}](results/{r.id}.md) | {t.name if t else tid} | {vals} | {STATUS_WORDS[r.status]} |")
        out.append("")
        for r in paper:
            att = attempt_record(r.id)
            if att:
                t = p.task(next(iter(r.results)))
                def label(m):
                    md = t.metric(m) if t else None
                    return re.sub("<[^>]+>", "", md.label) if md else m
                dis = "; ".join(f"{label(m)} {_fmt(d['submitted'], 3)} reported, {_fmt(d['obtained'], 3)} obtained here" for m, d in att.get("compared", {}).items())
                out += [f"Re-evaluating the shipped checkpoint with this code on the same split gives: {dis} "
                        f"([details](results/{r.id}.md)). The protocol rows above report this code's numbers on the test split.", ""]
    else:
        out += ["_None._", ""]
    return "\n".join(out)


def render_result(s: Submission, ds: Dataset | None) -> str:
    p = ds.protocol if ds else None
    out = [f"# {s.method.name}", "", s.method.description, "",
           "| field | value |", "|---|---|",
           f"| Dataset | [{ds.name if ds else s.dataset}](../{s.dataset}.md), protocol `{s.protocol}` |",
           f"| Type | {s.method.kind} |",
           f"| Inputs | {', '.join(f'`{m}`' for m in s.modalities)} |",
           f"| Parameters | {_params(s.method.parameters)} |",
           f"| Training data | {s.method.training_data or '–'} |",
           f"| Status | {STATUS_WORDS[s.status]}{' on ' + s.verified_on if s.verified_on else ''} |",
           f"| Evidence level | {LEVEL_WORDS[s.validation_level]} |",
           f"| Added | {s.date} by {s.submitter.name}{' (' + s.submitter.affiliation + ')' if s.submitter.affiliation else ''} |"]
    if s.method.checkpoint:
        url = s.method.links.weights or (s.method.checkpoint if s.method.checkpoint.startswith("http") else CODE_URL + "/blob/main/" + s.method.checkpoint)
        out.append(f"| Checkpoint | [{os.path.basename(s.method.checkpoint)}]({url})"
                   + (f" · sha256 `{s.method.checkpoint_sha256[:12]}…`" if s.method.checkpoint_sha256 else "") + " |")
    links = [f"[{k}]({v})" for k, v in s.method.links.model_dump().items() if v]
    if links:
        out.append(f"| Links | {' · '.join(links)} |")
    out.append("")
    for tid, res in s.results.items():
        t = p.task(tid) if p else None
        out += [f"## {t.name if t else tid}", ""]
        out += ["| metric | value | definition |", "|---|---|---|"]
        for m, v in res.items():
            md = t.metric(m) if t else None
            label = re.sub("<[^>]+>", "", md.label) if md else m
            unit = f" {md.unit}" if md and md.unit and _num(v) else ""
            out.append(f"| {label} | {_fmt(v, md.digits if md else 3)}{unit} | {md.definition if md else ''} |")
        out.append("")
        if tid == "inverse_design":
            sr = _scored_rows(s)
            if sr:
                out += ["### Candidates", "",
                        "Every candidate with its MLIP formation energy, novelty and, where Perov-5 has the same sites, the DFT band gap.", "",
                        "| candidate | formula | target gap (eV) | ΔHf (eV/atom) | stable | novel | DFT gap (eV) |", "|---|---|---|---|---|---|---|"]
                for x in sr:
                    dhf = x.get("dHf") or ""
                    dft = x.get("dft_dir_gap") or ""
                    out.append(f"| {x['id']} | {x['formula']} | {x.get('target_dir_gap', '')} | {_fmt(float(dhf), 3) if dhf else '–'} | "
                               f"{'yes' if x['stable'] == 'True' else 'no'} | {'yes' if x['novel'] == 'True' else 'no'} | {_fmt(float(dft), 2) if dft else '–'} |")
                out.append("")
        if tid == "property_prediction":
            charts = [c for c in (_parity(s, "heat_all", "formation enthalpy (eV/atom)"), _parity(s, "dir_gap", "direct band gap (eV)")) if c]
            if charts:
                out += ['<div class="bench-charts" markdown="0">' + "".join(charts) + "</div>", ""]
    if s.artifacts:
        out += ["## Outputs", ""] + [f"- {k}: [`{v}`]({v if v.startswith('http') else CODE_URL + '/tree/main/' + v.replace(os.sep, '/')})"
                                     for k, v in s.artifacts.items()] + [""]
    if s.evidence:
        out += ["## Evidence", ""] + [f"- <{e}>" if e.startswith("http") else f"- `{e}`" for e in s.evidence] + [""]
    if s.reproduce.command:
        out += ["## Reproduce", "", "```", s.reproduce.command, "```", ""]
        if s.reproduce.hardware:
            took = ""
            if s.reproduce.wall_time_s:
                w = s.reproduce.wall_time_s
                what = "generating the candidates" if "inverse_design" in s.results else "the evaluation"
                took = f"; {what} took {w / 60:.0f} min" if w >= 120 else f"; {what} took {w:.0f} s"
            out += [f"Computed on {s.reproduce.hardware}{took}.", ""]
    att = attempt_record(s.id)
    if att:
        out += ["## Re-evaluated here", "",
                f"On {att.get('date', '?')} this repository's code re-evaluated the shipped checkpoint on the same split "
                f"(MEIDNet {att.get('meidnet_version', '?')}).", "", "| metric | reported | obtained here |", "|---|---|---|"]
        t = p.task(next(iter(s.results))) if p else None
        for m, d in att.get("compared", {}).items():
            md = t.metric(m) if t else None
            out.append(f"| {re.sub('<[^>]+>', '', md.label) if md else m} | {_fmt(d['submitted'], 3)} | {_fmt(d['obtained'], 3)} |")
        out.append("")
    if s.notes:
        out += ["## Notes", "", s.notes, ""]
    return "\n".join(out)


def render_hub(ds: dict[str, Dataset], by_ds: dict[str, list[Submission]]) -> str:
    allrows = [r for rs in by_ds.values() for r in rs]
    with_proto = [d for d in ds.values() if d.protocol]
    hub = ["# MEIDNet Benchmarks", "",
           "Standardised tasks for multimodal materials models, each with a fixed protocol: the data split, the targets, "
           "the candidate budget and the metrics. Every method is evaluated the same way, the outputs behind each number "
           "are kept, and the scoring works for any model, not only MEIDNet. Results are compared within one dataset and "
           "one protocol version.", "",
           '<div class="bench-kpis" markdown="0">'
           f"<div><b>{len(with_proto)}</b><span>protocols</span></div>"
           f"<div><b>{sum(len(d.protocol.tasks) for d in with_proto)}</b><span>tasks</span></div>"
           f"<div><b>{len({r.id for r in allrows if r.protocol != 'paper'})}</b><span>methods</span></div>"
           f"<div><b>{sum(1 for r in allrows if r.status == 'meidnet_verified')}</b><span>computed here</span></div>"
           "</div>", "",
           "## Leaderboards", "", "| dataset | protocol | tasks | models | baselines |", "|---|---|---|---|---|"]
    for k, d in sorted(ds.items(), key=lambda kv: (kv[1].protocol is None, kv[1].name)):
        rows = [r for r in by_ds.get(k, []) if d.protocol and r.protocol == d.protocol.version]
        if d.protocol:
            hub.append(f"| [{d.name}]({k}.md) | `{d.protocol.version}` | "
                       f"{', '.join(f'[{t.name.lower()}]({k}.md#{_anchor(t.name)})' for t in d.protocol.tasks)} | "
                       f"{len({r.id for r in rows if r.method.kind == 'model'})} | {len({r.id for r in rows if r.method.kind == 'baseline'})} |")
        else:
            hub.append(f"| [{d.name}]({k}.md) | not yet defined | – | – | – |")
    hub += ["", "## How a result gets on a leaderboard", "",
            "1. **Protocol.** Each dataset fixes its tasks in `benchmarks/datasets/<dataset>.json`: splits, property targets, "
            "candidate budget, metrics and the direction in which each is better.",
            "2. **Run or score.** `python scripts/benchmarks.py run` evaluates a MEIDNet checkpoint end to end; "
            "`python scripts/benchmarks.py score` evaluates the predictions or candidate structures of any other model "
            "with the same code.",
            "3. **Record.** One JSON file per method (`benchmarks/submissions/<dataset>/<method>.json`) holds the description, "
            "the numbers per task and the folder with the outputs behind them.",
            "4. **Verification.** Numbers computed in this repository carry a record in `benchmarks/verified/`; submitted "
            "results are re-scored from their outputs before they are marked as computed here.", "",
            "[Contribute a method](../community/contribute.md) · [Databases by application](../explore/databases.md)", ""]
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
    for fn in os.listdir(os.path.join(out_dir, "results")):          # pages of records that no longer exist
        if fn.endswith(".md") and fn[:-3] not in {s.id for _, s in subs}:
            os.remove(os.path.join(out_dir, "results", fn))
    written = []
    _write(os.path.join(out_dir, "index.md"), render_hub(ds, by_ds)); written.append("benchmarks/index.md")
    for k, d in ds.items():
        _write(os.path.join(out_dir, k + ".md"), render_dataset(d, by_ds.get(k, []))); written.append(f"benchmarks/{k}.md")
    for _, s in subs:
        _write(os.path.join(out_dir, "results", s.id + ".md"), render_result(s, ds.get(s.dataset))); written.append(f"benchmarks/results/{s.id}.md")
    com = ["# Community results", "", "Every method record, newest first. [Contribute yours](contribute.md).", "",
           "| date | method | dataset | tasks | status |", "|---|---|---|---|---|"]
    for _, s in sorted(subs, key=lambda x: x[1].date, reverse=True):
        names = []
        for tid in s.results:
            t = ds[s.dataset].protocol.task(tid) if s.dataset in ds and ds[s.dataset].protocol else None
            names.append(t.name.lower() if t else tid)
        com.append(f"| {s.date} | [{s.method.name}](../benchmarks/results/{s.id}.md) | [{ds[s.dataset].name if s.dataset in ds else s.dataset}](../benchmarks/{s.dataset}.md) | "
                   f"{', '.join(names)} | {STATUS_WORDS[s.status]} |")
    com.append("")
    _write(os.path.join(DOCS, "community", "index.md"), "\n".join(com)); written.append("community/index.md")
    _write(os.path.join(DOCS, "explore", "databases.md"), render_databases(catalog())); written.append("explore/databases.md")
    return written


# ── run and score ────────────────────────────────────────────────────────────
BUILTIN = {
    "meidnet-2k": {
        "name": "MEIDNet (published model)", "kind": "model",
        "checkpoint": "checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth",
        "description": "Early fusion with property-aware decoding, trained for 2,000 epochs with a contrastive warm-up over the "
                       "first 1,200: the model of the paper and of the live Studio.",
        "tasks": ["inverse_design", "property_prediction", "representation"]},
    "meidnet-propertyaware": {
        "name": "MEIDNet (shorter training)", "kind": "model",
        "checkpoint": "checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware.pth",
        "description": "The architecture of the published model, trained for fewer epochs.",
        "tasks": ["inverse_design", "property_prediction", "representation"]},
    "meidnet-earlyfusion": {
        "name": "MEIDNet (first early-fusion model)", "kind": "model",
        "checkpoint": "checkpoints/dual_autoencoder_clip_earlyfusion.pth",
        "description": "The earliest ablation of the paper, without property-aware decoding.",
        "tasks": ["inverse_design", "property_prediction", "representation"]},
    "baseline-screening": {
        "name": "Encoder screening", "kind": "baseline", "uses": "meidnet-2k",
        "description": "Enumerates the compositions of each chemical family that pass its rules and keeps those that the "
                       "published model's structure encoder predicts closest to each target, ranked with the generator's own "
                       "selection score. No latent search.",
        "tasks": ["inverse_design"]},
    "baseline-random": {
        "name": "Random sampling", "kind": "baseline",
        "description": "Draws compositions at random, without repetition, from those that pass the family's rules.",
        "tasks": ["inverse_design"]},
    "baseline-composition-knn": {
        "name": "Composition k-NN", "kind": "baseline",
        "description": "Mean property of the five training materials nearest in element-fraction space: a composition-only "
                       "representation, without structure.",
        "tasks": ["property_prediction", "representation"]},
    "baseline-train-mean": {
        "name": "Training mean", "kind": "baseline",
        "description": "Predicts the training-set mean of each property.",
        "tasks": ["property_prediction"]},
    "baseline-chance": {
        "name": "Chance level", "kind": "baseline",
        "description": "Retrieval by random choice among the 3,785 test materials.",
        "tasks": ["representation"]},
}


def _mlip_python(arg: str | None) -> str:
    return arg or os.environ.get("MEIDNET_MLIP_PYTHON") or sys.executable


def _hardware() -> str:
    import platform
    return f"{platform.processor() or platform.machine()} ({os.cpu_count()} threads), CPU only"


def run_mlip(candidates_csv: str, out_csv: str, python: str, log=print) -> None:
    cmd = [python, os.path.join(ROOT, "scripts", "mlip_stability.py"), candidates_csv, out_csv]
    log("running " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    subprocess.run(cmd, check=True)


def _score_candidates(ds: Dataset, folder: str, log=print) -> tuple[dict, list[dict]]:
    from meidnet import benchmark as B
    t = ds.protocol.task("inverse_design")
    data_dir = os.path.join(ROOT, ds.protocol.data_dir)
    cands = B.read_candidates(os.path.join(folder, "candidates.csv"))
    stab = B.read_stability(os.path.join(folder, "stability.csv"))
    missing = [c["id"] for c in cands if c["id"] not in stab]
    if missing:
        raise SystemExit(f"{len(missing)} candidate(s) have no stability result ({missing[:3]} ...): run the MLIP step")
    known = B.known_by_site(data_dir, "dir_gap", cache=os.path.join(BENCH, "runs", ds.id, "known_dir_gap_by_site.json"))
    metrics, rows = B.score_inverse_design(cands, stab, t.settings, B.training_formulas(data_dir), known)
    with open(os.path.join(folder, "scored.csv"), "w", newline="", encoding="utf-8") as f:
        keys = list(rows[0]) if rows else ["id"]
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return metrics, rows


def _pick(task: Task, values: dict) -> dict:
    out = {m.id: _clean(float(values[m.id])) for m in task.metrics if m.id in values}
    out.setdefault(task.headline, None)          # e.g. retrieval for a model without a second modality: not applicable
    return out


def _record(ds: Dataset, method_id: str, spec: dict, results: dict, artifacts: dict, wall: float) -> str:
    """Write (or update) the method's record and the verification record."""
    path = os.path.join(BENCH, "submissions", ds.id, method_id + ".json")
    old = _read(path) if os.path.exists(path) else {}
    from meidnet import __version__ as ver
    ck = spec.get("checkpoint") or (BUILTIN[spec["uses"]]["checkpoint"] if spec.get("uses") else "")
    params = None
    if ck:
        from meidnet.checkpoint import load_checkpoint
        params = int(sum(p.numel() for p in load_checkpoint(os.path.join(ROOT, ck)).model.parameters()))
    model_like = spec["kind"] == "model" or spec.get("uses")
    rec = {
        "id": method_id, "dataset": ds.id, "protocol": ds.protocol.version,
        "date": old.get("date") or _dt.date.today().isoformat(),
        "submitter": {"name": "Anand Babu", "affiliation": "UCLouvain", "github": "ABnano"},
        "modalities": (["structure", *[f"property:{c}" for c in ds.properties]] if model_like else
                       (["composition"] if "knn" in method_id else ["structure"])),
        "method": {"name": spec["name"], "kind": spec["kind"], "description": spec["description"], "meidnet_version": ver,
                   "parameters": params, "training_data": "" if method_id in ("baseline-random", "baseline-chance") else "Perov-5 train (11,356)",
                   "checkpoint": ck, "checkpoint_sha256": sha256(os.path.join(ROOT, ck)) if ck else "",
                   "links": {"paper": PAPER_URL if model_like else "", "code": CODE_URL,
                             "weights": (WEIGHTS_URL + os.path.basename(ck)) if ck else ""}},
        "results": {**old.get("results", {}), **results},
        "validation_level": "mlip_validated" if "inverse_design" in {**old.get("results", {}), **results} else "generated",
        "evidence": [], "artifacts": {**old.get("artifacts", {}), **artifacts},
        "reproduce": {"command": f"python scripts/benchmarks.py run {ds.id} --method {method_id}", "hardware": _hardware(),
                      "wall_time_s": round(wall, 1)},          # candidate generation when there is one, else this run
        "status": "meidnet_verified", "verified_by": "maintainer", "verified_on": _dt.date.today().isoformat(),
        "notes": old.get("notes", ""),
    }
    Submission.model_validate(rec)
    _write(path, json.dumps(_clean(rec), indent=1, ensure_ascii=False) + "\n")
    _write(os.path.join(BENCH, "verified", method_id + ".json"), json.dumps(
        {"id": method_id, "submission_sha256": content_sha(path), "date": _dt.date.today().isoformat(), "by": "maintainer",
         "hardware": _hardware(), "meidnet_version": ver, "obtained": _clean(rec["results"])}, indent=1) + "\n")
    return path


def run(dataset: str, method_id: str, tasks: list[str] | None = None, stage: str = "all", mlip_python: str | None = None,
        log=print) -> str:
    import time
    from meidnet import benchmark as B
    ds = datasets()[dataset]
    if ds.protocol is None:
        raise SystemExit(f"{dataset} has no protocol")
    if method_id not in BUILTIN:
        raise SystemExit(f"unknown built-in method {method_id!r}; built-in: {', '.join(BUILTIN)} "
                         f"(other models: `score` their outputs and write a record)")
    spec = BUILTIN[method_id]
    tasks = tasks or spec["tasks"]
    data_dir = os.path.join(ROOT, ds.protocol.data_dir)
    run_root = os.path.join(BENCH, "runs", dataset, method_id)
    results, artifacts = {}, {}
    t0 = time.time()
    ck = spec.get("checkpoint") or (BUILTIN[spec["uses"]]["checkpoint"] if spec.get("uses") else "")
    lm = None
    if ck:
        from meidnet.checkpoint import load_checkpoint
        lm = load_checkpoint(os.path.join(ROOT, ck), device="cpu")
    if {"property_prediction", "representation"} & set(tasks):
        if spec["kind"] == "model":
            ev = B.evaluate_checkpoint(lm, data_dir, k=ds.protocol.task("representation").settings.get("probe_k", 5))
            values = {"property_prediction": ev.property_prediction, "representation": ev.representation}
            preds = ev.predictions
        else:
            bl = B.evaluate_baselines(data_dir, ds.properties, k=5)
            key = {"baseline-composition-knn": "composition_knn", "baseline-train-mean": "train_mean", "baseline-chance": "chance"}[method_id]
            values = bl[key]
            preds = bl["predictions"].get(key)
        for tid in ("property_prediction", "representation"):
            if tid in tasks and tid in values:
                results[tid] = _pick(ds.protocol.task(tid), values[tid])
        if "property_prediction" in tasks and preds:
            folder = os.path.join(run_root, "property_prediction")
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "predictions.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(preds[0]))
                w.writeheader()
                w.writerows({k: (f"{v:.5g}" if isinstance(v, float) else v) for k, v in p.items()} for p in preds)
            artifacts["property_prediction"] = os.path.relpath(folder, ROOT).replace(os.sep, "/")
    if "inverse_design" in tasks:
        t = ds.protocol.task("inverse_design")
        folder = os.path.join(run_root, "inverse_design")
        os.makedirs(folder, exist_ok=True)
        if stage in ("all", "generate"):
            tg = time.time()
            if method_id == "baseline-random":
                cands = B.design_random(t.settings, folder, seed=0)
            elif method_id == "baseline-screening":
                from meidnet.config import load_config
                cfg = load_config(os.path.join(ROOT, t.settings["generation_config"]))
                objectives = [o.model_dump() for o in cfg.generation.objectives]
                cands = B.design_screening(lm, t.settings, objectives, folder)
            else:
                import torch
                from meidnet.config import load_config
                cfg = load_config(os.path.join(ROOT, t.settings["generation_config"]))
                cands = B.design_meidnet(lm, cfg.generation, t.settings, folder, log=lambda *a: None, device=torch.device("cpu"))
            B.write_candidates(cands, os.path.join(folder, "candidates.csv"))
            import torch
            _write(os.path.join(folder, "timing.json"), json.dumps({"seconds": round(time.time() - tg, 1), "threads": torch.get_num_threads()}))
            log(f"{len(cands)} candidates written to {os.path.relpath(folder, ROOT)}")
        if stage in ("all", "mlip"):
            run_mlip(os.path.join(folder, "candidates.csv"), os.path.join(folder, "stability.csv"), _mlip_python(mlip_python), log)
        if stage in ("all", "score"):
            metrics, _ = _score_candidates(ds, folder, log)
            results["inverse_design"] = _pick(t, metrics)
            artifacts["inverse_design"] = os.path.relpath(folder, ROOT).replace(os.sep, "/")
    if not results:
        return ""
    wall = time.time() - t0
    timing = os.path.join(run_root, "inverse_design", "timing.json")
    if os.path.exists(timing):                               # the dominant cost: generating the candidates
        wall = float(_read(timing).get("seconds", wall))
    path = _record(ds, method_id, spec, results, artifacts, wall)
    log(f"wrote {os.path.relpath(path, ROOT)}")
    return path


def score(dataset: str, task_id: str, predictions: str | None = None, candidates: str | None = None,
          mlip_python: str | None = None, log=print) -> dict:
    """Score the outputs of any model under the protocol (prints the metrics; write them into a record to submit)."""
    import numpy as np
    from meidnet import benchmark as B
    ds = datasets()[dataset]
    t = ds.protocol.task(task_id)
    if t is None:
        raise SystemExit(f"unknown task {task_id}")
    data_dir = os.path.join(ROOT, ds.protocol.data_dir)
    if task_id == "property_prediction":
        if not predictions:
            raise SystemExit("--predictions file.csv is needed")
        import pandas as pd
        truth = pd.read_csv(os.path.join(data_dir, f"{t.settings.get('split', 'test')}.csv"), usecols=["material_id", *ds.properties])
        pred = pd.read_csv(predictions)
        m = truth.astype({"material_id": str}).merge(pred.astype({"id": str}), left_on="material_id", right_on="id", how="left")
        missing = int(m[[f"pred_{c}" for c in ds.properties]].isna().any(axis=1).sum())
        if missing:
            raise SystemExit(f"{missing} test material(s) have no prediction")
        values = B.property_metrics(ds.properties, m[ds.properties].to_numpy(float), m[[f"pred_{c}" for c in ds.properties]].to_numpy(float))
        return _pick(t, values)
    if task_id == "inverse_design":
        if not candidates:
            raise SystemExit("--candidates candidates.csv is needed")
        folder = os.path.dirname(os.path.abspath(candidates))
        if os.path.basename(candidates) != "candidates.csv":
            raise SystemExit("name the file candidates.csv (stability.csv and scored.csv are written next to it)")
        if not os.path.exists(os.path.join(folder, "stability.csv")):
            run_mlip(candidates, os.path.join(folder, "stability.csv"), _mlip_python(mlip_python), log)
        metrics, _ = _score_candidates(ds, folder, log)
        return _pick(t, metrics)
    raise SystemExit(f"`score` covers property_prediction and inverse_design; {task_id} needs the model's latents (use `run`)")


def paper_candidates(dataset: str, mlip_python: str | None = None, log=print) -> str:
    """Screen the CIFs shipped with the paper (examples/perov5/paper_results) and keep the result as a paper record."""
    import glob
    from meidnet import benchmark as B
    ds = datasets()[dataset]
    src = os.path.join(ROOT, "examples", dataset, "paper_results")
    folder = os.path.join(BENCH, "runs", dataset, "paper-candidates", "inverse_design")
    os.makedirs(os.path.join(folder, "cifs"), exist_ok=True)
    from pymatgen.core import Structure
    rows = []
    for p in sorted(glob.glob(os.path.join(src, "**", "*.cif"), recursive=True)):
        variant = os.path.basename(os.path.dirname(p))
        cid = f"{variant}_{os.path.splitext(os.path.basename(p))[0]}"
        dst = os.path.join("cifs", cid + ".cif")
        with open(p, encoding="utf-8") as fi, open(os.path.join(folder, dst), "w", encoding="utf-8", newline="\n") as fo:
            fo.write(fi.read())
        s = Structure.from_file(p)
        rows.append({"id": cid, "variant": variant, "target": "", "formula": s.composition.reduced_formula, "elements": "{}",
                     "cif": dst.replace(os.sep, "/"), "passes_rules": True})
    with open(os.path.join(folder, "candidates.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    if not os.path.exists(os.path.join(folder, "stability.csv")):
        run_mlip(os.path.join(folder, "candidates.csv"), os.path.join(folder, "stability.csv"), _mlip_python(mlip_python), log)
    t = ds.protocol.task("inverse_design")
    data_dir = os.path.join(ROOT, ds.protocol.data_dir)
    settings = {**t.settings, "budget": len(rows)}
    metrics, scored = B.score_inverse_design(B.read_candidates(os.path.join(folder, "candidates.csv")),
                                             B.read_stability(os.path.join(folder, "stability.csv")), settings,
                                             B.training_formulas(data_dir), {})
    with open(os.path.join(folder, "scored.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(scored[0]))
        w.writeheader()
        w.writerows(scored)
    res = {k: v for k, v in _pick(t, metrics).items() if k in ("sun_rate", "stable_rate", "unique_rate", "novel_rate", "dhf_median", "n_delivered", "n_sun")}
    path = os.path.join(BENCH, "submissions", dataset, "paper-candidates.json")
    from meidnet import __version__ as ver
    rec = {"id": "paper-candidates", "dataset": dataset, "protocol": "paper", "date": _dt.date.today().isoformat(),
           "submitter": {"name": "Anand Babu", "affiliation": "UCLouvain", "github": "ABnano"},
           "modalities": ["structure", *[f"property:{c}" for c in ds.properties]],
           "method": {"name": "Candidates shipped with the paper, screened here", "kind": "model",
                      "description": f"The {len(rows)} candidate structures in examples/{dataset}/paper_results, relaxed with "
                                     "MACE-MP-0 and scored with the protocol's stability, uniqueness and novelty criteria. "
                                     "Their targets and budget are those of the paper, so the record is not ranked.",
                      "meidnet_version": ver, "parameters": None, "training_data": "Perov-5 train (11,356)",
                      "checkpoint": "", "checkpoint_sha256": "", "links": {"paper": PAPER_URL, "code": CODE_URL, "weights": ""}},
           "results": {"inverse_design": res}, "validation_level": "mlip_validated", "evidence": [],
           "artifacts": {"inverse_design": os.path.relpath(folder, ROOT).replace(os.sep, "/")},
           "reproduce": {"command": f"python scripts/benchmarks.py paper-candidates {dataset}", "hardware": _hardware(), "wall_time_s": None},
           "status": "meidnet_verified", "verified_by": "maintainer", "verified_on": _dt.date.today().isoformat(), "notes": ""}
    Submission.model_validate(rec)
    _write(path, json.dumps(_clean(rec), indent=1, ensure_ascii=False) + "\n")
    _write(os.path.join(BENCH, "verified", "paper-candidates.json"), json.dumps(
        {"id": "paper-candidates", "submission_sha256": content_sha(path), "date": _dt.date.today().isoformat(), "by": "maintainer",
         "hardware": _hardware(), "meidnet_version": ver, "obtained": _clean(rec["results"])}, indent=1) + "\n")
    return path


def write_schema() -> str:
    path = os.path.join(BENCH, "schema.json")
    schema = Submission.model_json_schema()
    schema["$comment"] = "Task and metric ids come from the dataset's protocol (benchmarks/datasets/<dataset>.json)."
    _write(path, json.dumps(schema, indent=1))
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    sub.add_parser("render")
    sub.add_parser("schema")
    r = sub.add_parser("run")
    r.add_argument("dataset")
    r.add_argument("--method", required=True, choices=list(BUILTIN))
    r.add_argument("--tasks", nargs="*", default=None)
    r.add_argument("--stage", choices=["all", "generate", "mlip", "score"], default="all",
                   help="inverse design only: generate candidates, relax them, or score them")
    r.add_argument("--mlip-python", default=None)
    s = sub.add_parser("score")
    s.add_argument("dataset")
    s.add_argument("--task", required=True)
    s.add_argument("--predictions")
    s.add_argument("--candidates")
    s.add_argument("--mlip-python", default=None)
    pc = sub.add_parser("paper-candidates")
    pc.add_argument("dataset")
    pc.add_argument("--mlip-python", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        problems = validate()
        if problems:
            print("\n".join(problems))
            return 1
        print(f"ok: {len(submissions())} record(s), {len(datasets())} dataset(s), {len(catalog().databases)} database(s) in the catalogue")
        return 0
    if a.cmd == "render":
        for w in render():
            print("wrote docs/" + w)
        return 0
    if a.cmd == "schema":
        print("wrote", os.path.relpath(write_schema(), ROOT))
        return 0
    if a.cmd == "run":
        run(a.dataset, a.method, a.tasks, a.stage, a.mlip_python)
        return 0
    if a.cmd == "score":
        print(json.dumps(score(a.dataset, a.task, a.predictions, a.candidates, a.mlip_python), indent=1))
        return 0
    if a.cmd == "paper-candidates":
        print("wrote", os.path.relpath(paper_candidates(a.dataset, a.mlip_python), ROOT))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
