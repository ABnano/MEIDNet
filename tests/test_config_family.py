"""Config validation, family files and the plain-language error messages users see."""
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from meidnet.config import MEIDNetConfig, config_from_dict, dump_config, json_schema  # noqa: E402
from meidnet.family import FamilyError, list_families, load_family  # noqa: E402


def gen(**kw):
    base = {"family": "perovskite_abx3", "variant": "halide",
            "objectives": [{"property": "dir_gap"}], "targets": [{"dir_gap": 2.0}]}
    base.update(kw)
    return base


def test_minimal_generation_config_validates():
    cfg = config_from_dict({"generation": gen()})
    assert cfg.generation.per_target == 4
    assert cfg.out_dir.endswith("meidnet_run")


def test_target_missing_objective_value_is_rejected():
    with pytest.raises(Exception) as e:
        config_from_dict({"generation": gen(targets=[{"heat_all": 0.1}])})
    assert "dir_gap" in str(e.value)


def test_unknown_setting_is_rejected():
    with pytest.raises(Exception) as e:
        config_from_dict({"generation": gen(), "training": {"epocs": 3}})
    assert "epocs" in str(e.value)


def test_round_trip_through_yaml():
    cfg = config_from_dict({"name": "x", "generation": gen(exclude_elements=["Pb"])})
    import yaml
    again = MEIDNetConfig.model_validate(yaml.safe_load(dump_config(cfg)))
    assert again.generation.exclude_elements == ["Pb"]


def test_schema_has_descriptions():
    import json
    s = json.loads(json_schema())
    assert s["$defs"]["GenerationSection"]["properties"]["per_target"]["description"]


def test_builtin_families_load_all_variants():
    for name in list_families():
        fam = load_family(name, default_variant=True)
        for v in fam.variants:
            f = load_family(name, variant=v)
            assert f.n_sites >= 5
            for g in f.groups.values():
                assert g.sample


def test_family_needs_variant_message():
    with pytest.raises(FamilyError) as e:
        load_family("perovskite_abx3")
    assert "halide" in str(e.value)


def test_exclude_and_only_filters():
    fam = load_family("perovskite_abx3", variant="halide", exclude=["Pb"], only={"X": ["Br", "I"]})
    assert "Pb" not in fam.groups["B"].sample
    assert fam.groups["X"].sample == ["Br", "I"]


def test_overrides_change_constraint_window():
    fam = load_family("perovskite_abx3", variant="halide", overrides={"tolerance_factor": {"max": 0.95}})
    assert fam.constraint_params("tolerance_factor")["max"] == 0.95
    with pytest.raises(FamilyError):
        load_family("perovskite_abx3", variant="halide", overrides={"no_such_rule": {"max": 1}})


def test_variant_params_apply_to_tolerance_window():
    assert load_family("perovskite_abx3", variant="halide").constraint_params("tolerance_factor")["min"] == 0.75
    assert load_family("perovskite_abx3", variant="oxide").constraint_params("tolerance_factor")["min"] == 0.80


def test_unknown_element_in_family_file_is_reported(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("""
name: bad
prototype: {sites: [{group: A, frac: [0,0,0]}]}
groups: {A: {elements: [Xx]}}
""")
    with pytest.raises(FamilyError) as e:
        load_family(str(bad))
    assert "Xx" in str(e.value)


def test_top_level_family_is_used_for_generation():
    from meidnet.pipeline import family_for
    g = {k: v for k, v in gen().items() if k != "family"}           # generation names no family
    cfg = config_from_dict({"family": "double_perovskite_a2bbx6", "generation": g})
    assert cfg.generation.family == "double_perovskite_a2bbx6"
    assert family_for(cfg, need_variant=True).name == "double_perovskite_a2bbx6"
    both = config_from_dict({"family": "perovskite_abx3", "generation": gen(family="double_perovskite_a2bbx6")})
    assert both.generation.family == "double_perovskite_a2bbx6"     # written explicitly: it wins
    again = config_from_dict(MEIDNetConfig.model_validate(cfg.model_dump()).model_dump())
    assert again.generation.family == "double_perovskite_a2bbx6"    # stable through a save and reload


def test_output_prefix_must_be_a_file_name():
    assert config_from_dict({"generation": gen(output_prefix="halide-run_1")}).generation.output_prefix
    for bad in ("../../site/x", "/tmp/x", "a\\b", ".hidden", ""):
        with pytest.raises(Exception) as e:
            config_from_dict({"generation": gen(output_prefix=bad)})
        assert "output_prefix" in str(e.value), bad


def test_extra_rules_are_checked_early():
    from meidnet.pipeline import family_for
    with pytest.raises(Exception) as e:
        config_from_dict({"generation": gen(extra_constraints=[{"property": "dir_gap"}])})
    assert "name" in str(e.value)
    for rule, words in (({"name": "nope"}, "unknown rule"), ({"name": "tolerance_factor", "maxi": 1.0}, "maxi")):
        with pytest.raises(SystemExit) as e:
            family_for(config_from_dict({"generation": gen(extra_constraints=[rule])}), need_variant=True)
        assert words in str(e.value), rule
    two = config_from_dict({"generation": gen(extra_constraints=[
        {"name": "property_window", "property": "dir_gap", "min": 1.0},
        {"name": "property_window", "property": "heat_all", "max": 0.0}])})
    keys = [c.get("id", c["name"]) for c in family_for(two, need_variant=True).constraints]
    assert keys[-2:] == ["property_window_dir_gap", "property_window_heat_all"]
