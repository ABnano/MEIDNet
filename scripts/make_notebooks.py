"""
Build the Colab notebooks in notebooks/ from plain Python (no nbformat dependency).

    python scripts/make_notebooks.py

Three notebooks, one per user journey:
    01_quickstart.ipynb        try MEIDNet with the published model (CPU, ~3 min)
    02_your_own_data.ipynb     upload a table + CIFs → check → train → generate → reports
    03_add_a_rule.ipynb        write a custom constraint and use it
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "notebooks")
INSTALL = "!pip -q install torch --index-url https://download.pytorch.org/whl/cpu\n!pip -q install meidnet\n"
INSTALL_DEV = "!pip -q install torch --index-url https://download.pytorch.org/whl/cpu\n!pip -q install git+https://github.com/ABnano/MEIDNet.git\n"


def nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                     "language_info": {"name": "python"}, "colab": {"provenance": []}},
        "cells": [
            {"cell_type": kind, "metadata": {}, "source": src.splitlines(keepends=True),
             **({"outputs": [], "execution_count": None} if kind == "code" else {})}
            for kind, src in cells
        ],
    }


def show_report(path_expr):
    return (f"from IPython.display import HTML, display\n"
            f"display(HTML(open({path_expr}, encoding='utf-8').read()))")


QUICKSTART = [
    ("markdown", "# MEIDNet in 5 minutes\n\n"
                 "This notebook runs the **published perovskite model** on a CPU: pick a band-gap target, "
                 "let MEIDNet search its latent space, and read the report that explains every candidate.\n\n"
                 "Nothing here is specific to perovskites except the *family file*; the same commands work on "
                 "your own data (see notebook 02)."),
    ("code", INSTALL_DEV),
    ("markdown", "## 1. Choose a target\nBand gap in eV and formation enthalpy in eV/atom (the two properties the "
                 "published model knows). The report flags targets outside what the model saw in training."),
    ("code", "family = 'halide'      #@param ['halide', 'oxide', 'chalcogenide', 'nitride']\n"
             "band_gap = 2.0         #@param {type:'number'}\n"
             "enthalpy = -0.10       #@param {type:'number'}\n"
             "n_candidates = 3       #@param {type:'integer'}\n"),
    ("markdown", "## 2. Run the search\n`meidnet demo` downloads the 2.8 MB checkpoint, searches, applies the "
                 "family's rules and writes CIFs + a report."),
    ("code", "!meidnet demo --family {family} --band-gap {band_gap} --enthalpy {enthalpy} -n {n_candidates} "
             "--rounds 4 --steps 200 --no-open --device cpu"),
    ("markdown", "## 3. Read the report\nThe verdict, the *funnel* (where attempts were rejected), and one card per "
                 "candidate with its checklist and predicted-vs-target gauges."),
    ("code", show_report("'runs/demo/generation_report.html'")),
    ("markdown", "## 4. Look at a structure"),
    ("code", "import glob\nfrom pymatgen.core import Structure\nfor f in sorted(glob.glob('runs/demo/generation/cifs/*.cif')):\n"
             "    s = Structure.from_file(f)\n    print(f.split('/')[-1], s.composition.reduced_formula, "
             "f'a = {s.lattice.a:.3f} Å', s.get_space_group_info())"),
    ("markdown", "## 5. The whole design space at once\nFor a prototype family every possible composition can be "
                 "listed. `meidnet space` scores all of them with the structure encoder — compare with what the "
                 "latent search found."),
    ("code", "!meidnet init --template perov5 -o perov5.yaml --force\n"
             "!meidnet space perov5.yaml --model ~/.meidnet/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth -o space.csv\n"
             "import pandas as pd\ndf = pd.read_csv('space.csv')\n"
             "df[df.passes_all].assign(dist=(df.pred_dir_gap-band_gap).abs()).sort_values('dist').head(10)"),
    ("markdown", "## Next\n* Notebook **02** — the same pipeline on *your* table of structures and properties.\n"
                 "* `meidnet studio` locally — change rules and targets and watch the effect live.\n"
                 "* [Documentation](https://babu09-meidnet.hf.space/docs/)"),
]

YOUR_DATA = [
    ("markdown", "# MEIDNet on your own data\n\nYou need:\n\n1. a **table** (CSV/Excel) with one row per material: an id column, "
                 "one or more numeric property columns, and either a `cif` column with the CIF text or a folder of "
                 "`<id>.cif` files;\n2. to know which **material family** your structures belong to (built in: cubic "
                 "ABX₃ perovskites, A₂BB′X₆ double perovskites; or describe your own in a YAML file).\n\n"
                 "Run the cells in order. Each step writes an HTML report that says what happened in plain language."),
    ("code", INSTALL_DEV),
    ("markdown", "## 1. Upload your data\nEither upload a CSV with a `cif` column, or a CSV plus a zip of CIF files."),
    ("code", "from google.colab import files\nuploaded = files.upload()\nimport zipfile, os\n"
             "for name in uploaded:\n    if name.endswith('.zip'):\n        zipfile.ZipFile(name).extractall('structures')\n"
             "        print('extracted', len(os.listdir('structures')), 'files to structures/')\n"
             "table = next(n for n in uploaded if n.endswith(('.csv', '.xlsx')))\nprint('table:', table)"),
    ("code", "import pandas as pd\ndf = pd.read_csv(table) if table.endswith('.csv') else pd.read_excel(table)\n"
             "print(df.shape); df.head()"),
    ("markdown", "## 2. Describe your data in `meidnet.yaml`\nFill in the column names and the family. "
                 "`meidnet init` writes a commented file; you can edit it afterwards."),
    ("code", "id_column = 'material_id'                 #@param {type:'string'}\n"
             "properties = 'band_gap formation_energy'  #@param {type:'string'}\n"
             "cif_column = 'cif'                        #@param {type:'string'}\n"
             "family = 'perovskite_abx3'                #@param ['perovskite_abx3', 'double_perovskite_a2bbx6']\n"
             "variant = 'oxide'                         #@param {type:'string'}\n"
             "!meidnet init --name mine --table \"{table}\" --id-column {id_column} --cif-column {cif_column} "
             "--properties {properties} --family {family} --variant {variant} --force\n"
             "import os\nif os.path.isdir('structures'):\n"
             "    import re\n    y = open('meidnet.yaml').read().replace('cif_column: cif', 'cif_column: null\\n  structures_dir: structures')\n"
             "    open('meidnet.yaml','w').write(y)\nprint(open('meidnet.yaml').read())"),
    ("markdown", "## 3. Check\nReads every row exactly as training would and reports what is usable and why rows were skipped."),
    ("code", "!meidnet check meidnet.yaml"),
    ("code", show_report("'runs/mine/check_report.html'")),
    ("markdown", "## 4. Train\nStart with a few epochs to see the pipeline work, then raise `epochs` (200 is typical). "
                 "Colab's free GPU is enough: Runtime → Change runtime type → GPU."),
    ("code", "epochs = 20  #@param {type:'integer'}\n!meidnet train meidnet.yaml --epochs {epochs}"),
    ("code", show_report("'runs/mine/training_report.html'")),
    ("markdown", "## 5. Set targets and generate\nEdit the `targets:` in `meidnet.yaml` (or below) and run."),
    ("code", "import yaml\ncfg = yaml.safe_load(open('meidnet.yaml'))\nprops = [p['column'] for p in cfg['data']['properties']]\n"
             "print('properties:', props)\n# example: first property at its training median; edit freely\n"
             "cfg['generation']['targets'] = [{p: float(df[p].median()) for p in props}]\n"
             "cfg['generation']['per_target'] = 3\ncfg['generation']['rounds'] = 5\ncfg['generation']['steps'] = 300\n"
             "yaml.safe_dump(cfg, open('meidnet.yaml','w'), sort_keys=False)\nprint(cfg['generation']['targets'])"),
    ("code", "!meidnet generate meidnet.yaml"),
    ("code", show_report("'runs/mine/generation_report.html'")),
    ("markdown", "## 6. Download everything\nCIFs, `candidates.csv`, `model.pt`, the three reports and the exact "
                 "`meidnet.yaml` that produced them."),
    ("code", "!zip -qr meidnet_results.zip runs/mine meidnet.yaml\nfiles.download('meidnet_results.zip')"),
    ("markdown", "## Where to go next\n* **Rules**: `exclude_elements`, `overrides` and family files — "
                 "[recipes](https://babu09-meidnet.hf.space/docs/recipes/elements.html).\n* **Live exploration**: "
                 "`meidnet studio meidnet.yaml` on your computer.\n* **Stability**: `pip install 'meidnet[stability]'` "
                 "then `meidnet screen runs/mine/generation`."),
]

ADD_RULE = [
    ("markdown", "# Add your own rule\n\nA *rule* is a Python function that looks at a candidate and says pass/fail "
                 "with a measured value and a sentence. Register it, list the file as a plugin, name it in the family's "
                 "`constraints` — the search enforces it and every report explains it."),
    ("code", INSTALL_DEV),
    ("code", "%%writefile my_rules.py\nfrom meidnet.constraints import CONSTRAINTS\n\n"
             "@CONSTRAINTS.register('no_lead', 'Rejects any composition containing Pb.')\n"
             "def no_lead(cand):\n    return cand.result('no_lead', 'Pb' not in cand.elements.values())\n\n"
             "@CONSTRAINTS.register('mass_window', 'Mean atomic mass must be between min and max (g/mol).')\n"
             "def mass_window(cand, min=0.0, max=200.0):\n"
             "    from pymatgen.core import Element\n"
             "    m = sum(Element(e).atomic_mass for e in cand.structure.species) / len(cand.structure)\n"
             "    return cand.result('mass_window', min <= m <= max, float(m), (min, max), f'mean mass {m:.1f}')\n"),
    ("markdown", "## Use the rules in a family file\nCopy the built-in family and append the rules."),
    ("code", "import meidnet.family, shutil, os\nsrc = os.path.join(os.path.dirname(meidnet.family.__file__), 'families', 'perovskite_abx3.yaml')\n"
             "text = open(src).read().replace('name: perovskite_abx3', 'name: my_perovskite')\n"
             "text += '  - {name: no_lead}\\n  - {name: mass_window, min: 0, max: 120}\\n'\n"
             "open('my_perovskite.yaml', 'w').write(text)\nprint(text[-600:])"),
    ("code", "%%writefile meidnet.yaml\nname: rules_demo\nmodel_path: /root/.meidnet/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth\n"
             "plugins: [my_rules.py]\ngeneration:\n  family: my_perovskite.yaml\n  variant: halide\n"
             "  objectives:\n    - {property: dir_gap, loss: l2, weight: 10000}\n    - {property: heat_all, loss: at_most, weight: 6000, select_weight: 0.4}\n"
             "  targets: [{dir_gap: 1.8, heat_all: -0.1}]\n  per_target: 3\n  population: 24\n  rounds: 4\n  steps: 200\n"),
    ("code", "!meidnet demo --no-open -n 1 --rounds 1 --steps 20 --device cpu > /dev/null  # downloads the checkpoint\n"
             "!meidnet generate meidnet.yaml"),
    ("code", show_report("'runs/rules_demo/generation_report.html'")),
    ("markdown", "Every candidate card now lists **No lead** and **mass window** with the measured value — the same "
                 "function decided acceptance and wrote the explanation."),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, cells in (("01_quickstart", QUICKSTART), ("02_your_own_data", YOUR_DATA), ("03_add_a_rule", ADD_RULE)):
        path = os.path.join(OUT, f"{name}.ipynb")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb(cells), f, indent=1, ensure_ascii=False)
        print("wrote", path)


if __name__ == "__main__":
    main()
