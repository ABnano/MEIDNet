# Python API

The command line is a thin layer over these functions; use them from notebooks or your own scripts.

```python
from meidnet.config import load_config, config_from_dict
from meidnet.pipeline import check, train, generate

cfg = load_config("meidnet.yaml")
info = check(cfg)                 # dict: report (counts, skip reasons), records, family, report_path
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
