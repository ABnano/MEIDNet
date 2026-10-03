<p align="center"><img src="assets/meidnet_prism_logo.png" alt="MEIDNet Prism" width="640" style="background:#fff;border-radius:14px"></p>

# MEIDNet Prism

[← MEIDNet Prism home](https://babu09-meidnet.hf.space/) · the documentation of the MEIDNet framework and its platform.

**Learn, build and benchmark multimodal AI for materials discovery.** MEIDNet is the reference implementation:
it designs crystalline materials from target properties, using your own data and rules, configured in one YAML
file or in the Studio.

```
   Learn ──► Architectures ──► Build ──► Datasets ──► Benchmarks ──► Community
   what is   which design      MEIDNet    data that    results with   share and
   multimodal fits your data   Studio     works        evidence       reproduce
```

MEIDNet learns one latent space shared by crystal structures and their properties, then searches it for new
materials that hit property targets while obeying the chemical and structural rules of a *material family*.
The published cubic-perovskite model (band gap + formation enthalpy) is one application of it; the framework
accepts any table of structures and scalar properties and any prototype family you describe.

<figure class="tour-video">
  <video controls muted playsinline preload="metadata" poster="assets/meidnet_tour_poster.png" style="width:100%;max-width:960px;border-radius:12px">
    <source src="assets/meidnet_tour.webm" type="video/webm">
    Your browser cannot play this video: <a href="assets/meidnet_tour.webm">download it</a>.
  </video>
  <figcaption>MEIDNet in one minute: data, model, family, rules, targets, search and candidates. The same tour opens
  on a first visit to the <a href="https://babu09-meidnet.hf.space/">live Studio</a> (the “▶ How it works” button replays it).</figcaption>
</figure>

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

</div>

## The workflow

```
   Data ──► Model ──► Family ──► Rules ──► Targets ──► Search ──► Candidates
   table    shared    prototype  hard      property   latent     CIFs + report
   + CIFs   latent    + sites    checks    goals      optimisation
```

Each block is a setting in `meidnet.yaml`, a node in [MEIDNet Studio](use/studio.md), where a change in one block
updates the blocks after it, and a section in the HTML report that each step writes.

## Scope

- Generation works for **prototype families**: a fixed arrangement of sites whose occupants and cell size are
  chosen (ABX₃ perovskites, A₂BB′X₆ double perovskites, and anything you describe the same way). MEIDNet does
  not invent new atomic arrangements. [Details and roadmap](understand/limits.md).
- Predicted properties are the model's estimates. The reports say when a prediction is an extrapolation.
  Confirm candidates with DFT or experiment; `meidnet screen` is a first filter.

## Paper

A. Babu, R. Almeida Gouvêa, P. Vandergheynst, G.-M. Rignanese, *MEIDNet: Multimodal generative AI framework for
inverse materials design*, npj Computational Materials (2026). [Citation and benchmarks](research/paper.md) ·
[code as published (v1.0)](https://github.com/ABnano/MEIDNet/releases/tag/v1.0.0-paper).

Further reading: A. Babu, N. M. A. Krishnan, *Multimodal and cross-modal learning techniques*, APL Machine
Learning **4**, 030901 (2026), [doi:10.1063/5.0346744](https://doi.org/10.1063/5.0346744) · A. Babu,
R. Almeida Gouvêa, G.-M. Rignanese, *Toward automated discovery with generative models multimodal learning and
closed loop workflows in inverse materials design*, Cell Reports Physical Science **7**, 103561 (2026),
[doi:10.1016/j.xcrp.2026.103561](https://doi.org/10.1016/j.xcrp.2026.103561).
