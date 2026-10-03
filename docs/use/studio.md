# MEIDNet Studio — the live workbench

```bash
meidnet studio                 # the published perovskite model
meidnet studio meidnet.yaml    # your project
```

A page opens in your browser. The workflow is drawn as a strip of seven coloured blocks; click a block to open
it. **Whatever you change, the blocks after it update at once**, and a line under the strip says, in words, what
the change did to each later block — the way a LabVIEW diagram shows data flowing after you turn a knob.

No installation? Use the [hosted Studio](https://babu09-meidnet.hf.space/) — the same page, running on a shared
server.

```
 Data ──► Model ──► Family ──► Rules ──► Targets ──► Search ──► Candidates
 11,356    MAE       halide     5 rules   Eg 2.0     idle       0 found
 materials 0.17 eV   924 comps  27 pass   ΔHf −0.1
```

## Reading the workflow strip

Each block has its own colour, used everywhere on the page (its panel, its charts, its chips in the flow chain):

| Block | Colour | What it holds |
|---|---|---|
| Data | blue | the table of materials the model learns from |
| Model | orange | the trained network (published or yours) |
| Family | green | the crystal prototype and the elements allowed on each site |
| Rules | amber | the hard checks every candidate must pass |
| Targets | pink | the property values you want |
| Search | dark green | the latent search of the paper |
| Candidates | violet | what the search found |

- **The dot in the corner of a block** tells its state: grey = idle, green = fine, amber = just changed or needs a
  look (for example a target outside the training range), red = error, pulsing = running.
- **The two lines inside a block** are its live status: "924 comps", "27 pass all", "MAE 0.17", "running".
- **The label on each arrow** says what flows to the next block: "11,356 materials · 2 properties",
  "924 compositions", "27 pass all rules", "3 found".
- **Moving dots on the arrows** appear after every change: they travel from the block you edited to every block
  it reaches, and those blocks flash. This is the quickest way to see what depends on what.

Dashed pink lines are always a target; a violet ★ is always something the search found; green ✓ means passes.

## The flow chain and the flow log

Under the strip, the **flow chain** repeats the last change in words, block by block, for example:

> **Rules:** Goldschmidt tolerance factor max 1.05 → 1 ➜ **Rules:** pass all rules 27 → 23 (−4) ➜
> **Targets:** best match CsSnBr₃ → CsGeBr₃ ➜ **Candidates:** 1 of 3 found candidates would now be rejected

Click a step to open that block.

The **Flow log** below it keeps the last 60 changes. Click an entry to replay its flow on the strip.

## What is live, and how

For a prototype family the set of possible compositions is finite (924 for halide perovskites, 10,340 for
halide double perovskites). When you open a family the server builds this **design space** once: every
composition on the prototype, the value of each rule's descriptor (tolerance factor, octahedral factor, …) and
the model's predicted properties from the structure encoder. From then on, the page can answer instantly:

| You change | You see immediately |
|---|---|
| a rule's limit | how many compositions still pass that rule and all rules; the histogram of the descriptor with the window shaded; the funnel |
| an element (click a chip to exclude it) | compositions removed, new counts, new best matches |
| a target | the compositions predicted closest; the target drawn on the predicted-property histogram and scatter; an extrapolation warning if it lies outside the training range |
| the comparison kind (as close as possible / at most / at least) | the ranking |
| anything, after a search | which of the found candidates **would now be rejected** |

Descriptor values are computed by the same Python functions that `meidnet generate` uses, so what the page
shows is what the search enforces.

## The two directions of the model

The live tables use **structure → property** (encode the prototype structure, decode its properties): fast,
and it scores *every* composition. The **Search** block runs the paper's **property → structure** latent
optimisation and shows its progress (target, round, step, loss), the log, and each candidate as it is found,
with its checklist. Both views are of the same network; comparing them tells you whether the search found what
the encoder considers best, and whether the predictions agree.

## The blocks

- **Data** — how many materials were usable, why rows were skipped, property distributions, the elements
  present; *Bring your own data* (below).
- **Model** — properties, units, training ranges, validation errors, loss and alignment curves; *Train your own
  model* (below).
- **Family** — prototype sites with a rotatable 3D preview of the cell, element chips per site group with their
  charges (click to exclude), cell-size rule.
- **Rules** — each rule with its explanation, parameters, pass count and descriptor histogram; add a
  *predicted-property window* rule; the funnel.
- **Targets** — one card per objective: target value, comparison kind, weights; the predicted-property scatter
  of all compositions (coloured = passes, grey = rejected, ★ = found by the search). Click any point or table row
  for its checklist and its crystal in 3D.
- **Search** — budget (candidates, latents per round, rounds, steps), a rough time estimate, Run/Stop, progress,
  log, link to the full report.
- **Candidates** — one card per candidate: a rotatable 3D cell, elements, gauges of predicted values against the
  targets, the rule checklist, warnings, CIF links.

Crystals are drawn by a small built-in viewer: drag to rotate, double-click to spin.

## Beginner view and Researcher mode

The page opens in the **beginner view**: every block has an **Input ➜ Logic ➜ Output** strip with live numbers
("924 compositions ➜ 5 hard rules, applied in order ➜ 27 pass every rule") and the name of the Python function that
does the work, a short **In short** explanation, and a **glossary** in the side panel (composition, rule,
target, latent space, extrapolation).

The **Researcher mode** switch in the header trades these for the technical view: the **✎ Edit as text** YAML
drawer, and a **Behind the scenes** panel in every block with the `meidnet.yaml` and the Python of that block.
The choice is remembered by your browser.

## Behind the scenes

At the bottom of every block, **Behind the scenes** shows the same settings as the part of `meidnet.yaml` they
come from and as the Python that does the same thing — with the values currently on the page. Copy either into
your own project; nothing on the page is hidden from the command line.

## Bring your own data

The Data block has an **adapter**: it maps your column names to what MEIDNet expects. Nothing in your files is
changed.

1. **Upload** a table — CSV, Excel (`.xlsx`) or JSON, one row per material — with an id column, numeric property
   columns and the structures, either as a column of CIF text or as a zip of `<id>.cif` files (select both files
   together). Parquet works too when `pyarrow` is installed.
2. **Map the columns.** The Studio suggests the id column, the CIF column and the numeric property columns; pick
   the properties you want, give each a unit (eV, eV/atom, …) and optionally a label, and choose the family (and
   variant) your structures belong to. *Align to prototype* re-orders each structure's atoms onto the family's
   sites, which generation needs; raise the *prototype tolerance* if many rows are skipped as "does not match the
   prototype".
3. **Check my data.** Every row is parsed and checked; you see how many are usable, why the others were skipped
   (with examples), the distribution of each property and the elements present.
4. **Train** in the Model block: choose the number of epochs and press ▶ Train. The loss and alignment curves
   grow while it trains; at the end the validation errors appear and **every block switches to your model and
   your properties** — the design space is re-scored, the targets are your properties. Each property's typical
   error (MAE) is judged in words against the spread (standard deviation) of that property in your data — *good* below a quarter of
   the spread, *fair* below half, *weak* above — the same rule the training report uses; "matched correctly" is
   how often a validation structure is matched to its own properties.
5. Switch between **your model** and the **published model** at any time in the Model block. *Start over*
   removes your upload and model from the session.

A few epochs give a rough model in a minute or two; 100–200 epochs are typical for real work — run
`meidnet train` locally (with a GPU if you have one) and open the result with `meidnet studio meidnet.yaml`.

!!! note "On the hosted Studio"
    Each browser tab has its own private session: other visitors never see your data, model or candidates, and
    a session's files are deleted after an hour without activity. The shared machine allows up to 1,500 rows and
    8 MB per upload, 30 training epochs, 20 atoms per cell, and two jobs (training or search) at a time across
    all visitors; search budgets are capped too. Run the Studio on your own computer to lift every limit.

## Edit the configuration as text

**✎ Edit as text** in the header opens a drawer with the `generation` section of `meidnet.yaml` exactly as the
blocks have it: family, variant, excluded elements, rule overrides, extra rules, objectives, targets and search
budget. Change anything and press **Apply** — the blocks update and the flow chain shows what changed in each.

- **Validate only** checks without applying. Errors name the exact setting, for example
  `steps: Input should be greater than or equal to 1`.
- On the hosted Studio, values above the shared limits are accepted but capped, and a note says so:
  `rounds 99 → 6 (limit on this shared server)`.
- Predicted-property windows added in the Rules block appear as `extra_constraints`, so the file round-trips:
  apply it, download it, run it with `meidnet generate`.

**⬇ Download meidnet.yaml** (also in the Search block) writes the whole configuration — rules switched off on
the page are listed under `disabled_rules`, excluded elements become `exclude_elements`, changed limits become
`overrides` — so the command line reproduces exactly what the page shows. Settings the blocks do not show (for
example search terms set in your own `meidnet.yaml`) are kept as they are.

## Explore in 3D

Buttons marked 🧊 open the **3D explorer**: a map with one point per structure, linked to a 3D viewer — the
design space of the family, the candidates of a search, or the training data. See
[Explore in 3D](explore-3d.md).

## Deep links

Add to the address to open the page at a given place:

| Address ends with | Opens |
|---|---|
| `?panel=rules` | the Rules block (any block: `data`, `model`, `family`, `rules`, `targets`, `search`, `candidates`) |
| `?explore=space` | the 3D explorer on the design space (`candidates` or `data` work too) |

Both can be combined: `?panel=targets&explore=space`.

## Dark mode

The 🌙 / ☀️ button in the header switches between the light and the dark theme; your browser remembers the choice.

## Static copy for a website

```bash
meidnet studio --export-static docs/studio.html
```

embeds the state and design spaces into one HTML file. Everything works without a server except uploading,
training and running a new search — useful for a plain web host. The
[hosted Studio](https://babu09-meidnet.hf.space/) is the full server instead:

```bash
meidnet studio --public --host 0.0.0.0 --port 7860 --run-root /tmp/runs --docs-dir site
```

`--public` gives every visitor a private session and caps the budgets so the shared machine stays responsive;
`--docs-dir` also serves a built copy of this documentation at `/docs/`.
