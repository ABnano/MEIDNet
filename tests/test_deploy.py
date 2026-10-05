"""The Space bundle: every binary file must be of a type the Space's .gitattributes sends through LFS.

The Hub stores large binaries in LFS whatever .gitattributes says, but the Space build restores only the types it
names; anything else reaches the container as a ~130-byte pointer file. That broke the logo, the poster and the
tour video on the live page once.
"""
import codecs
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
    try:          # incremental: 4096 bytes may end inside a multi-byte character of a text file
        codecs.getincrementaldecoder("utf-8")().decode(head, final=False)
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


def test_the_original_space_is_only_replaced_on_purpose(monkeypatch):
    mod = _deploy_module()
    monkeypatch.setattr("sys.argv", ["deploy", "--repo", "babu09/meidnet", "--dry-run"])
    try:
        mod.main()
    except SystemExit as e:
        assert "refusing" in str(e) and "--allow-original" in str(e)
    else:
        raise AssertionError("the original Space was not refused")


def test_a_copy_gets_its_own_address(tmp_path):
    mod = _deploy_module()
    assert mod.space_host("Babu09/MEIDNet-Prism") == "babu09-meidnet-prism.hf.space"
    assert mod.space_host(mod.ORIGINAL) == mod.CANONICAL_HOST
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text('<a href="https://babu09-meidnet.hf.space/studio/">Studio</a>', encoding="utf-8")
    (tmp_path / "README.md").write_text("[Home](https://babu09-meidnet.hf.space/) · https://huggingface.co/spaces/Babu09/MEIDNet", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG babu09-meidnet.hf.space")
    assert mod.rewrite_host(str(tmp_path), "babu09-meidnet-prism.hf.space") == 2
    assert "babu09-meidnet-prism.hf.space/studio/" in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    card = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "babu09-meidnet-prism.hf.space/" in card and "huggingface.co/spaces/Babu09/MEIDNet" in card   # the Space page itself is kept
    assert (tmp_path / "logo.png").read_bytes() == b"\x89PNG babu09-meidnet.hf.space"                   # binaries untouched


def test_no_script_or_style_from_a_cdn_in_the_docs():
    import re
    with open(os.path.join(ROOT, "mkdocs.yml"), encoding="utf-8") as f:
        cfg = f.read()
    block = cfg[cfg.index("extra_javascript:"):cfg.index("nav:")]
    assert not re.search(r"https?://", block), "the docs load a script from another site"
    for p in ("assets/vendor/mathjax-3.2.2/es5/tex-mml-chtml.js", "assets/vendor/tablesort-5.3.0/tablesort.min.js",
              "assets/vendor/chemiscope-1.1.0/chemiscope.min.js"):
        assert os.path.getsize(os.path.join(ROOT, "docs", p)) > 1000, p
