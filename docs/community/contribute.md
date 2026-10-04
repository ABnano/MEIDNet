# Contribute a method

The benchmarks rank methods under fixed protocols. Any model can take part: the protocol defines the data, the
targets and the metrics, and the scoring code evaluates the outputs of a model whatever produced them. Submissions
go through GitHub, so every number has a public record and a reviewer.

## 1. Produce the outputs

Each task of a protocol asks for one kind of output. For [Perov-5](../benchmarks/perov5.md) (protocol `perov5-v1.1`):

| task | output | format |
|---|---|---|
| property prediction | a prediction for every test material | `predictions.csv`: `id` (the dataset's `material_id`), `pred_heat_all`, `pred_dir_gap` |
| inverse design | 54 candidate structures: 6 per target and chemical family | `candidates.csv`: `id`, `variant`, `target`, `formula`, `elements`, `cif`; the CIFs next to it |
| representation | latent vectors of the test materials | computed by `run` for MEIDNet checkpoints; for other models, contact the maintainer |

The targets, the families and the budget are listed in the [protocol](../benchmarks/perov5.md#protocol).

## 2. Score them

```bash
python scripts/benchmarks.py score perov5 --task property_prediction --predictions predictions.csv
python scripts/benchmarks.py score perov5 --task inverse_design --candidates my_run/candidates.csv
```

`score` prints the metrics of the task as JSON. Inverse design relaxes every candidate with MACE-MP-0 first
(`stability.csv` and `scored.csv` are written next to `candidates.csv`); if MACE is installed in another Python
environment, pass `--mlip-python` or set `MEIDNET_MLIP_PYTHON`.

A MEIDNet checkpoint can run every task at once:

```bash
python scripts/benchmarks.py run perov5 --method meidnet-2k
```

## 3. Write the record

Copy `benchmarks/submissions/_template.json` to `benchmarks/submissions/<dataset>/<method>.json` and fill it in:

| field | what to put |
|---|---|
| `protocol` | the dataset's protocol version, for example `perov5-v1.1` |
| `method` | name, type (`model` or `baseline`), a one-sentence description, parameters, training data, links to paper, code and weights |
| `method.test_in_training` | `true` if the training data included the test split; the row is then marked, because its test scores are not held-out |
| `method.alignment_space` | for the representation task: `encoder` or `projection`, the space in which the model's alignment loss compares the two latents |
| `results` | per task, the JSON printed by `score` |
| `spread`, `n_runs` | optional: the standard deviation of each metric over several training runs (seeds), and their number; `results` then holds the means |
| `artifacts` | per task, a public link to the folder with the outputs (predictions or candidates with their CIFs) |
| `validation_level` | `mlip_validated` for inverse design scored with the MLIP; `dft_validated` only with public DFT outputs in `evidence` |
| `status` | `community_submitted` |

Then run `python scripts/benchmarks.py validate`, which checks every task and metric name against the protocol, and
open a pull request (the template has a checklist). The maintainer re-scores the outputs with the same code; when
the numbers agree, the record is marked as computed here.

If you prefer not to open a pull request, the issue template *Benchmark submission* asks for the same information.

## Add a dataset

A dataset becomes a benchmark when its file in `benchmarks/datasets/` has a `protocol` section:

1. **Data and splits.** Where the data live (`data_dir`, with `train.csv`, `val.csv` and `test.csv`) and which split
   each task uses. Results are only compared within one dataset and one protocol version.
2. **Tasks.** For each task: an `id`, a `name`, a one-sentence `summary`, its `settings` (for inverse design: the
   family, its variants, the property targets, the candidate budget and the stability threshold) and the `headline`
   metric that orders the leaderboard.
3. **Metrics.** For each metric: an `id`, a short `label`, the `unit`, whether higher or lower is `better`, the number of
   `digits` shown and a one-sentence `definition`. Metrics marked `"show": false` appear on each method's page only.

`benchmarks/datasets/perov5.json` is the template. Changing the targets, the budget or a definition makes a new
protocol version; earlier records keep theirs.

## Common mistakes

1. **A different split.** The protocol fixes the split; numbers on another split are not comparable. A model trained on all
   materials can be listed, with `test_in_training` set.
2. **One seed.** Results differ between training seeds ([how much](../benchmarks/perov5-reproduction.md)); give the mean and the
   spread over several runs where you can.
3. **A metric computed differently.** Use `score`, which implements the definitions of the protocol.
4. **Outputs that are not public.** A record without its outputs cannot be re-scored and is not ranked.
5. **A validation level the evidence does not support.** `dft_validated` needs the DFT outputs.

Submissions are reviewed by the author of MEIDNet.
