# Add a property

MEIDNet's property modality is a vector of any length. Adding a property is a data change, not a code change.

1. Add the column to your table.
2. List it under `data.properties` (label and unit are for the reports; `normalize: true` is the default and
   recommended when properties have different scales):

    ```yaml
    data:
      properties:
        - {column: band_gap,     label: Band gap,          unit: eV}
        - {column: formation_e,  label: Formation energy,  unit: eV/atom}
        - {column: dielectric,   label: Dielectric constant}
    ```

3. `meidnet check` → `meidnet train`. The training report rates each property separately.
4. Use it in `generation.objectives` and `targets`.

Properties with many missing values: rows with a missing value are skipped (the check report counts them).
Fill them, or drop the property.

!!! note "The published model"
    The Perov-5 checkpoint has exactly two properties (formation enthalpy, direct band gap) and cannot steer
    others; train your own model to add some.
