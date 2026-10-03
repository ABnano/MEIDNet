# Configuration reference

Every setting of `meidnet.yaml`, generated from the code (`meidnet schema` gives the JSON Schema).
Unknown keys are rejected with a message naming the key, so typos cannot silently change a run.

## Top level

| setting | type | default | meaning |
|---|---|---|---|
| `name` | string | `meidnet_run` | Name of this project; outputs go to output_dir. |
| `description` | string |  | Free text shown at the top of reports. |
| `output_dir` | string | `runs/{name}` | Where checkpoints, CIFs and reports are written. |
| `family` | string/null | `None` | Family used to align training structures (defaults to generation.family). |
| `model_path` | string/null | `None` | Existing checkpoint to generate from (skip training). Default: <output_dir>/model.pt |
| `plugins` | array |  | Python files that register your own constraints or search terms (see 'Add a constraint'). |
| `data` | object/null | `None` |  |
| `model` | section |  |  |
| `training` | section |  |  |
| `generation` | object/null | `None` |  |

## `data:`

| setting | type | default | meaning |
|---|---|---|---|
| `table` | string | **required** | Path to a CSV/Excel/JSON table with one row per material. |
| `id_column` | string | `material_id` | Column with a unique identifier for each material. |
| `cif_column` | string/null | `cif` | Column that contains the CIF text of each structure. Set to null if you use structures_dir. |
| `structures_dir` | string/null | `None` | Folder with one CIF file per material, named <id>.cif (used when there is no cif_column). |
| `properties` | array | **required** | Numeric columns that form the property modality (any number, at least one). |
| `val_table` | string/null | `None` | Optional separate validation table with the same columns. |
| `val_fraction` | number | `0.1` | Fraction of rows held out for validation when no val_table is given (0 = no validation). |
| `max_sites` | integer | `20` | Largest number of atoms per cell. Bigger structures are skipped. |
| `neighbor_cutoff` | number | `4.0` | Distance (Å) below which two atoms count as neighbours. |
| `align_to_prototype` | boolean | `True` | Re-order the atoms of every structure so they match the family prototype's site order (needed for meaningful generation). The published Perov-5 model was trained without it. |
| `prototype_tolerance` | number | `0.15` | How far (fraction of a cell edge) an atom may sit from its prototype site and still count as that site. Raise it to accept distorted structures; lower it to keep only ideal ones. |

## `data.properties[]`

| setting | type | default | meaning |
|---|---|---|---|
| `column` | string | **required** | Name of the column in your table that holds this property. |
| `label` | string/null | `None` | Human-readable name used in reports (defaults to the column name). |
| `unit` | string |  | Unit shown in reports, e.g. 'eV' or 'eV/atom'. |
| `normalize` | boolean | `True` | Standardise the property to zero mean and unit spread before training. Keep this on when properties have very different scales. |

## `model:`

| setting | type | default | meaning |
|---|---|---|---|
| `latent_dim` | integer | `128` | Size of the shared latent space where structures and properties meet. |
| `node_hidden_dim` | integer | `128` | Width of the per-atom features inside the graph network. |
| `edge_dim` | integer | `64` | Width of the per-bond messages inside the graph network. |
| `species_embedding_dim` | integer | `64` | Size of the learned element embedding. |
| `property_hidden_dim` | integer | `128` | Width of the property encoder's hidden layer. |
| `decoder_coordinate_input` | `data` / `zeros` / `prototype` | `data` | What the crystal decoder receives as starting atom positions during training. 'data' (published model) uses the true positions; generation always starts from 'zeros' or the prototype. 'zeros'/'prototype' make training and generation consistent (experimental). |

## `training:`

| setting | type | default | meaning |
|---|---|---|---|
| `epochs` | integer | `200` | Number of passes over the training data. |
| `batch_size` | integer | `16` | Materials per training step (use 8 if memory is short). |
| `learning_rate` | number | `0.001` | Adam learning rate. |
| `contrastive_weight` | number | `5.0` | Strength of the alignment between structure and property latents. |
| `temperature` | number | `0.01` | Sharpness of the contrastive (InfoNCE) alignment. |
| `contrastive_warmup_epochs` | integer/null | `None` | Epochs over which the alignment strength ramps up from 0. Default: 60% of the epochs (the published model used 1200 of 2000). |
| `loss_weights` | section |  |  |
| `seed` | integer | `0` | Random seed for weight initialisation and data shuffling. |
| `device` | string | `auto` | 'auto', 'cpu' or 'cuda'. |
| `save_every` | integer | `50` | Write an intermediate checkpoint every N epochs. |

## `training.loss_weights:`

| setting | type | default | meaning |
|---|---|---|---|
| `joint_reconstruction` | number | `1.0` | Rebuild the crystal from the joint (structure+property) latent. |
| `joint_property` | number | `1.0` | Predict the properties from the joint latent. |
| `property_reconstruction` | number | `0.5` | Rebuild the crystal from the property latent alone - this is what makes inverse design possible. |
| `property_property` | number | `0.5` | Predict the properties back from the property latent. |

## `generation:`

| setting | type | default | meaning |
|---|---|---|---|
| `family` | string | `perovskite_abx3` | Built-in family name or path to your own family .yaml file. |
| `variant` | string/null | `None` | Sub-family, e.g. 'halide' or 'oxide' for perovskites. |
| `objectives` | array | **required** | Which properties to steer and how. |
| `targets` | array | **required** | One entry per design target, e.g. {dir_gap: 1.5, heat_all: -0.1}. Each runs its own search. |
| `per_target` | integer | `4` | Candidates to save for each target. |
| `population` | integer | `48` | Latent vectors optimised in parallel in each round. |
| `rounds` | integer | `20` | Maximum search rounds per target. |
| `steps` | integer | `800` | Gradient steps per round. |
| `learning_rate` | number | `0.0012` | Step size of the latent search. |
| `anchor_weight` | number | `12.0` | Keeps the search close to the latent that the target properties map to. |
| `temperature_start` | number | `1.6` | Softness of element choices at the start of a round. |
| `temperature_end` | number | `0.9` | Softness of element choices at the end of a round. |
| `diversity_weight` | number | `0.9` | Pushes the parallel searches apart from each other. |
| `diversity_tau` | number | `0.25` |  |
| `history_weight` | number | `1.0` | Pushes new searches away from latents that already produced a saved candidate. |
| `history_tau` | number | `0.25` |  |
| `restart_patience` | integer | `250` | Steps without improvement before a search is restarted with noise. |
| `restart_noise` | number | `0.35` |  |
| `grad_clip` | number | `1.0` |  |
| `z_clip` | number | `5.0` |  |
| `init_sigma` | number | `0.35` | Noise added to the starting latents. |
| `init_anchor_mix` | number | `0.75` | Share of the property-encoder latent in the starting point. |
| `init_rff_mix` | number | `0.6` | Share of the target-dependent random-feature direction in the starting point. |
| `init_noise_mix` | number | `0.25` | Share of random noise in the starting point. |
| `rff_frequencies` | integer | `48` |  |
| `decode_temperature` | number | `1.25` | Randomness when turning element scores into a choice. |
| `decode_topk` | integer | `12` | Only the k best-scoring elements of a group can be chosen. |
| `decode_tries` | integer | `12` | Attempts per latent to find a composition that passes all constraints. |
| `anti_repeat_alpha` | number | `0.6` | Down-weights elements that were already used in saved candidates. |
| `anti_repeat_group` | string/null | `None` | Group the anti-repeat applies to (default: first sampled group). |
| `geometry_scale` | number | `1.0` | Global strength of the family's search terms. |
| `property_first` | boolean | `False` | Ignore the family's search terms during the search (properties only). |
| `dedup_formula` | boolean | `True` | Save each composition at most once. |
| `min_cosine_sep` | number | `0.985` | Skip candidates whose latent is this similar (cosine) to an already saved one. |
| `unique_decimals` | integer | `3` |  |
| `exclude_elements` | array |  | Elements never to use, e.g. [Pb, Cd]. |
| `only_elements` | object |  | Restrict groups to these elements, e.g. {B: [Ti, Zr, Hf]}. |
| `overrides` | object |  | Change parameters of the family's search terms or constraints, e.g. {tolerance_factor: {max: 1.0}}. |
| `extra_constraints` | array |  | Additional rules appended to the family's constraints, e.g. [{name: property_window, property: dir_gap, min: 1.0, max: 3.0}]. |
| `disabled_rules` | array |  | Rules to switch off for this run, by name (or id when two rules share a name), e.g. [charge_neutrality]. The generation report lists them. |
| `seed` | integer | `937` | Random seed of the search. |
| `amp` | boolean | `True` | Use mixed precision on GPUs. |
| `output_prefix` | string/null | `None` | File-name prefix of saved CIFs (default: family variant). |

## `generation.objectives[]`

| setting | type | default | meaning |
|---|---|---|---|
| `property` | string | **required** | Property (column name) this objective refers to. |
| `loss` | `l2` / `l1` / `at_most` / `at_least` | `l2` | How a prediction is compared with the target: l2 = squared distance, l1 = absolute distance, at_most = only values above the target are penalised, at_least = only values below. |
| `weight` | number | `10000.0` | Importance of this objective during the latent search. |
| `select_weight` | number | `1.0` | Importance of this objective when ranking finished candidates. |
| `select_loss` | string/null | `None` | Comparison used for ranking (defaults to 'loss'). |
