# What data do I need?

## The checklist

| You need | Format | Notes |
|---|---|---|
| **Structures** | CIF text in a `cif` column of the table, or one `<id>.cif` file per material in a folder | up to `max_sites` atoms per cell (default 20); any elements |
| **Properties** | one or more **numeric** columns | any units; each property is standardised unless you say otherwise |
| **An id** | a column whose values match the CIF file names (if you use files) | `12`, `12.0` and `"12"` are treated as the same id |
| **A family** | the prototype your structures share (e.g. cubic ABX₃) | needed for generation; training without one is possible (`align_to_prototype: false`) |

A table like this is enough:

```
material_id,band_gap,dielectric,cif
mat_001,1.42,18.3,"# generated using pymatgen
data_CsPbBr3
_cell_length_a 5.87 ..."
mat_002,2.16,11.7,"..."
```

CSV, Excel (`.xlsx`) and JSON tables are read; Parquet too once `pyarrow` is installed
(`pip install "meidnet[parquet]"`).

## How much data?

The published model used 11k structures. A few thousand is typical; a few hundred lets you try the pipeline,
but expect rough predictions (the training report tells you how rough).

## What happens to each row

`meidnet check` reads every row exactly as training would and writes `check_report.html` with one line per
reason a row was skipped (unreadable CIF, too many atoms, missing value, does not match the prototype) and
example ids, so every skipped row is accounted for.

## Properties and ranges

MEIDNet can only design for property values it has seen. The check report draws each property's distribution;
the generation report flags targets outside the training range as extrapolation.

## Which family?

- Cubic ABX₃ perovskite → built-in `perovskite_abx3` (variants: oxide, halide, chalcogenide, nitride).
- Rock-salt-ordered double perovskite A₂BB′X₆ → built-in `double_perovskite_a2bbx6`.
- Anything else with a fixed arrangement of sites → [write a family file](../recipes/change-family.md)
  (positions, which elements may occupy which site, their charges, a cell-size rule, rules).
- Mixed prototypes → you can still train (`align_to_prototype: false`) and use the model to predict/screen, but
  generation needs one prototype.
