# Develop with MEIDNet

`meidnet` is the reference implementation of the method: one shared latent space for crystal structures and their properties, a prototype-family design space checked by chemistry rules, and a search in the latent space for candidates with the properties you want. Everything on this site runs on it.

```bash
pip install meidnet            # Python 3.10+; CPU is enough
meidnet demo                   # the published Perov-5 model, three oxide perovskites in a few minutes
meidnet studio                 # the same workflow in your browser
```

## Where to start

| I want to | Page |
|---|---|
| see the whole workflow once | [5-minute quickstart](start/quickstart.md) |
| know whether my data fits | [What data do I need?](start/what-data.md), [bring your own dataset](use/your-data.md) |
| train and design without installing anything | [Run in Colab](start/colab.md), [the Studio](use/studio.md) |
| change what the search looks for | [targets](recipes/change-targets.md), [properties](recipes/add-property.md), [elements](recipes/elements.md), [family](recipes/change-family.md), [rules](recipes/add-constraint.md) |
| check candidates with a machine-learned potential | [Screen stability with MACE](recipes/screen.md) |
| score my own model's structures | [Benchmark compatibility](benchmarks/compatibility.md) |
| call it from Python | [Python API](reference/api.md), [the configuration file](reference/config.md), [family files](reference/families.md) |
| read the reports | [Reading the reports](use/reports.md), [interpreting a candidate](understand/interpretability.md) |

## The package

- **Source:** [github.com/ABnano/MEIDNet](https://github.com/ABnano/MEIDNet) (MIT). Issues and pull requests are welcome; [getting help](community/help.md) says what to include.
- **Releases:** [PyPI](https://pypi.org/project/meidnet/) and [GitHub releases](https://github.com/ABnano/MEIDNet/releases). The [Hugging Face model page](https://huggingface.co/Babu09/MEIDNet) holds the published checkpoints.
- **Command line:** [every command](reference/cli.md): `init`, `check`, `train`, `generate`, `studio`, `space`, `demo`, `screen`, `score`, `info`, `families`, `schema`, `download-data`.
- **Extending it:** a new material family is a YAML file ([family files](reference/families.md)); a new rule is a Python function registered as a plugin ([add a rule](recipes/add-constraint.md)); a new property is a column ([add a property](recipes/add-property.md)).

## Build on it

[MEIDNet Matter](https://babu09-meidnet-matter.hf.space/) is the first application built on the package: a FastAPI service and a React interface around `meidnet.generate.Designer`, with the model behind one backend interface so that other engines can be plugged in. Its source is at [github.com/ABnano/MEIDNet-Matter](https://github.com/ABnano/MEIDNet-Matter); [the ecosystem page](ecosystem.md) says how the two relate.
