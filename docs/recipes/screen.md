# Screen stability with MACE

```bash
pip install "meidnet[stability]"            # ase + mace-torch (~500 MB of weights on first use)
meidnet screen runs/my_oxides/generation --train-csv materials.csv
```

For each CIF: relax cell and positions with the MACE-MP-0 universal potential, compute the formation energy
per atom against elemental reference phases, and report

- **S** stable — ΔH_f ≤ 0.10 eV/atom (Materials Project's "potentially synthesisable" criterion; `--threshold`),
- **U** unique — no structural duplicate among the candidates,
- **N** novel — reduced formula absent from the training table.

Results go to `stability.csv` in the folder. Structures with |ΔH_f| > 5 eV/atom are flagged as artefacts and
excluded from the rates. The reference phases and GGA-style O/N corrections are those of the paper.

This is a first filter, not a verdict: MACE formation energies carry ~0.1 eV/atom uncertainty, and a cubic
prototype may relax to a lower-symmetry structure.
