# The ecosystem

MEIDNet Prism and MEIDNet Matter do two jobs, and connect to what already exists rather than repeating it.

| | MEIDNet Prism | MEIDNet Matter |
|---|---|---|
| **Job** | Learn a method, reproduce it, compare it, benchmark it, implement it. | Bring a dataset and answer "what material should I investigate next?" |
| **You come here to** | read how multimodal learning works, run the published model, score a model against a fixed protocol, contribute a result, use the `meidnet` package. | set property targets and chemistry rules, read whether the data and model support them, search for candidates, read the evidence next to each one, export CIFs and a run bundle. |
| **Address** | [babu09-meidnet.hf.space](https://babu09-meidnet.hf.space/) | [babu09-meidnet-matter.hf.space](https://babu09-meidnet-matter.hf.space/) |

## What MEIDNet works with

**Data.** [Materials Project](https://next-gen.materialsproject.org/), [NOMAD](https://nomad-lab.eu/), the datasets on the [datasets page](explore/datasets.md) and the [31 databases by application](explore/databases.md), and your own tables of structures and properties. Matter reads a table with CIF files; imports from Materials Project and NOMAD are planned.

**Methods.** MEIDNet (this package) and any other model: the [benchmarks](benchmarks/index.md) score the predictions or candidate structures of any method with the same code, and `meidnet score` reports the generation quality of any folder of CIF files ([benchmark compatibility](benchmarks/compatibility.md)). Matter runs MEIDNet as its first backend behind one backend interface.

**Benchmarks.** The MEIDNet protocols per dataset, and metric families named as in [LeMat-GenBench](https://github.com/LeMaterial/lemat-genbench) so that results can be read side by side, with MEIDNet's conditional extension for property-conditioned generation.

**Synthesis knowledge.** Not here: [LeMat-Synth](https://lematerial.org/) and the [Materials Project Synthesis Explorer](https://next-gen.materialsproject.org/synthesis) hold the recipes; Matter will link a candidate to them rather than extract its own.

**Validation.** Machine-learned potentials (MACE through `meidnet screen`), DFT, and experiment. Matter records each candidate's stage on a validation ladder; the benchmarks count DFT-confirmed hits separately from predicted ones.

## The records that travel between them

A candidate leaves Matter as a JSON record (structure, targets, predicted values, domain status, rules, novelty, stability stage, model, dataset, provenance) and as a CIF file. `meidnet score` reads a folder of such CIF files with their `targets.csv`, so a Matter run can be scored on Prism with the same metrics as any other generator's output, and a scored set can go on to MLIP screening, DFT or an experiment.
