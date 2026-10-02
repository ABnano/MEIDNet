# MEIDNet Studio — the live workbench

```bash
meidnet studio                 # the published perovskite model
meidnet studio meidnet.yaml    # your project
```

A page opens in your browser. The workflow is drawn as a graph; click a node to edit it. **Whatever you change,
the nodes after it update at once** and a ribbon says what changed and what it did — the way a LabVIEW diagram
shows data flowing after you turn a knob.

```
 Data ──► Model ──► Family ──► Rules ──► Targets ──► Search ──► Candidates
 11,356    MAE       halide     5 rules   Eg 2.0     idle       0 found
 materials 0.17 eV   924 comps  27 pass   ΔHf −0.1
```

## What is live, and how

For a prototype family the set of possible compositions is finite (924 for halide perovskites, 10,340 for
halide double perovskites). When you open a family the server builds this **design space** once: every
composition on the prototype, the value of each rule's descriptor (tolerance factor, octahedral factor, …) and
the model's predicted properties from the structure encoder. From then on, the page can answer instantly:

| You change | You see immediately |
|---|---|
| a rule's limit (slider) | how many compositions still pass that rule and all rules; the histogram of the descriptor with the window shaded; the funnel |
| an element (click a chip to exclude) | compositions removed, new counts, new best matches |
| a target | the compositions predicted closest; the target drawn on the predicted-property histogram and scatter; an extrapolation warning if outside the training range |
| the comparison kind (as close as possible / at most / at least) | the ranking |
| anything, after a search | which of the found candidates **would now be rejected** |

Descriptor values are computed by the same Python functions that `meidnet generate` uses, so what the page
shows is what the search enforces.

## The two directions of the model

The live tables use **structure → property** (encode the prototype structure, decode its properties): fast,
and it scores *every* composition. The **Search** node runs the paper's **property → structure** latent
optimisation and shows its progress (target, round, step, loss), the log, and each candidate as it is found,
with its checklist. Both views are of the same network; comparing them tells you whether the search found what
the encoder considers best, and whether the predictions agree.

## Panels

- **Data** — how many materials were usable, why rows were skipped, property distributions.
- **Model** — properties, units, training ranges, validation errors; what "predicted" means.
- **Family** — prototype sites, element chips per site group with their charges, cell-size rule.
- **Rules** — each rule with its explanation, parameters, pass count and descriptor histogram; add a
  *predicted-property window* rule; the funnel.
- **Targets** — one block per objective: target slider, comparison kind, weights; predicted-property scatter
  of all compositions (blue pass, grey rejected, ★ found by the search). Click any point for its checklist.
- **Search** — budget (candidates, latents per round, rounds, steps), rough time estimate, Run/Stop, progress,
  log, link to the full report.
- **Candidates** — cards with elements, cell, gauges, checklist, warnings, CIF links.

**Export meidnet.yaml** writes the configuration exactly as the page has it — rules disabled on the page become
wide-open windows, excluded elements become `exclude_elements`, changed limits become `overrides` — so the
command line reproduces the run.

## Static copy for a website

```bash
meidnet studio --export-static docs/studio.html
```

embeds the state and design spaces into one HTML file. Everything works without a server except running a
new search — useful for a plain web host. The [hosted Studio](https://babu09-meidnet.hf.space/) is the full
server instead (`meidnet studio --public --host 0.0.0.0`): every visitor gets their own search session, and
budgets are capped so the shared machine stays responsive.
