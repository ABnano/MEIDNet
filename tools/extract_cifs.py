#!/usr/bin/env python3
"""
tools/extract_cifs.py
=====================
Utility to extract individual CIF files from the embedded 'cif' column in
the MEIDNet dataset CSVs (train.csv, val.csv, test.csv).

The dataset stores raw CIF text in a dedicated column alongside scalar
properties (material_id, heat_all, dir_gap).  The training data loader
(TripleModalityDataset in meidnet.model) expects individual CIF files on
disk, matched to CSV rows by material_id.

Run this script once before training to populate the cif_files/ directory.

Usage
-----
    # Extract training set only (required before training)
    python tools/extract_cifs.py

    # Extract all splits (train, val, test)
    python tools/extract_cifs.py --all

    # Custom CSV and output directory
    python tools/extract_cifs.py --csv data/train.csv --out cif_files/train
"""
import os
import argparse
import pandas as pd


def extract(csv_path: str, out_dir: str) -> int:
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(csv_path)
    if "cif" not in df.columns or "material_id" not in df.columns:
        raise ValueError(f"{csv_path}: expected columns 'material_id' and 'cif'.")
    written = 0
    for _, row in df.iterrows():
        try:
            mid = str(int(row["material_id"]))
        except Exception:
            mid = str(row["material_id"]).strip()
        cif_str = str(row["cif"]).strip()
        if not cif_str or cif_str.lower() == "nan":
            continue
        out_path = os.path.join(out_dir, mid + ".cif")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cif_str)
        written += 1
    print(f"  {csv_path} -> {out_dir}/  ({written} CIF files written)")
    return written


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv",  default="train.csv")
    p.add_argument("--out",  default="cif_files")
    p.add_argument("--all",  action="store_true",
                   help="also extract val.csv and test.csv into cif_files_val/ and cif_files_test/")
    args = p.parse_args()

    extract(args.csv, args.out)

    if args.all:
        extract("val.csv",  "cif_files_val")
        extract("test.csv", "cif_files_test")


if __name__ == "__main__":
    main()
