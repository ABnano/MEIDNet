"""The Space bundle: every binary file must be of a type the Space's .gitattributes sends through LFS.

The Hub stores large binaries in LFS whatever .gitattributes says, but the Space build restores only the types it
names; anything else reaches the container as a ~130-byte pointer file. That broke the logo, the poster and the
tour video on the live page once.
"""
import importlib.util
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _deploy_module():
    spec = importlib.util.spec_from_file_location("deploy_docker_space", os.path.join(ROOT, "app", "deploy_docker_space.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_binary(path):
    with open(path, "rb") as f:
        head = f.read(4096)
    if b"\0" in head:
        return True
    try:
        head.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def test_every_binary_docs_asset_is_tracked_by_lfs_on_the_space():
    lfs = set(_deploy_module().LFS_EXTENSIONS)
    missing = []
    for d, _, files in os.walk(os.path.join(ROOT, "docs")):
        for name in files:
            path = os.path.join(d, name)
            if _is_binary(path) and name.rsplit(".", 1)[-1].lower() not in lfs:
                missing.append(os.path.relpath(path, ROOT))
    assert not missing, f"binary files whose type is not in LFS_EXTENSIONS: {missing}"


def test_space_card_has_a_thumbnail_and_a_short_description_within_the_limit():
    mod = _deploy_module()
    front = mod.README.split("---")[1]
    fields = dict(line.split(":", 1) for line in front.strip().splitlines() if ":" in line)
    assert fields["thumbnail"].strip().startswith("https://")
    assert len(fields["short_description"].strip()) <= 60
