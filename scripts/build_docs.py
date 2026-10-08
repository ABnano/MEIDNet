"""
Generate the parts of the documentation that come from the code, so they never go stale:

    docs/reference/config.md       every meidnet.yaml setting with its description and default
    docs/reference/rules.md        built-in constraints and search terms with their explanations
    docs/studio.html               the static "try it in your browser" Studio (published model)
    docs/explore/capabilities.md   capabilities, from the registries (Available / Planned)
    docs/benchmarks/**             the benchmark pages, from benchmarks/*.json (scripts/benchmarks.py)

Run before `mkdocs build` (the docs workflow does).
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
DOCS = os.path.join(ROOT, "docs")

from meidnet.config import MEIDNetConfig  # noqa: E402
from meidnet.constraints import CONSTRAINTS, EXPLAIN  # noqa: E402
from meidnet.family import list_families, load_family  # noqa: E402
from meidnet.terms import LOGIT_TRANSFORMS, SEARCH_TERMS  # noqa: E402

# Modalities MEIDNet is designed for but does not implement yet (docs/understand/limits.md keeps the same list).
PLANNED_MODALITIES = [("Vector modalities: binned XRD, DOS", "an encoder per vector modality into the shared latent space"),
                      ("Spectra (Raman, UV-Vis)", "as vector modalities"),
                      ("Text (descriptions, synthesis)", "a text encoder into the shared latent space"),
                      ("Images (microscopy)", "an image encoder into the shared latent space")]
UPLOAD_FORMATS = [("CSV", "any delimiter pandas reads"), ("Excel (.xlsx, .xls)", "first sheet"), ("JSON table", "records"),
                  ("Parquet", "needs the optional pyarrow"), ("CIF text in a column", "one structure per row"),
                  ("CIF files (.cif, or a .zip of them)", "named <id>.cif")]


def config_reference() -> str:
    schema = MEIDNetConfig.model_json_schema()
    defs = schema["$defs"]
    out = ["# Configuration reference", "",
           "Every setting of `meidnet.yaml`, generated from the code (`meidnet schema` gives the JSON Schema).",
           "Unknown keys are rejected with a message naming the key, so typos cannot silently change a run.", ""]

    def section(title, props, required):
        out.append(f"## {title}")
        out.append("")
        out.append("| setting | type | default | meaning |")
        out.append("|---|---|---|---|")
        for name, p in props.items():
            typ = p.get("type") or ("/".join(x.get("type", "object") for x in p.get("anyOf", [])) if "anyOf" in p else "")
            if "$ref" in p:
                typ = "section"
            if "enum" in p:
                typ = " / ".join(f"`{e}`" for e in p["enum"])
            default = p.get("default", "**required**" if name in required else "")
            if isinstance(default, (dict, list)):
                default = f"`{json.dumps(default)}`" if default else ""
            elif default not in ("", "**required**"):
                default = f"`{default}`"
            desc = p.get("description", "").replace("\n", " ")
            out.append(f"| `{name}` | {typ} | {default} | {desc} |")
        out.append("")

    section("Top level", schema["properties"], schema.get("required", []))
    order = ["DataSection", "PropertyColumn", "ModelSection", "TrainingSection", "LossWeights", "GenerationSection", "Objective"]
    titles = {"DataSection": "`data:`", "PropertyColumn": "`data.properties[]`", "ModelSection": "`model:`",
              "TrainingSection": "`training:`", "LossWeights": "`training.loss_weights:`",
              "GenerationSection": "`generation:`", "Objective": "`generation.objectives[]`"}
    for k in order:
        section(titles[k], defs[k]["properties"], defs[k].get("required", []))
    return "\n".join(out)


def rules_reference() -> str:
    out = ["# Rules and search terms", "",
           "**Rules** (hard constraints) decide whether a candidate is saved. **Search terms** (soft penalties) "
           "steer the latent search towards decodable, sensible outputs. Both are referenced by name in family files.", "",
           "## Built-in rules", ""]
    for name in CONSTRAINTS.names():
        title, text = EXPLAIN.get(name, (name, CONSTRAINTS.doc(name)))
        out.append(f"### `{name}` — {title}")
        out.append("")
        out.append(text)
        out.append("")
    out += ["## Search terms", ""]
    for name in SEARCH_TERMS.names():
        out.append(f"- `{name}` — {SEARCH_TERMS.doc(name)}")
    out += ["", "## Logit transforms", ""]
    for name in LOGIT_TRANSFORMS.names():
        out.append(f"- `{name}` — {LOGIT_TRANSFORMS.doc(name)}")
    out += ["", "## Your own rule", "",
            "```python", "from meidnet.constraints import CONSTRAINTS", "",
            '@CONSTRAINTS.register("no_lead", "Rejects any composition containing Pb.")',
            "def no_lead(cand):", '    return cand.result("no_lead", "Pb" not in cand.elements.values())', "```", "",
            "Save it as `my_rules.py`, list it under `plugins:` in `meidnet.yaml`, and add `- {name: no_lead}` to the "
            "family's `constraints`. See [Add a rule](../recipes/add-constraint.md).", ""]
    return "\n".join(out)


def capabilities_reference(verified_modalities=()) -> str:
    """Available / Benchmarked / Planned, read from the code. Benchmarked is given only to a modality or
    property named by a benchmark row that has been reproduced here (scripts/benchmarks.py)."""
    def status(name, planned=False):
        if planned:
            return "Planned"
        return "Benchmarked" if name in verified_modalities else "Available"
    out = ["# Capabilities", "",
           "This page is generated from the code. **Available**: in this release. **Benchmarked**: used by a "
           "benchmark result reproduced here. **Planned**: on the [roadmap](../understand/limits.md), not yet "
           "implemented.", "",
           "## Modalities", "", "| modality | status | how |", "|---|---|---|",
           f"| Crystal structure (CIF, up to `max_sites` atoms, default 20) | {status('structure')} | an equivariant graph encoder; structures are aligned to the family prototype |",
           f"| Scalar properties (any number of numeric columns) | {status('property')} | one property encoder; every column becomes a target you can set |",
           f"| Published properties: direct band gap (`dir_gap`), formation enthalpy (`heat_all`) | {status('property:dir_gap')} | the shipped Perov-5 checkpoint |"]
    for name, how in PLANNED_MODALITIES:
        out.append(f"| {name} | {status(name, planned=True)} | {how} |")
    out += ["", "## Fusion", "", "The structure latent and the property latent of a material are averaged into the joint "
            "latent (`meidnet/model.py`); the paper calls this early fusion. The two latents are first aligned by a "
            "contrastive loss whose weight increases over `training.contrastive_warmup_epochs` (the curriculum of the "
            "paper). Other fusion schemes are compared in the [Architecture Atlas](../learn/architectures.md).", "",
            "## Input formats", "", "| format | note |", "|---|---|"]
    for name, note in UPLOAD_FORMATS:
        out.append(f"| {name} | {note} |")
    out += ["", "## Material families", "", "| family | variants | site groups |", "|---|---|---|"]
    for name in list_families():
        fam = load_family(name, default_variant=True)
        variants = ", ".join(f"`{v}`" for v in (fam.variants or {})) or "-"
        out.append(f"| `{name}` - {fam.title} | {variants} | {', '.join(fam.groups)} |")
    out += ["", "Any other prototype family can be described in a [family file](../reference/families.md).", "",
            "## Rules (hard constraints)", ""]
    for name in CONSTRAINTS.names():
        title, _ = EXPLAIN.get(name, (name, ""))
        out.append(f"- `{name}` - {title}")
    out += ["", "## Search terms (soft)", ""]
    for name in SEARCH_TERMS.names():
        out.append(f"- `{name}` - {SEARCH_TERMS.doc(name)}")
    out += ["", "## After generation", "", "- `meidnet screen`: MACE-MP-0 relaxation and the stable / unique / novel (SUN) counts "
            "(optional `pip install meidnet[stability]`). DFT and experiments are yours: the [benchmark evidence ladder](../benchmarks/index.md) records them.", ""]
    return "\n".join(out)


def main():
    os.makedirs(os.path.join(DOCS, "reference"), exist_ok=True)
    with open(os.path.join(DOCS, "reference", "config.md"), "w", encoding="utf-8") as f:
        f.write(config_reference())
    with open(os.path.join(DOCS, "reference", "rules.md"), "w", encoding="utf-8") as f:
        f.write(rules_reference())
    print("wrote docs/reference/config.md and rules.md")
    sys.path.insert(0, os.path.dirname(__file__))
    import benchmarks as bench
    verified = set()
    for _, sub in bench.submissions():
        if sub.status == "meidnet_verified":
            verified.update(sub.modalities); verified.add("property" if any(m.startswith("property:") for m in sub.modalities) else "")
    os.makedirs(os.path.join(DOCS, "explore"), exist_ok=True)
    with open(os.path.join(DOCS, "explore", "capabilities.md"), "w", encoding="utf-8") as f:
        f.write(capabilities_reference(verified))
    bench.write_schema()
    for w in bench.render():
        pass
    import reproduction_pages                      # the analysis pages of Perov-5, from benchmarks/reproduction/perov5/
    reproduction_pages.main()
    print("wrote docs/explore/capabilities.md, docs/benchmarks/**, docs/community/index.md")
    # the Ask PRISM panel, as a documentation asset: a page under /docs/ (the Space) or at the mirror's root loads it
    # relatively; the Space's own pages keep /ask-prism.js
    import shutil
    shutil.copyfile(os.path.join(ROOT, "meidnet", "studio", "ask_prism.js"), os.path.join(DOCS, "assets", "ask-prism.js"))
    if "--no-studio" not in sys.argv:
        from meidnet.cli import published_checkpoint
        from meidnet.studio.server import export_static
        os.chdir(ROOT)
        export_static(None, os.path.join(DOCS, "studio.html"), model_path=published_checkpoint())


if __name__ == "__main__":
    main()
