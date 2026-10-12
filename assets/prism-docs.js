/* Components of the MEIDNet Prism documentation, written in the pages as empty elements and drawn here:
     <div class="pflow" data-flow="workflow|studio"></div>      the seven blocks of the workflow, with arrows
     <figure class="pscene" data-scene="model"></figure>         one chapter of the live tour, looping while visible
     <div class="pcrystal" data-el="Cs,Pb,I"></div>               an ABX3 cell to turn with the mouse
     <div class="pmodal"></div>                                   the materials modalities, with what MEIDNet does with each
     <div class="pdiagram" data-diagram="architecture"></div>    the MEIDNet architecture
   Without JavaScript the elements stay empty, and the text around them still reads on its own. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  function base() {        // the documentation's root, relative to this page (Material writes it into #__config)
    try { var c = JSON.parse(document.getElementById("__config").textContent); return (c.base || ".").replace(/\/$/, ""); } catch (e) { return "."; }
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]; }); }
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── the workflow ── */
  var ICON = {
    data: '<rect x="1" y="2.5" width="14" height="11" rx="2"/><path d="M1 6.5h14M6 2.5v11"/>',
    model: '<circle cx="3" cy="8" r="2"/><circle cx="13" cy="3.5" r="2"/><circle cx="13" cy="12.5" r="2"/><path d="M5 7.2l6-3M5 8.8l6 3"/>',
    family: '<path d="M8 1.5l6 3.2v6.6l-6 3.2-6-3.2V4.7z"/><path d="M8 8l6-3.3M8 8L2 4.7M8 8v6.5"/>',
    rules: '<path d="M2 4.5l1.5 1.5L6 3.5M2 9.5l1.5 1.5L6 8.5M8 4.5h6M8 9.5h6"/>',
    targets: '<circle cx="8" cy="8" r="6.5"/><circle cx="8" cy="8" r="3.5"/><circle cx="8" cy="8" r=".8" fill="currentColor"/>',
    search: '<circle cx="6.5" cy="6.5" r="4.5"/><path d="M10 10l4.5 4.5"/>',
    candidates: '<path d="M8 1.5l2 4.2 4.6.6-3.4 3.2.9 4.6L8 11.8l-4.1 2.3.9-4.6L1.4 6.3 6 5.7z"/>'
  };
  var FLOW = [
    {id: "data", name: "Data", c: "#2a78d6", sub: "a table of structures and properties", live: ["11,356", "materials"], href: "/use/your-data.html"},
    {id: "model", name: "Model", c: "#eb6834", sub: "one latent space for both", live: ["MAE 0.17", "eV"], href: "/understand/how-it-works.html"},
    {id: "family", name: "Family", c: "#1baf7a", sub: "a prototype and its sites", live: ["924", "compositions"], href: "/recipes/change-family.html"},
    {id: "rules", name: "Rules", c: "#eda100", sub: "hard chemical checks", live: ["27", "pass every rule"], href: "/recipes/add-constraint.html"},
    {id: "targets", name: "Targets", c: "#e87ba4", sub: "the properties you want", live: ["E<sub>g</sub> 2.0 eV", "ΔH<sub>f</sub> −0.1"], href: "/recipes/change-targets.html"},
    {id: "search", name: "Search", c: "#008300", sub: "optimisation in the latent space", live: ["idle", ""], href: "/understand/how-it-works.html#inverse-design-search-in-that-space"},
    {id: "candidates", name: "Candidates", c: "#4a3aa7", sub: "crystals, checks and a report", live: ["0", "found"], href: "/use/reports.html"}
  ];
  function flow(el) {
    var live = el.getAttribute("data-flow") === "studio", b = base();
    el.innerHTML = FLOW.map(function (f, i) {
      return (i ? '<span class="pf-arrow" aria-hidden="true"></span>' : "") +
        '<a class="pf-b" href="' + b + f.href + '" style="--c:' + f.c + '">' +
        '<svg viewBox="0 0 16 16" aria-hidden="true">' + ICON[f.id] + "</svg>" +
        "<b>" + f.name + "</b>" +
        (live ? '<span class="pf-live"><strong>' + f.live[0] + "</strong> " + f.live[1] + "</span>" : '<span class="pf-sub">' + f.sub + "</span>") + "</a>";
    }).join("");
    el.setAttribute("role", "list");
  }

  /* ── one chapter of the tour, looping ── */
  var scenes = [];
  function scene(el) {
    var S = window.PrismScenes; if (!S) return;
    var i = S.index(el.getAttribute("data-scene")); if (i < 0) return;
    var meta = S.list[i], blk = S.blocks.filter(function (b) { return b.id === meta.block; })[0];
    el.style.setProperty("--c", blk ? blk.c : "#4f46e5");
    el.innerHTML = '<div class="ps-stage"><canvas role="img" aria-label="' + esc("Animation: " + meta.title + ". " + meta.cap) + '"></canvas></div>' +
      '<figcaption><button type="button" class="ps-play" aria-label="Pause the animation">❚❚</button>' +
      (blk ? '<b style="color:' + blk.c + '">' + blk.name + ".</b> " : "") + esc(el.getAttribute("data-caption") || meta.cap) +
      (blk ? ' <a class="ps-open" href="https://babu09-meidnet.hf.space/studio/?panel=' + blk.id + '" target="_blank" rel="noopener">Open in the Studio →</a>' : "") + "</figcaption>";
    var cv = el.querySelector("canvas"), c2d = cv.getContext("2d"), btn = el.querySelector(".ps-play");
    var st = {el: el, i: i, ms: reduce ? meta.ms - 1 : 0, total: meta.ms + 1800, playing: !reduce, visible: false, last: 0, W: 0, H: 0, dpr: 1};
    function size() { var r = cv.getBoundingClientRect(); st.dpr = Math.min(2, window.devicePixelRatio || 1); st.W = r.width; st.H = r.height;
      cv.width = Math.round(st.W * st.dpr); cv.height = Math.round(st.H * st.dpr); draw(); }
    function draw() { if (st.W > 0) S.render(c2d, st.i, Math.min(1, st.ms / meta.ms), st.W, st.H, st.dpr); }
    function label() { btn.textContent = st.playing ? "❚❚" : "▶"; btn.setAttribute("aria-label", st.playing ? "Pause the animation" : "Play the animation"); }
    btn.addEventListener("click", function () { st.playing = !st.playing; st.last = 0; label(); });
    if (window.ResizeObserver) new ResizeObserver(size).observe(cv); else size();
    if (window.IntersectionObserver) new IntersectionObserver(function (es) { st.visible = es[0].isIntersecting; }).observe(cv); else st.visible = true;
    st.draw = draw; st.tick = function (now) {
      if (!st.playing || !st.visible || document.hidden) { st.last = 0; return; }
      var dt = st.last ? Math.min(100, now - st.last) : 0; st.last = now;
      st.ms = (st.ms + dt) % st.total;          // the chapter, then its last picture held for a moment, then again
      draw();
    };
    label(); scenes.push(st);
  }

  /* ── a crystal to turn ── */
  var crystals = [];
  function crystal(el) {
    var P = window.Prism3D; if (!P) return;
    var e = (el.getAttribute("data-el") || "Cs,Pb,I").split(","), cell = P.perovskite({A: e[0], B: e[1], X: e[2]});
    el.innerHTML = '<canvas role="img" aria-label="' + esc("The cubic ABX3 cell of " + e.join("") + "3: " + e[0] + " on the corners, " + e[1] + " in the centre, " + e[2] + " on the faces. Drag to turn it.") + '"></canvas>' +
      '<span class="pc-cap">' + esc(el.getAttribute("data-label") || (e[0] + e[1] + e[2] + "₃")) + " · drag to turn</span>";
    var cv = el.querySelector("canvas"), c2d = cv.getContext("2d");
    var st = {yaw: -0.6, pitch: -0.38, auto: !reduce, W: 0, H: 0, dpr: 1, drag: null, visible: false};
    function size() { var r = cv.getBoundingClientRect(); st.dpr = Math.min(2, window.devicePixelRatio || 1); st.W = r.width; st.H = r.height;
      cv.width = Math.round(st.W * st.dpr); cv.height = Math.round(st.H * st.dpr); draw(); }
    function draw() {
      if (!st.W) return;
      c2d.setTransform(st.dpr, 0, 0, st.dpr, 0, 0); c2d.clearRect(0, 0, st.W, st.H);
      var cam = P.camera({cx: st.W / 2, cy: st.H / 2, scale: Math.min(st.W, st.H) / 4.4, yaw: st.yaw, pitch: st.pitch});
      P.crystal(c2d, cam, cell, {labels: true, dark: P.isDark()});
    }
    cv.addEventListener("pointerdown", function (ev) { st.drag = {x: ev.clientX, y: ev.clientY, yaw: st.yaw, pitch: st.pitch}; st.auto = false; cv.setPointerCapture(ev.pointerId); });
    cv.addEventListener("pointermove", function (ev) { if (!st.drag) return;
      st.yaw = st.drag.yaw + (ev.clientX - st.drag.x) * 0.01; st.pitch = Math.max(-1.2, Math.min(1.2, st.drag.pitch + (ev.clientY - st.drag.y) * 0.01)); draw(); });
    cv.addEventListener("pointerup", function () { st.drag = null; }); cv.addEventListener("pointercancel", function () { st.drag = null; });
    cv.addEventListener("dblclick", function () { st.auto = !st.auto; });
    if (window.ResizeObserver) new ResizeObserver(size).observe(cv); else size();
    if (window.IntersectionObserver) new IntersectionObserver(function (es) { st.visible = es[0].isIntersecting; }).observe(cv); else st.visible = true;
    st.draw = draw; st.tick = function () { if (st.auto && st.visible && !document.hidden) { st.yaw += 0.006; draw(); } };
    crystals.push(st);
  }

  /* ── the modalities ── */
  var GLYPH = {
    structure: '<g class="g-b"><path d="M6 10l12-4 12 4-12 4z M6 10v14l12 4 12-4V10 M18 14v14"/></g><g class="g-a"><circle cx="6" cy="10" r="2.6"/><circle cx="30" cy="10" r="2.6"/><circle cx="18" cy="14" r="2.6"/><circle cx="18" cy="28" r="2.6"/><circle cx="6" cy="24" r="2.6"/><circle cx="30" cy="24" r="2.6"/></g>',
    composition: '<text x="18" y="23" text-anchor="middle" class="g-t">CsPbI<tspan dy="3" font-size="7">3</tspan></text>',
    properties: '<g class="g-a"><rect x="6" y="18" width="5" height="10" rx="1"/><rect x="15.5" y="10" width="5" height="18" rx="1"/><rect x="25" y="14" width="5" height="14" rx="1"/></g>',
    xrd: '<path class="g-b" d="M3 28h30"/><path class="g-l" d="M4 27h4l1-14 1 14h5l1-8 1 8h4l1-19 1 19h5l1-6 1 6h3"/>',
    spectra: '<path class="g-b" d="M3 28h30"/><path class="g-l" d="M4 26c4 0 5-4 7-10s3-8 5-3 2 9 5 9 4-10 7-10 3 13 5 14"/>',
    image: '<rect class="g-b" x="5" y="7" width="26" height="22" rx="3"/><g class="g-a"><circle cx="13" cy="15" r="3"/><circle cx="22" cy="21" r="4"/><circle cx="25" cy="12" r="2"/></g>',
    text: '<g class="g-b"><path d="M7 10h22M7 15h22M7 20h22M7 25h14"/></g>'
  };
  var MODALITIES = [
    {k: "structure", name: "Crystal structure", data: "atoms in a unit cell: a graph", net: "graph neural network (EGNN)", st: "sup", label: "in MEIDNet"},
    {k: "properties", name: "Scalar properties", data: "a short vector of numbers", net: "fully connected network (MLP)", st: "sup", label: "in MEIDNet"},
    {k: "composition", name: "Composition", data: "elements and fractions: a set", net: "set or element network", st: "part", label: "through the structure"},
    {k: "xrd", name: "Diffraction (XRD)", data: "intensity versus 2θ", net: "1D convolutional network", st: "plan", label: "planned"},
    {k: "spectra", name: "Spectra and DOS", data: "signal versus energy", net: "1D CNN or transformer", st: "plan", label: "planned"},
    {k: "image", name: "Micrographs", data: "a grid of pixels", net: "2D CNN or vision transformer", st: "plan", label: "planned"},
    {k: "text", name: "Text", data: "words: a synthesis procedure", net: "language model", st: "plan", label: "planned"}
  ];
  function modalities(el) {
    el.innerHTML = MODALITIES.map(function (m) {
      return '<div class="pm-card ' + m.st + '"><svg viewBox="0 0 36 36" aria-hidden="true">' + GLYPH[m.k] + "</svg>" +
        "<b>" + m.name + '</b><span class="pm-data">' + m.data + '</span><span class="pm-net">' + m.net + "</span>" +
        '<span class="pm-st">' + m.label + "</span></div>";
    }).join("");
  }

  /* ── the architecture ── */
  function diagram(el) {
    if (el.getAttribute("data-diagram") !== "architecture") return;
    var box = function (x, y, w, h, cls, t1, t2) {
      return '<rect class="' + cls + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="12"/>' +
        '<text x="' + (x + w / 2) + '" y="' + (y + h / 2 - (t2 ? 3 : -5)) + '" class="t1">' + t1 + "</text>" +
        (t2 ? '<text x="' + (x + w / 2) + '" y="' + (y + h / 2 + 15) + '" class="t2">' + t2 + "</text>" : "");
    };
    var arr = function (d) { return '<path class="ar" d="' + d + '" marker-end="url(#pd-head)"/>'; };
    el.innerHTML = '<svg viewBox="0 0 900 330" role="img" aria-label="The MEIDNet architecture: a crystal and its properties are encoded into two latents, pulled together by a contrastive loss and averaged into one joint latent, from which two decoders rebuild the crystal and the properties.">' +
      '<defs><marker id="pd-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" class="hd"/></marker>' +
      '<linearGradient id="pd-z" x1="0" x2="1"><stop offset="0" stop-color="#1baf7a"/><stop offset="1" stop-color="#e87ba4"/></linearGradient></defs>' +
      box(20, 40, 130, 70, "in c", "crystal", "CIF: atoms, cell") + box(20, 220, 130, 70, "in p", "properties", "E<tspan dy=\"4\" font-size=\"10\">g</tspan><tspan dy=\"-4\">, ΔH</tspan><tspan dy=\"4\" font-size=\"10\">f</tspan><tspan dy=\"-4\">, …</tspan>") +
      box(200, 40, 160, 70, "enc", "crystal encoder", "E(n)-equivariant GNN") + box(200, 220, 160, 70, "enc", "property encoder", "MLP") +
      arr("M150 75H196") + arr("M150 255H196") +
      '<circle cx="420" cy="75" r="20" class="zc"/><text x="420" y="80" class="zt">z<tspan dy="4" font-size="11">c</tspan></text>' +
      '<circle cx="420" cy="255" r="20" class="zp"/><text x="420" y="260" class="zt">z<tspan dy="4" font-size="11">p</tspan></text>' +
      arr("M360 75H396") + arr("M360 255H396") +
      '<path class="nce" d="M420 97V233"/><text x="432" y="160" class="t2 l">InfoNCE: pull</text><text x="432" y="177" class="t2 l">the pair together</text>' +
      arr("M440 82L530 150") + arr("M440 248L530 180") +
      '<circle cx="560" cy="165" r="30" class="zj"/><text x="560" y="171" class="zt w">z</text><text x="560" y="220" class="t2">z = ½ (z<tspan dy="4" font-size="10">c</tspan><tspan dy="-4"> + z</tspan><tspan dy="4" font-size="10">p</tspan><tspan dy="-4">) ∈ ℝ¹²⁸</tspan></text>' +
      box(660, 40, 220, 70, "dec", "crystal decoder", "species, lattice, positions") + box(660, 220, 220, 70, "dec", "property decoder", "the properties") +
      arr("M588 152L656 92") + arr("M588 178L656 238") +
      '<path class="ar dash" d="M440 262C520 300 600 300 656 270" marker-end="url(#pd-head)"/><text x="540" y="318" class="t2">from z<tspan dy="4" font-size="10">p</tspan><tspan dy="-4"> alone too: inverse design</tspan></text>' +
      "</svg>";
  }

  /* ── wiring ── */
  function mount(root) {
    root.querySelectorAll(".pflow:not([data-done])").forEach(function (e) { e.setAttribute("data-done", ""); flow(e); });
    root.querySelectorAll(".pscene:not([data-done])").forEach(function (e) { e.setAttribute("data-done", ""); scene(e); });
    root.querySelectorAll(".pcrystal:not([data-done])").forEach(function (e) { e.setAttribute("data-done", ""); crystal(e); });
    root.querySelectorAll(".pmodal:not([data-done])").forEach(function (e) { e.setAttribute("data-done", ""); modalities(e); });
    root.querySelectorAll(".pdiagram:not([data-done])").forEach(function (e) { e.setAttribute("data-done", ""); diagram(e); });
  }
  function loop(now) { scenes.forEach(function (s) { s.tick(now); }); crystals.forEach(function (c) { c.tick(now); }); requestAnimationFrame(loop); }
  function start() { mount(document); requestAnimationFrame(loop); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
  // the colour switch of the documentation: redraw what is paused
  if (window.MutationObserver) new MutationObserver(function () { scenes.concat(crystals).forEach(function (s) { s.draw(); }); })
    .observe(document.body || document.documentElement, {attributes: true, attributeFilter: ["data-md-color-scheme"]});
})();
