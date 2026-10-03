/* MEIDNet Prism docs: the multimodality map, the contrastive-loss playground and the architecture advisor.
   Plain JavaScript, no dependencies. Each widget fills its own container if the page has it. */
(function () {
  "use strict";
  var STUDIO = "https://babu09-meidnet.hf.space/studio/";
  var STATUS = {
    sup: "Supported", part: "Partly", inside: "Inside the structure", plan: "Planned",
  };

  function h(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  function links(list) {
    return (list || []).map(function (l) { return '<a href="' + l[1] + '">' + l[0] + "</a>"; }).join(" · ");
  }

  /* ───────────────────────────── the multimodality map ───────────────────────────── */
  var MODS = [
    { id: "structure", name: "Crystal structure", st: "sup",
      what: "Atoms, their positions and the unit cell, usually a CIF file. A natural graph: atoms are nodes, neighbours are edges.",
      ex: "Relaxed DFT structures (Materials Project, OQMD, JARVIS, Alexandria) and experimental ones (ICSD, COD). Perov-5 in MEIDNet.",
      enc: "Graph neural networks. MEIDNet uses an E(n)-equivariant graph network (EGNN), so rotating or translating the cell changes nothing; CGCNN is a widely used alternative.",
      combo: "With scalar properties (MEIDNet), with diffraction patterns (structure from a pattern), with text, with images.",
      meid: "Supported. Up to max_sites atoms per cell (default 20), any elements.",
      links: [["Datasets", "../explore/datasets.html"], ["Databases by application", "../explore/databases.html"]],
      refs: [["Satorras et al. 2021 (EGNN)", "https://arxiv.org/abs/2102.09844"], ["Xie and Grossman 2018 (CGCNN)", "https://doi.org/10.1103/PhysRevLett.120.145301"]] },
    { id: "properties", name: "Scalar properties", st: "sup",
      what: "Numbers measured or computed for each material: band gap, formation enthalpy, bulk modulus, dielectric constant.",
      ex: "In Perov-5: direct band gap (dir_gap, eV) and formation enthalpy (heat_all, eV/atom). Any numeric column of your table.",
      enc: "A small fully connected network (MLP) over the vector of normalised values.",
      combo: "With structures (MEIDNet: design from target properties), with compositions, with spectra.",
      meid: "Supported. All scalar columns form one vector, read by one MLP; every column becomes a target you can set in the search.",
      links: [["Change the target properties", "../recipes/change-targets.html"], ["Add a property", "../recipes/add-property.html"]],
      refs: [["Babu et al. 2026 (MEIDNet)", "https://doi.org/10.1038/s41524-026-02153-3"]] },
    { id: "conditions", name: "Processing conditions", st: "part",
      what: "How a material was made or measured: annealing temperature, pressure, time, atmosphere, doping level.",
      ex: "Synthesis and processing tables of experimental groups; growth logs of thin films.",
      enc: "Numbers go into an MLP like properties; categories (atmosphere, method) as one-hot codes.",
      combo: "With composition (early fusion of features), with text (the same information written in a paper).",
      meid: "Partly. Numeric conditions can be added as extra scalar columns. They are then encoded together with the properties, and the model does not know that they are conditions rather than outcomes.",
      links: [["Add a property", "../recipes/add-property.html"]],
      refs: [["Baltrušaitis et al. 2019", "https://doi.org/10.1109/TPAMI.2018.2798607"]] },
    { id: "composition", name: "Composition", st: "inside",
      what: "Which elements, in what ratio, without positions: the formula.",
      ex: "Experimental property tables often give only formulas, for example experimental band gaps and several Matbench tasks.",
      enc: "Networks over the set of elements weighted by their fractions, such as Roost; element descriptors with tree models.",
      combo: "With processing conditions (early fusion), with structures when they are known.",
      meid: "Inside the structure. The element on each site is part of the structure, so MEIDNet sees the composition, but it cannot train on formulas alone. Formulas that sit on one prototype can be turned into structures on that prototype.",
      links: [["Recipe: formula only", "recipes.html#formula-only"]],
      refs: [["Goodall and Lee 2020 (Roost)", "https://doi.org/10.1038/s41467-020-19964-7"]] },
    { id: "text", name: "Text", st: "plan",
      what: "Papers, synthesis procedures and descriptions: sequences of words.",
      ex: "Text-mined synthesis recipes: nearly 20,000 procedures extracted from the literature.",
      enc: "Language models: BERT-style encoders or embeddings of large language models.",
      combo: "With structures (contrastive alignment, like images and captions in CLIP), with processing conditions.",
      meid: "Planned: a text encoder into the shared space. Not implemented.",
      links: [["Recipe: synthesis text", "recipes.html#synthesis-text"]],
      refs: [["Kononova et al. 2019", "https://doi.org/10.1038/s41597-019-0224-1"], ["Moro, Loh et al. 2025", "https://doi.org/10.1016/j.newton.2025.100016"]] },
    { id: "images", name: "Microscopy images", st: "plan",
      what: "Micrographs (SEM, TEM, AFM) and other 2D maps: grains, morphology, defects.",
      ex: "Microscopy collections of experimental groups; usually small and rarely paired with structures.",
      enc: "2D convolutional networks or vision transformers.",
      combo: "With processing conditions (how the microstructure formed), with properties measured on the same sample.",
      meid: "Planned: an image encoder into the shared space. Not implemented.",
      links: [["Capabilities", "../explore/capabilities.html"]],
      refs: [["Guo et al. 2019", "https://doi.org/10.1109/ACCESS.2019.2916887"]] },
    { id: "spectra", name: "Spectra and DOS", st: "plan",
      what: "Signal versus energy or wavenumber: density of states (DOS), X-ray absorption (XAS), Raman, UV-Vis.",
      ex: "Computed DOS in the Materials Project and JARVIS; measured spectra.",
      enc: "1D convolutional networks or transformers over the binned curve.",
      combo: "With structures (which sites shape which features), with properties (a band gap read from the DOS).",
      meid: "Planned: as vector modalities with an encoder each. Not implemented.",
      links: [["Scope and roadmap", "../understand/limits.html"]],
      refs: [["Tsai et al. 2019 (attention across sequences)", "https://doi.org/10.18653/v1/P19-1656"]] },
    { id: "xrd", name: "Diffraction (XRD)", st: "plan",
      what: "Intensity versus diffraction angle 2θ: a fingerprint of the lattice and its symmetry.",
      ex: "Patterns simulated from any structure database (for example with pymatgen); measured powder patterns.",
      enc: "1D convolutional networks; transformers over peak lists.",
      combo: "With structures (identify a structure from its pattern), with compositions.",
      meid: "Planned: binned XRD as a vector modality, the first item of the roadmap. Not implemented.",
      links: [["Recipe: XRD to structure", "recipes.html#xrd-structure"]],
      refs: [["Park et al. 2017", "https://doi.org/10.1107/S205225251700714X"]] },
  ];
  var CORE = {
    name: "The shared representation",
    html: "<p>Every modality gets its own encoder, and all encoders write into <b>one space</b>. " +
      "<b>Contrastive learning</b> (InfoNCE) pulls the vectors of the same material together and pushes different " +
      "materials apart. MEIDNet then averages the structure vector and the property vector into one joint vector " +
      "that its decoders read.</p><p>A point in this space can be read in both directions: from a structure to its " +
      "properties, and from wanted properties to a structure, which is inverse design. In MEIDNet the space has 128 " +
      "dimensions and joins two modalities: crystal structure and scalar properties.</p>" +
      '<p class="mm-links"><a href="#contrastive-learning">Contrastive learning</a> · ' +
      '<a href="architectures.html#shared-latent">Shared latent space in the Atlas</a> · ' +
      '<a href="#inverse-design">From a shared space to inverse design</a></p>',
  };

  function detailHtml(m) {
    return '<h4>' + m.name + ' <span class="mstatus ' + m.st + '">' + STATUS[m.st] + "</span></h4>" +
      '<table class="mm-facts"><tr><th>What it is</th><td>' + m.what + "</td></tr>" +
      "<tr><th>Examples</th><td>" + m.ex + "</td></tr>" +
      "<tr><th>Networks that read it</th><td>" + m.enc + "</td></tr>" +
      "<tr><th>Combined with</th><td>" + m.combo + "</td></tr>" +
      "<tr><th>In MEIDNet</th><td>" + m.meid + "</td></tr>" +
      "<tr><th>Go further</th><td>" + links(m.links) + "</td></tr>" +
      "<tr><th>References</th><td>" + links(m.refs) + "</td></tr></table>";
  }

  function initMap(root) {
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "1";
    var W = 680, H = 400, cx = 340, cy = 200, rx = 255, ry = 150, bw = 148, bh = 46;
    var svg = ['<svg class="mm-svg" viewBox="0 0 ' + W + " " + H + '" role="group" aria-label="Modalities around the shared representation">',
      '<defs><radialGradient id="mm-core-g" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#7c6cf2"/><stop offset="1" stop-color="#4f46e5"/></radialGradient></defs>'];
    var pos = MODS.map(function (m, i) {
      var a = (-90 + i * 45) * Math.PI / 180;
      return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)];
    });
    pos.forEach(function (p, i) {
      svg.push('<path class="link ' + MODS[i].st + '" d="M' + p[0].toFixed(1) + "," + p[1].toFixed(1) + " L" + cx + "," + cy + '"/>');
    });
    svg.push('<g class="core" tabindex="0" role="button" data-id="core" aria-label="The shared representation">' +
      '<circle cx="' + cx + '" cy="' + cy + '" r="66" fill="url(#mm-core-g)"/>' +
      '<text x="' + cx + '" y="' + (cy - 8) + '" text-anchor="middle">Shared</text>' +
      '<text x="' + cx + '" y="' + (cy + 10) + '" text-anchor="middle">representation</text>' +
      '<text class="st" x="' + cx + '" y="' + (cy + 30) + '" text-anchor="middle">contrastive alignment</text></g>');
    MODS.forEach(function (m, i) {
      var x = pos[i][0] - bw / 2, y = pos[i][1] - bh / 2;
      svg.push('<g class="node ' + m.st + '" tabindex="0" role="button" data-id="' + m.id + '" aria-label="' + m.name + ": " + STATUS[m.st] + '">' +
        '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw + '" height="' + bh + '" rx="10"/>' +
        '<text x="' + pos[i][0].toFixed(1) + '" y="' + (pos[i][1] - 3).toFixed(1) + '" text-anchor="middle">' + m.name + "</text>" +
        '<text class="st" x="' + pos[i][0].toFixed(1) + '" y="' + (pos[i][1] + 14).toFixed(1) + '" text-anchor="middle">' + STATUS[m.st] + "</text></g>");
    });
    svg.push("</svg>");
    var legend = '<div class="mm-legend"><span><i class="sw sup"></i>Supported in MEIDNet</span><span><i class="sw part"></i>Partly</span>' +
      '<span><i class="sw inside"></i>Inside the structure</span><span><i class="sw plan"></i>Planned</span></div>';
    var list = '<div class="mm-list" role="group" aria-label="Modalities"><button type="button" data-id="core" class="core-btn">Shared representation</button>' +
      MODS.map(function (m) { return '<button type="button" data-id="' + m.id + '" class="' + m.st + '">' + m.name + "<small>" + STATUS[m.st] + "</small></button>"; }).join("") + "</div>";
    root.innerHTML = legend + svg.join("") + list + '<div class="mm-detail" aria-live="polite"></div>';
    var detail = root.querySelector(".mm-detail");
    function select(id) {
      var m = MODS.filter(function (x) { return x.id === id; })[0];
      detail.innerHTML = m ? detailHtml(m) : "<h4>" + CORE.name + "</h4>" + CORE.html;
      root.querySelectorAll("[data-id]").forEach(function (n) {
        n.classList.toggle("on", n.getAttribute("data-id") === id);
      });
    }
    root.querySelectorAll("[data-id]").forEach(function (n) {
      n.addEventListener("click", function () { select(n.getAttribute("data-id")); });
      n.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); select(n.getAttribute("data-id")); }
      });
    });
    select("core");
  }

  /* ───────────────────────────── the contrastive playground ───────────────────────────── */
  var NAMES = ["CsPbI₃", "SrTiO₃", "BaZrS₃", "KMgF₃", "LaAlO₃"];
  var TRAINED = [[0.82, 0.31, 0.10, 0.45, 0.05], [0.28, 0.76, 0.40, 0.12, 0.20], [0.15, 0.52, 0.70, 0.08, 0.33],
    [0.48, 0.10, 0.05, 0.79, 0.22], [0.02, 0.25, 0.38, 0.18, 0.66]];
  var UNTRAINED = [[0.04, 0.09, -0.06, 0.02, 0.07], [0.08, -0.03, 0.05, 0.10, -0.02], [-0.05, 0.06, 0.01, 0.03, 0.09],
    [0.07, 0.02, 0.08, -0.04, 0.01], [0.03, 0.10, -0.01, 0.06, 0.02]];

  function softmaxRows(S, tau) {
    return S.map(function (row) {
      var m = Math.max.apply(null, row), e = row.map(function (v) { return Math.exp((v - m) / tau); });
      var s = e.reduce(function (a, b) { return a + b; }, 0);
      return e.map(function (v) { return v / s; });
    });
  }
  function transpose(S) { return S[0].map(function (_, j) { return S.map(function (r) { return r[j]; }); }); }

  function initNce(root) {
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "1";
    root.innerHTML =
      '<div class="nce-ctl"><span class="nce-mode" role="group" aria-label="Which encoders">' +
      '<button type="button" data-m="untrained">Before training</button><button type="button" data-m="trained" class="on">After training</button></span>' +
      '<label>temperature τ <input type="range" min="-2" max="0" step="0.05" value="-1" aria-label="temperature"> <b class="nce-tau"></b></label></div>' +
      '<div class="nce-wrap"></div><p class="nce-out"></p>';
    var slider = root.querySelector("input"), wrap = root.querySelector(".nce-wrap"), out = root.querySelector(".nce-out");
    var mode = "trained";
    function draw() {
      var tau = Math.pow(10, parseFloat(slider.value)), S = mode === "trained" ? TRAINED : UNTRAINED;
      var P = softmaxRows(S, tau), Q = softmaxRows(transpose(S), tau);
      var loss = 0;
      for (var i = 0; i < 5; i++) loss += -Math.log(P[i][i]) - Math.log(Q[i][i]);
      loss /= 10;
      root.querySelector(".nce-tau").textContent = tau < 0.1 ? tau.toFixed(3) : tau.toFixed(2);
      var t = '<table class="nce-grid"><tr><th></th><th colspan="5" class="cap">probability that these are the properties of the structure</th></tr><tr><th></th>' +
        NAMES.map(function (n) { return "<th>" + n + "</th>"; }).join("") + "</tr>";
      for (var r = 0; r < 5; r++) {
        t += "<tr><th>" + NAMES[r] + "</th>";
        for (var c = 0; c < 5; c++) {
          var p = P[r][c];
          t += '<td class="' + (r === c ? "d" : "") + '" style="background:rgba(79,70,229,' + (0.06 + 0.84 * p).toFixed(3) + ");color:" + (p > 0.55 ? "#fff" : "inherit") +
            '" title="cosine ' + S[r][c].toFixed(2) + '">' + Math.round(100 * p) + "%</td>";
        }
        t += "</tr>";
      }
      wrap.innerHTML = t + "</table>";
      out.innerHTML = "Loss <b>" + loss.toFixed(2) + "</b> (0 when every structure picks its own properties with certainty; " +
        "random guessing gives ln 5 ≈ 1.61). Rows: structures; columns: the property vectors of the same batch; the outlined " +
        "diagonal holds the true pairs. " + (mode === "untrained"
          ? "Before training the encoders do not agree, so no temperature makes the right answer stand out: at a high τ the model guesses at random, at a low τ it is confidently wrong and the loss rises above random guessing."
          : "After training the diagonal has the highest cosine in each row; a small τ (MEIDNet uses 0.01) makes the model insist on it.");
    }
    slider.addEventListener("input", draw);
    root.querySelectorAll("[data-m]").forEach(function (b) {
      b.addEventListener("click", function () {
        mode = b.getAttribute("data-m");
        root.querySelectorAll("[data-m]").forEach(function (x) { x.classList.toggle("on", x === b); });
        draw();
      });
    });
    draw();
  }

  /* ───────────────────────────── the architecture advisor ───────────────────────────── */
  var HAVE = [["structure", "Crystal structures"], ["properties", "Scalar properties"], ["composition", "Formulas only"],
    ["conditions", "Processing conditions"], ["xrd", "Diffraction patterns"], ["spectra", "Spectra or DOS"],
    ["images", "Microscopy images"], ["text", "Text"]];
  var GOALS = [["design", "Design new materials from target properties"], ["predict", "Predict properties"],
    ["retrieve", "Find materials that match a profile, across modalities"], ["identify", "Identify a structure or phase from a measurement"],
    ["combine", "Combine all my data into one prediction"]];
  var LABEL = { sup: "Supported in MEIDNet", part: "Partly in MEIDNet", plan: "Planned in MEIDNet", no: "Not in MEIDNet: use another tool", info: "First step" };
  var EXTRA_NAMES = { xrd: "diffraction patterns", spectra: "spectra", images: "images", text: "text" };

  function advise(has, goal) {
    var notes = [], r = adviseCore(has, goal, notes);
    r.notes = notes;
    return r;
  }

  function adviseCore(has, goal, notes) {
    var S = has.structure, P = has.properties, C = has.composition, K = has.conditions;
    var X = has.xrd, Sp = has.spectra, I = has.images, T = has.text;
    var extra = ["xrd", "spectra", "images", "text"].filter(function (k) { return has[k]; }).map(function (k) { return EXTRA_NAMES[k]; });
    var n = Object.keys(has).filter(function (k) { return has[k]; }).length;
    function meidnetNotes() {
      if (extra.length) notes.push("MEIDNet uses structures and scalar properties today. Your " + extra.join(", ") +
        " would each need an encoder of their own, which is planned; train on the structures and properties now.");
      if (K) notes.push("Processing conditions can be added as extra scalar columns. They are encoded with the properties, and the model does not know they are conditions rather than outcomes.");
    }
    if (!n) return { st: "info", title: "Tick the data you have", why: "The recommendation depends on which modalities describe your materials." };

    if (goal === "design") {
      if (S && P) {
        meidnetNotes();
        return { st: "sup", arch: "shared-latent", title: "Shared latent space with contrastive alignment: MEIDNet",
          why: "You have structures paired with properties and want to go from properties to structures. A shared space whose crystal decoder is also trained from the property latent alone gives exactly that direction; contrastive alignment makes the two latents agree.",
          steps: ["Bring the table to the Studio's Data block (or run meidnet init): an id, your property columns, one CIF per row.",
            "Train. The training report says whether the two modalities aligned (retrieval top 1 and top 5).",
            "Choose a material family and its rules, set the targets, run the search.",
            "Screen the candidates with MACE, then confirm with DFT."],
          links: [["Use your dataset in the Studio", STUDIO + "?panel=data", 1], ["Try it on Perov-5", STUDIO], ["Recipe", "recipes.html#own-family"]],
          alt: "MEIDNet places compositions on a prototype family. To generate new atomic arrangements, see conditional generative models (MatterGen, CDVAE) in the Atlas." };
      }
      if (P && C && !S) return { st: "no", arch: "early-fusion", title: "A composition model in a screening loop, or structures built on a prototype",
        why: "MEIDNet needs a structure for every row. If all your formulas sit on one prototype (for example ABX₃), build those structures on the prototype and use MEIDNet. Otherwise train a composition model such as Roost and use it to screen candidate formulas.",
        links: [["Recipe: formula only", "recipes.html#formula-only", 1], ["Roost (Goodall and Lee 2020)", "https://doi.org/10.1038/s41467-020-19964-7"]] };
      if (S && !P) return { st: "info", arch: "shared-latent", title: "First add property values to your structures",
        why: "Design from properties needs examples of structures with their property values. Compute them (DFT) or take them from a database, then train the shared space.",
        links: [["Databases by application", "../explore/databases.html", 1], ["What data do I need?", "../start/what-data.html"]] };
      if (P && extra.length) return { st: "plan", arch: "shared-latent", title: "Shared latent space with an encoder for your " + extra.join(" and "),
        why: "The same design as MEIDNet, with an encoder suited to your modality in place of the structure encoder. Design then returns " + extra.join(" or ") + " rather than structures, which is useful only if those can be turned into materials.",
        links: [["Shared latent space", "#shared-latent", 1], ["Scope and roadmap", "../understand/limits.html"]] };
      return { st: "info", title: "Add a description of each material besides its properties",
        why: "Design needs to output something you can make: structures (MEIDNet) or at least formulas. Tick crystal structures or formulas.",
        links: [["Datasets", "../explore/datasets.html", 1]] };
    }

    if (goal === "predict") {
      if (!P) return { st: "info", title: "Add the property values you want to predict",
        why: "A model learns to predict a property from examples where the property is known. Tick scalar properties if you have them.",
        links: [["Databases by application", "../explore/databases.html", 1]] };
      if (S) {
        if (extra.length) notes.push("To add your " + extra.join(", ") + ", join one encoder per modality in a shared space (intermediate fusion), or use late fusion if some materials lack them.");
        return { st: "sup", arch: "shared-latent", title: "A graph network on the structure (MEIDNet's structure encoder does this)",
          why: "For structure to property alone, a single-modality graph network such as CGCNN is the simplest strong choice. MEIDNet's structure encoder does the same and scores every composition of a family instantly, and it adds the reverse direction if you later want to design.",
          links: [["Recipe: screen a family", "recipes.html#screen-family", 1], ["Open the Studio", STUDIO], ["CGCNN (Xie and Grossman 2018)", "https://doi.org/10.1103/PhysRevLett.120.145301"]] };
      }
      if (C && !extra.length) return { st: "no", arch: K ? "early-fusion" : null, title: "A composition network such as Roost" + (K ? ", with the conditions joined by early fusion" : ""),
        why: "Without structures, the formula is the description. Roost learns from the formula alone; numeric conditions can be concatenated to its features.",
        links: [["Recipe: formula only", "recipes.html#formula-only", 1], ["Roost (Goodall and Lee 2020)", "https://doi.org/10.1038/s41467-020-19964-7"]] };
      if (extra.length === 1 && !C && !K) {
        var one = { "diffraction patterns": "a 1D convolutional network on the binned pattern", spectra: "a 1D convolutional network on the binned spectrum",
          images: "a 2D convolutional network or a vision transformer", text: "a fine-tuned language model" }[extra[0]];
        return { st: "no", title: "One modality: " + one, why: "With a single input modality, a network suited to its shape is the right start. Multimodal designs help once a second modality is paired with it.",
          links: [["Modalities and their networks", "index.html#what-is-a-modality", 1]] };
      }
      return { st: "no", arch: "late-fusion", title: "Late fusion, or early fusion if every material has every modality",
        why: "Several inputs of different shapes and one property to predict: train one model per modality and combine their predictions (late fusion, robust to missing data), or concatenate fixed-length features into one model (early fusion) when every material has everything.",
        links: [["Late fusion", "#late-fusion", 1], ["Early fusion", "#early-fusion"]] };
    }

    if (goal === "retrieve") {
      if (S && P) {
        meidnetNotes();
        return { st: "sup", arch: "contrastive", title: "Contrastive alignment of structures and properties: MEIDNet",
          why: "Contrastive training makes each structure's nearest property vector its own; the training report measures it (retrieval top 1 and top 5). The Studio's design space lists the compositions of a family predicted closest to a property profile.",
          links: [["Open the design space", STUDIO + "?explore=space", 1], ["Contrastive learning", "index.html#contrastive-learning"]] };
      }
      if (S && (X || Sp)) return { st: "plan", arch: "contrastive", title: "Contrastive alignment of patterns or spectra with structures",
        why: "Pairs of (pattern, structure) can be simulated from any structure database, so a pattern can retrieve the structures it matches. In MEIDNet this needs the planned vector-modality encoder.",
        links: [["Recipe: XRD to structure", "recipes.html#xrd-structure", 1]] };
      if (S && (I || T)) return { st: "plan", arch: "contrastive", title: "CLIP-style contrastive alignment of " + extra.join(" and ") + " with structures",
        why: "The same loss that pairs pictures with captions pairs your " + extra.join(" and ") + " with structures, given enough pairs. MEIDNet plans these encoders; they are not implemented.",
        links: [["Contrastive learning", "#contrastive", 1], ["Recipe: synthesis text", "recipes.html#synthesis-text"]] };
      return { st: "info", title: "Retrieval needs pairs of two modalities",
        why: "Tick at least two modalities that describe the same materials, for example crystal structures and scalar properties." };
    }

    if (goal === "identify") {
      if (X || Sp) {
        if (S) notes.push("With structures as well, a contrastive model can retrieve the matching structure instead of a class label; simulate the patterns from the structures to get as many pairs as you need.");
        return { st: "plan", arch: "contrastive", title: "A 1D convolutional classifier on the pattern; contrastive retrieval as the multimodal version",
          why: "A pattern or spectrum is a fingerprint. A classifier needs labels (crystal system, space group, phase); a contrastive pattern-structure model needs only pairs. In MEIDNet the pattern encoder is planned.",
          links: [["Recipe: XRD to structure", "recipes.html#xrd-structure", 1], ["Park et al. 2017", "https://doi.org/10.1107/S205225251700714X"]] };
      }
      if (I) return { st: "no", title: "An image classifier: a convolutional network or a vision transformer",
        why: "Phases and microstructures can be classified from micrographs given labelled examples. This is a single-modality task outside MEIDNet.",
        links: [["Microscopy images on the map", "index.html#the-multimodality-map", 1]] };
      return { st: "info", title: "Identification starts from a measurement",
        why: "Tick diffraction patterns, spectra or images: the measurement you want to identify a structure or phase from." };
    }

    // combine
    if (n < 2) return { st: "info", title: "Combining needs at least two modalities", why: "Tick every kind of data you have for the same materials." };
    var tabular = ["structure", "xrd", "spectra", "images", "text"].every(function (k) { return !has[k]; });
    notes.push("If some materials lack a modality, late fusion (one model per modality, predictions averaged) is the robust choice.");
    if (tabular) return { st: "no", arch: "early-fusion", title: "Early fusion: concatenate the features into one model",
      why: "Properties, formulas and conditions all become fixed-length numbers, so concatenating them is a strong and cheap baseline.",
      links: [["Early fusion", "#early-fusion", 1], ["Late fusion", "#late-fusion"]] };
    if (T || (n >= 3 && (X || Sp || I))) return { st: "no", arch: "cross-attention", title: "Cross-attention fusion, with a shared latent space as the cheaper start",
      why: "Text, spectra or images next to structures have parts that interact in detail; attention learns which parts matter to which. It needs much data. A shared latent space (one encoder per modality, aligned and averaged) is the cheaper first step.",
      links: [["Cross-attention", "#cross-attention", 1], ["Shared latent space", "#shared-latent"]] };
    return { st: S && P && !extra.length ? "part" : "no", arch: "shared-latent", title: "Intermediate fusion: one encoder per modality into a shared space, then a prediction head",
      why: "Modalities of different shapes each get the encoder that suits them, and their latents are joined. MEIDNet does this for structures and scalar properties (aligned, then averaged); a separate prediction head for another quantity is not part of it.",
      links: [["Shared latent space", "#shared-latent", 1], ["Open the Studio", STUDIO]] };
  }

  function renderAdvice(r, notes) {
    var b = '<div class="adv-card ' + r.st + '"><span class="mstatus ' + r.st + '">' + LABEL[r.st] + "</span><h4>" + r.title + "</h4>" +
      "<p><b>Why.</b> " + r.why + "</p>";
    if (r.steps) b += "<ol>" + r.steps.map(function (s) { return "<li>" + s + "</li>"; }).join("") + "</ol>";
    if (notes.length) b += '<ul class="adv-notes">' + notes.map(function (s) { return "<li>" + s + "</li>"; }).join("") + "</ul>";
    if (r.alt) b += '<p class="adv-alt">' + r.alt + "</p>";
    var ls = (r.links || []).slice();
    if (r.arch && !ls.some(function (l) { return l[1] === "#" + r.arch; })) ls.push(["This architecture in the Atlas", "#" + r.arch]);
    if (ls.length) b += '<p class="adv-links">' + ls.map(function (l) {
      return '<a class="adv-btn' + (l[2] ? " primary" : "") + '" href="' + l[1] + '">' + l[0] + "</a>";
    }).join("") + "</p>";
    return b + "</div>";
  }

  function initAdvisor(root) {
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "1";
    root.innerHTML = '<div class="adv-q"><b>1. What data do you have for the same materials?</b><div class="adv-opts">' +
      HAVE.map(function (o) { return '<label><input type="checkbox" name="have" value="' + o[0] + '"' + (o[0] === "structure" || o[0] === "properties" ? " checked" : "") + "> " + o[1] + "</label>"; }).join("") +
      '</div></div><div class="adv-q"><b>2. What do you want to do?</b><div class="adv-opts">' +
      GOALS.map(function (o, i) { return '<label><input type="radio" name="goal" value="' + o[0] + '"' + (i === 0 ? " checked" : "") + "> " + o[1] + "</label>"; }).join("") +
      '</div></div><div class="adv-out"></div>';
    var out = root.querySelector(".adv-out");
    function update() {
      var has = {};
      root.querySelectorAll('input[name="have"]').forEach(function (i) { has[i.value] = i.checked; });
      var goal = (root.querySelector('input[name="goal"]:checked') || {}).value || "design";
      var r = advise(has, goal);
      out.innerHTML = renderAdvice(r, r.notes);
    }
    root.addEventListener("change", update);
    update();
  }

  window.meidnetLearn = { advise: advise, modalities: MODS };   // used by the tests

  function init() {
    initMap(document.getElementById("mm-map"));
    initNce(document.getElementById("nce-play"));
    initAdvisor(document.getElementById("arch-advisor"));
  }
  if (window.document$ && typeof window.document$.subscribe === "function") window.document$.subscribe(init);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
