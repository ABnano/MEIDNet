## Benchmark submission

- [ ] One JSON file `benchmarks/submissions/<dataset>/<method>.json` (copied from `_template.json`) describing the method and its results per task
- [ ] `protocol` names the dataset's current protocol version (for example `perov5-v1`)
- [ ] The numbers come from `python scripts/benchmarks.py score ...` (or `run` for a MEIDNet checkpoint)
- [ ] The outputs behind them are included or linked: `predictions.csv` and/or `candidates.csv` with the CIFs, under `artifacts`
- [ ] `python scripts/benchmarks.py validate` passes locally
- [ ] `status` is `community_submitted` (the maintainer re-scores the outputs before marking the record as computed here)

The method, in two sentences:
