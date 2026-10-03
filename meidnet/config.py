"""
The MEIDNet configuration file.

Everything a user can change lives here, with a plain-language description for
each setting.  The same schema drives three things:

* validation of ``meidnet.yaml`` files (clear error messages, no silent typos),
* the reference documentation (generated from the descriptions), and
* the MEIDNet Studio web page (``meidnet schema`` exports it as JSON Schema).

Defaults reproduce the published MEIDNet v1 behaviour unless a field says otherwise.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PropertyColumn(_Section):
    column: str = Field(description="Name of the column in your table that holds this property.")
    label: Optional[str] = Field(None, description="Human-readable name used in reports (defaults to the column name).")
    unit: str = Field("", description="Unit shown in reports, e.g. 'eV' or 'eV/atom'.")
    normalize: bool = Field(
        True,
        description="Standardise the property to zero mean and unit spread before training. "
                    "Keep this on when properties have very different scales.",
    )

    @property
    def display(self) -> str:
        return self.label or self.column


class DataSection(_Section):
    table: str = Field(description="Path to a CSV/Excel/JSON table with one row per material.")
    id_column: str = Field("material_id", description="Column with a unique identifier for each material.")
    cif_column: Optional[str] = Field(
        "cif", description="Column that contains the CIF text of each structure. Set to null if you use structures_dir."
    )
    structures_dir: Optional[str] = Field(
        None, description="Folder with one CIF file per material, named <id>.cif (used when there is no cif_column)."
    )
    properties: list[PropertyColumn] = Field(
        description="Numeric columns that form the property modality (any number, at least one).", min_length=1
    )
    val_table: Optional[str] = Field(None, description="Optional separate validation table with the same columns.")
    val_fraction: float = Field(
        0.1, ge=0.0, lt=0.9,
        description="Fraction of rows held out for validation when no val_table is given (0 = no validation).",
    )
    max_sites: int = Field(20, ge=1, le=200, description="Largest number of atoms per cell. Bigger structures are skipped.")
    neighbor_cutoff: float = Field(4.0, gt=0, description="Distance (Å) below which two atoms count as neighbours.")
    align_to_prototype: bool = Field(
        True,
        description="Re-order the atoms of every structure so they match the family prototype's site order "
                    "(needed for meaningful generation). The published Perov-5 model was trained without it.",
    )
    prototype_tolerance: float = Field(
        0.15, gt=0, le=0.5,
        description="How far (fraction of a cell edge) an atom may sit from its prototype site and still count as "
                    "that site. Raise it to accept distorted structures; lower it to keep only ideal ones.",
    )


class ModelSection(_Section):
    latent_dim: int = Field(128, ge=8, description="Size of the shared latent space where structures and properties meet.")
    node_hidden_dim: int = Field(128, ge=8, description="Width of the per-atom features inside the graph network.")
    edge_dim: int = Field(64, ge=4, description="Width of the per-bond messages inside the graph network.")
    species_embedding_dim: int = Field(64, ge=4, description="Size of the learned element embedding.")
    property_hidden_dim: int = Field(128, ge=4, description="Width of the property encoder's hidden layer.")
    decoder_coordinate_input: Literal["data", "zeros", "prototype"] = Field(
        "data",
        description="What the crystal decoder receives as starting atom positions during training. "
                    "'data' (published model) uses the true positions; generation always starts from 'zeros' "
                    "or the prototype. 'zeros'/'prototype' make training and generation consistent (experimental).",
    )


class LossWeights(_Section):
    joint_reconstruction: float = Field(1.0, ge=0, description="Rebuild the crystal from the joint (structure+property) latent.")
    joint_property: float = Field(1.0, ge=0, description="Predict the properties from the joint latent.")
    property_reconstruction: float = Field(
        0.5, ge=0, description="Rebuild the crystal from the property latent alone - this is what makes inverse design possible."
    )
    property_property: float = Field(0.5, ge=0, description="Predict the properties back from the property latent.")


class TrainingSection(_Section):
    epochs: int = Field(200, ge=1, description="Number of passes over the training data.")
    batch_size: int = Field(16, ge=2, description="Materials per training step (use 8 if memory is short).")
    learning_rate: float = Field(1e-3, gt=0, description="Adam learning rate.")
    contrastive_weight: float = Field(5.0, ge=0, description="Strength of the alignment between structure and property latents.")
    temperature: float = Field(0.01, gt=0, description="Sharpness of the contrastive (InfoNCE) alignment.")
    contrastive_warmup_epochs: Optional[int] = Field(
        None, ge=1,
        description="Epochs over which the alignment strength ramps up from 0. Default: 60% of the epochs "
                    "(the published model used 1200 of 2000).",
    )
    loss_weights: LossWeights = Field(default_factory=LossWeights)
    seed: int = Field(0, description="Random seed for weight initialisation and data shuffling.")
    device: str = Field("auto", description="'auto', 'cpu' or 'cuda'.")
    save_every: int = Field(50, ge=1, description="Write an intermediate checkpoint every N epochs.")

    def warmup(self) -> int:
        return self.contrastive_warmup_epochs or max(1, round(0.6 * self.epochs))


class Objective(_Section):
    property: str = Field(description="Property (column name) this objective refers to.")
    loss: Literal["l2", "l1", "at_most", "at_least"] = Field(
        "l2",
        description="How a prediction is compared with the target: l2 = squared distance, l1 = absolute distance, "
                    "at_most = only values above the target are penalised, at_least = only values below.",
    )
    weight: float = Field(1e4, ge=0, description="Importance of this objective during the latent search.")
    select_weight: float = Field(1.0, ge=0, description="Importance of this objective when ranking finished candidates.")
    select_loss: Optional[Literal["l2", "l1", "at_most", "at_least"]] = Field(
        None, description="Comparison used for ranking (defaults to 'loss')."
    )


class GenerationSection(_Section):
    family: str = Field("perovskite_abx3", description="Built-in family name or path to your own family .yaml file.")
    variant: Optional[str] = Field(None, description="Sub-family, e.g. 'halide' or 'oxide' for perovskites.")
    objectives: list[Objective] = Field(description="Which properties to steer and how.", min_length=1)
    targets: list[dict[str, float]] = Field(
        description="One entry per design target, e.g. {dir_gap: 1.5, heat_all: -0.1}. Each runs its own search.",
        min_length=1,
    )
    per_target: int = Field(4, ge=1, description="Candidates to save for each target.")
    population: int = Field(48, ge=2, description="Latent vectors optimised in parallel in each round.")
    rounds: int = Field(20, ge=1, description="Maximum search rounds per target.")
    steps: int = Field(800, ge=1, description="Gradient steps per round.")
    learning_rate: float = Field(1.2e-3, gt=0, description="Step size of the latent search.")
    anchor_weight: float = Field(12.0, ge=0, description="Keeps the search close to the latent that the target properties map to.")
    temperature_start: float = Field(1.6, gt=0, description="Softness of element choices at the start of a round.")
    temperature_end: float = Field(0.9, gt=0, description="Softness of element choices at the end of a round.")
    diversity_weight: float = Field(0.9, ge=0, description="Pushes the parallel searches apart from each other.")
    diversity_tau: float = Field(0.25, gt=0)
    history_weight: float = Field(1.0, ge=0, description="Pushes new searches away from latents that already produced a saved candidate.")
    history_tau: float = Field(0.25, gt=0)
    restart_patience: int = Field(250, ge=1, description="Steps without improvement before a search is restarted with noise.")
    restart_noise: float = Field(0.35, ge=0)
    grad_clip: float = Field(1.0, gt=0)
    z_clip: float = Field(5.0, gt=0)
    init_sigma: float = Field(0.35, ge=0, description="Noise added to the starting latents.")
    init_anchor_mix: float = Field(0.75, description="Share of the property-encoder latent in the starting point.")
    init_rff_mix: float = Field(0.60, description="Share of the target-dependent random-feature direction in the starting point.")
    init_noise_mix: float = Field(0.25, description="Share of random noise in the starting point.")
    rff_frequencies: int = Field(48, ge=1)
    decode_temperature: float = Field(1.25, gt=0, description="Randomness when turning element scores into a choice.")
    decode_topk: int = Field(12, ge=1, description="Only the k best-scoring elements of a group can be chosen.")
    decode_tries: int = Field(12, ge=1, description="Attempts per latent to find a composition that passes all constraints.")
    anti_repeat_alpha: float = Field(0.6, ge=0, description="Down-weights elements that were already used in saved candidates.")
    anti_repeat_group: Optional[str] = Field(None, description="Group the anti-repeat applies to (default: first sampled group).")
    geometry_scale: float = Field(1.0, ge=0, description="Global strength of the family's search terms.")
    property_first: bool = Field(False, description="Ignore the family's search terms during the search (properties only).")
    dedup_formula: bool = Field(True, description="Save each composition at most once.")
    min_cosine_sep: float = Field(0.985, description="Skip candidates whose latent is this similar (cosine) to an already saved one.")
    unique_decimals: int = Field(3, ge=0)
    exclude_elements: list[str] = Field(default_factory=list, description="Elements never to use, e.g. [Pb, Cd].")
    only_elements: dict[str, list[str]] = Field(
        default_factory=dict, description="Restrict groups to these elements, e.g. {B: [Ti, Zr, Hf]}."
    )
    overrides: dict[str, dict] = Field(
        default_factory=dict,
        description="Change parameters of the family's search terms or constraints, e.g. {tolerance_factor: {max: 1.0}}.",
    )
    extra_constraints: list[dict] = Field(
        default_factory=list,
        description="Additional rules appended to the family's constraints, e.g. "
                    "[{name: property_window, property: dir_gap, min: 1.0, max: 3.0}].",
    )
    disabled_rules: list[str] = Field(
        default_factory=list,
        description="Rules to switch off for this run, by name (or id when two rules share a name), "
                    "e.g. [charge_neutrality]. The generation report lists them.",
    )
    seed: int = Field(937, description="Random seed of the search.")
    amp: bool = Field(True, description="Use mixed precision on GPUs.")
    output_prefix: Optional[str] = Field(None, description="File-name prefix of saved CIFs (default: family variant).")

    @model_validator(mode="after")
    def _targets_cover_objectives(self):
        names = [o.property for o in self.objectives]
        for i, t in enumerate(self.targets):
            missing = [n for n in names if n not in t]
            if missing:
                raise ValueError(f"target #{i + 1} {t} has no value for {missing}")
        return self

    @field_validator("extra_constraints")
    @classmethod
    def _rules_have_names(cls, v):
        for i, c in enumerate(v):
            if not isinstance(c.get("name"), str) or not c["name"]:
                raise ValueError(f"rule #{i + 1} {c} needs a 'name', e.g. {{name: property_window, property: ..., "
                                 "min: ..., max: ...}")
        return v

    @field_validator("output_prefix")
    @classmethod
    def _plain_file_name(cls, v):
        if v is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,59}", v):
            raise ValueError("use a plain file-name prefix: letters, digits, '-', '_' and '.' (no folders)")
        return v


class MEIDNetConfig(_Section):
    name: str = Field("meidnet_run", description="Name of this project; outputs go to output_dir.")
    description: str = Field("", description="Free text shown at the top of reports.")
    output_dir: str = Field("runs/{name}", description="Where checkpoints, CIFs and reports are written.")
    family: Optional[str] = Field(
        None, description="Family used to align training structures (defaults to generation.family)."
    )
    model_path: Optional[str] = Field(
        None, description="Existing checkpoint to generate from (skip training). Default: <output_dir>/model.pt"
    )
    plugins: list[str] = Field(
        default_factory=list,
        description="Python files that register your own constraints or search terms (see 'Add a constraint').",
    )
    data: Optional[DataSection] = None
    model: ModelSection = Field(default_factory=ModelSection)
    training: TrainingSection = Field(default_factory=TrainingSection)
    generation: Optional[GenerationSection] = None

    @model_validator(mode="after")
    def _generation_uses_the_family(self):
        # a config that names only the top-level family generates in that family, not in the default one
        if self.generation is not None and self.family and "family" not in self.generation.model_fields_set:
            self.generation.family = self.family
        return self

    # ── paths ────────────────────────────────────────────────────────────────
    _base_dir: str = "."

    def resolve(self, p: str | None) -> str | None:
        if p is None:
            return None
        p = p.replace("{name}", self.name)
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(self._base_dir, p))

    @property
    def out_dir(self) -> str:
        return self.resolve(self.output_dir)

    @property
    def checkpoint_path(self) -> str:
        return self.resolve(self.model_path) if self.model_path else os.path.join(self.out_dir, "model.pt")

    @property
    def family_name(self) -> str | None:
        return self.family or (self.generation.family if self.generation else None)


def format_validation_error(err: ValidationError, source: str = "config") -> str:
    lines = [f"Your {source} has {err.error_count()} problem(s):"]
    for e in err.errors():
        loc = " → ".join(str(x) for x in e["loc"])
        lines.append(f"  • {loc}: {e['msg']}")
    lines.append("Run `meidnet schema` or see docs/reference/config.md for every allowed setting.")
    return "\n".join(lines)


def load_config(path: str | os.PathLike) -> MEIDNetConfig:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    try:
        cfg = MEIDNetConfig.model_validate(raw)
    except ValidationError as err:
        raise SystemExit(format_validation_error(err, source=path.name)) from None
    cfg._base_dir = str(path.parent.resolve())
    return cfg


def config_from_dict(raw: dict, base_dir: str = ".") -> MEIDNetConfig:
    cfg = MEIDNetConfig.model_validate(raw)
    cfg._base_dir = base_dir
    return cfg


def dump_config(cfg: MEIDNetConfig) -> str:
    doc = cfg.model_dump(mode="json", exclude_none=True)
    if cfg.data is not None and cfg.data.cif_column is None:
        doc["data"]["cif_column"] = None   # "no CIF column" must survive: leaving it out would mean the default 'cif'
    return yaml.safe_dump(doc, sort_keys=False)


def json_schema() -> str:
    return json.dumps(MEIDNetConfig.model_json_schema(), indent=1)
