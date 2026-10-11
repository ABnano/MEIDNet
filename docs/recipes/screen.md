# Screen candidates with MACE

```bash
pip install "meidnet[stability]"            # ase + mace-torch (~500 MB of weights on first use)
meidnet screen runs/my_oxides/generation --train-csv materials.csv
```

For each CIF: relax cell and positions with the MACE-MP-0 universal potential, compute the formation energy
per atom against elemental reference phases, and report

- **S** passes the formation-energy filter — ΔH_f ≤ 0.10 eV/atom against the elemental phases (`--threshold`); the report
  prints it as STABLE,
- **U** unique — no structural duplicate among the candidates,
- **N** novel — reduced formula absent from the training table.

Results go to `stability.csv` in the folder. Structures with |ΔH_f| > 5 eV/atom are flagged as artefacts and
excluded from the rates. The reference phases and GGA-style O/N corrections are those of the paper.

The S is not stability in the usual sense. The common 0.1 eV/atom threshold for metastable, possibly synthesisable
materials concerns the energy above the convex hull of all competing phases; the formation energy against the elements is
a weaker test, so a candidate can pass it and still decompose into other compounds. A stability statement needs the energy
above the hull (DFT, or an MLIP against a reference set of competing phases).

This is a first filter, not a verdict: MACE formation energies carry ~0.1 eV/atom uncertainty, and a cubic
prototype may relax to a lower-symmetry structure.
