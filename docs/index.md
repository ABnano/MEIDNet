<div class="phero" markdown>

# MEIDNet Prism documentation

Learn, build and benchmark multimodal AI for materials discovery. MEIDNet, the reference implementation, learns one
latent space shared by crystal structures and their properties, and searches it for materials with the properties
you want, using your own data, rules and material families.

<div class="pbtns" markdown>
[▶ Open the Studio](https://babu09-meidnet.hf.space/studio/){ .primary }
[5-minute quickstart](start/quickstart.md)
[Learn multimodality](learn/index.md)
[← MEIDNet Prism home](https://babu09-meidnet.hf.space/)
</div>

</div>

## The workflow

Seven blocks, from a table of known materials to new candidates. Each block is a section of `meidnet.yaml`, a node in
[MEIDNet Studio](use/studio.md) (where a change in one block updates every block after it) and a section of the
report that each step writes. Click a block to read about it.

<div class="pflow" data-flow="workflow"></div>

<section class="tour3d" id="tour3d" aria-labelledby="t3-title">
  <h2 id="t3-title">From concept to demonstration</h2>
  <p class="sec-sub">The seven blocks at work on the published perovskite model. Click a block to jump to it.</p>
  <ol class="t3-strip" aria-label="Chapters"></ol>
  <div class="t3-stage"><canvas tabindex="0" role="img" aria-label="Animated tour of MEIDNet in three dimensions: data, model, family, rules, targets, search and candidates. The caption below gives each step in words."></canvas></div>
  <p class="t3-cap" aria-live="polite"></p>
  <div class="t3-bar">
    <button type="button" class="t3-b primary" data-t3="play" aria-label="Play the tour">▶ Play</button>
    <button type="button" class="t3-b" data-t3="prev" aria-label="Previous chapter">◀</button>
    <button type="button" class="t3-b" data-t3="next" aria-label="Next chapter">▶</button>
    <div class="t3-prog" role="slider" tabindex="0" aria-label="Position in the tour, in seconds" aria-valuemin="0" aria-valuemax="63" aria-valuenow="0"><i></i></div>
    <span class="t3-time">0:00</span>
    <a class="t3-open" href="https://babu09-meidnet.hf.space/studio/">Open the Studio →</a>
  </div>
</section>

## Where to start

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } **Learn multimodality**

    ---

    What a modality is, the five challenges of multimodal learning, contrastive learning with a playground, and
    an interactive map of materials modalities.

    [:octicons-arrow-right-24: Learn](learn/index.md)

-   :material-sitemap:{ .lg .middle } **Choose an architecture**

    ---

    Early fusion, late fusion, shared latent spaces, cross-attention and contrastive learning, and an advisor
    that recommends one for your data and goal.

    [:octicons-arrow-right-24: Architecture Atlas](learn/architectures.md)

-   :material-play-circle:{ .lg .middle } **Try MEIDNet**

    ---

    The [live Studio](https://babu09-meidnet.hf.space/studio/) runs in the browser without installation;
    `meidnet demo` runs on a laptop CPU.

    [:octicons-arrow-right-24: 5-minute quickstart](start/quickstart.md)

-   :material-database-import:{ .lg .middle } **Use MEIDNet on my data**

    ---

    A table with an id, property columns and CIFs. Four commands lead from a data check to
    candidates with reports.

    [:octicons-arrow-right-24: Bring your own dataset](use/your-data.md)

-   :material-tune:{ .lg .middle } **Change what it does**

    ---

    Targets, elements, rules and family are set in one YAML file, or with the controls of
    MEIDNet Studio, which exports the same file.

    [:octicons-arrow-right-24: Recipes](recipes/change-targets.md)

-   :material-head-question:{ .lg .middle } **Understand it**

    ---

    How the two modalities are aligned, how the search works, what the reports mean,
    and where the limits are.

    [:octicons-arrow-right-24: How MEIDNet works](understand/how-it-works.md)

-   :material-scale-balance:{ .lg .middle } **Benchmark any model**

    ---

    Leaderboards under fixed protocols, and `meidnet score` for a folder of generated structures from any
    model: the LeMat-GenBench metric families plus the conditional extension.

    [:octicons-arrow-right-24: Benchmark compatibility](benchmarks/compatibility.md)

-   :material-flask-outline:{ .lg .middle } **Design with my data in Matter**

    ---

    MEIDNet Matter is the companion application: a dataset, a design goal, a readiness report, candidates
    with evidence, and a validation ladder.

    [:octicons-arrow-right-24: The ecosystem](ecosystem.md)

</div>

## Scope

!!! meidnet "What MEIDNet generates, and what it does not"
    Generation works for **prototype families**: a fixed arrangement of sites whose occupants and cell size are
    chosen (ABX₃ perovskites, A₂BB′X₆ double perovskites, and anything you describe the same way). MEIDNet does
    not invent new atomic arrangements. [Details and roadmap](understand/limits.md).

    Predicted properties are the model's estimates, and the reports say when a prediction is an extrapolation.
    Confirm candidates with DFT or experiment; `meidnet screen` is a first filter.

## Paper

A. Babu, R. Almeida Gouvêa, P. Vandergheynst, G.-M. Rignanese, *MEIDNet: Multimodal generative AI framework for
inverse materials design*, npj Computational Materials (2026). [Citation and benchmarks](research/paper.md) ·
[code as published (v1.0)](https://github.com/ABnano/MEIDNet/releases/tag/v1.0.0-paper).

Further reading: A. Babu, R. Almeida Gouvêa, G.-M. Rignanese, *Toward automated discovery with generative
models multimodal learning and closed loop workflows in inverse materials design*, Cell Reports Physical Science
**7**, 103561 (2026), [doi:10.1016/j.xcrp.2026.103561](https://doi.org/10.1016/j.xcrp.2026.103561) · A. Babu,
N. M. A. Krishnan, *Multimodal and cross-modal learning techniques*, APL Machine Learning **4**, 030901 (2026),
[doi:10.1063/5.0346744](https://doi.org/10.1063/5.0346744).
