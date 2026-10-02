# Exclude or restrict elements

```yaml
generation:
  exclude_elements: [Pb, Cd, Hg]           # never used, on any site
  only_elements:                           # restrict a site group to a shortlist
    B: [Ti, Zr, Hf, Sn]
```

Both are applied to the family before the search starts, so the decoder cannot even propose an excluded
element. The Studio's element chips do the same thing (click to toggle) and show the counts change.

To change *which elements a family allows at all*, or their oxidation states, copy the family file and edit the
`groups:` section — see [Change the material family](change-family.md).
