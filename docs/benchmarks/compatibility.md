# Benchmark compatibility

Two families of metrics, so that a result here can be read next to results elsewhere.

## Crystal-generation quality: the LeMat-GenBench families

[LeMat-GenBench](https://github.com/LeMaterial/lemat-genbench) (Siron et al., 2025) evaluates crystal generative models in eight families. `meidnet score` reports the same families, from a folder of CIF files produced by any model, with the definitions below. Where this implementation differs from LeMat-GenBench, the table says so; for leaderboard-comparable numbers, run LeMat-GenBench itself.

| family | LeMat-GenBench | `meidnet score` |
|---|---|---|
| validity | charge neutrality, minimum interatomic distance, coordination environment, physical plausibility | charge neutrality (an oxidation-state assignment that sums to zero), closest pair ≥ max(0.8 Å, 0.6 × the sum of the atomic radii), density 0.5–25 g/cm³, cell lengths 1–60 Å, angles 10–170°. Coordination environments are not checked. |
| uniqueness | BAWL fingerprints or StructureMatcher within the set | pymatgen StructureMatcher (ltol 0.2, stol 0.3, angle_tol 5°, primitive cells) |
| novelty | fraction not in LeMat-Bulk (BAWL or StructureMatcher) | against a reference you name (`--reference`: the Perov-5 split, or any CSV with `cif`/`formula` columns): by composition (reduced formula) and by structure (StructureMatcher against the reference entries of the same composition) |
| diversity | Vendi scores and Shannon entropy of elements, space groups, site numbers, physical size | Shannon entropy (bits) and counts of the elements, space groups (spglib, symprec 0.1) and site numbers; the density's mean and spread |
| distribution | JSD of categorical properties, MMD of volume and density, Fréchet distance of MLIP embeddings | Jensen–Shannon distance (base 2) of the element frequencies and of the site numbers against the reference. MMD and Fréchet distances are not computed. |
| stability | energy above the convex hull from several MLIPs (stable ≤ 0, metastable ≤ 0.1 eV/atom) | with `--mlip`: relaxation with MACE-MP and the formation energy per atom against elemental reference phases (`meidnet screen`'s proxy), stable if ≤ 0.1 eV/atom. This is not the energy above the hull. |
| hhi | production and reserve supply risk | not computed |
| sun | stable ∧ unique ∧ novel; MetaSUN | stable ∧ unique ∧ novel by structure, with `--mlip` and a reference with CIFs |

## Conditional inverse-design quality: the MEIDNet extension

A conditional generator is asked for a property; these metrics say whether it delivered. They need `targets.csv` with a `file` column (the CIF file name) and, per property, `<p>_target` and optionally `<p>_value`, the value the submitter reports for the structure, with a `source` column saying how it was obtained (`dft`, `experiment`, `predicted`). Without a value, `--model <checkpoint>` predicts it with a MEIDNet model, and the report labels those values model-predicted.

| metric | definition |
|---|---|
| target success rate | share of structures with \|value − target\| ≤ tolerance, per property; the tolerance is `--tolerance p=…` or 5 % of the reference's range |
| target error | mean \|value − target\| |
| multi-property success | share with every targeted property within tolerance |
| constraint success | valid structures (the validity family) among the successes |
| conditional diversity | distinct compositions among the successes, over the successes |
| target coverage | distinct target vectors with at least one success, over the distinct targets |
| interpolation share | targets inside the reference's property range (needs property columns in the reference) |

Oracle efficiency, the number of candidates evaluated per success, is a property of a run, not of a set of structures: the Perov-5 protocol reports it as the candidate budget and the delivered count.

## Running it

```bash
pip install "meidnet>=2.3"                       # or: pip install "meidnet[stability]" for --mlip
meidnet download-data                            # Perov-5 as a reference (data/perov5/)
meidnet score generated/ --reference data/perov5
meidnet score generated/ --reference data/perov5 --targets targets.csv --tolerance dir_gap=0.3
meidnet score generated/ --reference data/perov5 --mlip --out report.json
```

`generated/` is a folder of CIF files (any depth) or a CSV with a `cif` column. The report prints as a table; `--out` writes the JSON with the per-structure checks. A run bundle from MEIDNet Matter contains `cifs/` and `targets.csv` in this layout.

Example: the 26 candidate structures shipped with the paper (`examples/perov5/paper_results`) scored against the full Perov-5 set, without MLIP, in three seconds:

```text
| validity     | valid (all checks)            | 100.0 %            |
| uniqueness   | unique structures             | 24 of 26 (92.3 %)  |
| novelty      | new compositions vs perov5    |  69.2 %            |
| novelty      | new structures vs perov5      |  69.2 %            |
| diversity    | elements (entropy)            | 25 (3.48 bits)     |
| diversity    | space groups (entropy)        | 1 (0.00 bits)      |
| distribution | element JSD vs reference      | 0.717              |
```

One space group, because every structure is a cubic ABX₃ prototype: the diversity family shows where a prototype-family generator sits next to a free-form one.

Numbers from the metric families go into a submission under `results.generation`; the [contribute page](../community/contribute.md) has the record layout.
