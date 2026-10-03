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
tags: [materials, inverse-design, generative, crystal, perovskite]
---

# MEIDNet Studio

**Design crystalline materials from target properties - with your own data, rules and
families.** This Space runs the live MEIDNet Studio with the published cubic-ABX₃ perovskite
model (band gap + formation enthalpy, Perov-5):

* the workflow as a strip of colour-coded blocks *Data → Model → Family → Rules → Targets →
  Search → Candidates*; change a rule's limit, exclude an element or move a target and watch
  the change flow through every later block, explained in plain words;
* bring your own data: upload a table (CSV / Excel / JSON) with CIF structures, map the
  columns, check it and train a small model in the browser - then design with your own
  properties;
* explore the design space, your data or the candidates in 3D: a property map linked to a
  crystal viewer (chemiscope);
* edit the configuration as YAML, run the paper's latent search, read each candidate's
  checklist and export the `meidnet.yaml` that reproduces the run on your own computer.

The documentation lives at **/docs/** on this Space. Code: https://github.com/ABnano/MEIDNet ·
Paper: https://www.nature.com/articles/s41524-026-02153-3

Each browser tab has a private session (deleted after an hour without activity). Budgets on this
shared server are capped (1,500 rows, 30 training epochs, two jobs at a time);
`pip install meidnet` for full control.
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
