# MEIDNet Benchmarks

Reproducible results for multimodal materials representation and inverse design, **one leaderboard per dataset**. Different datasets are different tasks, so there is no ranking across them: compare rows only within a page. The idea follows [Matbench Discovery](https://matbench-discovery.materialsproject.org): fixed data, inspectable submissions, plots and an evidence level per row.

<div class="bench-kpis" markdown="0"><div><b>3</b><span>datasets</span></div><div><b>5</b><span>results</span></div><div><b>2</b><span>reproduced here</span></div><div><b>1</b><span>DFT or experiment</span></div></div>

## Datasets

| dataset | role | results | reproduced | highest evidence |
|---|---|---|---|---|
| [Carbon-24](carbon24.md) | published: structure-representation generalization (not a multimodal benchmark) | 0 | 0 | – |
| [MP-20](mp20.md) | published: structure-representation generalization (not a multimodal benchmark) | 0 | 0 | – |
| [Perov-5](perov5.md) | the published multimodal benchmark: alignment, property reconstruction and inverse design | 5 | 2 | DFT validated |

## The evidence ladder

| level | means |
|---|---|
| ○○○○○ generated | the model produced it |
| ●○○○○ ML filtered | it passed the family's rules and the model's own checks |
| ●●○○○ MLIP validated | relaxed and found stable with a machine-learned potential (`meidnet screen`, MACE) |
| ●●●○○ DFT validated | confirmed by density-functional calculations |
| ●●●●○ experimentally validated | synthesised and measured |

<div class="bench-chart" markdown="0"><svg class="chart" viewBox="0 0 420 76" role="img"><title>results per evidence level (all datasets)</title><text class="tick" x="102" y="20" text-anchor="end">generated</text><rect class="bar" x="108" y="9" width="242.0" height="14"/><text class="val" x="355.0" y="20">3</text><text class="tick" x="102" y="42" text-anchor="end">MLIP validated</text><rect class="bar" x="108" y="31" width="80.7" height="14"/><text class="val" x="193.7" y="42">1</text><text class="tick" x="102" y="64" text-anchor="end">DFT validated</text><rect class="bar" x="108" y="53" width="80.7" height="14"/><text class="val" x="193.7" y="64">1</text></svg></div>

## Status of a row

**Published** = quoted from the paper · **Community submitted** = a pull request, validated by CI · **MEIDNet verified** = reproduced here from the submitted configuration (`python scripts/benchmarks.py reproduce <id>`). [How to contribute](../community/contribute.md) · [Databases by application](../explore/databases.md)

## Latest results

| date | result | dataset | category | evidence | status |
|---|---|---|---|---|---|
| 2026-10-03 | [MLIP screening of the shipped paper candidates (MACE-MP-0)](results/paper-results-mace-screen.md) | [Perov-5](perov5.md) | Validation level | <span class="ladder" title="MLIP validated">●●●○○</span> MLIP validated | <span class="bstatus sub">Community submitted</span> |
| 2026-10-03 | [Shipped checkpoint re-evaluated on the training split (this code)](results/shipped-checkpoint-train-split.md) | [Perov-5](perov5.md) | Representation quality | <span class="ladder" title="generated">●○○○○</span> generated | <span class="bstatus ver">MEIDNet verified</span> |
| 2026-10-03 | [Shipped checkpoint re-evaluated on the held-out validation split (this code)](results/shipped-checkpoint-val-split.md) | [Perov-5](perov5.md) | Representation quality | <span class="ladder" title="generated">●○○○○</span> generated | <span class="bstatus ver">MEIDNet verified</span> |
| 2026-05-29 | [MEIDNet (paper): inverse design of perovskites from property targets](results/paper-inverse-design.md) | [Perov-5](perov5.md) | Conditional design | <span class="ladder" title="DFT validated">●●●●○</span> DFT validated | <span class="bstatus pub">Published (from the paper)</span> |
| 2026-05-29 | [MEIDNet (paper): alignment of structure and property latents on Perov-5](results/paper-representation.md) | [Perov-5](perov5.md) | Representation quality | <span class="ladder" title="generated">●○○○○</span> generated | <span class="bstatus pub">Published (from the paper)</span> |
