# MEIDNet Benchmarks

Standardised tasks for multimodal materials models, each with a fixed protocol: the data split, the targets, the candidate budget and the metrics. Every method is evaluated the same way, the outputs behind each number are kept, and the scoring works for any model, not only MEIDNet. Results are compared within one dataset and one protocol version.

<div class="bench-kpis" markdown="0"><div><b>1</b><span>protocols</span></div><div><b>3</b><span>tasks</span></div><div><b>8</b><span>methods</span></div><div><b>9</b><span>computed here</span></div></div>

## Leaderboards

| dataset | protocol | tasks | models | baselines |
|---|---|---|---|---|
| [Perov-5](perov5.md) | `perov5-v1` | [inverse design](perov5.md#inverse-design), [property prediction](perov5.md#property-prediction), [representation](perov5.md#representation) | 3 | 5 |
| [Carbon-24](carbon24.md) | not yet defined | – | – | – |
| [MP-20](mp20.md) | not yet defined | – | – | – |

## How a result gets on a leaderboard

1. **Protocol.** Each dataset fixes its tasks in `benchmarks/datasets/<dataset>.json`: splits, property targets, candidate budget, metrics and the direction in which each is better.
2. **Run or score.** `python scripts/benchmarks.py run` evaluates a MEIDNet checkpoint end to end; `python scripts/benchmarks.py score` evaluates the predictions or candidate structures of any other model with the same code.
3. **Record.** One JSON file per method (`benchmarks/submissions/<dataset>/<method>.json`) holds the description, the numbers per task and the folder with the outputs behind them.
4. **Verification.** Numbers computed in this repository carry a record in `benchmarks/verified/`; submitted results are re-scored from their outputs before they are marked as computed here.

[Contribute a method](../community/contribute.md) · [Databases by application](../explore/databases.md)
