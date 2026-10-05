"""Write the input of the alignment training script from the Perov-5 data that `meidnet download-data` fetches:
train.csv (material_id, heat_all, dir_gap: all 18,928 materials of train, val and test, sorted by material_id) and
cif_files/<material_id>.cif, in the current folder. Each CIF is read and written again by pymatgen, as for the runs on
the reproduction page (this puts every atom inside the cell), so the training input is the same as theirs.

    meidnet download-data                  # in the repository root: data/perov5/{train,val,test}.csv
    cd reproduction/paper_alignment
    python prepare_data.py                 # writes train.csv and cif_files/ here
"""
import argparse
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=os.path.join(HERE, "..", "..", "data", "perov5"),
                    help="folder with train.csv, val.csv and test.csv (default: data/perov5 of the repository)")
    ap.add_argument("--out", default=".", help="where to write train.csv and cif_files/ (default: the current folder)")
    a = ap.parse_args()

    parts = []
    for split in ("train", "val", "test"):
        path = os.path.join(a.data_dir, f"{split}.csv")
        if not os.path.exists(path):
            raise SystemExit(f"{os.path.abspath(path)} is missing: run `meidnet download-data` in the repository root first")
        parts.append(pd.read_csv(path, usecols=["material_id", "cif", "heat_all", "dir_gap"]))
    d = pd.concat(parts, ignore_index=True).sort_values("material_id", kind="stable")

    import warnings
    from pymatgen.core import Structure
    warnings.filterwarnings("ignore")              # pymatgen's notes on CIF details, one per file
    cif_dir = os.path.join(a.out, "cif_files")
    os.makedirs(cif_dir, exist_ok=True)
    for mid, cif in zip(d["material_id"], d["cif"]):
        with open(os.path.join(cif_dir, f"{mid}.cif"), "w", encoding="utf-8", newline="\n") as f:
            f.write(Structure.from_str(cif, fmt="cif").to(fmt="cif"))
    d[["material_id", "heat_all", "dir_gap"]].to_csv(os.path.join(a.out, "train.csv"), index=False)
    print(f"{len(d)} materials: train.csv and cif_files/ written to {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
