"""
The Colab notebooks share one contract (scripts/make_notebooks.py builds them):

* main(out_dir) writes exactly four notebooks: 01_quickstart, 02_your_own_data, 03_add_a_rule and
  04_MEIDNet_Studio_in_Colab;
* each is nbformat 4 JSON saved without outputs (every code cell: outputs [] and execution_count null);
* each walks through the Studio's seven blocks, in order, with one markdown header cell per block
  ("Block 1 · Data" ... "Block 7 · Candidates", separator U+00B7) shown in the block's colour.

The same checks run on freshly built notebooks and on the committed notebooks/ folder.
"""
import importlib.util
import json
import os
import re
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)                      # the builder may import meidnet (e.g. for its version)
SCRIPT = os.path.join(ROOT, "scripts", "make_notebooks.py")
COMMITTED = os.path.join(ROOT, "notebooks")
NOTEBOOKS = ["01_quickstart.ipynb", "02_your_own_data.ipynb", "03_add_a_rule.ipynb",
             "04_MEIDNet_Studio_in_Colab.ipynb"]
SEP = " · "                                   # " · " as in the Studio's block titles
BLOCKS = [("Data", "#2a78d6"), ("Model", "#eb6834"), ("Family", "#1baf7a"), ("Rules", "#eda100"),
          ("Targets", "#e87ba4"), ("Search", "#008300"), ("Candidates", "#4a3aa7")]
HEADERS = [f"Block {i}{SEP}{name}" for i, (name, _) in enumerate(BLOCKS, start=1)]
CELL_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")     # nbformat 4.5 cell ids


def load_builder():
    spec = importlib.util.spec_from_file_location("make_notebooks_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def text(cell) -> str:
    src = cell.get("source", "")
    return src if isinstance(src, str) else "".join(src)


def folder_state(folder) -> dict:
    return {n: os.stat(os.path.join(folder, n)).st_mtime_ns for n in sorted(os.listdir(folder))} \
        if os.path.isdir(folder) else {}


def notebooks_in(folder) -> list:
    return sorted(n for n in os.listdir(folder) if n.endswith(".ipynb"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("notebooks")
    load_builder().main(out_dir=str(out))
    return str(out)


def source_dir(which, request):
    """The freshly built folder, or the committed one (checked even when the builder itself fails)."""
    return request.getfixturevalue("built") if which == "built" else COMMITTED


def test_builder_writes_exactly_the_four_notebooks(built):
    assert notebooks_in(built) == sorted(NOTEBOOKS)


def test_builder_writes_only_into_out_dir(tmp_path):
    out = tmp_path / "elsewhere"
    out.mkdir()
    before = folder_state(COMMITTED)
    load_builder().main(out_dir=str(out))
    assert notebooks_in(out) == sorted(NOTEBOOKS)
    assert folder_state(COMMITTED) == before, "main(out_dir=...) must not touch notebooks/"


def test_committed_folder_has_the_four_notebooks():
    assert notebooks_in(COMMITTED) == sorted(NOTEBOOKS)


@pytest.mark.parametrize("name", NOTEBOOKS)
@pytest.mark.parametrize("which", ["built", "committed"])
def test_notebook_contract(which, name, request):
    path = os.path.join(source_dir(which, request), name)
    nb = read(path)                                         # valid JSON (UTF-8)
    assert nb["nbformat"] == 4 and isinstance(nb.get("nbformat_minor"), int), name
    assert isinstance(nb.get("metadata"), dict) and isinstance(nb.get("cells"), list) and nb["cells"], name
    for i, cell in enumerate(nb["cells"]):
        where = f"{which}/{name} cell {i}"
        assert cell.get("cell_type") in ("markdown", "code", "raw"), where
        assert isinstance(cell.get("metadata"), dict), where
        src = cell.get("source")
        assert isinstance(src, str) or (isinstance(src, list) and all(isinstance(s, str) for s in src)), where
        if cell["cell_type"] == "code":
            assert cell.get("outputs") == [] and "outputs" in cell, f"{where}: outputs must be []"
            assert "execution_count" in cell and cell["execution_count"] is None, f"{where}: execution_count must be null"
        else:
            assert "outputs" not in cell and "execution_count" not in cell, f"{where}: only code cells have outputs"

    # seven header cells, one per block, in the Studio's order (other cells may mention blocks too)
    markdown = [text(c) for c in nb["cells"] if c["cell_type"] == "markdown"]
    k = 0
    for t in markdown:
        if k < len(HEADERS) and HEADERS[k] in t:
            k += 1
    assert k == len(HEADERS), f"{which}/{name}: missing or out-of-order block header '{HEADERS[k]}'"
    for header, (_, colour) in zip(HEADERS, BLOCKS):
        assert any(header in t and colour in t.lower() for t in markdown), \
            f"{which}/{name}: the '{header}' header is not shown in its colour {colour}"


@pytest.mark.parametrize("name", NOTEBOOKS)
@pytest.mark.parametrize("which", ["built", "committed"])
def test_cell_ids_follow_nbformat(which, name, request):
    """nbformat 4.5 requires a unique id on every cell; earlier minor versions do not have ids."""
    nb = read(os.path.join(source_dir(which, request), name))
    if nb["nbformat_minor"] < 5:
        return
    ids = [c.get("id") for c in nb["cells"]]
    assert all(isinstance(i, str) and CELL_ID.match(i) for i in ids), f"{which}/{name}: cells need an 'id' (nbformat 4.5)"
    assert len(set(ids)) == len(ids), f"{which}/{name}: cell ids must be unique"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_committed_notebooks_are_up_to_date(name, built):
    """notebooks/ holds exactly what the builder writes (cell ids aside): rerun the script after editing it."""
    def content(path):
        nb = read(path)
        for c in nb["cells"]:
            c.pop("id", None)
        return nb
    assert content(os.path.join(COMMITTED, name)) == content(os.path.join(built, name)), \
        f"notebooks/{name} is stale: run python scripts/make_notebooks.py"
