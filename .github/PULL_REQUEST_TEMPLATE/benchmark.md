## Benchmark submission

- [ ] One JSON file under `benchmarks/submissions/<dataset>/<id>.json` (copied from `_template.json`), one category per file
- [ ] `python scripts/benchmarks.py validate` passes locally
- [ ] The dataset exists in `benchmarks/datasets/` (or this PR adds it with source, size and split)
- [ ] Every link in `evidence` is public; the validation level matches the evidence
- [ ] `reproduce.config`, `reproduce.seed` and `reproduce.command` let someone else obtain the numbers
- [ ] `status` is `community_submitted` (the maintainer sets `meidnet_verified` after `reproduce`)

What was measured, in two sentences:
