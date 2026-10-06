# MEIDNet Benchmarks

Standardised tasks for multimodal materials models, each with a fixed protocol: the data split, the targets, the candidate budget and the metrics. Every method is evaluated the same way, the outputs behind each number are kept, and the scoring works for any model, not only MEIDNet. Results are compared within one dataset and one protocol version.

<div class="bench-kpis" markdown="0"><div><b>1</b><span>protocols</span></div><div><b>3</b><span>tasks</span></div><div><b>10</b><span>methods</span></div><div><b>11</b><span>computed here</span></div></div>

## Leaderboards

| dataset | protocol | tasks | models | baselines |
|---|---|---|---|---|
| [Perov-5](perov5.md) | `perov5-v1.1` | [inverse design](perov5.md#inverse-design), [property prediction](perov5.md#property-prediction), [representation](perov5.md#representation) | 5 | 5 |
| [Carbon-24](carbon24.md) | not yet defined | – | – | – |
| [MP-20](mp20.md) | not yet defined | – | – | – |

## Analysis

What the benchmark runs show beyond one number per method: the spread between training seeds, results on materials held out of training, where reconstruction fails, and what the shared space contains.

- **Perov-5:** [Alignment across seeds](perov5-reproduction.md) · [What the runs show](perov5-insights.md) · [Choose a model and generate](perov5-guide.md)

## How a result gets on a leaderboard

1. **Protocol.** Each dataset fixes its tasks in `benchmarks/datasets/<dataset>.json`: splits, property targets, candidate budget, metrics and the direction in which each is better.
2. **Run or score.** `python scripts/benchmarks.py run` evaluates a MEIDNet checkpoint end to end; `python scripts/benchmarks.py score` evaluates the predictions or candidate structures of any other model with the same code.
3. **Record.** One JSON file per method (`benchmarks/submissions/<dataset>/<method>.json`) holds the description, the numbers per task and the folder with the outputs behind them.
4. **Verification.** Numbers computed in this repository carry a record in `benchmarks/verified/`; submitted results are re-scored from their outputs before they are marked as computed here.

## Score any model's generated structures

`meidnet score generated/ --reference data/perov5 [--targets targets.csv] [--mlip]` reports the generation quality of a folder of CIF files from any model in the metric families of LeMat-GenBench (validity, uniqueness, novelty, diversity, distribution, stability, SUN) and MEIDNet's conditional extension (target success, target error, multi-property success, constraint satisfaction, conditional diversity, target coverage). The [compatibility page](compatibility.md) defines every metric and states where this implementation differs from LeMat-GenBench. A run bundle from MEIDNet Matter is scored the same way.

[Contribute a method](../community/contribute.md) · [Benchmark compatibility](compatibility.md) · [Databases by application](../explore/databases.md)
