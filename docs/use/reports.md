# Reading the reports

Each command writes a self-contained HTML file in `runs/<name>/`. All three open with a one-sentence
**verdict** (green / amber / red), show the evidence, and end with what to do next.

## `check_report.html`

- **Verdict**: how many rows are usable; the most common problem if many were skipped.
- **What MEIDNet read**: table, columns, structure source, family and how many structures were re-ordered to
  the prototype.
- **Rows that were skipped**: one row per reason with counts and example ids, and a "how do I fix these?" box.
- **Your properties**: histogram, min/median/max, and warnings (e.g. "72 % of band-gap values are 0 — the model
  sees few examples of other values").
- **Your structures**: atoms per cell, most common elements.

## `training_report.html`

- **Verdict**: are the properties predicted well *from structure alone*?
- **How accurate**: per property, typical error (MAE), natural spread (std), R², and a word — *good* if the error
  is under a quarter of the spread, *fair* under a half, *weak* otherwise — with predicted-vs-true plots.
- **Did the two modalities align**: retrieval accuracy (a structure's own property vector is its nearest match
  x % of the time) and the cosine curve. Inverse design depends on this.
- **Training curves** and notes (e.g. the alignment ramp longer than training).

## `generation_report.html`

- **Verdict**: how many candidates, and whether any rely on extrapolated predictions.
- Per target: the **funnel** (compositions alive after each rule — the biggest drop is the rule that limits the
  family most), the **candidate cards**, and **examples of rejected compositions** with the rule and the
  measured value.
- A candidate card shows: elements per site, cell edge, round found, a **gauge** per objective (training range
  as a track, target as a tick, prediction as a dot), the **checklist** with each rule's value and allowed
  window (hover for the explanation), and **warnings**: prediction outside the training range, or a latent far
  from where training latents live (predictions less reliable).
- **Where the search went**: latents before and after optimisation projected to two dimensions.

## `candidates.csv` and `generation.json`

The CSV has one row per candidate with targets, predictions, elements, cell edge, every rule's value, score and
file name. The JSON holds the full funnel counts, rejected examples and settings — everything the report shows.
