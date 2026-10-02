"""
Generate the parts of the documentation that come from the code, so they never go stale:

    docs/reference/config.md       every meidnet.yaml setting with its description and default
    docs/reference/rules.md        built-in constraints and search terms with their explanations
    docs/studio.html               the static "try it in your browser" Studio (published model)

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
from meidnet.terms import LOGIT_TRANSFORMS, SEARCH_TERMS  # noqa: E402


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


def main():
    os.makedirs(os.path.join(DOCS, "reference"), exist_ok=True)
    with open(os.path.join(DOCS, "reference", "config.md"), "w", encoding="utf-8") as f:
        f.write(config_reference())
    with open(os.path.join(DOCS, "reference", "rules.md"), "w", encoding="utf-8") as f:
        f.write(rules_reference())
    print("wrote docs/reference/config.md and rules.md")
    if "--no-studio" not in sys.argv:
        from meidnet.cli import published_checkpoint
        from meidnet.studio.server import export_static
        os.chdir(ROOT)
        export_static(None, os.path.join(DOCS, "studio.html"), model_path=published_checkpoint())


if __name__ == "__main__":
    main()
