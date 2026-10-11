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

What the rows contain matters more than how many there are. Measured on the case studies of
[MEIDNet Matter](https://babu09-meidnet-matter.hf.space/limits#data):

| to do this | what it needs | measured |
|---|---|---|
| predict a property from structure | a well-posed property: continuous, few zero values, few materials sharing one property profile | 166 training structures read a band gap with r 0.97 and a 0.65 eV error (34 test structures); 897 with 35 % zero gaps fell short on telling metals from non-metals |
| screen an enumerated family | data that fit one family, and a property model that passes | 166 to 897 training structures |
| generate | one prototype, and hundreds of distinct compositions per element for the decoder | Perov-5 generates; data with 11 to 48 compositions per element went to screening |

A few hundred structures train a property model, not a generator: with 236 structures of 40 elements (11 compositions
per element), the decoder rebuilt none of the test compositions, and every candidate came from screening. Count the rows
that carry the property: Perov-5 is mostly metals, and 441 of the 11,356 structures of its training split have a
non-zero band gap. `meidnet check` warns below 200 usable rows; the training report's note below 500 training materials
is a rule of thumb. [Scope, limitations and roadmap](../understand/limits.md)

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
