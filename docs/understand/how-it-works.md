# How MEIDNet works

MEIDNet learns one latent space shared by crystal structures and their properties. Prediction reads it from the
structure side; inverse design reads it from the property side and searches it for crystals with the properties you
want.

## One latent space for two modalities

<div class="pdiagram" data-diagram="architecture"></div>

- The **crystal encoder** embeds each atom's element, passes messages along neighbour bonds using only squared
  distances (so rotating or translating the cell changes nothing), pools the atoms and adds the lattice.
- The **property encoder** maps the vector of (normalised) properties to the same space.
- Both are projected and normalised to unit length; a **contrastive loss** makes each structure's latent closest
  to its own property latent and far from the others in the batch. Its weight ramps up during training so the
  decoders stabilise first.
- The decoders are trained from the **joint** latent *and* from the **property latent alone**. That second
  term is what makes inverse design possible: a point chosen from properties must decode into a structure.

<figure class="pscene" data-scene="model"></figure>

The training objective is

$$
L = w_1 L_\text{recon}(z_\text{joint}) + w_2 L_\text{prop}(z_\text{joint}) + w_3 L_\text{recon}(z_p) + w_4 L_\text{prop}(z_p) + \lambda(t)\, L_\text{InfoNCE}(z_c, z_p).
$$

!!! key "The idea in one sentence"
    Train the two encoders so that a crystal and its own properties land on the same point; then a point chosen
    from properties alone can be decoded into a crystal.

## Inverse design = search in that space { #inverse-design-search-in-that-space }

For each target:

<div class="psteps" markdown>

1. **Start** a population of latents at the property encoder's output for the target, plus a target-dependent
   random direction (so different targets start apart) and noise.
2. **Optimise** them by gradient descent on: distance of the decoded properties to the target (each objective
   with its `loss` and `weight`); a cosine anchor to the target latent; the family's **search terms** (atoms
   apart, cubic cell, positions near the prototype, expected charge zero, same element on equivalent sites,
   loose tolerance factor); and repulsion between population members and from earlier successes (diversity).
3. **Decode**: for each latent, choose one element per site group from the decoder's scores with temperature
   and top-k sampling; the last group is drawn only from elements whose charge balances the others. Place the
   elements on the prototype; the cell edge comes from ionic radii (`a = 2(r_B + r_X)` for perovskites).
4. **Rules**: symmetry-refine, then apply every hard constraint. Only compositions that pass all are kept.
5. **Rank** by distance to the target (`select_weight`, `select_loss`), skip duplicates and near-duplicate
   latents, save as CIF.

</div>

<figure class="pscene" data-scene="search"></figure>

## What "family" means

<div class="pcrystal" data-el="Cs,Pb,I" data-label="CsPbI₃, cubic ABX₃"></div>

A family is data, not code: a prototype (site positions), site groups (allowed elements and oxidation states),
a cell-size rule, soft search terms, and hard rules. The published perovskite tables are
`families/perovskite_abx3.yaml`; the same machinery runs `double_perovskite_a2bbx6.yaml` and any file you write.

In the cubic ABX₃ perovskite, the A cation sits on the corners of the cell, the B cation in the centre and the
X anions on the face centres, so that B and its six X neighbours form an octahedron. A composition is one choice
of element for each of the three sites.

## The design space

For a prototype family, the set of compositions the decoder can output is finite. `meidnet space` and the Studio
enumerate it and score each composition with the structure encoder. The search's candidates are a subset of
this space; comparing the two views (encoder prediction vs search's decoded prediction) is a useful sanity
check that the reports encourage.

<figure class="pscene" data-scene="rules"></figure>

## Reproducibility

!!! meidnet "MEIDNet 2 reproduces MEIDNet 1"
    The same featurisation, forward pass, training step and generation output: `tests/test_v1_regression.py`
    compares against the frozen v1 code in `tests/legacy_v1/`. One fix: v1's results depended on Python's hash seed
    through set iteration order; v2 fixes element order, so the same seed gives the same CIFs in any process.
