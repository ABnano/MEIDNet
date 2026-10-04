# The alignment training script

The scripts behind [Perov-5: alignment across seeds](../../docs/benchmarks/perov5-reproduction.md).

| file | what it is |
|---|---|
| `tri_curri_v1_save.py` | the alignment training script: early fusion, contrastive weight raised over the first 1,500 of 2,200 epochs |
| `tri_v2_ev1.py` | the same model without the curriculum: constant contrastive weight, 2,500 epochs |
| `retrain_alignment.py` | wrapper: imports the script, sets a seed, trains, saves `<out>_seed<N>.pth`, evaluates with the script's own functions and writes `<out>_seed<N>.json` |

```bash
# in a folder holding these files, train.csv (material_id, heat_all, dir_gap) and cif_files/<material_id>.cif
python -u retrain_alignment.py --seed 4 --epochs 2200                  # one GPU, about 7 hours
python -u retrain_alignment.py --ckpt meidnet_paper_rerun_seed4.pth     # evaluate a checkpoint, no training
python -u retrain_alignment.py --script tri_v2_ev1.py --epochs 2500 --seed 0 --out noCL   # without the curriculum
```

A seed gives the same numbers on any GPU. The seven checkpoints of seeds 0 to 6 are at
<https://huggingface.co/Babu09/MEIDNet/tree/main/reproduction>; their results are in
[`benchmarks/reproduction/perov5/runs.csv`](../../benchmarks/reproduction/perov5/runs.csv).

These are version-1 scripts (Python 3.10, torch 2.6, pymatgen 2024–2025), kept as they ran; they are not part of the
`meidnet` package. The checkpoints they write load with `meidnet.checkpoint.load_checkpoint`, and
`python scripts/reproduce_alignment.py --seed 4` recomputes their results on a CPU.
