# Family files

A family file is YAML with these keys. `meidnet families NAME` prints a summary and the constraints with their
explanations; errors name the offending key or element.

| key | required | meaning |
|---|---|---|
| `name`, `title`, `description` | name | identification; `description` appears in the Studio |
| `prototype.lattice` | yes | `cubic`, `fcc_primitive`, `bcc_primitive`, or explicit `a, b, c, alpha, beta, gamma` |
| `prototype.reference_a` | | typical cubic cell edge (Å), used by the `cubic_cell` search term |
| `prototype.sites[]` | yes | `{group, frac}` in decoder slot order; fractional coordinates |
| `groups.<G>.description` | | sentence shown in reports |
| `groups.<G>.elements` | yes | every element the group may hold (all variants) |
| `groups.<G>.sample` | | subset offered to the final element choice (default: `elements`) |
| `groups.<G>.oxidation_states` | | `{element: [charges]}` used for charge balance and neutrality bias |
| `sampling_order` | | order in which groups are chosen; the **last** is restricted to charge-balancing elements |
| `lattice.rule` | | `bond_sum` (`a = factor × Σ r_ionic` of `groups`, clipped to `min..max`) or `fixed` |
| `variants.<V>.groups` | | per-variant `elements`, `sample`, `oxidation_states` of any group |
| `variants.<V>.params` | | `{rule_or_term_name: {param: value}}` applied to search terms and constraints |
| `require_variant` | | default true: a variant must be chosen when variants exist |
| `search_terms[]` | | `{name, …params}` soft penalties during the latent search |
| `logit_transforms[]` | | `{name, …params}` edits of the decoder's element scores (e.g. `neutrality_bias`) |
| `constraints[]` | | `{name, …params}` hard rules; `min_distance` runs before symmetry refinement, the rest after |
| `refine_symmetry`, `symprec` | | run spglib refinement on candidates (default true, 0.05) |

User-side changes without editing the file: `generation.variant`, `exclude_elements`, `only_elements`,
`overrides` (`{name: {param: value}}` for any search term or constraint).

The built-in files are the complete reference: [`perovskite_abx3.yaml`](https://github.com/ABnano/MEIDNet/blob/main/meidnet/families/perovskite_abx3.yaml),
[`double_perovskite_a2bbx6.yaml`](https://github.com/ABnano/MEIDNet/blob/main/meidnet/families/double_perovskite_a2bbx6.yaml).
