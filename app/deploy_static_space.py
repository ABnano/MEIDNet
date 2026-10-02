"""
Deploy the FREE static Space: the MEIDNet Studio (design-space explorer) as a plain web page.

    python app/deploy_static_space.py --repo Babu09/MEIDNet

Static Spaces cost nothing on Hugging Face. They cannot run the latent search (no Python);
the page links to Colab and to the local install for that.
"""
import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE = os.path.join(ROOT, "build", "space_static")

README = """---
title: MEIDNet Studio
emoji: 🔮
colorFrom: indigo
colorTo: purple
sdk: static
pinned: true
license: mit
short_description: Inverse design of crystals - explore the design space live
tags: [materials, inverse-design, generative, crystal, perovskite]
---

# MEIDNet Studio

Property-conditioned inverse design of crystalline materials in a shared structure-property
latent space, constrained by the physical rules of a material family (npj Comput. Mater. 2026).

This page holds the published cubic-ABX₃ perovskite model's view of every composition in four
families: move rule limits and property targets and watch, instantly, which compositions pass
and which are predicted closest. Running a new latent search needs Python: open the Colab
notebook or install `meidnet` locally.

Docs: https://babu09-meidnet.hf.space/docs/ · Code: https://github.com/ABnano/MEIDNet
"""

BANNER = (
    '<span class="mode" id="mode"></span>'
    '<span class="sub" style="margin-left:12px">'
    '<a href="https://babu09-meidnet.hf.space/docs/" target="_blank">Docs</a> · '
    '<a href="https://github.com/ABnano/MEIDNet" target="_blank">Code</a> · '
    '<a href="https://www.nature.com/articles/s41524-026-02153-3" target="_blank">Paper</a> · '
    '<a href="https://colab.research.google.com/github/ABnano/MEIDNet/blob/main/notebooks/01_quickstart.ipynb" '
    'target="_blank">Run a search in Colab</a></span>'
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    src = os.path.join(ROOT, "docs", "studio.html")
    if not os.path.exists(src):
        sys.exit("docs/studio.html missing - run scripts/build_docs.py first")
    html = open(src, encoding="utf-8").read()
    assert '<span class="mode" id="mode"></span>' in html
    html = html.replace('<span class="mode" id="mode"></span>', BANNER, 1)
    os.makedirs(STAGE, exist_ok=True)
    with open(os.path.join(STAGE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(STAGE, "README.md"), "w", encoding="utf-8") as f:
        f.write(README)
    print(f"staged {STAGE} ({os.path.getsize(os.path.join(STAGE, 'index.html')) / 1e6:.1f} MB)")
    if a.dry_run:
        return
    from huggingface_hub import HfApi
    api = HfApi()
    who = api.whoami()
    print("logged in as", who.get("name"))
    api.create_repo(a.repo, repo_type="space", space_sdk="static", exist_ok=True)
    api.upload_folder(folder_path=STAGE, repo_id=a.repo, repo_type="space",
                      commit_message="Deploy MEIDNet Studio (static)")
    print(f"live at https://huggingface.co/spaces/{a.repo}")


if __name__ == "__main__":
    main()
