# Python API

The command line is a thin layer over these functions; use them from notebooks or your own scripts.

```python
from meidnet.config import load_config, config_from_dict
from meidnet.pipeline import check, train, generate

cfg = load_config("meidnet.yaml")
info = check(cfg)                 # dict: report (counts, skip reasons), records, family, report_path
info = check(cfg, keep_structures=True)   # records also keep their pymatgen Structure (record.structure)
model_path = train(cfg)           # writes model.pt + training_report.html, returns the path
result = generate(cfg)            # GenerationResult: .saved (candidates), .targets (funnel logs)
```

## Pieces

```python
from meidnet.checkpoint import load_checkpoint, describe, property_ranges
lm = load_checkpoint("model.pt")          # LoadedModel: .model, .stats (property names/units/normalisation)
lm.model.encode_crystal(x)                # structure → latent (x from meidnet.data.featurize)
lm.model.encode_properties(p)             # normalised property vector → latent

from meidnet.family import load_family
fam = load_family("perovskite_abx3", variant="halide", exclude=["Pb"], overrides={"tolerance_factor": {"max": 1.0}})

from meidnet.constraints import build_candidate, evaluate, CONSTRAINTS
cand = evaluate(build_candidate(fam, {"A": "Cs", "B": "Sn", "X": "Br"}), fam.constraints)
cand.passed, [r.to_dict() for r in cand.results]

from meidnet.generate import Designer
from meidnet.config import GenerationSection
g = GenerationSection(family="perovskite_abx3", variant="halide",
                      objectives=[{"property": "dir_gap"}], targets=[{"dir_gap": 2.0}], rounds=3, steps=200)
res = Designer(lm, fam, g, on_saved=lambda c, t: print(c.formula)).run("out/")

from meidnet.designspace import enumerate_space, space_to_csv
space = enumerate_space(fam, lm)          # every composition: rule values + predictions
```

Custom rules and search terms: [`CONSTRAINTS.register`](rules.md), `meidnet.terms.SEARCH_TERMS.register`.

## Extra rules in the configuration

`generation.extra_constraints` adds rules to the family's own for one run, without editing the family file —
this is how the Studio saves a *predicted-property window*:

```yaml
generation:
  family: perovskite_abx3
  variant: halide
  extra_constraints:
    - {name: property_window, property: dir_gap, min: 1.5, max: 3.0}
```

`meidnet.pipeline.family_for(cfg, need_variant=True)` returns the family a run uses, with these rules
appended; `generation.family` / `generation.variant` take precedence over the top-level `family`.

## 3D datasets (chemiscope)

`meidnet.studio.chemiscope` turns MEIDNet objects into [chemiscope](https://chemiscope.org) datasets — plain
dicts you can save with `json.dump` and open at chemiscope.org, or show in a notebook with
`chemiscope.show(...)`:

```python
from meidnet.studio.chemiscope import (space_dataset, candidates_dataset, records_dataset,
                                       published_data_dataset, structure_to_chemiscope)

ds = space_dataset(fam, space, lm, max_structures=2000)   # design space: formula, site_*, pred_*, rule_*, passes_all
ds = candidates_dataset(candidate_dicts, fam, run_dir)    # candidates of a run (reads their CIFs when present)
ds = records_dataset(info["records"], cfg.data.properties, source="my data")   # needs check(cfg, keep_structures=True)
structure_to_chemiscope(structure)                         # one pymatgen Structure → {size, names, x, y, z, cell}
```

`candidate_dicts` are saved candidates as dicts — `[c.to_dict() for c in res.saved]` after a `Designer` run,
or `[c for t in json.load(open("generation.json"))["targets"] for c in t["saved"]]` from a finished run.
`run_dir` is the run folder that contains `generation/` (`cfg.out_dir` after `meidnet generate`); where a CIF
file is not found, the structure is rebuilt on the prototype from the candidate's elements.

## Scripting the Studio

The Studio server is a small class you can drive without a browser — the 04 Colab notebook does exactly this.
Every method takes the same JSON-like dicts the page sends; `session` keeps users (or experiments) apart.

```python
import base64
from meidnet.studio.server import Studio

st = Studio(None)                                   # the published model; or Studio(load_config("meidnet.yaml"))
sid = "my-session"
st.state(sid)                                       # model, ranges, families, limits, session info

b64 = base64.b64encode(open("materials.csv", "rb").read()).decode()
up = st.upload({"session": sid, "files": [{"name": "materials.csv", "b64": b64}]})
up["suggest"]                                       # suggested id / CIF / property columns

st.check_data({"session": sid, "id_column": "material_id", "cif_column": "cif",
               "properties": [{"column": "dir_gap", "unit": "eV"}],
               "family": "perovskite_abx3", "variant": "halide"})
st.start_train({"session": sid, "epochs": 10, "batch_size": 16})
st.status(sid, "train")                             # poll: running, progress (epoch, loss, curve), done, error
st.select_model(sid, "published")                   # or "own"

st.family({"session": sid, "family": "perovskite_abx3", "variant": "halide"})   # design space, scored
st.start_search({"session": sid, "generation": {"per_target": 2, "rounds": 2, "steps": 100}})
st.status(sid, "search")                            # candidates as they are found
st.chemiscope(sid, "space", "perovskite_abx3", "halide")   # or "candidates" / "data"
st.validate({"yaml": "generation:\n  rounds: 2\n"})        # {ok, generation, notes} or {ok: False, errors}
st.export({"session": sid, "generation": {}})              # the meidnet.yaml text
```
