"""
Build the Colab notebooks in notebooks/ from plain Python (no nbformat dependency).

    python scripts/make_notebooks.py [OUT_DIR]

Four notebooks, one per journey. Each walks through the seven blocks of MEIDNet Studio, in the
Studio's order and colours (Data, Model, Family, Rules, Targets, Search, Candidates):

    01_quickstart.ipynb               the published model on a CPU, about 5 minutes
    02_your_own_data.ipynb            your table + CIFs -> check -> train -> design with your model
    03_add_a_rule.ipynb               write two rules, see what they remove, search with them
    04_MEIDNet_Studio_in_Colab.ipynb  the Studio page inside Colab, then the same Studio from Python

Every notebook starts with one SETUP cell (installs in Colab; defines the chart and 3D helpers).
Every block opens with block_header(key), a markdown box in the block colour, and closes with a
print_flow(...) line that says what flows on to the next block.  main(out_dir) writes the four
notebooks into out_dir (default: notebooks/) and nowhere else.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "notebooks")
COLAB_URL = "https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/"
DOCS_URL = "https://babu09-meidnet.hf.space/docs/"
SEP = " · "                      # the " · " of "Block 1 · Data", as in the Studio

# key, emoji, name, colour and one-sentence purpose of each block (the Studio's colours and wording)
BLOCKS = [
    ("data", "📊", "Data", "#2a78d6",
     "What MEIDNet learns from: a table of materials with their structures and properties."),
    ("model", "🧠", "Model", "#eb6834",
     "One shared latent space where structures and properties meet."),
    ("family", "🧱", "Family", "#1baf7a",
     "The crystal type: where atoms sit and which elements may occupy each site."),
    ("rules", "📏", "Rules", "#eda100",
     "Hard checks that every candidate must pass, in order."),
    ("targets", "🎯", "Targets", "#e87ba4",
     "What the material should have, and how much each goal matters."),
    ("search", "🔎", "Search", "#008300",
     "The latent optimisation of the paper: from targets back to structures."),
    ("candidates", "💎", "Candidates", "#4a3aa7",
     "What came out, and why each one passed."),
]

CREDITS = ("<sub>Notebook by Anand Babu. MEIDNet: <i>Multimodal generative AI framework for inverse materials "
           "design</i>, npj Computational Materials (2026), "
           "<a href=\"https://doi.org/10.1038/s41524-026-02153-3\">doi:10.1038/s41524-026-02153-3</a>. "
           "3D views use chemiscope: G. Fraux, R. K. Cersonsky, M. Ceriotti, <i>Chemiscope: interactive "
           "structure-property explorer for materials and molecules</i>, JOSS 5, 2117 (2020).</sub>")

HOW_TO = ("**How to use it:** run the cells from top to bottom (Shift+Enter, or *Runtime → Run all*). "
          "Cells with fields are forms: change a value, then run that cell and the ones below it again.")


# ───────────────────────── cells ─────────────────────────
def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")}


def code(src: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "source": src.strip("\n")}


def form_cell(src: str) -> dict:
    """A Colab form: '#@title', '#@param' and '#@markdown' lines become fields; the code stays folded."""
    cell = code(src)
    cell["metadata"] = {"cellView": "form"}
    return cell


def _tint(colour: str, alpha: float) -> str:
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def block_header(key: str) -> dict:
    """The markdown cell that opens a block: a box in the block colour with 'Block n · Name' and its purpose."""
    n = [b[0] for b in BLOCKS].index(key) + 1
    _, emoji, name, colour, purpose = BLOCKS[n - 1]
    cell = md(f'<div style="border-left:6px solid {colour};background:{_tint(colour, 0.09)};border-radius:6px;'
              f'padding:12px 18px;margin:6px 0">\n'
              f'<h2 style="margin:0 0 6px 0">{emoji} Block {n}{SEP}{name}</h2>\n'
              f'<p style="margin:0">{purpose}</p>\n'
              f'</div>')
    cell["_section"] = key
    return cell


def block_map() -> str:
    """The seven blocks in a row, in their colours (the order every notebook follows)."""
    chips = [f'<span style="display:inline-block;border-left:5px solid {colour};background:{_tint(colour, 0.09)};'
             f'border-radius:4px;padding:2px 9px;margin:2px 0">{emoji} {n}{SEP}{name}</span>'
             for n, (_, emoji, name, colour, _) in enumerate(BLOCKS, start=1)]
    return "<p>" + " → ".join(chips) + "</p>"


def title_cell(title: str, file: str, intro: str) -> dict:
    badge = f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({COLAB_URL}{file})"
    return md(f"# {title}\n\n{badge}\n\n{intro.strip()}\n\n{block_map()}\n\n{HOW_TO}\n\n{CREDITS}")


def notebook(cells: list[dict], name: str) -> dict:
    """nbformat 4.5 JSON: every cell gets a stable id (block key + position), code cells no outputs."""
    out, section, counts = [], "intro", {}
    for cell in cells:
        section = cell.get("_section", section)
        counts[section] = counts.get(section, 0) + 1
        nb_cell = {"cell_type": cell["cell_type"], "id": f"{section}-{counts[section]}",
                   "metadata": dict(cell["metadata"]), "source": cell["source"].splitlines(keepends=True)}
        if cell["cell_type"] == "code":
            nb_cell.update(execution_count=None, outputs=[])
        out.append(nb_cell)
    return {"cells": out, "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"colab": {"name": f"{name}.ipynb", "provenance": [], "toc_visible": True},
                         "kernelspec": {"display_name": "Python 3", "name": "python3"},
                         "language_info": {"name": "python"}}}


# ───────────────────────── the shared setup cell ─────────────────────────
SETUP = r'''
#@title ⚙️ Setup: install MEIDNet and load the helpers (run this cell first)
#@markdown In Colab this installs MEIDNet (PyTorch for CPU is enough), chemiscope and ASE, then defines the helpers that every block uses: charts in the block colours, 3D views and report display. It takes about a minute the first time.
import os
import sys

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    !pip -q install torch --index-url https://download.pytorch.org/whl/cpu
    !pip -q install git+https://github.com/ABnano/MEIDNet.git chemiscope ase
    from google.colab import output as colab_output
    colab_output.enable_custom_widget_manager()       # chemiscope's 3D viewer is a notebook widget
    from importlib.metadata import version as _installed
    if "numpy" in sys.modules and sys.modules["numpy"].__version__ != _installed("numpy"):
        print("pip updated numpy: choose Runtime -> Restart session, then run this cell again.")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import HTML, display
try:
    import meidnet
except ImportError:
    raise ImportError("MEIDNet is not installed in this Python: "
                      "pip install git+https://github.com/ABnano/MEIDNet.git chemiscope ase") from None

# one colour per block, as in MEIDNet Studio; ink and paper of the charts
BLOCK = {"data": "#2a78d6", "model": "#eb6834", "family": "#1baf7a", "rules": "#eda100",
         "targets": "#e87ba4", "search": "#008300", "candidates": "#4a3aa7"}
INK, INK2, MUTED, GRID, AXIS, PAPER, REST = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#d3d2cb"
for _key, _value in {
        "figure.figsize": (6.4, 3.6), "figure.dpi": 110, "figure.facecolor": PAPER, "savefig.facecolor": PAPER,
        "axes.facecolor": PAPER, "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID,
        "grid.linewidth": 0.8, "grid.linestyle": "-", "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.titlecolor": INK, "axes.labelcolor": INK2, "axes.labelsize": 10,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2,
        "lines.solid_capstyle": "round"}.items():
    try:
        plt.rcParams[_key] = _value
    except (KeyError, ValueError):                    # an older matplotlib: keep its default
        pass


def print_flow(to, *items):
    """The last line of a block: what it hands on to the next block."""
    print(f"-> {to}: " + "; ".join(str(i) for i in items))


# ── charts: one axis each, block colours for the data, plain-word titles and labels ──
def _finish(fig, ax, title, xlabel, ylabel, subtitle=None):
    ax.set_title(title, pad=22 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=9, color=INK2)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    plt.show()


def _window_text(lo, hi):
    if lo is not None and hi is not None:
        return f"{lo:g} to {hi:g}"
    return f"at least {lo:g}" if lo is not None else f"at most {hi:g}"


def hist_prop(values, label, unit="", colour=BLOCK["data"], target=None, window=None, bins=40, title=None,
              ylabel="count"):
    """Histogram in a block colour, with an optional target line and allowed window (min, max)."""
    v = pd.to_numeric(pd.Series(list(values), dtype="object"), errors="coerce").astype(float)
    v = v[np.isfinite(v)]
    if v.empty:
        print(f"(no values to plot for {label})")
        return
    fig, ax = plt.subplots()
    ax.hist(v, bins=bins, color=colour, edgecolor=PAPER, linewidth=0.8)
    if window is not None:
        lo, hi = window
        x0, x1 = ax.get_xlim()
        a, b = (x0 if lo is None else lo), (x1 if hi is None else hi)
        ax.axvspan(a, b, color=colour, alpha=0.14, lw=0, zorder=0, label=f"allowed: {_window_text(lo, hi)}")
        ax.set_xlim(min(x0, a), max(x1, b))
    if target is not None:
        ax.axvline(target, color=INK, lw=1.5, label=f"target: {target:g} {unit}".strip())
    if window is not None or target is not None:
        ax.legend(loc="best")
    unit_text = f" [{unit}]" if unit else ""
    stats = f"{len(v):,} values, median {np.median(v):.3g}{' ' + unit if unit else ''}"
    _finish(fig, ax, title or label, f"{label}{unit_text}", ylabel, subtitle=stats)


def funnel_plot(stages, colour=BLOCK["rules"], title="Compositions still allowed after each rule"):
    """Horizontal bars: how many compositions survive each rule, applied in order (stages: [(label, count)])."""
    labels, counts = [str(s[0]) for s in stages], [int(s[1]) for s in stages]
    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(stages) + 1.2))
    y = np.arange(len(stages))[::-1]
    ax.barh(y, counts, height=0.6, color=colour, edgecolor=PAPER, linewidth=0.8)
    top = max(counts) or 1
    for yi, c in zip(y, counts):
        ax.text(c + 0.01 * top, yi, f"{c:,}", va="center", ha="left", color=INK2, fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, top * 1.15)
    ax.grid(axis="y", visible=False)
    _finish(fig, ax, title, "compositions still allowed", "")


def parity_plot(true, pred, label, unit="", colour=BLOCK["model"]):
    """Predicted against true values; points on the grey diagonal are perfect predictions."""
    t, p = np.asarray(true, dtype=float), np.asarray(pred, dtype=float)
    mae = float(np.mean(np.abs(p - t)))
    ss = float(np.sum((t - t.mean()) ** 2))
    r2 = 1 - float(np.sum((p - t) ** 2)) / ss if ss > 0 else float("nan")
    lo, hi = float(min(t.min(), p.min())), float(max(t.max(), p.max()))
    pad = 0.05 * ((hi - lo) or 1.0)
    fig, ax = plt.subplots(figsize=(4.8, 4.6))
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color=AXIS, lw=1, zorder=1)
    ax.scatter(t, p, s=28, color=colour, edgecolor=PAPER, linewidth=0.8, zorder=2)
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_aspect("equal", adjustable="box")
    u = f" [{unit}]" if unit else ""
    _finish(fig, ax, f"{label}: predicted vs true", f"true {label}{u}", f"predicted {label}{u}",
            subtitle=f"mean error {mae:.3g}{' ' + unit if unit else ''}, R² {r2:.2f}, {len(t):,} materials")


def loss_curves(ckpt, colour=BLOCK["model"]):
    """Training loss and validation error per epoch, from the history saved in a MEIDNet checkpoint."""
    import torch
    saved = torch.load(ckpt, map_location="cpu", weights_only=False)
    history = saved.get("history") if isinstance(saved, dict) else None
    if not history or not history.get("train"):
        print("this checkpoint stores no training history (the published v1 model does not)")
        return
    from matplotlib.ticker import MaxNLocator
    train_log, val_log = history["train"], history.get("val") or []
    dots = dict(marker="o", ms=5, mec=PAPER, mew=1)
    losses = [r["total"] for r in train_log]
    fig, ax = plt.subplots()
    ax.plot([r["epoch"] for r in train_log], losses, color=colour, **(dots if len(train_log) <= 30 else {}))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    wide = min(losses) > 0 and max(losses) / min(losses) > 20          # a log axis only when it helps
    if wide:
        ax.set_yscale("log")
    _finish(fig, ax, "Training loss (lower is better)", "epoch", "loss (log scale)" if wide else "loss",
            subtitle=f"{len(train_log)} epochs, last value {losses[-1]:.3g}")
    units = {p["column"]: p.get("unit", "") for p in saved.get("properties", [])}
    for prop in (val_log[-1]["mae"] if val_log else {}):
        fig, ax = plt.subplots()
        ax.plot([r["epoch"] for r in val_log], [r["mae"][prop] for r in val_log], color=colour,
                **(dots if len(val_log) <= 30 else {}))
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        u = units.get(prop, "")
        _finish(fig, ax, f"Validation error of {prop} (lower is better)", "epoch",
                f"mean absolute error{' [' + u + ']' if u else ''}",
                subtitle=f"last value {val_log[-1]['mae'][prop]:.3g}{' ' + u if u else ''}")


def space_scatter(table, x, y, colour=BLOCK["targets"], target=None, highlight=None,
                  highlight_label="closest to the target", xlabel=None, ylabel=None,
                  title="Every composition, as the model predicts it"):
    """Compositions that pass every rule in the block colour, the rejected ones in grey, the target as a cross."""
    ok = table["passes_all"].astype(bool)
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    ax.scatter(table.loc[~ok, x], table.loc[~ok, y], s=12, color=REST, lw=0,
               label=f"rejected by a rule ({int((~ok).sum()):,})")
    ax.scatter(table.loc[ok, x], table.loc[ok, y], s=30, color=colour, edgecolor=PAPER, lw=0.8,
               label=f"passes every rule ({int(ok.sum()):,})")
    if highlight is not None and len(highlight):
        ax.scatter(highlight[x], highlight[y], s=90, facecolor="none", edgecolor=INK, lw=1.2,
                   label=f"{highlight_label} ({len(highlight)})")
        first = highlight.iloc[0]
        ax.annotate(first["formula"], (first[x], first[y]), xytext=(7, 7), textcoords="offset points",
                    fontsize=9, color=INK)
    if target is not None:
        tx, ty = target
        if ty is None:
            ax.axvline(tx, color=INK, lw=1.5, label="target")
        else:
            ax.scatter([tx], [ty], marker="+", s=220, color=INK, lw=2, zorder=5, label="target")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0)
    _finish(fig, ax, title, xlabel or x, ylabel or y)


# ── 3D: chemiscope (G. Fraux, R. K. Cersonsky, M. Ceriotti, JOSS 5, 2117, 2020) ──
def _as_structure(item):
    """A pymatgen Structure from a Structure, a chemiscope structure dict or an ase.Atoms."""
    from pymatgen.core import Lattice, Structure
    if isinstance(item, Structure):
        return item
    if isinstance(item, dict):
        xyz = np.column_stack([item["x"], item["y"], item["z"]])
        return Structure(Lattice(np.reshape(item["cell"], (3, 3))), item["names"], xyz, coords_are_cartesian=True)
    from pymatgen.io.ase import AseAtomsAdaptor
    return AseAtomsAdaptor.get_structure(item)


def _num(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return 0.0
    return f if np.isfinite(f) else 0.0


def _chemiscope_property(name, value, n):
    prop = dict(value) if isinstance(value, dict) else {"values": value}
    values = list(prop["values"])
    if len(values) != n:
        raise ValueError(f"property '{name}' has {len(values)} values for {n} structures")
    if not all(isinstance(x, str) for x in values):
        values = [_num(x) for x in values]          # one type per property, finite numbers only
    out = {"target": prop.get("target", "structure"), "values": values}
    for key in ("units", "description"):
        if prop.get(key):
            out[key] = str(prop[key])
    return out


def show3d(structures, properties=None, settings=None):
    """
    Structures in 3D next to a map of their properties, with chemiscope (G. Fraux, R. K. Cersonsky,
    M. Ceriotti, JOSS 5, 2117, 2020). Click a point of the map to see its crystal. Without chemiscope
    a small table (formula, a, space group) is printed instead.
    """
    structs = [_as_structure(s) for s in structures]
    if not structs:
        print("(no structures to show)")
        return
    props = {name: _chemiscope_property(name, v, len(structs)) for name, v in (properties or {}).items()}
    if sum(not isinstance(p["values"][0], str) for p in props.values()) < 2:     # the map needs two numbers
        props.setdefault("a", {"target": "structure", "values": [round(s.lattice.a, 4) for s in structs],
                               "units": "Å", "description": "cell edge a"})
        props.setdefault("volume_per_atom", {"target": "structure", "units": "Å^3",
                                             "values": [round(s.volume / len(s), 4) for s in structs],
                                             "description": "cell volume per atom"})
    try:
        import chemiscope
        from pymatgen.io.ase import AseAtomsAdaptor
        atoms = [AseAtomsAdaptor.get_atoms(s) for s in structs]
        display(chemiscope.show(atoms, properties=props, settings=settings))
    except Exception as err:                          # no chemiscope (or no widget support): a small table
        print(f"(3D view not available here: {type(err).__name__}: {err})")
        rows = []
        for s in structs[:12]:
            try:
                group = s.get_space_group_info(symprec=0.1)[0]
            except Exception:
                group = "?"
            rows.append({"formula": s.composition.reduced_formula, "a (Å)": round(s.lattice.a, 3),
                         "space group": group})
        print(pd.DataFrame(rows).to_string(index=False))
        if len(structs) > 12:
            print(f"... and {len(structs) - 12} more")


def show_dataset(dataset):
    """Show a chemiscope dataset made by MEIDNet (meidnet.studio.chemiscope or Studio.chemiscope) with show3d."""
    if not dataset.get("structures"):
        print(dataset.get("note", "nothing to show yet"))
        return
    print(f"{dataset['meta']['name']}: {dataset['meta']['description']}")
    show3d(dataset["structures"], dataset.get("properties"), dataset.get("settings"))


# ── tables ──
def space_table(space):
    """meidnet.designspace.enumerate_space(...) as a table: one row per composition, a column per rule."""
    rules = [r["name"] for r in space["rules"]]
    rows = []
    for r in space["rows"]:
        row = {"formula": r["f"], **{f"site_{g}": e for g, e in r["e"].items()}, "a": r["a"]}
        for name in rules:
            row[name] = r["d"].get(name)
            row[f"ok_{name}"] = bool(r["ok"].get(name, True))
        row["passes_all"] = bool(all(r["ok"].values()))
        row.update({f"pred_{c}": v for c, v in r["p"].items()})
        rows.append(row)
    return pd.DataFrame(rows)


def rule_window(params):
    """The allowed (min, max) of a rule from its parameters, or None for a pass/fail rule."""
    lo, hi = params.get("min", params.get("low")), params.get("max", params.get("high"))
    return None if lo is None and hi is None else (lo, hi)


def measured(rule):
    """(what a rule measures, unit), in plain words, for axis labels; other rules fall back to their title."""
    p = rule["params"]
    known = {"min_distance": ("closest distance between two atoms", "Å"),
             "bond_window": (f"nearest {p.get('to', 'B')}–{p.get('from', 'X')} distance ÷ sum of ionic radii", ""),
             "tolerance_factor": ("tolerance factor t", ""),
             "octahedral_factor": ("octahedral factor μ = r_B / r_X", "")}
    return known.get(rule.get("rule", rule["name"]), (rule["title"], ""))


def funnel_stages(table, rules):
    """[(label, count)]: compositions still allowed after each rule, in the family's order."""
    alive = pd.Series(True, index=table.index)
    stages = [("all compositions", len(table))]
    for rule in rules:
        alive &= table[f"ok_{rule['name']}"].astype(bool)
        stages.append((rule["title"], int(alive.sum())))
    return stages


def rank_by_target(table, target, objectives):
    """Sort compositions by the score the search ranks its candidates with (0 = exactly on target)."""
    from meidnet.generate import objective_distance
    score = np.zeros(len(table))
    for o in objectives:
        o = o if isinstance(o, dict) else o.model_dump()
        loss = o.get("select_loss") or o.get("loss", "l2")
        score += o.get("select_weight", 1.0) * np.array(
            [objective_distance(float(v), float(target[o["property"]]), loss) for v in table[f"pred_{o['property']}"]])
    return table.assign(score=score).sort_values("score")


def candidates_table(candidates):
    """One row per saved candidate: where it was found, its predictions and every rule (✓ + measured value)."""
    rows = []
    for c in candidates:
        c = c if isinstance(c, dict) else c.to_dict()
        row = {"formula": c["formula"], "target": c.get("target_index", 1), "round": c["round"],
               "a (Å)": round(c["lattice_a"], 3)}
        row.update({f"predicted {k}": round(v, 3) for k, v in c["predictions"].items()})
        for r in c["constraint_results"]:
            value = r.get("value")
            shown = f" {value:.3g}" if value is not None and r["name"] != "charge_neutrality" else ""
            row[r["name"]] = ("✓" if r["passed"] else "✗") + shown
        row["warnings"] = "; ".join(c.get("flags") or [])
        rows.append(row)
    return pd.DataFrame(rows)


# ── model helpers ──
def predict_records(lm, records):
    """True and predicted (structure -> properties) values for records read by meidnet.pipeline.check."""
    import torch
    x = torch.tensor(np.stack([r.dense for r in records]), dtype=torch.float32, device=lm.device)
    with torch.no_grad():
        z, _ = lm.model.encode_crystal(x)
        predicted = lm.stats.denormalize_tensor(lm.model.property_decoder(z)).cpu().numpy()
    return np.stack([r.properties for r in records]), predicted


def validation_records(cfg):
    """The materials that training held out (the same split as `meidnet train`), for an honest parity plot."""
    from meidnet.data import split_records
    from meidnet.pipeline import check
    info = check(cfg, write_report=False)
    held_out = info["val_records"] or split_records(info["records"], cfg.data.val_fraction, cfg.training.seed)[1]
    if not held_out:
        print("too few materials for a validation split: showing the training materials instead")
        held_out = info["records"]
    return held_out


def show_report(path, height=900):
    """Show one of MEIDNet's HTML reports (check, training, generation) inside the notebook."""
    import html as _html
    with open(path, encoding="utf-8") as f:
        page = f.read()
    if IN_COLAB:                                      # Colab gives every output its own frame
        display(HTML(page))
    else:                                             # elsewhere: a frame keeps the report's style to itself
        display(HTML(f'<iframe srcdoc="{_html.escape(page)}" style="width:100%;height:{height}px;'
                     f'border:1px solid {GRID};border-radius:8px"></iframe>'))
    print("report file:", os.path.abspath(path))


print(f"MEIDNet {meidnet.__version__} is ready" + (" in Colab" if IN_COLAB else ""))
'''


def setup_cell() -> dict:
    return form_cell(SETUP)


# ───────────────────────── blocks shared by notebooks 01 and 03 (published model) ─────────────────────────
def published_model_block() -> list[dict]:
    return [
        block_header("model"),
        md("The model is two encoders trained together. One turns a crystal into a point of a 128-number "
           "*latent space*; the other turns property values into a point of the **same** space. After training, "
           "a property target points to the region where crystals with those properties live.\n\n"
           "The published checkpoint (2.8 MB) is downloaded once. The table shows the range of each property in "
           "its training data: targets outside it are *extrapolation*, and the report will say so."),
        code(r'''
from meidnet.cli import published_checkpoint
from meidnet.checkpoint import describe, load_checkpoint, property_ranges
ckpt = published_checkpoint()                 # downloads the published model to ~/.meidnet the first time
lm = load_checkpoint(ckpt)
print(describe(lm))
ranges = property_ranges(lm)                  # what the model saw in training, per property
display(pd.DataFrame([{"property": label, "column": col, "unit": unit, "lowest seen": ranges[col][0],
                       "highest seen": ranges[col][1]}
                      for col, label, unit in zip(lm.stats.columns, lm.stats.labels, lm.stats.units)]))
print_flow("Family", f"a model that predicts {' and '.join(l.lower() for l in lm.stats.labels)} from a structure")
'''),
    ]


def published_targets_block() -> list[dict]:
    return [
        block_header("targets"),
        md("A **target** is the property value you want. The model has already predicted both properties of every "
           "composition (structure → properties takes a split second), so the compositions that pass every rule "
           "can be ranked by how close they come to your target, before any search. The score is the one the "
           "search uses to rank its candidates: the band-gap distance squared plus 0.4 × the enthalpy distance "
           "(0 = exactly on target)."),
        form_cell(r'''
#@title Set your targets
band_gap = 2.0    #@param {type:"number"}
enthalpy = -0.10  #@param {type:"number"}
#@markdown Band gap in eV; formation enthalpy in eV/atom (lower = more stable).
'''),
        code(r'''
OBJECTIVES = [{"property": "dir_gap", "loss": "l2", "weight": 10000, "select_weight": 1.0},
              {"property": "heat_all", "loss": "l1", "weight": 6000, "select_weight": 0.4}]
target = {"dir_gap": band_gap, "heat_all": enthalpy}
for col, value in target.items():
    lo, hi = ranges[col]
    if not lo <= value <= hi:
        print(f"note: {col} = {value} lies outside the training range {lo} to {hi}: the model would be extrapolating")
allowed = table_search[table_search["passes_all"]]
if allowed.empty:
    print("No composition passes every rule: widen a window in the Rules block or choose another variant.")
top10 = rank_by_target(allowed, target, OBJECTIVES).head(10)
sites = [c for c in table_search.columns if c.startswith("site_")]
display(top10[["formula", *sites, "pred_dir_gap", "pred_heat_all", "score"]].round(3).reset_index(drop=True))
space_scatter(table_search, "pred_dir_gap", "pred_heat_all", colour=BLOCK["targets"], target=(band_gap, enthalpy),
              highlight=top10, xlabel="predicted band gap [eV]", ylabel="predicted formation enthalpy [eV/atom]")
hist_prop(allowed["pred_dir_gap"], "predicted band gap", "eV", colour=BLOCK["targets"], target=band_gap,
          title="Predicted band gap of the allowed compositions", ylabel="compositions")
'''),
        md("The same design space in 3D (chemiscope): one point per composition on the ideal prototype, coloured by "
           "whether it passes every rule. Click a point to see its crystal."),
        code(r'''
from meidnet.studio.chemiscope import space_dataset
show_dataset(space_dataset(fam_search, space_search, lm))
best = top10["formula"].iloc[0] if len(top10) else "none"
print_flow("Search", f"target band gap {band_gap} eV and enthalpy {enthalpy} eV/atom "
                     f"(closest allowed composition: {best})")
'''),
    ]


SEARCH_PRINTERS = r'''
names = dict(zip(lm.stats.columns, lm.stats.labels))
units = dict(zip(lm.stats.columns, lm.stats.units))

def on_saved(candidate, target_log):          # called by the search for every candidate it saves
    preds = ", ".join(f"{names[k].lower()} {v:.3g} {units[k]}".strip() for k, v in candidate.predictions.items())
    print(f"  found {candidate.formula:<10} {preds}   (round {candidate.round})")

def progress(*parts):                         # the search's own progress lines, without repeating the finds
    line = " ".join(str(p) for p in parts).strip("\n")
    if not line.strip().startswith("saved"):
        print(line)
'''


def search_intro() -> dict:
    return md("The ranking above only scores compositions of the prototype. The **search** of the paper works the "
              "other way round: it starts from the point of the latent space your targets map to, moves through the "
              "space by gradient descent, decodes crystals on the way and keeps the ones that pass every rule. "
              "Each candidate is printed as soon as it is saved. The budget below is small so that it runs on a CPU "
              "in about a minute; raise it for a real study.")


SEARCH_FORM = r'''
#@title Search budget
n_candidates = 3  #@param {type:"integer"}
rounds = 3        #@param {type:"integer"}
steps = 300       #@param {type:"integer"}
#@markdown A round moves 24 latent points for *steps* gradient steps; the search stops after *rounds* rounds or once *n_candidates* candidates are saved.
'''


def published_search_block(run: str) -> list[dict]:
    return [
        block_header("search"),
        search_intro(),
        form_cell(SEARCH_FORM),
        code((r'''
from meidnet.config import GenerationSection
from meidnet.generate import Designer
gen = GenerationSection(family=family_name, variant=variant, objectives=OBJECTIVES, targets=[target],
                        per_target=n_candidates, population=24, rounds=rounds, steps=steps,
                        min_cosine_sep=0.98, overrides=overrides)
run_dir = "runs/__RUN__"
''' + SEARCH_PRINTERS + r'''
res = Designer(lm, fam_search, gen, log=progress, on_saved=on_saved).run(os.path.join(run_dir, "generation"),
                                                                         ranges=property_ranges(lm))
print_flow("Candidates", f"{len(res.saved)} candidate(s), written to {run_dir}/generation/")
''').replace("__RUN__", run)),
    ]


CANDIDATES_TABLE_3D = r'''
display(candidates_table(res.saved))
from pymatgen.core import Structure
found = [Structure.from_file(os.path.join(res.out_dir, c.file)) for c in res.saved]
if found:
    show3d(found, properties={"formula": [c.formula for c in res.saved],
                              **{f"pred_{k}": {"values": [c.predictions[k] for c in res.saved], "units": units[k]}
                                 for k in lm.stats.columns},
                              "score": [c.score for c in res.saved]})
else:
    print("No candidate this time: try more rounds, another target, or a wider window in the Rules block.")
'''

CANDIDATES_INTRO = ("Every saved candidate passed every rule. The report explains each one: its elements and cell, the "
                    "measured value of every rule, and the predicted properties next to your target, plus a *funnel* "
                    "that shows where the search lost its attempts. Predicted values are the model's estimates: "
                    "confirm promising candidates with DFT or experiment.")


def published_candidates_block(run: str, plugins: str, note: str = "") -> list[dict]:
    return [
        block_header("candidates"),
        md(CANDIDATES_INTRO + (f"\n\n{note}" if note else "")),
        code(r'''
from meidnet.config import config_from_dict, dump_config
from meidnet.report import generation_report
cfg = config_from_dict({"name": "__RUN__", "output_dir": run_dir, "model_path": os.path.abspath(ckpt),
                        "plugins": __PLUGINS__, "generation": gen.model_dump()}, base_dir=os.getcwd())
with open("__RUN__.yaml", "w", encoding="utf-8") as f:
    f.write(dump_config(cfg))                 # the same search from a terminal: meidnet generate __RUN__.yaml
report = generation_report(cfg, lm, fam_search, res, os.path.join(run_dir, "generation_report.html"))
show_report(report)
'''.replace("__RUN__", run).replace("__PLUGINS__", plugins)),
        md("The candidates as a table (✓ = the rule passed, with its measured value) and in 3D, from the CIF "
           "files the search wrote."),
        code(CANDIDATES_TABLE_3D + r'''
print_flow("Next steps", f"{len(found)} CIF file(s), candidates.csv and generation_report.html in {run_dir}/")
'''),
    ]


def after_blocks(cell: dict) -> dict:
    """A cell after the seven blocks (stopping a server, where to go next): its own section, not Candidates."""
    cell["_section"] = "end"
    return cell


def next_steps(*lines: str) -> dict:
    return after_blocks(md("## Where to go next\n" + "\n".join(f"* {line}" for line in lines) + f"\n\n{CREDITS}"))


# ───────────────────────── 01 quickstart ─────────────────────────
def quickstart() -> list[dict]:
    return [
        title_cell(
            "MEIDNet quickstart: from a band-gap target to new perovskites", "01_quickstart.ipynb",
            "MEIDNet learns one shared map (a *latent space*) of crystal **structures** and their **properties**, "
            "then walks it backwards: you ask for a property value and it proposes crystals that should have it "
            "and that obey simple chemistry rules.\n\n"
            "This notebook uses the **published model** and runs on a normal CPU in about five minutes. It follows "
            "the seven blocks of MEIDNet Studio, in the same order and colours. Every block ends with a line such as "
            "`-> Rules: 924 compositions` that says what it hands on to the next block."),
        setup_cell(),

        block_header("data"),
        md("The published model learned from **Perov-5**: 11,356 cubic perovskites whose band gap and formation "
           "enthalpy were computed with DFT (Castelli et al. 2012, in the split used by CDVAE, Xie et al. 2022). "
           "Download it and look at what the model has seen: it can only design well for values that appear here."),
        code(r'''
!meidnet download-data
perov5 = pd.read_csv("data/perov5/train.csv")
print(f"{len(perov5):,} training materials; columns: {', '.join(perov5.columns[1:])}")
gap = perov5["dir_gap"]
print(f"{(gap == 0).mean():.0%} of them are metals (band gap 0 eV); the first chart shows the other {(gap > 0).sum():,}")
hist_prop(gap[gap > 0], "direct band gap", "eV", colour=BLOCK["data"], ylabel="materials",
          title="Band gap of the Perov-5 semiconductors (gap above 0)")
hist_prop(perov5["heat_all"], "formation enthalpy", "eV/atom", colour=BLOCK["data"], ylabel="materials",
          title="Formation enthalpy of all Perov-5 materials")
'''),
        md("Every row also holds the crystal structure, as CIF text. Here are 150 of them in 3D with chemiscope: "
           "click a point of the map to see its crystal. (Without chemiscope a short table is printed instead.)"),
        code(r'''
from meidnet.data import parse_structure
sample = perov5.sample(150, random_state=0)
structures = [parse_structure(cif_text=cif) for cif in sample["cif"]]
show3d(structures,
       properties={"formula": [s.composition.reduced_formula for s in structures],
                   "dir_gap": {"values": sample["dir_gap"].tolist(), "units": "eV",
                               "description": "direct band gap (DFT)"},
                   "heat_all": {"values": sample["heat_all"].tolist(), "units": "eV/atom",
                                "description": "formation enthalpy (DFT)"}},
       settings={"map": {"x": {"property": "heat_all"}, "y": {"property": "dir_gap"},
                         "color": {"property": "dir_gap"}}})
print_flow("Model", f"{len(perov5):,} crystal structures, each with a band gap and a formation enthalpy")
'''),

        *published_model_block(),

        block_header("family"),
        md("A **family** is a crystal type: a prototype cell with fixed sites and, for each site, the elements "
           "allowed there with their charges. Everything MEIDNet can generate is one way to fill these sites. The "
           "built-in cubic perovskite ABX₃ family (five atoms: A on the corner, B in the centre, three X on the "
           "faces) has four *variants*, one per kind of anion on the X sites."),
        form_cell(r'''
#@title Choose the variant
variant = "halide"  #@param ["halide", "oxide", "chalcogenide", "nitride"]
'''),
        code(r'''
from meidnet.family import load_family
from meidnet.designspace import total_compositions
from meidnet.constraints import build_candidate
family_name = "perovskite_abx3"
fam = load_family(family_name, variant=variant)
print(fam.describe())
display(pd.DataFrame([{"site group": g, "atoms per cell": len(grp.slots), "elements allowed": " ".join(grp.sample)}
                      for g, grp in fam.groups.items()]))
EXAMPLES = {"halide": {"A": "Cs", "B": "Pb", "X": "I"}, "oxide": {"A": "Sr", "B": "Ti", "X": "O"},
            "chalcogenide": {"A": "Ba", "B": "Zr", "X": "S"}, "nitride": {"A": "La", "B": "W", "X": "N"}}
example = build_candidate(fam, EXAMPLES[variant])
print(f"\nOne way to fill the prototype: {example.formula()}, cell edge a = {example.lattice_a:.2f} Å")
show3d([example.raw], properties={"formula": [example.formula()]})
print_flow("Rules", f"{total_compositions(fam):,} compositions (every way to fill the sites)")
'''),

        block_header("rules"),
        md("Rules are simple chemistry checks that every candidate must pass, in order: atoms must not overlap, "
           "charges must balance, bonds must be sensible, and the ions must fit the perovskite cage (tolerance and "
           "octahedral factors). Each rule measures one number and compares it with an allowed window. MEIDNet now "
           "checks **every** composition of the family, and the model predicts the properties of each one."),
        code(r'''
from meidnet.designspace import enumerate_space
space = enumerate_space(fam, lm)              # every composition: the value of each rule + predicted properties
table = space_table(space)
for rule in space["rules"]:
    print(f"- {rule['title']}: {rule['text']}")
n_pass = int(table["passes_all"].sum())
print(f"\n{n_pass:,} of {len(table):,} compositions pass every rule")
for rule in space["rules"]:
    window = rule_window(rule["params"])
    if window and table[rule["name"]].notna().any():
        label, unit = measured(rule)
        hist_prop(table[rule["name"]], label, unit, colour=BLOCK["rules"], window=window, title=rule["title"],
                  ylabel="compositions")
funnel_plot(funnel_stages(table, space["rules"]), colour=BLOCK["rules"])
'''),
        md("**Try it:** move the tolerance-factor window. A narrower window keeps only ions that fit the cage well. "
           "The count is recomputed by the same Python functions that accept or reject candidates during the "
           "search. Tick *use_for_search* to carry your window into the next blocks."),
        form_cell(r'''
#@title Change the tolerance-factor window
t_min = 0.80           #@param {type:"slider", min:0.6, max:1.0, step:0.01}
t_max = 1.00           #@param {type:"slider", min:0.9, max:1.2, step:0.01}
use_for_search = True  #@param {type:"boolean"}
'''),
        code(r'''
default = fam.constraint_params("tolerance_factor")
window_overrides = {"tolerance_factor": {"min": t_min, "max": t_max}}
fam_new = load_family(family_name, variant=variant, overrides=window_overrides)
table_new = space_table(enumerate_space(fam_new))         # the rules only: no predictions needed to count
print(f"family window {default['min']} to {default['max']}: {n_pass:,} compositions pass every rule")
print(f"your window   {t_min} to {t_max}: {int(table_new['passes_all'].sum()):,} compositions pass every rule")
hist_prop(table_new["tolerance_factor"], "tolerance factor t", colour=BLOCK["rules"], window=(t_min, t_max),
          title="Goldschmidt tolerance factor, your window", ylabel="compositions")
if use_for_search:
    fam_search, overrides, space_search = fam_new, window_overrides, enumerate_space(fam_new, lm)
else:
    fam_search, overrides, space_search = fam, {}, space
table_search = space_table(space_search)
print_flow("Targets", f"{int(table_search['passes_all'].sum()):,} of {len(table_search):,} compositions pass every rule")
'''),

        *published_targets_block(),
        *published_search_block("quickstart"),
        *published_candidates_block("quickstart", "[]"),

        next_steps("**02**: the same seven blocks with *your* table of structures and properties, and your own model.",
                   "**03**: write your own rule in a few lines and watch it work in every block.",
                   "**04**: MEIDNet Studio inside Colab, the interactive page with the seven blocks side by side.",
                   f"On your computer: `pip install meidnet`, then `meidnet studio`. Documentation: {DOCS_URL}"),
    ]


# ───────────────────────── 02 your own data ─────────────────────────
def your_own_data() -> list[dict]:
    return [
        title_cell(
            "MEIDNet on your own data", "02_your_own_data.ipynb",
            "Bring a **table** (CSV or Excel) with one row per material: an id column, one or more numeric property "
            "columns, and the crystal structure of each row, either as CIF text in a column or as a zip of "
            "`<id>.cif` files. MEIDNet checks the data, trains a model on it and designs new materials for your "
            "targets, block by block as in MEIDNet Studio.\n\n"
            "No data at hand? Tick **use_example** in the first form and 600 rows of Perov-5 are used instead. "
            "Training is faster on a GPU (*Runtime → Change runtime type → GPU*), but a CPU is fine for a first try "
            "with a few epochs."),
        setup_cell(),

        block_header("data"),
        md("MEIDNet reads every row exactly as training will, and tells you which rows it can use and why the "
           "others were skipped. Each structure is also *aligned* to the family's prototype (atom *i* on site *i*), "
           "which generation needs."),
        form_cell(r'''
#@title Your data
use_example = False  #@param {type:"boolean"}
#@markdown Untick to upload your own table (and, if you have one, a .zip of `<id>.cif` files) when the next cell runs; tick to use 600 rows of Perov-5.
'''),
        code(r'''
import re
import zipfile
from meidnet.data import read_table
if use_example:
    !meidnet download-data
    pd.read_csv("data/perov5/train.csv").head(600).to_csv("example_materials.csv", index=False)
    table_file = "example_materials.csv"
elif IN_COLAB:
    from google.colab import files
    uploaded = files.upload()                 # choose your table, plus a .zip of CIF files if you have one
    for name in uploaded:
        if name.lower().endswith(".zip"):
            os.makedirs("structures", exist_ok=True)
            with zipfile.ZipFile(name) as z:
                for member in z.namelist():
                    if member.lower().endswith(".cif"):
                        with open(os.path.join("structures", os.path.basename(member)), "wb") as out:
                            out.write(z.read(member))
            print(len(os.listdir("structures")), "CIF files in structures/")
    table_file = next((n for n in uploaded if n.lower().endswith((".csv", ".xlsx", ".xls", ".json"))), None)
    if table_file is None:
        raise ValueError("Please upload a table (.csv or .xlsx) with one row per material.")
else:
    table_file = "materials.csv"              # outside Colab: put your table next to this notebook
df = read_table(table_file)
print(f"{table_file}: {len(df):,} rows; columns: {', '.join(map(str, df.columns))}")
display(df.head())
'''),
        form_cell(r'''
#@title Describe your table
id_column = "material_id"        #@param {type:"string"}
cif_column = "cif"               #@param {type:"string"}
properties = "heat_all dir_gap"  #@param {type:"string"}
family = "perovskite_abx3"       #@param ["perovskite_abx3", "double_perovskite_a2bbx6"]
variant = "halide"               #@param ["halide", "oxide", "chalcogenide", "nitride"] {allow-input: true}
prototype_tolerance = 0.15       #@param {type:"number"}
#@markdown **properties**: the numeric columns to learn, separated by spaces. **cif_column**: the column with the CIF text (not used when you uploaded a zip of CIF files). **variant**: halide, oxide, chalcogenide or nitride for ABX₃; halide or oxide for A₂BB′X₆. **prototype_tolerance**: how far (as a fraction of a cell edge) an atom may sit from its ideal site; raise it to accept distorted structures.
'''),
        code(r'''
init_args = (f'--name mine --table "{table_file}" --id-column {id_column} --cif-column {cif_column or "cif"} '
             f'--properties {properties} --family {family}' + (f" --variant {variant}" if variant.strip() else ""))
!meidnet init {init_args} --force
text = open("meidnet.yaml", encoding="utf-8").read()
if os.path.isdir("structures") and not use_example:      # the structures come from the zip of CIF files
    text = re.sub(r"(?m)^  cif_column: .*$", "  cif_column: null\n  structures_dir: structures", text)
text = re.sub(r"(?m)^(  align_to_prototype: .*)$", rf"\1\n  prototype_tolerance: {prototype_tolerance}", text)
with open("meidnet.yaml", "w", encoding="utf-8") as f:
    f.write(text)

from meidnet.config import load_config
from meidnet.pipeline import check
cfg = load_config("meidnet.yaml")
info = check(cfg, keep_structures=True)       # reads every row as training will; writes check_report.html
rep, records = info["report"], info["records"]
print(f"\n{rep.kept:,} of {rep.rows:,} rows are usable ({rep.aligned:,} aligned to the {cfg.family_name} prototype)")
if rep.skipped:
    display(pd.DataFrame([{"skipped because": reason, "rows": n, "for example": ", ".join(rep.examples.get(reason, []))}
                          for reason, n in rep.skipped.most_common()]))
for j, p in enumerate(cfg.data.properties):
    hist_prop([r.properties[j] for r in records], p.display, p.unit, colour=BLOCK["data"], ylabel="materials",
              title=f"{p.display} in your usable data")
'''),
        md("Your usable structures in 3D, after alignment to the prototype (chemiscope; up to 300 shown)."),
        code(r'''
shown = records[:300]
if shown:
    show3d([r.structure for r in shown],
           properties={"formula": [r.formula for r in shown], "material_id": [r.material_id for r in shown],
                       **{p.column: {"values": [float(r.properties[j]) for r in shown], "units": p.unit}
                          for j, p in enumerate(cfg.data.properties)}})
print_flow("Model", f"{rep.kept:,} usable materials with {len(cfg.data.properties)} properties "
                    f"({', '.join(p.column for p in cfg.data.properties)})")
'''),

        block_header("model"),
        md("Training teaches the two encoders to meet in one latent space: the crystal of each material and its "
           "property values must land on the same point. Start with a few epochs to see the whole pipeline work, "
           "then raise *epochs* (200 is typical). The training report says in plain words how good the model is."),
        form_cell(r'''
#@title Training
epochs = 30  #@param {type:"integer"}
'''),
        code(r'''
from meidnet.pipeline import train
from meidnet.checkpoint import describe, load_checkpoint, property_ranges
ckpt = train(cfg, epochs=epochs)              # writes runs/mine/model.pt and training_report.html
lm = load_checkpoint(ckpt)
print(describe(lm))
loss_curves(ckpt)
'''),
        md("How accurate is it? The materials held out from training (the validation split) are predicted **from "
           "their structure alone**, the same situation as judging a new candidate. Points on the grey diagonal are "
           "perfect predictions."),
        code(r'''
held_out = validation_records(cfg)
true, predicted = predict_records(lm, held_out)
for j, (label, unit) in enumerate(zip(lm.stats.labels, lm.stats.units)):
    parity_plot(true[:, j], predicted[:, j], label, unit, colour=BLOCK["model"])
show_report(os.path.join(cfg.out_dir, "training_report.html"))
errors = ", ".join(f"{c} {np.mean(np.abs(predicted[:, j] - true[:, j])):.3g}" for j, c in enumerate(lm.stats.columns))
print_flow("Family", f"your model (mean validation error: {errors})")
'''),

        block_header("family"),
        md("Generation fills the prototype your structures were aligned to with new combinations of elements. The "
           "family and variant come from `meidnet.yaml` (the form of the Data block)."),
        code(r'''
from meidnet.pipeline import family_for
from meidnet.designspace import enumerate_space, total_compositions
from meidnet.constraints import build_candidate, evaluate
cfg.generation.overrides = {}                 # the Rules block may set a window later
fam = family_for(cfg, need_variant=True)      # the family and variant named in meidnet.yaml
print(fam.describe())
display(pd.DataFrame([{"site group": g, "atoms per cell": len(grp.slots), "elements allowed": " ".join(grp.sample)}
                      for g, grp in fam.groups.items()]))
example = evaluate(build_candidate(fam, {g: grp.sample[0] for g, grp in fam.groups.items()}), fam.constraints)
print(f"\nOne way to fill the prototype: {example.formula()}; it passes every rule: {example.passed} "
      "(the Rules block checks them all)")
show3d([example.raw], properties={"formula": [example.formula()]})
print_flow("Rules", f"{total_compositions(fam):,} compositions (every way to fill the sites)")
'''),

        block_header("rules"),
        md("Every composition of the family is checked against its rules, in order, and **your** model predicts its "
           "properties. Each rule measures one number and compares it with an allowed window."),
        code(r'''
space = enumerate_space(fam, lm)              # every composition: the value of each rule + predicted properties
table = space_table(space)
for rule in space["rules"]:
    print(f"- {rule['title']}: {rule['text']}")
n_pass = int(table["passes_all"].sum())
print(f"\n{n_pass:,} of {len(table):,} compositions pass every rule")
for rule in space["rules"]:
    window = rule_window(rule["params"])
    if window and table[rule["name"]].notna().any():
        label, unit = measured(rule)
        hist_prop(table[rule["name"]], label, unit, colour=BLOCK["rules"], window=window, title=rule["title"],
                  ylabel="compositions")
funnel_plot(funnel_stages(table, space["rules"]), colour=BLOCK["rules"])
'''),
        md("**Try it:** change the tolerance-factor window and see how many compositions remain. Tick "
           "*use_for_search* to keep your window for the search; it is stored in `meidnet.yaml` under "
           "`generation.overrides`."),
        form_cell(r'''
#@title Change the tolerance-factor window
t_min = 0.80           #@param {type:"slider", min:0.6, max:1.0, step:0.01}
t_max = 1.00           #@param {type:"slider", min:0.9, max:1.2, step:0.01}
use_for_search = True  #@param {type:"boolean"}
'''),
        code(r'''
default = fam.constraint_params("tolerance_factor")
fam_search, space_search = fam, space
if default is None:
    print("this family has no tolerance-factor rule")
else:
    cfg.generation.overrides = {"tolerance_factor": {"min": t_min, "max": t_max}}
    fam_new = family_for(cfg, need_variant=True)
    table_new = space_table(enumerate_space(fam_new))     # the rules only: no predictions needed to count
    print(f"family window {default['min']} to {default['max']}: {n_pass:,} compositions pass every rule")
    print(f"your window   {t_min} to {t_max}: {int(table_new['passes_all'].sum()):,} compositions pass every rule")
    hist_prop(table_new["tolerance_factor"], "tolerance factor t", colour=BLOCK["rules"], window=(t_min, t_max),
              title="Goldschmidt tolerance factor, your window", ylabel="compositions")
    if use_for_search:
        fam_search, space_search = fam_new, enumerate_space(fam_new, lm)
    else:
        cfg.generation.overrides = {}
table_search = space_table(space_search)
print_flow("Targets", f"{int(table_search['passes_all'].sum()):,} of {len(table_search):,} compositions pass every rule")
'''),

        block_header("targets"),
        md("Set one target value per property. Properties you leave out aim at the median of your data. The "
           "allowed compositions are ranked with the objectives of `meidnet.yaml` (one squared distance per "
           "property), the score the search uses for its candidates."),
        form_cell(r'''
#@title Your targets
targets_text = ""  #@param {type:"string"}
#@markdown For example `dir_gap=1.5, heat_all=-0.1`. Leave empty to aim every property at the median of your data.
'''),
        code(r'''
columns = list(lm.stats.columns)
target = {p.column: round(float(np.median([r.properties[j] for r in records])), 3)
          for j, p in enumerate(cfg.data.properties)}
for part in filter(None, (s.strip() for s in targets_text.replace(";", ",").split(","))):
    name, value = (x.strip() for x in part.split("="))
    if name not in target:
        raise ValueError(f"'{name}' is not one of your properties: {', '.join(target)}")
    target[name] = float(value)
print("target:", target)
ranges = property_ranges(lm)
for col, value in target.items():
    lo, hi = ranges.get(col, (value, value))
    if not lo <= value <= hi:
        print(f"note: {col} = {value} lies outside the training range {lo:.3g} to {hi:.3g}: the model would be extrapolating")
objectives = [o.model_dump() for o in cfg.generation.objectives]
allowed = table_search[table_search["passes_all"]]
if allowed.empty:
    print("No composition passes every rule: widen a window in the Rules block or choose another variant.")
top10 = rank_by_target(allowed, target, objectives).head(10)
sites = [c for c in table_search.columns if c.startswith("site_")]
display(top10[["formula", *sites, *[f"pred_{c}" for c in columns], "score"]].round(3).reset_index(drop=True))
x = f"pred_{columns[0]}"
y = f"pred_{columns[1]}" if len(columns) > 1 else "a"
space_scatter(table_search, x, y, colour=BLOCK["targets"], highlight=top10,
              target=(target[columns[0]], target[columns[1]] if len(columns) > 1 else None),
              xlabel=f"predicted {columns[0]}", ylabel=f"predicted {columns[1]}" if len(columns) > 1 else "cell edge a [Å]")
hist_prop(allowed[x], f"predicted {columns[0]}", lm.stats.units[0], colour=BLOCK["targets"],
          target=target[columns[0]], title=f"Predicted {columns[0]} of the allowed compositions", ylabel="compositions")
'''),
        md("The design space in 3D (chemiscope), with your model's predictions: one point per composition, coloured "
           "by whether it passes every rule."),
        code(r'''
from meidnet.studio.chemiscope import space_dataset
show_dataset(space_dataset(fam_search, space_search, lm))
print_flow("Search", f"target {target}" + (f" (closest allowed composition: {top10['formula'].iloc[0]})" if len(top10) else ""))
'''),

        block_header("search"),
        search_intro(),
        form_cell(SEARCH_FORM),
        code(r'''
from meidnet.generate import Designer
gen = cfg.generation                          # the generation section of meidnet.yaml, with your choices
gen.targets, gen.per_target, gen.population, gen.rounds, gen.steps = [target], n_candidates, 24, rounds, steps
''' + SEARCH_PRINTERS + r'''
res = Designer(lm, fam_search, gen, log=progress, on_saved=on_saved).run(os.path.join(cfg.out_dir, "generation"),
                                                                         ranges=property_ranges(lm))
print_flow("Candidates", f"{len(res.saved)} candidate(s), written to {os.path.join(cfg.out_dir, 'generation')}")
'''),

        block_header("candidates"),
        md(CANDIDATES_INTRO),
        code(r'''
from meidnet.config import dump_config
from meidnet.report import generation_report
with open("meidnet.yaml", "w", encoding="utf-8") as f:
    f.write(dump_config(cfg))                 # meidnet.yaml now holds exactly the settings of this run
report = generation_report(cfg, lm, fam_search, res, os.path.join(cfg.out_dir, "generation_report.html"))
show_report(report)
'''),
        md("The candidates as a table (✓ = the rule passed, with its measured value) and in 3D, from the CIF "
           "files the search wrote."),
        code(CANDIDATES_TABLE_3D),
        md("**Download everything:** the CIFs, `candidates.csv`, `model.pt`, the three reports and the "
           "`meidnet.yaml` that produced them, in one zip file."),
        code(r'''
with zipfile.ZipFile("meidnet_results.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for folder, _, file_names in os.walk(cfg.out_dir):
        for file_name in file_names:
            path = os.path.join(folder, file_name)
            z.write(path, os.path.relpath(path))
    z.write("meidnet.yaml")
print(f"meidnet_results.zip: {os.path.getsize('meidnet_results.zip') / 1e6:.1f} MB")
if IN_COLAB:
    from google.colab import files
    files.download("meidnet_results.zip")
print_flow("Next steps", f"{len(res.saved)} candidate(s), your model and three reports in meidnet_results.zip")
'''),

        next_steps("Same data, more epochs: raise *epochs* in the Model block (200 is typical) and run again.",
                   "**03**: add your own rule, for example to exclude toxic elements.",
                   "On your computer: `pip install meidnet`, then `meidnet studio meidnet.yaml` opens the seven blocks "
                   "side by side with your model.",
                   f"Rules, element filters and family files: {DOCS_URL}"),
    ]


# ───────────────────────── 03 add a rule ─────────────────────────
def add_a_rule() -> list[dict]:
    return [
        title_cell(
            "Add your own rule to MEIDNet", "03_add_a_rule.ipynb",
            "A **rule** is a small Python function that looks at a candidate and says pass or fail, with a measured "
            "value and a sentence. Register it under a name, list that name in a family file, and every part of "
            "MEIDNet uses it: the design space, the search and the reports.\n\n"
            "In this notebook you write two rules (no lead; a window on the mean atomic mass), add them to a copy of "
            "the perovskite family, see which compositions they remove, and run a search that obeys them. It uses "
            "the published model and runs on a CPU in about five minutes."),
        setup_cell(),

        block_header("data"),
        md("Nothing to prepare here: this notebook reuses the published model, which has already learned from "
           "**Perov-5** (11,356 cubic perovskites; notebook 01 shows them). To learn from your own table, use "
           "notebook 02."),
        code(r'''
print_flow("Model", "Perov-5, already learned by the published model: nothing to load")
'''),

        *published_model_block(),

        block_header("family"),
        md("Rules are listed in the family file, under `constraints`. Copy the built-in perovskite family, give it "
           "a new name and append two rules. The names `no_lead` and `mass_window` do not exist yet: the next block "
           "defines them. A rule's parameters (here the mass window) live in the family file, next to its name."),
        form_cell(r'''
#@title Your copy of the family
variant = "halide"  #@param ["halide", "oxide", "chalcogenide", "nitride"]
max_mass = 110      #@param {type:"number"}
#@markdown **max_mass**: the largest mean atomic mass (g/mol) your rule will allow.
'''),
        code(r'''
import yaml
from meidnet.family import FAMILY_DIR, load_family
from meidnet.designspace import total_compositions
family_yaml = yaml.safe_load((FAMILY_DIR / "perovskite_abx3.yaml").read_text(encoding="utf-8"))
family_yaml["name"] = "my_perovskite"
family_yaml["title"] = "Cubic ABX3 perovskite with my two rules"
family_yaml["constraints"] += [{"name": "no_lead"}, {"name": "mass_window", "min": 0, "max": max_mass}]
with open("my_perovskite.yaml", "w", encoding="utf-8") as f:
    yaml.safe_dump(family_yaml, f, sort_keys=False, allow_unicode=True)
print("constraints in my_perovskite.yaml:")
for rule in family_yaml["constraints"]:
    print("  -", rule)
family_name = "my_perovskite.yaml"
builtin_fam = load_family("perovskite_abx3", variant=variant)
my_fam = load_family(family_name, variant=variant)
print()
print(my_fam.describe())
print_flow("Rules", f"{total_compositions(my_fam):,} compositions; {len(builtin_fam.constraints)} built-in rules + your 2")
'''),

        block_header("rules"),
        md("A rule receives a candidate (the element on each site, the cell and the structure) and returns "
           "`cand.result(name, passed, value, window, sentence)`. The `%%writefile` line saves the cell as "
           "`my_rules.py`; loading that file registers the two rules. In a project you list it under `plugins:` in "
           "`meidnet.yaml`, and the command line loads it for you."),
        code(r'''
%%writefile my_rules.py
"""Two custom MEIDNet rules. List this file under `plugins:` in meidnet.yaml."""
from pymatgen.core import Element

from meidnet.constraints import CONSTRAINTS


@CONSTRAINTS.register("no_lead", "Rejects any composition that contains lead (Pb).")
def no_lead(cand):
    has_lead = "Pb" in cand.elements.values()
    return cand.result("no_lead", not has_lead, detail="contains Pb" if has_lead else "lead-free")


@CONSTRAINTS.register("mass_window", "The mean atomic mass must lie between min and max (g/mol).")
def mass_window(cand, min=0.0, max=200.0):  # noqa: A002 (min/max are the names used in family files)
    mass = sum(Element(site.specie.symbol).atomic_mass for site in cand.structure) / len(cand.structure)
    return cand.result("mass_window", min <= mass <= max, float(mass), (min, max), f"mean atomic mass {mass:.1f} g/mol")
'''),
        code(r'''
from meidnet.constraints import CONSTRAINTS
from meidnet.pipeline import load_plugins
load_plugins(["my_rules.py"], os.path.abspath)     # what `plugins: [my_rules.py]` does in meidnet.yaml
for name in ("no_lead", "mass_window"):
    print(f"registered rule '{name}': {CONSTRAINTS.doc(name)}")
'''),
        md("**Before and after.** The same compositions, checked with the built-in rules only, then with your two "
           "rules added at the end. The last two bars of the second funnel are your rules at work."),
        code(r'''
from meidnet.designspace import enumerate_space
space_before = enumerate_space(builtin_fam, lm)
space_after = enumerate_space(my_fam, lm)
table_before, table_after = space_table(space_before), space_table(space_after)
n_before, n_after = int(table_before["passes_all"].sum()), int(table_after["passes_all"].sum())
funnel_plot(funnel_stages(table_before, space_before["rules"]), colour=BLOCK["rules"],
            title=f"Built-in rules only: {n_before:,} of {len(table_before):,} pass")
funnel_plot(funnel_stages(table_after, space_after["rules"]), colour=BLOCK["rules"],
            title=f"With your two rules: {n_after:,} of {len(table_after):,} pass")
hist_prop(table_after["mass_window"], "mean atomic mass", "g/mol", colour=BLOCK["rules"], window=(0, max_mass),
          title="Your mass_window rule", ylabel="compositions")
removed = sorted(set(table_before.loc[table_before["passes_all"], "formula"])
                 - set(table_after.loc[table_after["passes_all"], "formula"]))
print("removed by your rules:", ", ".join(removed) or "none")
fam_search, space_search, table_search, overrides = my_fam, space_after, table_after, {}
print_flow("Targets", f"{n_after:,} of {len(table_after):,} compositions pass every rule "
                      f"(with the built-in rules only: {n_before:,})")
'''),

        *published_targets_block(),
        *published_search_block("my_rules"),
        *published_candidates_block(
            "my_rules", '["my_rules.py"]',
            note="Each candidate card now lists **no_lead** and **mass_window** with the measured value: the same "
                 "function decided acceptance and wrote the explanation. `my_rules.yaml` (written below) reruns this "
                 "search from a terminal with `meidnet generate my_rules.yaml`; it names `my_rules.py` under "
                 "`plugins` and `my_perovskite.yaml` as the family."),

        next_steps("Rules that need the model's prediction already exist: `property_window` keeps candidates whose "
                   "predicted property lies in a window (add it to a family's `constraints`, or to "
                   "`generation.extra_constraints` in `meidnet.yaml`).",
                   "Soft guidance during the search (instead of a hard rule) is a *search term*: "
                   "`meidnet.terms.SEARCH_TERMS.register`, the same pattern.",
                   "**04**: MEIDNet Studio inside Colab; its Rules block shows every rule's window as a slider.",
                   f"The recipe in the documentation: {DOCS_URL}recipes/add-constraint.html"),
    ]


# ───────────────────────── 04 MEIDNet Studio in Colab ─────────────────────────
def studio_in_colab() -> list[dict]:
    return [
        title_cell(
            "MEIDNet Studio in Colab", "04_MEIDNet_Studio_in_Colab.ipynb",
            "**MEIDNet Studio** is a web page that lays the seven blocks out side by side: change a rule's window or "
            "a target and watch the effect flow through every block. Part 1 starts the Studio inside this Colab "
            "session and shows it here. Part 2 drives the **same Studio code** from Python, block by block, so you "
            "can script what you clicked."),
        setup_cell(),

        md("## Part 1 · Open the Studio\n"
           "The Studio is a small web server. The next cell downloads Perov-5 (the Data block shows it), fetches the "
           "published model, starts the server in the background and waits until it answers."),
        code(r'''
import shutil
import subprocess
import time
import urllib.request
!meidnet download-data
from meidnet.cli import published_checkpoint
published_checkpoint()                        # fetch the published model once, before the server needs it
STUDIO_PORT = 8765
if "studio_proc" in globals() and studio_proc.poll() is None:
    print("The Studio is already running")
else:
    command = ["meidnet", "studio", "--no-open", "--port", str(STUDIO_PORT), "--host", "127.0.0.1"]
    if shutil.which("meidnet") is None:       # a checkout without the `meidnet` command: the same, through Python
        command = [sys.executable, "-m", "meidnet.cli"] + command[1:]
    studio_log = open("studio_server.log", "w", encoding="utf-8")
    studio_proc = subprocess.Popen(command, stdout=studio_log, stderr=subprocess.STDOUT)
    for _ in range(180):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{STUDIO_PORT}/api/state", timeout=5) as answer:
                answer.read()
            print(f"MEIDNet Studio is running on port {STUDIO_PORT} (server log: studio_server.log)")
            break
        except Exception:
            if studio_proc.poll() is not None:
                raise RuntimeError("The Studio stopped:\n" + open("studio_server.log", encoding="utf-8").read())
            time.sleep(1)
    else:
        print("The Studio is still starting: run the next cell in a moment (server log: studio_server.log)")
'''),
        code(r'''
if IN_COLAB:
    from google.colab import output
    output.serve_kernel_port_as_iframe(STUDIO_PORT, height=950)
    output.serve_kernel_port_as_window(STUDIO_PORT, anchor_text="Open MEIDNet Studio in its own browser tab")
else:
    print(f"Open http://127.0.0.1:{STUDIO_PORT}/ in your browser")
'''),
        md("**Tips.** If the frame stays blank, use the link below it. Deep links open the page on one block: "
           "`output.serve_kernel_port_as_iframe(STUDIO_PORT, path=\"/?panel=rules\", height=950)`; "
           "`path=\"/?explore=space\"` opens the 3D explorer of the design space (chemiscope)."),

        md("## Part 2 · The same Studio, from Python\n"
           "Every button of the page calls a method of the `Studio` class in `meidnet.studio.server`. Below, a "
           "separate `Studio` object living in this notebook goes through the seven blocks, so what you do here does "
           "not appear in the page above. `sid` names your session, the way a browser tab does."),
        code(r'''
from meidnet.studio.server import Studio
s = Studio(None)                              # the published model, as `meidnet studio` without a config file
sid = "colab-notebook"                        # one session = one browser tab: its upload, model and searches
state = s.state(sid)
print(state["model"]["description"])
print("families:", ", ".join(state["families"]))
'''),

        block_header("data"),
        md("The Data block shows the data behind the current model and lets you bring your own: upload a table, map "
           "its columns, check it. Here 400 rows of Perov-5 stand in for your upload."),
        code(r'''
import base64
summary = s.data(sid)                         # the published model's data (Perov-5), once downloaded
print(summary.get("source") or summary.get("note"))
pd.read_csv("data/perov5/train.csv").head(400).to_csv("example_materials.csv", index=False)
with open("example_materials.csv", "rb") as f:
    upload = s.upload({"session": sid, "files": [{"name": "example_materials.csv",
                                                  "b64": base64.b64encode(f.read()).decode("ascii")}]})
print(f"uploaded {upload['rows']} rows; the Studio suggests {upload['suggest']}")
'''),
        form_cell(r'''
#@title Map the columns
properties = "heat_all dir_gap"  #@param {type:"string"}
variant = "halide"               #@param ["halide", "oxide", "chalcogenide", "nitride"]
prototype_tolerance = 0.25       #@param {type:"number"}
'''),
        code(r'''
checked = s.check_data({"session": sid, "id_column": upload["suggest"]["id_column"],
                        "cif_column": upload["suggest"]["cif_column"],
                        "properties": [{"column": c} for c in properties.split()],
                        "family": "perovskite_abx3", "variant": variant,
                        "align_to_prototype": True, "prototype_tolerance": prototype_tolerance})
print(f"{checked['kept']} of {checked['rows']} rows usable; skipped: {checked['skipped'] or 'none'}")
records = s.session(sid).check_info["records"]
for j, col in enumerate(properties.split()):
    hist_prop([r.properties[j] for r in records], col, colour=BLOCK["data"], ylabel="materials",
              title=f"{col} in the checked upload")
show_dataset(s.chemiscope(sid, "data"))       # the checked structures in 3D, as the page's explorer shows them
print_flow("Model", f"{checked['kept']} checked materials")
'''),

        block_header("model"),
        md("Train a model for this session on the checked data. A few epochs only show the mechanics; the published "
           "model stays available, and the form decides which model the next blocks use."),
        form_cell(r'''
#@title Train on your data
epochs = 5            #@param {type:"integer"}
use_my_model = False  #@param {type:"boolean"}
#@markdown Leave **use_my_model** off to continue with the published model: a model trained for a few epochs is only a demonstration.
'''),
        code(r'''
started = s.start_train({"session": sid, "epochs": epochs, "batch_size": 16})
print(started)
job = s.status(sid, "train")
while started.get("ok") and not job["done"]:
    time.sleep(2)
    job = s.status(sid, "train")
    p = job["progress"]
    print(f"  epoch {p['epoch']}/{p['epochs']}  loss {p['loss']:.3f}" if p["loss"] is not None else "  starting ...")
if job["error"]:
    print("training failed:", job["error"])
session = s.session(sid)
if session.lm is not None:
    loss_curves(session.lm.path)
    true, predicted = predict_records(session.lm, validation_records(session.cfg))
    for j, (label, unit) in enumerate(zip(session.lm.stats.labels, session.lm.stats.units)):
        parity_plot(true[:, j], predicted[:, j], label, unit, colour=BLOCK["model"])
    s.select_model(sid, "own" if use_my_model else "published")
print(s.state(sid)["model"]["description"])
print_flow("Family", "your model" if s.state(sid)["model"]["own"] else "the published model")
'''),

        block_header("family"),
        md("The Family block loads a family and variant and lists every composition it allows (the *design "
           "space*), with the properties the current model predicts for each."),
        code(r'''
from meidnet.family import load_family
from meidnet.constraints import build_candidate
payload = s.family({"session": sid, "family": "perovskite_abx3", "variant": variant})
print(payload["describe"])
display(pd.DataFrame([{"site group": g, "atoms per cell": len(grp["slots"]), "elements allowed": " ".join(grp["sample"])}
                      for g, grp in payload["groups"].items()]))
space = payload["space"]
fam = load_family(payload["name"], variant=payload["variant"])
first = build_candidate(fam, space["rows"][0]["e"])
print(f"\nOne way to fill the prototype: {first.formula()}")
show3d([first.raw], properties={"formula": [first.formula()]})
print_flow("Rules", f"{space['total']:,} compositions")
'''),

        block_header("rules"),
        md("The page draws one chart per rule and lets you drag each window. It re-runs no chemistry for that: "
           "every composition already carries the value of every rule, so the page only compares numbers with your "
           "window. The same comparison, in pandas:"),
        code(r'''
table = space_table(space)
for rule in space["rules"]:
    print(f"- {rule['title']}: {rule['text']}")
for rule in space["rules"]:
    window = rule_window(rule["params"])
    if window and table[rule["name"]].notna().any():
        label, unit = measured(rule)
        hist_prop(table[rule["name"]], label, unit, colour=BLOCK["rules"], window=window, title=rule["title"],
                  ylabel="compositions")
funnel_plot(funnel_stages(table, space["rules"]), colour=BLOCK["rules"])
'''),
        form_cell(r'''
#@title Try a stricter tolerance-factor window
t_min = 0.80  #@param {type:"slider", min:0.6, max:1.0, step:0.01}
t_max = 1.00  #@param {type:"slider", min:0.9, max:1.2, step:0.01}
'''),
        code(r'''
overrides = {"tolerance_factor": {"min": t_min, "max": t_max}}
verdict = s.validate({"session": sid, "generation": {"variant": variant, "overrides": overrides}})
print("the Studio accepts these settings" if verdict["ok"] else f"the Studio refuses them: {verdict['errors']}")
others = [f"ok_{r['name']}" for r in space["rules"] if r["name"] != "tolerance_factor"]
table_search = table.assign(passes_all=table[others].all(axis=1) & table["tolerance_factor"].between(t_min, t_max))
print(f"family window: {int(table['passes_all'].sum()):,} compositions pass every rule; "
      f"your window {t_min} to {t_max}: {int(table_search['passes_all'].sum()):,}")
print_flow("Targets", f"{int(table_search['passes_all'].sum()):,} of {len(table_search):,} compositions pass every rule")
'''),

        block_header("targets"),
        md("Rank the allowed compositions by how close their predicted properties come to your targets, with the "
           "objectives of the Studio's configuration (the score its search uses)."),
        form_cell(r'''
#@title Set your targets
band_gap = 2.0    #@param {type:"number"}
enthalpy = -0.10  #@param {type:"number"}
'''),
        code(r'''
objectives = s.state(sid)["config"]["generation"]["objectives"]
target = {"dir_gap": band_gap, "heat_all": enthalpy}
allowed = table_search[table_search["passes_all"]]
top10 = rank_by_target(allowed, target, objectives).head(10)
sites = [c for c in table_search.columns if c.startswith("site_")]
display(top10[["formula", *sites, "pred_dir_gap", "pred_heat_all", "score"]].round(3).reset_index(drop=True))
space_scatter(table_search, "pred_dir_gap", "pred_heat_all", colour=BLOCK["targets"], target=(band_gap, enthalpy),
              highlight=top10, xlabel="predicted band gap [eV]", ylabel="predicted formation enthalpy [eV/atom]")
hist_prop(allowed["pred_dir_gap"], "predicted band gap", "eV", colour=BLOCK["targets"], target=band_gap,
          title="Predicted band gap of the allowed compositions", ylabel="compositions")
'''),
        md("The page's 3D explorer of the design space is a chemiscope dataset; `Studio.chemiscope` returns it, "
           "here shown with chemiscope in the notebook (colours: the family's own windows)."),
        code(r'''
show_dataset(s.chemiscope(sid, "space", "perovskite_abx3", variant))
best = top10["formula"].iloc[0] if len(top10) else "none"
print_flow("Search", f"target band gap {band_gap} eV and enthalpy {enthalpy} eV/atom (closest allowed: {best})")
'''),

        block_header("search"),
        md("Start a search in the background and poll its status, as the page does every second. "
           "`s.stop(sid)` would end it early (the page's Stop button)."),
        form_cell(SEARCH_FORM),
        code(r'''
request = {"variant": variant, "targets": [target], "overrides": overrides,
           "per_target": n_candidates, "population": 24, "rounds": rounds, "steps": steps}
started = s.start_search({"session": sid, "generation": request})
print(started)
seen = 0
job = s.status(sid, "search")
while started.get("ok"):
    job = s.status(sid, "search")
    for c in job["candidates"][seen:]:
        print(f"  found {c['formula']:<10} " + ", ".join(f"{k} {v:.3g}" for k, v in c["predictions"].items()))
    seen = len(job["candidates"])
    if job["done"]:
        break
    time.sleep(1)
if job["error"]:
    print("the search failed:", job["error"])
print_flow("Candidates", f"{seen} candidate(s)")
'''),

        block_header("candidates"),
        md("What the Candidates block shows: every candidate with each rule and its measured value, the report of "
           "the search, the candidates in 3D, and the `meidnet.yaml` that reruns the search from a terminal."),
        code(r'''
display(candidates_table(job["candidates"]))
if job["report"]:
    show_report(os.path.join(s.run_root, job["report"]))
show_dataset(s.chemiscope(sid, "candidates"))
yaml_text = s.export({"session": sid, "generation": request})   # the page's "download YAML" button
print(yaml_text)
print_flow("Next steps", "save the YAML above as meidnet.yaml and run `meidnet generate meidnet.yaml` anywhere")
'''),
        after_blocks(md("When you are done, stop the server (the page above stops answering):")),
        code(r'''
if "studio_proc" in globals() and studio_proc.poll() is None:
    studio_proc.terminate()
    print("MEIDNet Studio stopped")
'''),

        next_steps("On your computer: `pip install meidnet`, then `meidnet studio` (or `meidnet studio meidnet.yaml` "
                   "with your own model).",
                   "**01** to **03**: the same seven blocks as plain notebook cells.",
                   f"Documentation: {DOCS_URL}"),
    ]


NOTEBOOKS = {
    "01_quickstart": quickstart,
    "02_your_own_data": your_own_data,
    "03_add_a_rule": add_a_rule,
    "04_MEIDNet_Studio_in_Colab": studio_in_colab,
}


def main(out_dir: str | None = None) -> list[str]:
    """Write the four notebooks into out_dir (default: notebooks/ of the repository) and return their paths."""
    out_dir = os.path.abspath(out_dir or OUT)
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, build in NOTEBOOKS.items():
        path = os.path.join(out_dir, f"{name}.ipynb")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(notebook(build(), name), f, indent=1, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        print("wrote", path)
        paths.append(path)
    return paths


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
