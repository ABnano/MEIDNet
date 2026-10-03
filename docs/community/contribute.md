# Contribute a benchmark result

MEIDNet Benchmarks collect results **per dataset**, each with the evidence behind it. Anyone who runs MEIDNet on a
dataset — the published Perov-5, or their own — can submit a result. Submissions go through GitHub, so every
number has a public record and a reviewer.

## What a submission is

One JSON file, `benchmarks/submissions/<dataset>/<id>.json`, that follows `benchmarks/schema.json`. The short
version:

| field | what to put |
|---|---|
| `dataset` | an id from `benchmarks/datasets/` (`perov5`, …); a new dataset needs its own `datasets/<id>.json` with source, size and split |
| `modalities` | what the model aligned: `structure`, `property:<column>` (one per property), later `xrd`, … |
| `model` | MEIDNet version, family and variant, the configuration (`meidnet.yaml`), checkpoint link and its SHA-256 |
| `category` | `representation_quality`, `conditional_design`, `efficiency` or `validation` — one category per file |
| `results` | metric → `{value, unit}`; only the metric names allowed for that category (listed in the schema) |
| `validation_level` | the evidence ladder: `generated` → `ml_filtered` → `mlip_validated` → `dft_validated` → `experimentally_validated` |
| `evidence` | public links: CIF archive, `stability.csv`, DFT inputs/outputs, paper DOI |
| `reproduce` | configuration, seed and the exact command that produces the numbers |
| `status` | always `community_submitted` for a new file |

## The five things people get wrong

1. **Mixing categories** in one file. A representation result (MAE, R², retrieval) and a design result (SUN rate)
   are two files.
2. **A metric name that is not in the list.** `validate` refuses it; the lists exist so that rows are comparable.
3. **No split.** State the split you evaluated on (or link a file of ids). A number on an unknown split is not comparable.
4. **Evidence that is not public.** A result without an inspectable artefact stays at `generated`.
5. **Claiming a validation level the evidence does not support.** `dft_validated` needs the DFT outputs, not the intention.

## How it works

1. Copy `benchmarks/submissions/_template.json`, fill it in, run `python scripts/benchmarks.py validate`.
2. Open a pull request (the template has a checklist). CI runs `validate`.
3. Once merged, the result is rendered on the dataset's benchmark page and gets a permanent page of its own,
   marked **Community submitted**.
4. The maintainer may run `python scripts/benchmarks.py reproduce <id>`: it re-runs the stated command from the
   stated configuration and compares the numbers. If they agree within the tolerances, the row becomes
   **MEIDNet verified** (a record in `benchmarks/verified/`, which only the maintainer can add).

**Verified** means *reproduced from the submitted configuration with this code*. It does not mean the material is
real: that is what the validation level says. A re-run that does **not** agree is kept too
(`benchmarks/verified/<id>.attempt.json`) and shown on the row's page next to the submitted numbers, so that a
disagreement is visible rather than silent — this applies to the paper's own rows as much as to anyone else's.

Representation rows that are reproduced here also get their per-material predictions saved
(`benchmarks/verified/<id>.predictions.csv`), which the pages turn into parity plots and a latent-agreement histogram.

If you prefer not to open a pull request, the issue template *Benchmark submission* asks for the same fields and the
maintainer converts it. Submissions are reviewed by the author of MEIDNet; there is no promised response time.
