# The configuration file

`meidnet.yaml` holds everything a run depends on. One file = one reproducible experiment: it is copied into
every output folder and stored inside `model.pt`.

```yaml
name: my_oxides                 # outputs → runs/my_oxides/
plugins: []                     # Python files with custom rules (optional)

data:        # where the structures and properties come from        → meidnet check
model:       # size of the network (defaults are the paper's)
training:    # epochs, batch size, learning rate, alignment schedule → meidnet train
generation:  # family, objectives, targets, rules overrides, budget  → meidnet generate
```

Rules of thumb:

- **Unknown keys are errors.** A typo such as `epocs:` stops the run with a message naming the key.
- **Paths are relative to the YAML file**, so a project folder can be moved or shared.
- **Defaults reproduce the paper.** Leave a section out and the published settings apply.
- `meidnet schema` prints the JSON Schema (editors such as VS Code use it for completion and validation).

The complete list of settings with their meaning and defaults is in the [configuration reference](../reference/config.md).

## The four sections in one picture

```yaml
data:
  table: materials.csv            # one row per material
  properties: [{column: band_gap, unit: eV}, {column: dielectric}]
  align_to_prototype: true        # atoms re-ordered to the family prototype

training:
  epochs: 200
  contrastive_weight: 5.0         # how strongly structure and property latents are pulled together

generation:
  family: perovskite_abx3
  variant: oxide
  objectives:                     # what to steer, and how to compare prediction with target
    - {property: band_gap, loss: l2, weight: 10000}
  targets:                        # one search per entry
    - {band_gap: 2.0}
  overrides:                      # change a family rule's parameters without editing the family file
    tolerance_factor: {min: 0.85, max: 1.0}
  exclude_elements: [Pb]
```
