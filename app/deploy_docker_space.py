"""
Deploy the live MEIDNet Studio (+ documentation site) as a Docker Space.

    python scripts/build_docs.py --no-studio && mkdocs build      # fresh docs site in site/
    python app/deploy_docker_space.py --repo Babu09/MEIDNet       # build the bundle and upload
    python app/deploy_docker_space.py --repo Babu09/MEIDNet --dry-run

The bundle is self-contained (package, checkpoint, Perov-5 training table for the Data node,
built docs), so the Space does not depend on the GitHub repository.  Needs a write token:
`HF_TOKEN` in the environment or a cached login.  Docker Spaces require a PRO account.
"""
import argparse
import os
import shutil
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE = os.path.join(ROOT, "build", "space_docker")
CKPT = "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"

README = """---
title: MEIDNet Prism
emoji: 🔮
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: Multimodal materials representation and inverse design
tags: [materials, inverse-design, generative, crystal, perovskite, multimodal, chemistry]
models: [Babu09/MEIDNet]
---

# MEIDNet Prism

**Design crystalline materials from the properties you want.** MEIDNet learns one shared latent space
for crystal structures and their properties, enumerates a prototype-family design space checked by
chemistry rules, and searches the latent space for candidates. **MEIDNet Prism** is the interactive
platform around it:

* **[Home](https://babu09-meidnet.hf.space/)** — what MEIDNet does, in one minute (animated tour).
* **[Studio](https://babu09-meidnet.hf.space/studio/)** — the live workbench: seven colour-coded blocks
  *Data → Model → Family → Rules → Targets → Search → Candidates*. Change a rule, exclude an element or
  move a target and watch the effect flow through the later blocks. Bring your own table (CSV / Excel /
  JSON + CIFs), train a model in the browser, run the search, inspect every candidate in 3D, export the
  `meidnet.yaml` that reproduces it on your machine.
* **[Explore](https://babu09-meidnet.hf.space/docs/explore/datasets.html)** — datasets, properties and
  modalities that work today, and what is planned.
* **[Benchmarks](https://babu09-meidnet.hf.space/docs/benchmarks/index.html)** — reproducible results
  per dataset with an evidence ladder (generated → ML filtered → MLIP → DFT → experiment);
  [contribute yours](https://babu09-meidnet.hf.space/docs/community/contribute.html) through GitHub.
* **[Documentation](https://babu09-meidnet.hf.space/docs/)** — quickstart, your own data, recipes,
  how it works, reference, Colab notebooks.

**Model:** [Babu09/MEIDNet](https://huggingface.co/Babu09/MEIDNet) (the pretrained Perov-5 checkpoints) ·
**Code:** [github.com/ABnano/MEIDNet](https://github.com/ABnano/MEIDNet) (MIT) ·
**Paper:** A. Babu, R. A. Gouvêa, P. Vandergheynst, G.-M. Rignanese, *npj Computational Materials* (2026),
[doi:10.1038/s41524-026-02153-3](https://doi.org/10.1038/s41524-026-02153-3).

This public Space is shared: uploads are capped (8 MB, 1,500 rows, 30 epochs), one training at a time,
sessions are private per browser tab and removed after an hour. Predicted properties are the model's
estimates — confirm candidates by DFT or experiment.
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
openpyxl>=3.1
"""


def build_stage() -> str:
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    shutil.copytree(os.path.join(ROOT, "meidnet"), os.path.join(STAGE, "meidnet"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    os.makedirs(os.path.join(STAGE, "checkpoints"))
    shutil.copy(os.path.join(ROOT, "checkpoints", CKPT), os.path.join(STAGE, "checkpoints", CKPT))
    train = os.path.join(ROOT, "data", "perov5", "train.csv")
    if os.path.exists(train):
        os.makedirs(os.path.join(STAGE, "data", "perov5"))
        shutil.copy(train, os.path.join(STAGE, "data", "perov5", "train.csv"))
    else:
        print("note: data/perov5/train.csv missing (run `meidnet download-data`) - the Data node will be empty")
    site = os.path.join(ROOT, "site")
    if not os.path.isdir(site):
        sys.exit("site/ missing - run `python scripts/build_docs.py --no-studio && mkdocs build` first")
    shutil.copytree(site, os.path.join(STAGE, "site"))
    shutil.copy(os.path.join(ROOT, "app", "Dockerfile"), os.path.join(STAGE, "Dockerfile"))
    with open(os.path.join(STAGE, "README.md"), "w", encoding="utf-8") as f:
        f.write(README)
    with open(os.path.join(STAGE, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(REQUIREMENTS)
    with open(os.path.join(STAGE, ".gitattributes"), "w") as f:
        f.write("*.pth filter=lfs diff=lfs merge=lfs -text\n*.csv filter=lfs diff=lfs merge=lfs -text\n")
    total = sum(os.path.getsize(os.path.join(d, x)) for d, _, fs in os.walk(STAGE) for x in fs)
    print(f"staged {STAGE} ({total / 1e6:.1f} MB)")
    return STAGE


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="e.g. Babu09/MEIDNet")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--wait", type=int, default=900, help="seconds to wait for the build")
    a = p.parse_args()
    stage = build_stage()
    if a.dry_run:
        return
    from huggingface_hub import HfApi
    api = HfApi()
    try:
        who = api.whoami()
    except Exception:
        sys.exit("Not logged in to Hugging Face (set HF_TOKEN or run `hf auth login`).")
    print(f"logged in as {who.get('name')}")
    try:
        info = api.space_info(a.repo)
        if info.sdk != "docker":
            print(f"existing Space uses sdk={info.sdk}; recreating it as a Docker Space")
            api.delete_repo(a.repo, repo_type="space")
    except Exception:
        pass
    api.create_repo(a.repo, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(folder_path=stage, repo_id=a.repo, repo_type="space",
                      commit_message="Deploy MEIDNet Studio", delete_patterns=["*"])
    url = f"https://huggingface.co/spaces/{a.repo}"
    print(f"uploaded -> {url}  (building...)")
    t0 = time.time()
    last = None
    while time.time() - t0 < a.wait:
        stage_ = api.get_space_runtime(a.repo).stage
        if stage_ != last:
            print(f"  {time.time() - t0:5.0f}s  {stage_}")
            last = stage_
        if stage_ in ("RUNNING", "RUNNING_APP_STARTING"):
            if stage_ == "RUNNING":
                break
        if stage_ in ("BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"):
            sys.exit(f"Space failed with {stage_}; see {url}?logs=build")
        time.sleep(10)
    owner, name = a.repo.split("/")
    print(f"live: https://{owner.lower()}-{name.lower()}.hf.space/   docs: https://{owner.lower()}-{name.lower()}.hf.space/docs/")


if __name__ == "__main__":
    main()
