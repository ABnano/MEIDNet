"""
Deploy the live MEIDNet Studio (+ documentation site) as a Docker Space.

    python scripts/build_docs.py --no-studio && mkdocs build      # fresh docs site in site/
    python app/deploy_docker_space.py --repo Babu09/MEIDNet-Prism                  # build the bundle and upload
    python app/deploy_docker_space.py --repo Babu09/MEIDNet-Prism --dry-run
    python app/deploy_docker_space.py --repo Babu09/MEIDNet --allow-original       # the original Space: only on purpose

The pages name their Space's address (babu09-meidnet.hf.space); a copy deployed to another Space gets its own
address written into the bundle, so its links stay on it. After the build the script checks / and /health.

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
ORIGINAL = "Babu09/MEIDNet"                      # the Space the pages are written for; replaced only with --allow-original
CANONICAL_HOST = "babu09-meidnet.hf.space"
TEXT_TYPES = (".html", ".js", ".css", ".md", ".json", ".xml", ".txt", ".py", ".yaml", ".yml")
CKPT = "dual_autoencoder_clip_earlyfusion_propertyaware_2k.pth"
# binary file types in the bundle, all tracked by LFS on the Space (see stage())
LFS_EXTENSIONS = ("pth", "csv", "png", "jpg", "jpeg", "gif", "webp", "ico", "webm", "mp4", "gz", "zip", "pdf",
                  "woff", "woff2", "ttf")

README = """---
title: MEIDNet Prism
emoji: 🔮
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: Learn, build and benchmark multimodal AI for materials
thumbnail: https://babu09-meidnet.hf.space/docs/assets/meidnet_prism_logo.png
tags: [materials, inverse-design, generative, crystal, perovskite, multimodal, contrastive-learning, chemistry]
models: [Babu09/MEIDNet]
---

<p align="center"><img src="https://babu09-meidnet.hf.space/docs/assets/meidnet_prism_logo.png" width="640" alt="MEIDNet Prism"></p>

# MEIDNet Prism

**Learn, build and benchmark multimodal AI for materials discovery.** MEIDNet, the reference
implementation, learns one shared latent space for crystal structures and their properties, enumerates a
prototype-family design space checked by chemistry rules, and searches the latent space for candidates
with the properties you want.

* **[Home](https://babu09-meidnet.hf.space/)** — overview and a guided tour, from concept to demonstration.
* **[Learn](https://babu09-meidnet.hf.space/docs/learn/index.html)** — what a modality is, the five
  challenges of multimodal learning, contrastive learning with a playground, the
  [Architecture Atlas](https://babu09-meidnet.hf.space/docs/learn/architectures.html) with an advisor,
  how MEIDNet works, and [the ecosystem](https://babu09-meidnet.hf.space/docs/ecosystem.html) it fits in.
* **[Benchmark](https://babu09-meidnet.hf.space/docs/benchmarks/index.html)** — leaderboards under fixed
  protocols (inverse design, property prediction, representation on Perov-5, with baselines), metric
  families named as in LeMat-GenBench plus a conditional extension, `meidnet score` for any model's
  generated structures ([compatibility](https://babu09-meidnet.hf.space/docs/benchmarks/compatibility.html)),
  datasets and databases, and [contributed results](https://babu09-meidnet.hf.space/docs/community/contribute.html).
* **[Develop](https://babu09-meidnet.hf.space/docs/develop.html)** — the `meidnet` package (`pip install meidnet`),
  the [Studio](https://babu09-meidnet.hf.space/studio/) with the workflow *Data → Model → Family → Rules →
  Targets → Search → Candidates*, your own data, recipes, the configuration file, the Python API.
* **[MEIDNet Matter ↗](https://babu09-meidnet-matter.hf.space/)** — the companion application for
  researchers: bring a dataset, set a design goal, read whether the data and model support it, search for
  candidates with evidence next to each one, export them with a validation ladder.

**Model:** [Babu09/MEIDNet](https://huggingface.co/Babu09/MEIDNet) (the pretrained Perov-5 checkpoints) ·
**Code:** [github.com/ABnano/MEIDNet](https://github.com/ABnano/MEIDNet) (MIT) ·
**Paper:** A. Babu, R. A. Gouvêa, P. Vandergheynst, G.-M. Rignanese, *npj Computational Materials* (2026),
[doi:10.1038/s41524-026-02153-3](https://doi.org/10.1038/s41524-026-02153-3).

**Further reading**

1. Y. Bengio, A. Courville, P. Vincent, *Representation learning: a review and new perspectives*, IEEE TPAMI 35,
   1798–1828 (2013), [doi:10.1109/TPAMI.2013.50](https://doi.org/10.1109/TPAMI.2013.50).
2. Y. LeCun, Y. Bengio, G. Hinton, *Deep learning*, Nature 521, 436–444 (2015),
   [doi:10.1038/nature14539](https://doi.org/10.1038/nature14539).
3. B. Sanchez-Lengeling, A. Aspuru-Guzik, *Inverse molecular design using machine learning: generative models for
   matter engineering*, Science 361, 360–365 (2018), [doi:10.1126/science.aat2663](https://doi.org/10.1126/science.aat2663).
4. A. Babu, R. Almeida Gouvêa, G.-M. Rignanese, *Toward automated discovery with generative models multimodal
   learning and closed loop workflows in inverse materials design*, Cell Reports Physical Science 7, 103561 (2026),
   [doi:10.1016/j.xcrp.2026.103561](https://doi.org/10.1016/j.xcrp.2026.103561).
5. A. Babu, N. M. A. Krishnan, *Multimodal and cross-modal learning techniques*, APL Machine Learning 4, 030901
   (2026), [doi:10.1063/5.0346744](https://doi.org/10.1063/5.0346744).

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
        # Every binary type must be listed: the Hub stores large binaries in LFS whatever this file says, and the
        # Space build only restores the files this file names. Unlisted ones arrive as 130-byte pointer files
        # (that is how the logo, the poster and the tour video broke on the live page).
        f.write("".join(f"*.{ext} filter=lfs diff=lfs merge=lfs -text\n" for ext in LFS_EXTENSIONS))
    total = sum(os.path.getsize(os.path.join(d, x)) for d, _, fs in os.walk(STAGE) for x in fs)
    print(f"staged {STAGE} ({total / 1e6:.1f} MB)")
    return STAGE


def space_host(repo: str) -> str:
    owner, name = repo.split("/")
    return f"{owner.lower()}-{name.lower().replace('_', '-').replace('.', '-')}.hf.space"


def rewrite_host(stage: str, host: str) -> int:
    """Point a copy's links at its own address: every text file of the bundle, CANONICAL_HOST -> host."""
    n = 0
    for d, _, files in os.walk(stage):
        for f in files:
            if not f.endswith(TEXT_TYPES):
                continue
            p = os.path.join(d, f)
            with open(p, encoding="utf-8", errors="surrogateescape") as fh:
                s = fh.read()
            if CANONICAL_HOST in s:
                with open(p, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
                    fh.write(s.replace(CANONICAL_HOST, host))
                n += 1
    return n


def check_live(host: str, tries: int = 30) -> None:
    import urllib.request
    for path in ("/health", "/", "/studio/", "/docs/"):
        for i in range(tries):
            try:
                with urllib.request.urlopen(f"https://{host}{path}", timeout=30) as r:
                    if r.status == 200:
                        print(f"  {path:9s} 200")
                        break
            except Exception as e:          # the container may still be starting
                err = e
            time.sleep(5)
        else:
            sys.exit(f"https://{host}{path} did not answer 200 ({err})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="e.g. Babu09/MEIDNet-Prism")
    p.add_argument("--allow-original", action="store_true", help=f"needed to replace {ORIGINAL}")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--wait", type=int, default=900, help="seconds to wait for the build")
    a = p.parse_args()
    if a.repo.lower() == ORIGINAL.lower() and not a.allow_original:
        sys.exit(f"refusing to replace {ORIGINAL}: pass --allow-original to deploy there on purpose")
    stage = build_stage()
    host = space_host(a.repo)
    if host != CANONICAL_HOST:
        print(f"links rewritten to {host} in {rewrite_host(stage, host)} files")
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
    check_live(host)
    print(f"live: https://{host}/   docs: https://{host}/docs/")


if __name__ == "__main__":
    main()
