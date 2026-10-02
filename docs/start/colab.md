# Run in Google Colab

Each notebook is a complete, runnable workflow. Training runs in *your* Colab session (free GPU is enough):
your data never leaves your Google account.

| Notebook | What it does | Time |
|---|---|---|
| [01 — Quickstart](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/01_quickstart.ipynb) | published model, pick a target, read the report, list the whole design space | 5 min, CPU |
| [02 — Your own data](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/02_your_own_data.ipynb) | upload table + CIFs → check → train → generate → download everything | 15 min + training |
| [03 — Add a rule](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/03_add_a_rule.ipynb) | write a custom constraint in 5 lines and see it in every report | 5 min |

The notebooks are generated from `scripts/make_notebooks.py`, so they stay in step with the command line.
