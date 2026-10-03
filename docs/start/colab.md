# Run in Google Colab

Each notebook is a complete, runnable workflow. Training runs in *your* Colab session (free GPU is enough):
your data never leaves your Google account.

| Notebook | What it does | Time |
|---|---|---|
| [01 — Quickstart](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/01_quickstart.ipynb) | published model, pick a target, read the report, explore the whole design space in 3D | 5 min, CPU |
| [02 — Your own data](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/02_your_own_data.ipynb) | upload table + CIFs → check → train → generate → download everything | 15 min + training |
| [03 — Add a rule](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/03_add_a_rule.ipynb) | write a custom constraint in a few lines and see its effect before and after | 5 min |
| [04 — MEIDNet Studio in Colab](https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/04_MEIDNet_Studio_in_Colab.ipynb) | the live Studio inside the notebook, then the same blocks driven from Python | 10 min |

## Block by block, like the Studio

Every notebook follows the seven blocks of the [Studio](../use/studio.md), in order and in the same colours:
**Block 1 · Data** (blue), **Block 2 · Model** (orange), **Block 3 · Family** (green), **Block 4 · Rules**
(amber), **Block 5 · Targets** (pink), **Block 6 · Search** (dark green) and **Block 7 · Candidates** (violet).
Each block starts with a coloured header saying what it does, has a form for its settings, shows its result as
charts (and crystals in 3D where it helps), and ends by printing what flows on to the next block.

Run the cells from top to bottom (*Runtime → Run all* also works). Change a value in a form and re-run from that
block on: the later blocks pick up the change.

The notebooks are generated from `scripts/make_notebooks.py`, so they stay in step with the command line.
