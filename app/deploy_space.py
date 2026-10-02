"""
Deploy the demo to a Hugging Face Space.

    python app/deploy_space.py --repo Babu09/MEIDNet            # create/update the Space
    python app/deploy_space.py --repo Babu09/MEIDNet --dry-run  # only build the staging folder

The Space is self-contained: it carries its own copy of the `meidnet` package, the published
checkpoint and the static Studio page, so it does not depend on the state of the GitHub
repository.  Authentication: run `huggingface-cli login` once (token with *write* access), or
set HF_TOKEN in the environment.
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE = os.path.join(ROOT, "build", "space")
CKPT = "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"

README = """---
title: MEIDNet
emoji: 🔮
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: {sdk_version}
python_version: "3.12"
app_file: app.py
pinned: true
license: mit
short_description: Inverse design of crystals from property targets
tags: [materials, inverse-design, generative, crystal, perovskite]
---

# MEIDNet

Property-conditioned inverse design of crystalline materials in a shared structure–property
latent space, constrained by the physical rules of a material family. This Space runs the
published cubic-ABX₃ perovskite model (band gap + formation enthalpy) on a free CPU.

* **Generate** — pick a family and targets; candidates come with the rule checklist that
  accepted them and their CIF files.
* **Explore (Studio)** — every composition of four families scored by the model; move rule
  limits and targets and watch what passes.

Full framework (your own data, rules and families; live Studio):
https://babu09-meidnet.hf.space/docs/ · Code: https://github.com/ABnano/MEIDNet
"""

REQUIREMENTS = """--extra-index-url https://download.pytorch.org/whl/cpu
torch>=2.1
numpy>=1.24
pandas>=2.0
pymatgen>=2024.1.1
scikit-learn>=1.3
matplotlib>=3.7
pyyaml>=6.0
pydantic>=2.5
gradio=={sdk_version}
"""


def build_stage(sdk_version: str) -> str:
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    shutil.copytree(os.path.join(ROOT, "meidnet"), os.path.join(STAGE, "meidnet"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    os.makedirs(os.path.join(STAGE, "checkpoints"))
    shutil.copy(os.path.join(ROOT, "checkpoints", CKPT), os.path.join(STAGE, "checkpoints", CKPT))
    shutil.copy(os.path.join(ROOT, "app", "app.py"), os.path.join(STAGE, "app.py"))
    studio = os.path.join(ROOT, "docs", "studio.html")
    if os.path.exists(studio):
        shutil.copy(studio, os.path.join(STAGE, "studio.html"))
    else:
        print("note: docs/studio.html missing - run scripts/build_docs.py to include the Studio tab")
    with open(os.path.join(STAGE, "README.md"), "w", encoding="utf-8") as f:
        f.write(README.format(sdk_version=sdk_version))
    with open(os.path.join(STAGE, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(REQUIREMENTS.format(sdk_version=sdk_version))
    with open(os.path.join(STAGE, ".gitattributes"), "w") as f:
        f.write("*.pth filter=lfs diff=lfs merge=lfs -text\n")
    total = sum(os.path.getsize(os.path.join(d, x)) for d, _, fs in os.walk(STAGE) for x in fs)
    print(f"staged {STAGE} ({total / 1e6:.1f} MB)")
    return STAGE


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="e.g. Babu09/MEIDNet")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--private", action="store_true")
    a = p.parse_args()
    import gradio
    stage = build_stage(gradio.__version__)
    if a.dry_run:
        return
    from huggingface_hub import HfApi
    api = HfApi()
    try:
        who = api.whoami()
    except Exception:
        sys.exit("Not logged in to Hugging Face. Run `huggingface-cli login` (write token) or set HF_TOKEN.")
    print(f"logged in as {who.get('name')}")
    api.create_repo(a.repo, repo_type="space", space_sdk="gradio", exist_ok=True, private=a.private)
    api.upload_folder(folder_path=stage, repo_id=a.repo, repo_type="space",
                      commit_message="Deploy MEIDNet demo", delete_patterns=["*"])
    print(f"deployed → https://huggingface.co/spaces/{a.repo}")


if __name__ == "__main__":
    main()
