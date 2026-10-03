# MEIDNet Benchmarks

Reproducible results for multimodal materials representation and inverse design, **one page per dataset**.
Different datasets are different tasks, so there is no leaderboard across them: compare rows only within a page.

## The evidence ladder

| level | means |
|---|---|
| ○○○○○ generated | the model produced it |
| ●○○○○ ML filtered | it passed the family's rules and the model's own checks |
| ●●○○○ MLIP validated | relaxed and found stable with a machine-learned potential (`meidnet screen`, MACE) |
| ●●●○○ DFT validated | confirmed by density-functional calculations |
| ●●●●○ experimentally validated | synthesised and measured |

Each row also carries a status: **Published** (quoted from the paper), **Community submitted** (a pull request),
**MEIDNet verified** (reproduced here from the submitted configuration). [How to contribute](../community/contribute.md).

## Datasets

- **[Carbon-24](carbon24.md)** — published: structure-representation generalization (not a multimodal benchmark) · 0 result(s), 0 verified
- **[MP-20](mp20.md)** — published: structure-representation generalization (not a multimodal benchmark) · 0 result(s), 0 verified
- **[Perov-5](perov5.md)** — the published multimodal benchmark: alignment, property reconstruction and inverse design · 3 result(s), 0 verified
