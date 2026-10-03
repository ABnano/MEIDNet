"""Collect the files of the Kaggle / Science Data Bank bundle into build/kaggle (nothing is uploaded)."""
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "build", "kaggle")
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
for src in ("checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth",
            "checkpoints/dual_autoencoder_clip_earlyfusion_propertyaware.pth",
            "checkpoints/dual_autoencoder_clip_earlyfusion.pth",
            "examples/perov5/meidnet.yaml", "meidnet/families/perovskite_abx3.yaml",
            "distribution/kaggle/dataset-metadata.json", "LICENSE"):
    shutil.copy(os.path.join(ROOT, src), OUT)
shutil.copytree(os.path.join(ROOT, "examples", "perov5", "paper_results"), os.path.join(OUT, "paper_results"))
print("bundle in", OUT, "-", len(os.listdir(OUT)), "entries")
