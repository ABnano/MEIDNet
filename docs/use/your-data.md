# Bring your own dataset

This page takes a table of structures and properties to designed candidates. Every step writes a report that
explains what happened; nothing requires Python.

## 0. Install

```bash
pip install meidnet
```

## 1. Describe your data: `meidnet init`

```bash
meidnet init --name my_oxides --table materials.csv \
             --id-column material_id --cif-column cif \
             --properties band_gap dielectric \
             --family perovskite_abx3 --variant oxide
```

This writes a commented `meidnet.yaml`. Open it: every line says what it does. If your CIFs are files instead
of a column, set `cif_column: null` and `structures_dir: structures/`.

```yaml
data:
  table: materials.csv
  id_column: material_id
  cif_column: cif
  properties:
    - {column: band_gap,   unit: eV}
    - {column: dielectric, unit: ""}
  val_fraction: 0.1
  max_sites: 20
  align_to_prototype: true
```

## 2. Is it usable? `meidnet check`

```bash
meidnet check meidnet.yaml
```

```
412 of 430 materials usable.
  skipped     14  does not match the perovskite_abx3 prototype   e.g. m_031, m_118, m_204
  skipped      4  missing property value                          e.g. m_077, m_300
report: runs/my_oxides/check_report.html
```

The report shows the verdict, the distribution of each property, the elements present and, for each skip
reason, how to fix it (for example raise `data.prototype_tolerance` for distorted cells).

## 3. Learn the latent space: `meidnet train`

```bash
meidnet train meidnet.yaml            # 200 epochs by default
meidnet train meidnet.yaml --epochs 5 # a quick smoke test first
```

`training_report.html` answers three questions in plain words: *how accurate is each property prediction*
(error vs natural spread → good / fair / weak), *did the two modalities align* (retrieval accuracy), and *what
were the training curves*. The model is saved as `runs/my_oxides/model.pt` with the property names, units and
normalisation inside; `meidnet info runs/my_oxides/model.pt` describes it.

!!! tip "Time"
    About 21 s per epoch per 11k structures on a laptop GPU; roughly 10× slower on CPU. Use Colab's free GPU
    ([notebook 02](../start/colab.md)) if you have none.

## 4. Design: `meidnet generate`

Set the targets in `meidnet.yaml`:

```yaml
generation:
  family: perovskite_abx3
  variant: oxide
  objectives:
    - {property: band_gap,   loss: l2,       weight: 10000}
    - {property: dielectric, loss: at_least, weight: 5000}
  targets:
    - {band_gap: 2.0, dielectric: 20}
    - {band_gap: 3.0, dielectric: 20}
  per_target: 4
  exclude_elements: [Pb, Cd]
```

```bash
meidnet generate meidnet.yaml
```

`generation_report.html` shows, per target, the *funnel* (how many attempts each rule removed), one card per
candidate (elements, cell, each rule's measured value and window, predicted vs target gauges, warnings about
extrapolation) and examples of rejected compositions. CIFs and `candidates.csv` are in
`runs/my_oxides/generation/`.

## 5. Explore live: `meidnet studio`

```bash
meidnet studio meidnet.yaml
```

Change a rule's limit, exclude an element or move a target and see immediately how many compositions pass
and which are predicted closest; run searches and export the YAML. [Studio guide](studio.md).

## 6. Confirm

Predicted properties are estimates. `meidnet screen runs/my_oxides/generation` (MACE universal potential,
optional extra) gives a first stability filter; DFT or experiment has the last word.
