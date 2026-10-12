/* How multimodal learning connects materials data: the one-minute tour of the MEIDNet Prism landing page (#tour3d),
   drawn live with the Prism3D toolkit. Seven chapters: the modalities of one material, a specialised encoder for each,
   alignment and fusion, three tasks (prediction, retrieval, generation), evaluation, MEIDNet as one reference
   implementation, and where to go next. Every frame is a pure function of time, so playing, seeking, the chapter
   buttons and reduced motion all show the same pictures.
   The example material is SrTiO3, a cubic perovskite (a = 3.905 Å): its powder diffraction pattern is computed from
   that structure (Cu Kα1, structure factors, multiplicities, Lorentz-polarisation), its micrograph is a sketch of a
   Z-contrast (HAADF-STEM) image along [001] in which Sr columns are brightest, and its properties are measured values.
   Diffraction, images and text are marked as concepts: MEIDNet learns from crystal structures and numerical
   properties today. The original inverse-design walkthrough (prism-tour.js, window.PrismScenes, embedded by the
   documentation and kept by MEIDNet Matter) is separate and unchanged; this script exposes window.PrismIntroScenes
   and the landing player's window.prismTour. */
(function () {
  "use strict";
  var P = window.Prism3D;
  if (!P) return;
  var T = P.T, ctx = null;               // the canvas being drawn: set by render() for each frame
  var VW = 960, VH = 540;
  var MATTER = "https://babu09-meidnet-matter.hf.space/";

  var BLOCKS = [
    {id: "modalities", name: "Modalities", c: "#2563eb", href: "/docs/learn/index.html#what-is-a-modality", link: "What is a modality? →"},
    {id: "encoders", name: "Encoders", c: "#f97316", href: "/docs/learn/index.html#the-multimodality-map", link: "The multimodality map →"},
    {id: "alignment", name: "Alignment", c: "#7c3aed", href: "/docs/learn/architectures.html", link: "The Architecture Atlas →"},
    {id: "tasks", name: "Tasks", c: "#1baf7a", href: "/docs/learn/recipes.html", link: "Recipes by problem →"},
    {id: "evaluation", name: "Evaluation", c: "#eda100", href: "/docs/benchmarks/index.html", link: "The benchmarks →"},
    {id: "meidnet", name: "MEIDNet", c: "#4f46e5", href: "/docs/understand/how-it-works.html", link: "How MEIDNet works →"},
    {id: "explore", name: "Explore", c: "#e87ba4", href: MATTER, link: "Explore MEIDNet Matter ↗"}
  ];
  var COL = {}; BLOCKS.forEach(function (b) { COL[b.id] = b.c; });
  // the modalities of one material: a colour and a mark each, the network that usually reads it, and whether MEIDNet uses it today
  var MODS = [
    {id: "structure", name: "structure", c: "#3b82f6", net: "graph neural network", sub: "atoms and bonds as a graph", impl: true},
    {id: "properties", name: "properties", c: "#e87ba4", net: "dense network (MLP)", sub: "a short vector of numbers", impl: true},
    {id: "xrd", name: "diffraction", c: "#f59e0b", net: "1D convolutional network", sub: "intensity versus angle", impl: false},
    {id: "image", name: "image", c: "#14b8a6", net: "2D CNN or vision transformer", sub: "a grid of pixels", impl: false},
    {id: "text", name: "text", c: "#8b5cf6", net: "language model", sub: "a sequence of words", impl: false}
  ];
  var M = {}; MODS.forEach(function (m) { M[m.id] = m; });
  var INDIGO = "#4f46e5";
  var th = P.theme();
  var LUM = {};
  function lum(hex) {
    if (LUM[hex] === undefined) {
      var c = P.rgbOf(hex).map(function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
      LUM[hex] = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    }
    return LUM[hex];
  }
  function ink(hex) {                                 // a palette colour readable as text on this theme
    var c = P.rgbOf(hex);
    return P.css(th.dark ? P.mix(c, [255, 255, 255], 0.3) : P.mix(c, [0, 0, 0], T.clamp(0.08 + (lum(hex) - 0.2) * 1.1, 0.06, 0.42)));
  }
  function tint(hex, a) { return P.css(P.rgbOf(hex), a); }

  /* ── the example material and its views ── */
  var STO = P.perovskite({A: "Sr", B: "Ti", X: "O"}), BTO = P.perovskite({A: "Ba", B: "Ti", X: "O"}), ABX = P.perovskite({A: "A", B: "B", X: "X"});
  function rocksalt(cat, an) {          // the rock-salt cell, half edge 1: cations on the fcc sites, anions between them
    var atoms = [], edges = [];
    for (var x = -1; x <= 1; x++) for (var y = -1; y <= 1; y++) for (var z = -1; z <= 1; z++) {
      var cation = Math.abs(x + y + z) % 2 === 1;
      atoms.push({p: [x, y, z], site: cation ? "A" : "X", el: cation ? cat : an});
    }
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (u) {
      edges.push([[-1, u[0], u[1]], [1, u[0], u[1]]]); edges.push([[u[0], -1, u[1]], [u[0], 1, u[1]]]); edges.push([[u[0], u[1], -1], [u[0], u[1], 1]]);
    });
    return {atoms: atoms, edges: edges, faces: []};
  }
  var SRO = rocksalt("Sr", "O");
  // powder XRD of SrTiO3 (Cu Kα1): 2θ in degrees and relative intensity, computed from the cubic structure
  var XRD = [[22.75, 4], [32.4, 100], [39.96, 21], [46.47, 41], [52.35, 3], [57.79, 37], [67.83, 23], [72.57, 2], [77.19, 16], [81.72, 6]];
  var XRD_LO = 15, XRD_HI = 85, XRD_CURVE = (function () {   // a measured-looking curve: peaks (FWHM 0.55°), a low background, a little noise
    var R = T.rng(17), out = [], k = 4 * Math.log(2) / (0.55 * 0.55);
    for (var x = XRD_LO; x <= XRD_HI + 1e-9; x += 0.2) {
      var y = 2.2 - 0.012 * (x - XRD_LO) + (R() + R() - 1) * 0.9;
      XRD.forEach(function (p) { y += p[1] * Math.exp(-k * (x - p[0]) * (x - p[0])); });
      out.push([x, Math.max(0, y)]);
    }
    return out;
  })();
  function xrd(x, y, w, h, upto, color, o) {        // the pattern in the box (x, y, w, h), scanned up to the fraction `upto`
    o = o || {};
    if (upto <= 0) return;
    var n = Math.max(2, Math.round(XRD_CURVE.length * T.clamp(upto))), X = function (v) { return x + (v - XRD_LO) / (XRD_HI - XRD_LO) * w; };
    ctx.save(); ctx.beginPath();
    for (var i = 0; i < n; i++) { var p = XRD_CURVE[i], px = X(p[0]), py = y + h - p[1] / 104 * h; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
    ctx.lineJoin = "round"; ctx.lineWidth = o.lw || 1.6; ctx.strokeStyle = color; ctx.stroke();
    if (upto < 1) { var e = X(XRD_CURVE[n - 1][0]); ctx.globalAlpha *= 0.45; ctx.fillStyle = color; ctx.fillRect(e - 1, y, 2, h); }
    ctx.restore();
  }
  var stemCache = null;
  function stem() {           // a Z-contrast (HAADF-STEM) sketch of SrTiO3 along [001]: Sr columns brightest, Ti–O columns dimmer, O columns faint
    if (stemCache) return stemCache;
    var S = 2, w = 244 * S, h = 136 * S, cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    var g = cv.getContext("2d"), img = g.createImageData(w, h), d = img.data, R = T.rng(11), a = 21 * S, s2 = 2 * 0.115 * 0.115;
    for (var j = 0; j < h; j++) for (var i = 0; i < w; i++) {
      var u = (i - 0.37 * a) / a + 0.012 * Math.sin(j * 0.045), v = (j - 0.3 * a) / a;     // a slight scan wobble
      var fu = u - Math.round(u), fv = v - Math.round(v), gu = u - Math.floor(u) - 0.5, gv = v - Math.floor(v) - 0.5;
      var I = Math.exp(-(fu * fu + fv * fv) / s2) + 0.46 * Math.exp(-(gu * gu + gv * gv) / s2) +
              0.07 * (Math.exp(-(gu * gu + fv * fv) / s2) + Math.exp(-(fu * fu + gv * gv) / s2));
      I = T.clamp(0.07 + 0.9 * I + (R() + R() + R() - 1.5) * 0.08);
      var gray = Math.round(255 * Math.pow(I, 0.85)), k = 4 * (j * w + i);
      d[k] = gray; d[k + 1] = gray; d[k + 2] = gray; d[k + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    stemCache = {cv: cv, S: S, cell: a / S};
    return stemCache;
  }
  function micrograph(x, y, w, h, upto, o) {         // the image drawn into (x, y, w, h), acquired line by line up to `upto`
    o = o || {};
    if (upto <= 0) return;
    var im = stem(), sw = Math.min(im.cv.width, w * im.S), sh = Math.min(im.cv.height, h * im.S), hh = h * T.clamp(upto);
    ctx.save(); P.rrect(ctx, x, y, w, h, o.r === undefined ? 8 : o.r); ctx.clip();
    ctx.fillStyle = "#0b0d10"; ctx.fillRect(x, y, w, h);
    ctx.drawImage(im.cv, 0, 0, sw, sh * T.clamp(upto), x, y, w, hh);
    if (upto < 1) { ctx.fillStyle = "rgba(255,255,255,.55)"; ctx.fillRect(x, y + hh - 1, w, 2); }
    if (o.bar && upto >= 1) {                          // scale bar: 1 nm = 1 / 0.3905 unit cells
      var L = im.cell * w * im.S / sw / 0.3905, bx = x + 12, by = y + h - 13;
      ctx.fillStyle = "#fff"; ctx.fillRect(bx, by, L, 3.5);
      P.text(ctx, "1 nm", bx + L / 2, by - 6, {size: 12, weight: 700, color: "#fff", align: "center"});
    }
    ctx.restore();
  }
  var QUOTE = "SrTiO₃ adopts the cubic perovskite structure at room temperature. Crystals grown by flame fusion are common substrates for oxide films.";

  /* ── flat helpers in the 960 × 540 stage (after prism-tour.js) ── */
  function card(x, y, w, h, o) {
    o = o || {};
    ctx.save(); if (o.alpha !== undefined) ctx.globalAlpha *= T.clamp(o.alpha);
    P.rrect(ctx, x, y, w, h, o.r === undefined ? 14 : o.r);
    ctx.fillStyle = o.fill || (th.dark ? "rgba(27,31,36,.86)" : "rgba(255,255,255,.88)"); ctx.fill();
    if (o.stroke !== null) { ctx.lineWidth = o.sw || 1.5; ctx.strokeStyle = o.stroke || th.line; if (o.dash) ctx.setLineDash(o.dash); ctx.stroke(); }
    ctx.restore();
  }
  function label(str, x, y, o) { o = o || {}; P.text(ctx, str, x, y, {size: o.size || 18, weight: o.weight || 600, color: o.color || th.ink, align: o.align, alpha: o.alpha, family: o.family, italic: o.italic, baseline: o.baseline}); }
  function cam(cx, cy, scale, yaw, pitch) { return P.camera({cx: cx, cy: cy, scale: scale, yaw: yaw, pitch: pitch === undefined ? -0.38 : pitch}); }
  function chip(x, y, str, hex, on, o) {
    o = o || {}; var w = o.w || Math.max(46, 11 * str.length + 26), h = o.h || 32;
    card(x - w / 2, y - h / 2, w, h, {r: h / 2, fill: on ? hex : (th.dark ? "#1b1f24" : "#fff"), stroke: hex, sw: 2, alpha: o.alpha});
    label(str, x, y + (o.size || 16) * 0.36, {align: "center", size: o.size || 16, weight: 700, color: on ? "#fff" : ink(hex), alpha: o.alpha});
  }
  function star(x, y, r, color, a) {
    ctx.save(); ctx.globalAlpha *= a === undefined ? 1 : a; ctx.beginPath();
    for (var i = 0; i < 10; i++) { var rr = i % 2 ? r * 0.45 : r, an = -Math.PI / 2 + i * Math.PI / 5; ctx.lineTo(x + rr * Math.cos(an), y + rr * Math.sin(an)); }
    ctx.closePath(); ctx.fillStyle = color; ctx.shadowColor = color; ctx.shadowBlur = 12; ctx.fill(); ctx.restore();
  }
  function dot(cm, p, r, color, a) {
    var q = cm.proj(p); ctx.save(); ctx.globalAlpha *= a === undefined ? 1 : a;
    ctx.beginPath(); ctx.arc(q[0], q[1], Math.max(1, r * q[3]), 0, 2 * Math.PI); ctx.fillStyle = color; ctx.fill(); ctx.restore(); return q;
  }
  function cloud(seed, n, radius) {
    var R = T.rng(seed), pts = [];
    while (pts.length < n) { var p = [R() * 2 - 1, R() * 2 - 1, R() * 2 - 1]; if (p[0] * p[0] + p[1] * p[1] + p[2] * p[2] <= 1) pts.push(p.map(function (v) { return v * radius; })); }
    return pts;
  }
  function dotFlat(x, y, r, color, a) { ctx.save(); ctx.globalAlpha *= a; ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fillStyle = color; ctx.fill(); ctx.restore(); }
  function ringFlat(x, y, r, color, a) { ctx.save(); ctx.globalAlpha *= a; ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.lineWidth = 2.5; ctx.strokeStyle = color; ctx.stroke(); ctx.restore(); }
  function rule(x1, x2, y, a) { ctx.save(); ctx.globalAlpha *= a === undefined ? 1 : a; ctx.fillStyle = th.line; ctx.fillRect(x1, y, x2 - x1, 1); ctx.restore(); }
  function dashed(x1, y1, x2, y2, p, color, w, a) {     // a dashed connector, drawn from its start up to the fraction p
    if (p <= 0) return;
    ctx.save(); ctx.globalAlpha *= a === undefined ? 1 : a; ctx.setLineDash([5, 5]); ctx.lineWidth = w || 2; ctx.lineCap = "round"; ctx.strokeStyle = color;
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(T.lerp(x1, x2, p), T.lerp(y1, y2, p)); ctx.stroke(); ctx.restore();
  }
  function tw(str, size, weight, family) { ctx.save(); ctx.font = (weight || 600) + " " + size + "px " + (family || P.FONT); var w = ctx.measureText(str).width; ctx.restore(); return w; }
  function concept(xr, y, a) {          // the discreet mark of a modality MEIDNet does not use today; xr: its right end, y: its middle
    if (a !== undefined && a <= 0) return;
    var w = tw("concept", 11.5, 500, P.MONO) + 16;
    card(xr - w, y - 10, w, 20, {r: 10, fill: th.dark ? "#1b1f24" : "#fff", stroke: th.faint, sw: 1, dash: [3, 2.5], alpha: a});
    label("concept", xr - w / 2, y + 4, {size: 11.5, weight: 500, family: P.MONO, color: th.muted, align: "center", alpha: a});
  }
  function key(cx, y, a) {              // the key to the dashed cards, centred on cx
    if (a <= 0) return;
    var str = "dashed: a concept, not in MEIDNet today", w = 36 + tw(str, 13, 600), x = cx - w / 2;
    card(x, y - 13, 26, 18, {r: 6, fill: "rgba(0,0,0,0)", stroke: th.faint, sw: 1.2, dash: [4, 3], alpha: a});
    label(str, x + 36, y + 1, {size: 13, color: th.faint, alpha: a});
  }
  function vec(x, y, n, cw, ch, hex, seed, p, o) {     // a vector of n numbers as shaded cells, revealed left to right (p: 0..1)
    o = o || {};
    var R = T.rng(seed), c = P.rgbOf(hex), base = th.dark ? [27, 31, 36] : [255, 255, 255], gap = o.gap === undefined ? 3 : o.gap;
    for (var i = 0; i < n; i++) {
      var v = 0.15 + 0.85 * R(), a = T.clamp(p * n - i) * (o.alpha === undefined ? 1 : o.alpha);
      if (a <= 0) continue;
      ctx.save(); ctx.globalAlpha *= a;
      P.rrect(ctx, x + i * (cw + gap), y, cw, ch, Math.min(4, cw / 3));
      ctx.fillStyle = P.css(P.mix(c, base, 1 - v)); ctx.fill();
      ctx.lineWidth = 1; ctx.strokeStyle = P.css(c, 0.6); ctx.stroke();
      ctx.restore();
    }
  }
  function mark(id, x, y, r, a) {      // the mark of a modality at screen (x, y): atom, ring, diamond, square, triangle
    var m = M[id], c = P.rgbOf(m.c);
    ctx.save(); ctx.globalAlpha *= a === undefined ? 1 : a; ctx.beginPath();
    if (id === "structure") {
      var g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
      g.addColorStop(0, "rgba(255,255,255,.95)"); g.addColorStop(0.32, P.css(P.mix(c, [255, 255, 255], 0.3))); g.addColorStop(1, P.css(P.mix(c, [0, 0, 0], 0.3)));
      ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fillStyle = g; ctx.fill();
    } else if (id === "properties") {
      ctx.arc(x, y, r * 0.85, 0, 2 * Math.PI); ctx.lineWidth = Math.max(1.6, r * 0.42); ctx.strokeStyle = m.c; ctx.stroke();
    } else {
      if (id === "xrd") { ctx.moveTo(x, y - r * 1.2); ctx.lineTo(x + r * 1.2, y); ctx.lineTo(x, y + r * 1.2); ctx.lineTo(x - r * 1.2, y); }
      else if (id === "image") ctx.rect(x - r * 0.88, y - r * 0.88, r * 1.76, r * 1.76);
      else { ctx.moveTo(x, y - r * 1.15); ctx.lineTo(x + r * 1.05, y + r * 0.8); ctx.lineTo(x - r * 1.05, y + r * 0.8); }
      ctx.closePath(); ctx.fillStyle = m.c; ctx.fill();
      ctx.lineWidth = 1; ctx.strokeStyle = th.dark ? "rgba(0,0,0,.4)" : "rgba(255,255,255,.75)"; ctx.stroke();
    }
    ctx.restore();
  }
  function wrap(str, maxW, size, o) {    // words into lines no wider than maxW, measured in the font they are drawn with
    o = o || {};
    ctx.save(); ctx.font = (o.italic ? "italic " : "") + (o.weight || 600) + " " + size + "px " + (o.family || P.FONT);
    var lines = [], cur = "";
    str.split(" ").forEach(function (w) { var t2 = cur ? cur + " " + w : w; if (cur && ctx.measureText(t2).width > maxW) { lines.push(cur); cur = w; } else cur = t2; });
    if (cur) lines.push(cur);
    ctx.restore(); return lines;
  }
  function box3(c, half, color) {         // the wire frame of a cube: the shared space
    [[-1, -1], [-1, 1], [1, -1], [1, 1]].forEach(function (u) {
      P.line3(ctx, c, [-half, u[0] * half, u[1] * half], [half, u[0] * half, u[1] * half], color, 1);
      P.line3(ctx, c, [u[0] * half, -half, u[1] * half], [u[0] * half, half, u[1] * half], color, 1);
      P.line3(ctx, c, [u[0] * half, u[1] * half, -half], [u[0] * half, u[1] * half, half], color, 1);
    });
  }
  function frameColor() { return th.dark ? "rgba(148,163,184,.35)" : "rgba(100,116,139,.35)"; }
  function gauss(x0, x1, base, h, mu, sig, X, color, a, fill) {   // a normal density on screen: X maps values to pixels
    ctx.save(); ctx.globalAlpha *= a; ctx.beginPath();
    for (var i = 0; i <= 80; i++) { var v = x0 + (x1 - x0) * i / 80, y = base - h * Math.exp(-0.5 * Math.pow((v - mu) / sig, 2)); i ? ctx.lineTo(X(v), y) : ctx.moveTo(X(v), y); }
    if (fill) { ctx.lineTo(X(x1), base); ctx.lineTo(X(x0), base); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); }
    ctx.lineWidth = 2.2; ctx.strokeStyle = color; ctx.stroke(); ctx.restore();
  }

  /* data of the later chapters: materials in the shared space, the parity plot, the search */
  var MATS = (function () {             // six materials, five views each: scattered at first, then pulled together
    var R = T.rng(29), C = [[0.5, 0.42, 0.55], [-0.62, 0.5, -0.32], [0.12, -0.58, -0.62], [-0.6, -0.48, 0.42], [0.66, -0.4, -0.28], [-0.12, 0.62, 0.62]];
    return C.map(function (c, i) {
      var s = [], o = [];
      MODS.forEach(function (m, j) {
        s.push([R() * 2 - 1, R() * 2 - 1, R() * 2 - 1].map(function (v) { return v * 0.98; }));
        var an = j / MODS.length * 2 * Math.PI + i * 0.7, el = (R() - 0.5) * 0.9, rr = 0.15;
        o.push([rr * Math.cos(an) * Math.cos(el), rr * Math.sin(el), rr * Math.sin(an) * Math.cos(el)]);
      });
      return {c: c, s: s, o: o};
    });
  })();
  var PAIRS = (function () {             // MEIDNet's two views per material: a crystal and its properties
    var R = T.rng(7), out = [];
    for (var k = 0; k < 8; k++) out.push({m: [R() * 1.4 - 0.7, R() * 1.4 - 0.7, R() * 1.4 - 0.7], d: [R() - 0.5, R() - 0.5, R() - 0.5]});
    return out;
  })();
  var PARITY = {                        // true and predicted values (eV): test materials like the training data, and an unseen family
    seen: [[0.4, 0.52], [0.55, 0.7], [0.7, 0.61], [0.9, 1.02], [1.05, 0.94], [1.2, 1.11], [1.4, 1.55], [1.6, 1.52], [1.9, 2.04], [2.1, 1.98],
           [2.3, 2.41], [2.5, 2.43], [2.65, 2.82], [2.8, 2.7], [3.0, 3.13], [3.2, 3.08], [3.5, 3.62], [3.7, 3.55]],
    unseen: [[0.8, 1.6], [1.1, 1.9], [1.3, 0.62], [1.7, 2.62], [2.2, 1.3], [2.6, 3.45], [3.1, 2.1], [3.4, 2.62]]
  };
  var SPACE_CLOUD = cloud(5, 70, 1);
  function walk(k, u, s) {                // one member of the search population, leaving the target's point (after prism-tour.js)
    var th0 = k * 1.26 + 0.3, ph = 0.6 * Math.sin(k * 1.7), r = s * (0.12 + 0.95 * T.ease(T.seg(u, 0.04, 0.7)) * (0.6 + 0.4 * ((k * 37) % 10) / 10));
    return [r * Math.cos(th0 + 0.9 * u) * Math.cos(ph), r * Math.sin(ph) + 0.06 * s * Math.sin(u * 9 + k), r * Math.sin(th0 + 0.9 * u) * Math.cos(ph)];
  }

  /* ── the chapters ── */
  var SCENES = [
    {block: "modalities", ms: 9000,
     cap: "One material can be described in complementary ways: its crystal structure, its properties, a diffraction pattern, a microscope image and text. MEIDNet learns from the first two today; the others are marked as concepts.",
     draw: function (t) {
       var C = [480, 236];
       // the views, clockwise from the top left, each joined to the material
       var views = [{id: "properties", x: 24, y: 26, h: 196, ax: 304, ay: 124, s: 0.2}, {id: "xrd", x: 656, y: 26, h: 196, ax: 656, ay: 124, s: 0.34},
                    {id: "image", x: 656, y: 300, h: 196, ax: 656, ay: 398, s: 0.48}, {id: "text", x: 24, y: 300, h: 196, ax: 304, ay: 398, s: 0.62}];
       views.forEach(function (v) {
         var dx = v.ax - C[0], dy = v.ay - C[1], L = Math.hypot(dx, dy);
         dashed(C[0] + dx / L * 112, C[1] + dy / L * 112, v.ax, v.ay, T.ease(T.seg(t, v.s, v.s + 0.07)), tint(M[v.id].c, 0.8), 2);
       });
       var asm = T.ease(T.seg(t, 0, 0.2));
       P.crystal(ctx, cam(C[0], C[1], 66, -0.8 + 0.95 * t), STO, {explode: 1 - asm, glass: T.seg(t, 0.12, 0.24), edges: T.seg(t, 0.12, 0.24),
                                                           labels: t > 0.15, dark: th.dark, alpha: T.seg(t, 0, 0.05)});
       label("SrTiO₃", C[0], 404, {size: 30, weight: 800, align: "center", alpha: T.seg(t, 0.12, 0.22)});
       label("crystal structure · cubic perovskite", C[0], 432, {size: 16, weight: 700, color: ink(M.structure.c), align: "center", alpha: T.seg(t, 0.16, 0.26)});
       views.forEach(function (v) {
         var m = M[v.id], a = T.out(T.seg(t, v.s + 0.03, v.s + 0.11)), left = v.x < C[0], W = 280, x = v.x, y = v.y;
         if (a <= 0) return;
         ctx.save(); ctx.translate((left ? -26 : 26) * (1 - a), 0);
         card(x, y, W, v.h, {alpha: a, stroke: tint(m.c, 0.9), sw: 2, dash: m.impl ? null : [7, 5]});
         label(v.id === "xrd" ? "Diffraction" : v.id === "image" ? "Microscopy" : v.id === "text" ? "Text" : "Properties", x + 20, y + 32,
               {size: 18, weight: 800, color: ink(m.c), alpha: a});
         if (!m.impl) concept(x + W - 16, y + 26, a);
         var p = T.seg(t, v.s + 0.07, v.s + 0.2);       // the view fills in: rows, a scan, an image, words
         if (v.id === "properties") {
           [["band gap", "3.2 eV"], ["formation enthalpy", "−3.5 eV/atom"], ["dielectric constant", "≈ 300"]].forEach(function (r, k) {
             var b = T.seg(p, k * 0.25, k * 0.25 + 0.4), yy = y + 64 + k * 44;
             label(r[0], x + 20, yy, {size: 13.5, color: th.muted, alpha: a * b});
             label(r[1], x + 20, yy + 21, {size: 19, weight: 800, alpha: a * b});
             if (k < 2) rule(x + 20, x + W - 20, yy + 31, a * b);
           });
           label("measured", x + W - 20, y + 32, {size: 12, color: th.faint, align: "right", alpha: a * T.seg(p, 0.6, 1)});
         } else if (v.id === "xrd") {
           var px = x + 20, pw = W - 40, py = y + 62, ph = 98, X = function (d) { return px + (d - XRD_LO) / (XRD_HI - XRD_LO) * pw; };
           ctx.save(); ctx.globalAlpha *= a;
           ctx.fillStyle = th.line; ctx.fillRect(px, py + ph, pw, 1.5);
           [20, 40, 60].forEach(function (d) { ctx.fillRect(X(d) - 0.5, py + ph, 1, 5); label(String(d), X(d), py + ph + 19, {size: 12, color: th.faint, align: "center"}); });
           label("2θ (°)", px + pw, py + ph + 19, {size: 12, color: th.faint, align: "right"});
           xrd(px, py, pw, ph, p, ink(m.c), {lw: 1.5});
           label("(110)", X(32.4) + 6, py + 12, {size: 12, weight: 700, color: th.muted, alpha: T.seg(p, 0.35, 0.55)});
           label("(200)", X(46.47) + 5, py + ph * 0.6 + 4, {size: 12, weight: 700, color: th.muted, alpha: T.seg(p, 0.55, 0.75)});
           ctx.restore();
         } else if (v.id === "image") {
           ctx.save(); ctx.globalAlpha *= a; micrograph(x + 18, y + 48, W - 36, v.h - 64, p, {bar: true}); ctx.restore();
           label("Z-contrast STEM, along [001]", x + W - 20, y + v.h - 22, {size: 11.5, weight: 600, color: "rgba(255,255,255,.8)", align: "right", alpha: a * T.seg(p, 0.95, 1)});
         } else {
           var lines = wrap(QUOTE, W - 40, 16, {italic: true, weight: 500, family: P.MATH}), total = 0, shown = Math.floor(QUOTE.length * p);
           lines.forEach(function (ln, k) {
             var str = ln.slice(0, Math.max(0, shown - total)); total += ln.length + 1;
             if (str) label(str, x + 20, y + 66 + k * 24, {size: 16, weight: 500, italic: true, family: P.MATH, alpha: a});
           });
         }
         ctx.restore();
       });
       key(C[0], 500, T.seg(t, 0.82, 0.92));
     }},

    {block: "encoders", ms: 8000,
     cap: "A specialised network turns each modality into a vector: a graph network for the structure, a dense network for the numbers, convolutional networks for patterns and images, and a language model for text.",
     draw: function (t) {
       [["modality", 100], ["specialised encoder", 347], ["vector", 644]].forEach(function (h) {
         label(h[0], h[1], 40, {size: 14, weight: 700, color: th.faint, align: "center", alpha: T.seg(t, 0, 0.06)});
       });
       MODS.forEach(function (m, i) {
         var cy = 92 + i * 88, s = 0.04 + i * 0.105, a = T.out(T.seg(t, s, s + 0.06)), col = m.c;
         if (a <= 0) return;
         // the modality, small
         card(40, cy - 30, 120, 60, {r: 10, alpha: a, stroke: tint(col, 0.65), sw: 1.5, dash: m.impl ? null : [5, 4]});
         ctx.save(); ctx.globalAlpha *= a;
         if (m.id === "structure") P.crystal(ctx, cam(100, cy, 14.5, -0.6 + 0.9 * t + i), STO, {dark: th.dark, glass: 0.8});
         else if (m.id === "properties") {
           label("3.2 eV", 100, cy - 4, {size: 17, weight: 800, align: "center"});
           label("−3.5 eV/atom", 100, cy + 16, {size: 12.5, weight: 700, color: th.muted, align: "center"});
         } else if (m.id === "xrd") { ctx.fillStyle = th.line; ctx.fillRect(50, cy + 21, 100, 1); xrd(50, cy - 21, 100, 42, 1, ink(col), {lw: 1.2}); }
         else if (m.id === "image") micrograph(46, cy - 25, 108, 50, 1, {r: 6});
         else ["SrTiO₃ adopts the", "cubic perovskite", "structure at room…"].forEach(function (s2, k) {
           label(s2, 50, cy - 9 + k * 15, {size: 12.5, weight: 500, italic: true, family: P.MATH});
         });
         ctx.restore();
         P.arrow(ctx, 166, cy, 205, cy, T.ease(T.seg(t, s + 0.04, s + 0.1)), tint(col, 0.9), 3);
         // its encoder
         var b = T.out(T.seg(t, s + 0.07, s + 0.13));
         card(212, cy - 30, 270, 60, {alpha: b, fill: th.dark ? tint(col, 0.13) : P.css(P.mix(P.rgbOf(col), [255, 255, 255], 0.9)), stroke: col, sw: 2.2, dash: m.impl ? null : [7, 5]});
         var u = T.seg(t, s + 0.1, s + 0.24);
         if (u > 0 && u < 1) {                     // the modality passing through
           ctx.save(); P.rrect(ctx, 212, cy - 30, 270, 60, 14); ctx.clip();
           var gx = 212 - 60 + 390 * u, g = ctx.createLinearGradient(gx - 50, 0, gx + 50, 0);
           g.addColorStop(0, "rgba(255,255,255,0)"); g.addColorStop(0.5, th.dark ? "rgba(255,255,255,.16)" : "rgba(255,255,255,.75)"); g.addColorStop(1, "rgba(255,255,255,0)");
           ctx.fillStyle = g; ctx.fillRect(gx - 50, cy - 30, 100, 60); ctx.restore();
         }
         label(m.net, 347, cy - 3, {size: 15.5, weight: 800, color: ink(col), align: "center", alpha: b});
         label(m.sub, 347, cy + 18, {size: 12.5, weight: 500, family: P.MONO, color: th.muted, align: "center", alpha: b});
         if (!m.impl) concept(470, cy - 30, b);
         P.arrow(ctx, 488, cy, 524, cy, T.ease(T.seg(t, s + 0.18, s + 0.23)), tint(col, 0.9), 3);
         vec(532, cy - 17, 12, 16, 34, col, 101 + i, T.seg(t, s + 0.21, s + 0.33));
       });
       var e = T.seg(t, 0.8, 0.9);
       ctx.save(); ctx.globalAlpha *= e; ctx.strokeStyle = th.faint; ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.beginPath();
       ctx.moveTo(772, 64); ctx.quadraticCurveTo(782, 64, 782, 76); ctx.lineTo(782, 256); ctx.quadraticCurveTo(782, 268, 792, 268);
       ctx.quadraticCurveTo(782, 268, 782, 280); ctx.lineTo(782, 460); ctx.quadraticCurveTo(782, 472, 772, 472); ctx.stroke(); ctx.restore();
       label("one vector", 802, 256, {size: 17, weight: 800, color: th.muted, alpha: e});
       label("per modality", 802, 278, {size: 17, weight: 800, color: th.muted, alpha: e});
       label("(an embedding)", 802, 302, {size: 14, color: th.faint, alpha: e});
       key(400, 508, T.seg(t, 0.84, 0.94));
     }},

    {block: "alignment", ms: 9000,
     cap: "Training relates the vectors so that the views of one material end up close together, for example in a shared latent space, one possible approach. Fusion then combines the aligned vectors into one representation of the material.",
     draw: function (t) {
       var c = cam(372, 262, 100, -0.62 + 0.5 * t, -0.3), half = 1.15, show = T.seg(t, 0.02, 0.12), pull = T.ease(T.seg(t, 0.14, 0.55));
       label("a shared latent space", 40, 50, {size: 18, weight: 800, color: th.muted, alpha: show});
       label("one possible approach", 40, 72, {size: 14, color: th.faint, alpha: show});
       ctx.save(); ctx.globalAlpha *= show; box3(c, half, frameColor());
       var pts = [];
       MATS.forEach(function (mt, i) {
         var k = 0.8 + 0.2 * pull, cen = [mt.c[0] * k, mt.c[1] * k, mt.c[2] * k];       // materials drift apart while their views gather
         MODS.forEach(function (m, j) {
           var e = [cen[0] + mt.o[j][0], cen[1] + mt.o[j][1], cen[2] + mt.o[j][2]], s = mt.s[j];
           var p = [T.lerp(s[0], e[0], pull), T.lerp(s[1], e[1], pull), T.lerp(s[2], e[2], pull)];
           pts.push({i: i, id: m.id, p: p, cen: cen, q: c.proj(p)});
         });
       });
       var link = th.dark ? "rgba(203,213,225," : "rgba(100,116,139,";
       pts.forEach(function (o) { P.line3(ctx, c, o.p, o.cen, link + (0.5 * (1 - 0.7 * pull)).toFixed(3) + ")", 1.2, [3, 4]); });
       pts.sort(function (a, b) { return a.q[2] - b.q[2]; }).forEach(function (o) {
         mark(o.id, o.q[0], o.q[1], 0.08 * o.q[3], o.i === 0 || t < 0.56 ? 1 : 1 - 0.45 * T.seg(t, 0.56, 0.64));
       });
       ctx.restore();
       // SrTiO3: its five views, now in one place
       var h = T.seg(t, 0.52, 0.6), sc = c.proj(MATS[0].c.map(function (v) { return v * (0.8 + 0.2 * pull); }));
       if (h > 0) {
         ctx.save(); ctx.globalAlpha *= h; ctx.beginPath(); ctx.arc(sc[0], sc[1], 30, 0, 2 * Math.PI);
         ctx.lineWidth = 2.5; ctx.strokeStyle = ink(COL.alignment); ctx.setLineDash([4, 4]); ctx.stroke(); ctx.restore();
         label("SrTiO₃", sc[0], sc[1] - 40, {size: 16, weight: 800, align: "center", alpha: h});
       }
       label("views of one material: pulled together", 372, 470, {size: 16, weight: 800, color: ink(COL.alignment), align: "center", alpha: T.seg(t, 0.42, 0.52)});
       // the key: the modalities MEIDNet uses, then the concepts in a dashed group
       var lk = T.seg(t, 0.06, 0.16);
       if (lk > 0) {
         var ws = MODS.map(function (m) { return 14 + tw(m.name, 14, 600); }), cw = tw("concepts", 13, 600), gap = 22;
         var total = ws.reduce(function (s, w) { return s + w + gap; }, 0) + cw + 16, lx = 372 - total / 2;
         MODS.forEach(function (m, j) {
           if (j === 2) { card(lx - 12, 492, ws[2] + ws[3] + ws[4] + 3 * gap + cw + 28, 30, {r: 15, fill: "rgba(0,0,0,0)", stroke: th.faint, sw: 1.1, dash: [4, 3], alpha: lk}); lx += 6; }
           mark(m.id, lx + 6, 507, 6.5, lk); label(m.name, lx + 18, 512, {size: 14, color: th.muted, alpha: lk});
           lx += ws[j] + gap;
         });
         label("concepts", lx, 512, {size: 13, color: th.faint, alpha: lk});
       }
       // fusion: the aligned vectors of SrTiO3 combined into one
       var f = T.out(T.seg(t, 0.56, 0.64)), fx = 676, fy = 64;
       if (f > 0) {
         dashed(sc[0] + 32, sc[1], fx - 4, fy + 120, T.ease(T.seg(t, 0.56, 0.64)), tint(COL.alignment, 0.85), 2);
         ctx.save(); ctx.translate(30 * (1 - f), 0);
         card(fx, fy, 254, 412, {alpha: f, stroke: tint(INDIGO, 0.8), sw: 2});
         label("Fusion", fx + 22, fy + 40, {size: 21, weight: 800, color: ink(INDIGO), alpha: f});
         label("aligned vectors, combined", fx + 22, fy + 64, {size: 14, color: th.muted, alpha: f});
         MODS.forEach(function (m, j) { vec(fx + 32, fy + 92 + j * 25, 10, 16, 14, m.c, 101 + j, T.seg(t, 0.6 + j * 0.02, 0.68 + j * 0.02), {alpha: f}); });
         var u = T.seg(t, 0.72, 0.84), top = fy + 92 + 5 * 25 + 6, bot = fy + 262;
         ctx.save(); ctx.globalAlpha *= f * u; ctx.beginPath();
         ctx.moveTo(fx + 32, top); ctx.lineTo(fx + 222, top); ctx.lineTo(fx + 186, bot); ctx.lineTo(fx + 68, bot); ctx.closePath();
         var g = ctx.createLinearGradient(0, top, 0, bot); g.addColorStop(0, tint(INDIGO, 0.04)); g.addColorStop(1, tint(INDIGO, th.dark ? 0.3 : 0.18));
         ctx.fillStyle = g; ctx.fill(); ctx.restore();
         label("fuse", fx + 127, top + 32, {size: 14, weight: 800, color: ink(INDIGO), align: "center", alpha: f * T.seg(t, 0.76, 0.84)});
         vec(fx + 52, bot + 6, 8, 16, 32, INDIGO, 131, T.seg(t, 0.8, 0.9), {alpha: f, gap: 3});
         label("one representation", fx + 127, bot + 70, {size: 17, weight: 800, align: "center", alpha: f * T.seg(t, 0.86, 0.94)});
         label("of SrTiO₃", fx + 127, bot + 92, {size: 15, weight: 700, color: th.muted, align: "center", alpha: f * T.seg(t, 0.86, 0.94)});
         label("by averaging, concatenating", fx + 127, bot + 124, {size: 13, color: th.faint, align: "center", alpha: f * T.seg(t, 0.9, 0.98)});
         label("or attention, for example", fx + 127, bot + 142, {size: 13, color: th.faint, align: "center", alpha: f * T.seg(t, 0.9, 0.98)});
         ctx.restore();
       }
     }},

    {block: "tasks", ms: 9500,
     cap: "A learned representation serves different tasks: predicting a property from a structure, retrieving the matching item in another modality, and generating new structures for target properties.",
     draw: function (t) {
       var col = COL.tasks;
       [["Prediction", "structure → property", 0.03], ["Retrieval", "one modality → another", 0.33], ["Generation", "target → new structure", 0.63]].forEach(function (pn, k) {
         var x0 = 30 + k * 307, a = T.out(T.seg(t, pn[2], pn[2] + 0.08)), on = t >= pn[2] && t < pn[2] + 0.3;
         ctx.save(); ctx.translate(0, 30 * (1 - a));
         card(x0, 60, 286, 404, {alpha: a, stroke: on ? col : th.line, sw: on ? 2.4 : 1.5});
         label(pn[0], x0 + 143, 100, {size: 23, weight: 800, color: ink(col), align: "center", alpha: a});
         label(pn[1], x0 + 143, 126, {size: 15, weight: 600, color: th.muted, align: "center", alpha: a});
         ctx.restore();
       });
       // prediction: a structure in, a property out
       var x0 = 30, p1 = T.seg(t, 0.06, 0.3);
       if (p1 > 0) {
         P.crystal(ctx, cam(x0 + 143, 218, 33, -0.6 + 0.8 * t), STO, {dark: th.dark, labels: true, alpha: T.seg(p1, 0, 0.2)});
         label("SrTiO₃", x0 + 143, 296, {size: 17, weight: 800, align: "center", alpha: T.seg(p1, 0.1, 0.3)});
         P.arrow(ctx, x0 + 143, 308, x0 + 143, 344, T.ease(T.seg(p1, 0.3, 0.5)), col, 3.5);
         card(x0 + 38, 354, 210, 84, {alpha: T.seg(p1, 0.45, 0.65), stroke: tint(M.properties.c, 0.9), sw: 2});
         label("predicted band gap", x0 + 143, 382, {size: 14, color: th.muted, align: "center", alpha: T.seg(p1, 0.5, 0.7)});
         label("≈ 3.1 eV", x0 + 143, 420, {size: 30, weight: 800, align: "center", alpha: T.seg(p1, 0.6, 0.8)});
       }
       // retrieval: a diffraction pattern finds its structure
       x0 = 337; var p2 = T.seg(t, 0.36, 0.6);
       if (p2 > 0) {
         card(x0 + 26, 144, 234, 74, {r: 10, alpha: T.seg(p2, 0, 0.15), stroke: tint(M.xrd.c, 0.9), sw: 1.8, dash: [6, 4]});
         label("query: a measured pattern", x0 + 40, 166, {size: 12.5, weight: 700, color: th.muted, alpha: T.seg(p2, 0, 0.15)});
         concept(x0 + 248, 144, T.seg(p2, 0, 0.15));
         ctx.save(); ctx.globalAlpha *= T.seg(p2, 0, 0.15); ctx.fillStyle = th.line; ctx.fillRect(x0 + 40, 208, 206, 1); ctx.restore();
         xrd(x0 + 40, 174, 206, 34, T.seg(p2, 0.05, 0.3), ink(M.xrd.c), {lw: 1.3});
         P.arrow(ctx, x0 + 143, 226, x0 + 143, 256, T.ease(T.seg(p2, 0.3, 0.42)), col, 3.5);
         label("closest known structures", x0 + 30, 280, {size: 13, weight: 700, color: th.muted, alpha: T.seg(p2, 0.38, 0.5)});
         [["SrTiO₃", STO, 0.94], ["BaTiO₃", BTO, 0.72], ["SrO", SRO, 0.31]].forEach(function (r, k) {
           var y = 318 + k * 48, b = T.seg(p2, 0.42 + k * 0.08, 0.56 + k * 0.08);
           if (b <= 0) return;
           P.crystal(ctx, cam(x0 + 50, y - 4, r[1] === SRO ? 10.5 : 12, -0.5 + 0.7 * t + k, -0.35), r[1], {dark: th.dark, glass: 0.8, alpha: b, atomScale: r[1] === SRO ? 0.72 : 1});
           label(r[0], x0 + 76, y + 2, {size: 17, weight: 800, alpha: b});
           card(x0 + 154, y - 9, 104, 10, {r: 5, fill: th.line, stroke: null, alpha: b});
           card(x0 + 154, y - 9, Math.max(10, 104 * r[2] * T.ease(T.seg(p2, 0.5 + k * 0.08, 0.7 + k * 0.08))), 10, {r: 5, fill: k ? tint(col, 0.45) : col, stroke: null, alpha: b});
           if (!k) P.check(ctx, x0 + 268, y - 22, true, T.seg(p2, 0.82, 0.92), th);
         });
         label("similarity in the shared space", x0 + 143, 448, {size: 12.5, color: th.faint, align: "center", alpha: T.seg(p2, 0.7, 0.85)});
       }
       // generation: target properties in, a new structure out
       x0 = 644; var p3 = T.seg(t, 0.66, 0.94);
       if (p3 > 0) {
         chip(x0 + 143, 176, "target: band gap 2 eV", M.properties.c, false, {w: 214, h: 38, size: 16, alpha: T.seg(p3, 0, 0.12)});
         P.arrow(ctx, x0 + 143, 200, x0 + 143, 226, T.ease(T.seg(p3, 0.1, 0.22)), col, 3.5);
         var cc = cam(x0 + 143, 266, 30, 0.6 * t, -0.3), ca = T.seg(p3, 0.15, 0.3);
         SPACE_CLOUD.map(function (q) { return [cc.proj(q), q]; }).sort(function (u, v) { return u[0][2] - v[0][2]; })
           .forEach(function (q) { dot(cc, q[1], 0.045, th.dark ? "#94a3b8" : "#94a3b8", ca * (0.3 + 0.3 * (q[0][2] + 1) / 2)); });
         var sq = cc.proj([0.25, 0.1, 0.3]);
         if (ca > 0) star(sq[0], sq[1], 9 + 2 * Math.sin(t * 40), INDIGO, T.seg(p3, 0.25, 0.35));
         label("a point in the", x0 + 186, 262, {size: 12.5, weight: 700, color: th.muted, alpha: T.seg(p3, 0.28, 0.4)});
         label("learned space", x0 + 186, 278, {size: 12.5, weight: 700, color: th.muted, alpha: T.seg(p3, 0.28, 0.4)});
         P.arrow(ctx, x0 + 143, 304, x0 + 143, 330, T.ease(T.seg(p3, 0.35, 0.45)), col, 3.5);
         var asm = T.ease(T.seg(p3, 0.42, 0.75));
         P.crystal(ctx, cam(x0 + 143, 384, 30, -0.4 + 0.9 * t), ABX, {explode: 1 - asm, glass: T.seg(p3, 0.7, 0.85), edges: T.seg(p3, 0.7, 0.85),
                                                            dark: th.dark, alpha: T.seg(p3, 0.4, 0.5), colors: {A: "#f59e0b", B: "#4f46e5", X: "#e87ba4"}});
         label("a new candidate structure", x0 + 143, 450, {size: 14, weight: 700, color: th.muted, align: "center", alpha: T.seg(p3, 0.8, 0.95)});
       }
     }},

    {block: "evaluation", ms: 8500,
     cap: "Shared benchmarks compare models on the same data and metrics. A trustworthy model also generalises to unseen materials and reports its uncertainty, and its best candidates are checked independently by calculation or experiment.",
     draw: function (t) {
       var col = COL.evaluation;
       var cards = [[40, 46, "Shared benchmarks", "the same data split and metrics for every model", 0.03], [488, 46, "Unseen materials", "test on families left out of training", 0.27],
                    [40, 280, "Uncertainty", "how sure is each prediction?", 0.5], [488, 280, "Independent validation", "evidence from outside the model", 0.72]];
       cards.forEach(function (cd) {
         var a = T.out(T.seg(t, cd[4], cd[4] + 0.08)), on = t >= cd[4] && t < cd[4] + 0.24;
         if (a <= 0) return;
         card(cd[0], cd[1], 432, 214, {alpha: a, stroke: on ? col : th.line, sw: on ? 2.4 : 1.5});
         label(cd[2], cd[0] + 22, cd[1] + 36, {size: 20, weight: 800, color: ink(col), alpha: a});
         label(cd[3], cd[0] + 22, cd[1] + 58, {size: 14, color: th.muted, alpha: a});
       });
       // a leaderboard
       var p = T.seg(t, 0.06, 0.28), x = 40, y = 46;
       if (p > 0) {
         label("error (MAE, eV) · lower is better", x + 410, y + 84, {size: 12, color: th.faint, align: "right", alpha: T.seg(p, 0, 0.2)});
         [["model A", 0.21], ["model B", 0.27], ["model C", 0.35], ["baseline", 0.62]].forEach(function (r, k) {
           var yy = y + 108 + k * 26, b = T.seg(p, 0.1 + k * 0.12, 0.3 + k * 0.12), L = 230 * r[1] / 0.65 * T.ease(b);
           label(r[0], x + 22, yy + 5, {size: 15, weight: k === 3 ? 600 : 700, color: k === 3 ? th.muted : th.ink, alpha: b});
           card(x + 112, yy - 7, Math.max(8, L), 14, {r: 7, fill: k === 3 ? th.line : tint(col, 0.85 - k * 0.18), stroke: null, alpha: b});
           label(r[1].toFixed(2), x + 120 + L, yy + 5, {size: 13, weight: 500, family: P.MONO, color: th.muted, alpha: b});
         });
       }
       // generalisation: a parity plot, seen-like test materials and an unseen family
       p = T.seg(t, 0.3, 0.52); x = 488; y = 46;
       if (p > 0) {
         var bx = x + 28, by = y + 76, bw = 160, bh = 122, X = function (v) { return bx + v / 4 * bw; }, Y = function (v) { return by + bh - v / 4 * bh; };
         ctx.save(); ctx.globalAlpha *= T.seg(p, 0, 0.15);
         ctx.strokeStyle = th.line; ctx.lineWidth = 1.5; ctx.strokeRect(bx, by, bw, bh);
         ctx.setLineDash([4, 4]); ctx.strokeStyle = th.faint; ctx.beginPath(); ctx.moveTo(X(0), Y(0)); ctx.lineTo(X(4), Y(4)); ctx.stroke(); ctx.restore();
         label("true", bx + bw / 2, by + bh + 16, {size: 12, color: th.faint, align: "center", alpha: T.seg(p, 0, 0.15)});
         ctx.save(); ctx.translate(bx - 8, by + bh / 2); ctx.rotate(-Math.PI / 2); label("predicted", 0, 0, {size: 12, color: th.faint, align: "center", alpha: T.seg(p, 0, 0.15)}); ctx.restore();
         ctx.save(); ctx.beginPath(); ctx.rect(bx, by, bw, bh); ctx.clip();
         PARITY.seen.forEach(function (d, k) { dotFlat(X(d[0]), Y(d[1]), 3.6, th.dark ? "#94a3b8" : "#64748b", T.seg(p, 0.1 + k * 0.015, 0.2 + k * 0.015)); });
         PARITY.unseen.forEach(function (d, k) { ringFlat(X(d[0]), Y(d[1]), 4.5, ink(col), T.seg(p, 0.45 + k * 0.04, 0.55 + k * 0.04)); });
         ctx.restore();
         dotFlat(x + 222, y + 108, 4, th.dark ? "#94a3b8" : "#64748b", T.seg(p, 0.2, 0.35)); label("like the training data", x + 234, y + 113, {size: 14, color: th.muted, alpha: T.seg(p, 0.2, 0.35)});
         ringFlat(x + 222, y + 136, 4.5, ink(col), T.seg(p, 0.5, 0.65)); label("an unseen family", x + 234, y + 141, {size: 14, color: th.muted, alpha: T.seg(p, 0.5, 0.65)});
         label("errors grow away", x + 222, y + 176, {size: 14, weight: 700, color: ink(col), alpha: T.seg(p, 0.75, 0.9)});
         label("from the training data", x + 222, y + 194, {size: 14, weight: 700, color: ink(col), alpha: T.seg(p, 0.75, 0.9)});
       }
       // uncertainty: two predictions, a narrow and a wide distribution
       p = T.seg(t, 0.53, 0.74); x = 40; y = 280;
       if (p > 0) {
         var ax0 = x + 28, ax1 = x + 404, base = y + 178, V = function (v) { return ax0 + v / 4 * (ax1 - ax0); };
         ctx.save(); ctx.globalAlpha *= T.seg(p, 0, 0.15); ctx.fillStyle = th.line; ctx.fillRect(ax0, base, ax1 - ax0, 1.5);
         [0, 1, 2, 3, 4].forEach(function (v) { ctx.fillRect(V(v) - 0.5, base, 1, 5); label(String(v), V(v), base + 19, {size: 12, color: th.faint, align: "center"}); });
         ctx.restore();
         label("predicted band gap (eV)", ax1, base - 8, {size: 12, color: th.faint, align: "right", alpha: T.seg(p, 0, 0.15)});
         var g1 = T.ease(T.seg(p, 0.1, 0.45)), g2 = T.ease(T.seg(p, 0.35, 0.7)), blue = ink(COL.alignment);
         gauss(0, 4, base, 88 * g1, 1.95, 0.12, V, blue, 1, tint(COL.alignment, 0.14));
         gauss(0, 4, base, 30 * g2, 2.5, 0.55, V, ink(col), 1, tint(col, 0.14));
         label("confident", V(1.95) - 14, base - 76, {size: 14, weight: 800, color: blue, align: "right", alpha: T.seg(p, 0.35, 0.5)});
         label("2.0 ± 0.1 eV", V(1.95) - 14, base - 58, {size: 13, weight: 600, color: blue, align: "right", alpha: T.seg(p, 0.35, 0.5)});
         label("uncertain", V(2.5) + 58, base - 52, {size: 14, weight: 800, color: ink(col), alpha: T.seg(p, 0.65, 0.8)});
         label("2.5 ± 0.6 eV", V(2.5) + 58, base - 34, {size: 13, weight: 600, color: ink(col), alpha: T.seg(p, 0.65, 0.8)});
       }
       // independent validation: a ladder of evidence, from the model's own prediction up to a measurement
       p = T.seg(t, 0.75, 0.97); x = 488; y = 280;
       if (p > 0) {
         P.arrow(ctx, x + 34, y + 198, x + 34, y + 82, T.ease(T.seg(p, 0, 0.9)), tint(col, 0.75), 2.5);
         ctx.save(); ctx.translate(x + 22, y + 140); ctx.rotate(-Math.PI / 2);
         label("stronger evidence", 0, 0, {size: 12, weight: 700, color: th.faint, align: "center", alpha: T.seg(p, 0.1, 0.3)}); ctx.restore();
         [["model", "predicts"], ["ML potential", "relaxes the structure"], ["DFT", "computes the property"], ["experiment", "makes and measures it"]].forEach(function (st, k) {
           var b = T.seg(p, k * 0.2, k * 0.2 + 0.18), yy = y + 186 - k * 31;
           if (b <= 0) return;
           card(x + 52, yy - 12, 356, 25, {r: 8, alpha: b, fill: th.dark ? tint(col, 0.07 + k * 0.05) : P.css(P.mix(P.rgbOf(col), [255, 255, 255], 0.93 - k * 0.06)), stroke: tint(col, 0.75), sw: 1.3});
           label(st[0], x + 66, yy + 5, {size: 14, weight: 800, alpha: b});
           label(st[1], x + 176, yy + 5, {size: 13, color: th.muted, alpha: b});
           P.check(ctx, x + 390, yy, true, T.seg(p, k * 0.2 + 0.1, k * 0.2 + 0.2), th);
         });
       }
     }},

    {block: "meidnet", ms: 10000,
     cap: "MEIDNet encodes crystal structures and numerical properties, such as band gap and formation enthalpy, into one shared space read by a property head and a structure decoder. Its inverse design searches that space from target properties to candidate structures.",
     draw: function (t) {
       var pc = M.properties.c, sc = M.structure.c, design = T.seg(t, 0.5, 0.56), dim = 1 - 0.6 * design;
       label("MEIDNet, one reference implementation", 40, 46, {size: 20, weight: 800, color: ink(INDIGO), alpha: T.seg(t, 0, 0.08)});
       label("two modalities: crystal structures and numerical properties", 40, 70, {size: 15, color: th.muted, alpha: T.seg(t, 0.02, 0.1)});
       var a1 = T.seg(t, 0.04, 0.14), a2 = T.out(T.seg(t, 0.1, 0.2));
       // inputs
       ctx.save(); ctx.globalAlpha *= dim;
       P.crystal(ctx, cam(96, 164, 27, -0.6 + 0.8 * t), STO, {dark: th.dark, alpha: a1});
       label("structure", 96, 222, {size: 14, weight: 700, color: th.muted, align: "center", alpha: a1});
       ctx.restore();
       var propA = a1 * (1 - design), tgtA = design;
       card(38, 300, 116, 58, {r: 12, alpha: propA, stroke: tint(pc, 0.9), sw: 2});
       label("band gap", 96, 324, {size: 13.5, weight: 700, align: "center", alpha: propA});
       label("formation enthalpy", 96, 344, {size: 11.5, weight: 700, color: th.muted, align: "center", alpha: propA});
       label("properties", 96, 380, {size: 14, weight: 700, color: th.muted, align: "center", alpha: propA});
       card(38, 300, 116, 58, {r: 12, alpha: tgtA, fill: th.dark ? tint(pc, 0.16) : "rgba(253,237,243,.95)", stroke: pc, sw: 2.5});
       label("target", 96, 322, {size: 12.5, weight: 700, color: th.muted, align: "center", alpha: tgtA});
       label("band gap 2 eV", 96, 345, {size: 15, weight: 800, color: ink(pc), align: "center", alpha: tgtA});
       label("target properties", 96, 380, {size: 14, weight: 700, color: ink(pc), align: "center", alpha: tgtA});
       // the two encoders
       [[134, "structure encoder", "graph network (EGNN)", sc, dim], [300, "property encoder", "dense network (MLP)", pc, 1]].forEach(function (e, k) {
         ctx.save(); ctx.globalAlpha *= e[4];
         card(184, e[0], 168, 60, {alpha: a2, fill: th.dark ? tint(e[3], 0.13) : P.css(P.mix(P.rgbOf(e[3]), [255, 255, 255], 0.9)), stroke: e[3], sw: k && design ? 3 : 2.2});
         label(e[1], 268, e[0] + 27, {size: 15, weight: 800, color: ink(e[3]), align: "center", alpha: a2});
         label(e[2], 268, e[0] + 47, {size: 12, weight: 500, family: P.MONO, color: th.muted, align: "center", alpha: a2});
         ctx.restore();
       });
       var ar = T.ease(T.seg(t, 0.12, 0.2));
       ctx.save(); ctx.globalAlpha *= dim; P.arrow(ctx, 136, 164, 178, 164, ar, tint(sc, 0.9), 3); P.arrow(ctx, 356, 164, 412, 206, T.ease(T.seg(t, 0.18, 0.26)), tint(sc, 0.9), 3); ctx.restore();
       P.arrow(ctx, 156, 330, 178, 330, ar, tint(pc, 0.9), 3); P.arrow(ctx, 356, 330, 412, 292, T.ease(T.seg(t, 0.18, 0.26)), tint(pc, 0.9), 3);
       // the shared space, with the pairs pulled together
       var c = cam(512, 250, 70, -0.6 + 0.45 * t, -0.3), half = 1.05, show = T.seg(t, 0.18, 0.28), pull = T.ease(T.seg(t, 0.26, 0.46));
       label("one shared space", 512, 112, {size: 16, weight: 800, color: th.muted, align: "center", alpha: show});
       ctx.save(); ctx.globalAlpha *= show; box3(c, half, frameColor());
       ctx.globalAlpha *= 1 - 0.75 * design;
       PAIRS.forEach(function (pr) {
         var s = 0.5 * (1 - pull), A = [pr.m[0] + pr.d[0] * s, pr.m[1] + pr.d[1] * s, pr.m[2] + pr.d[2] * s], B = [pr.m[0] - pr.d[0] * s, pr.m[1] - pr.d[1] * s, pr.m[2] - pr.d[2] * s];
         P.line3(ctx, c, A, B, th.dark ? "rgba(203,213,225,.55)" : "rgba(100,116,139,.6)", 1.3, [4, 4]);
         var qa = c.proj(A), qb = c.proj(B);
         mark("structure", qa[0], qa[1], 0.07 * qa[3]); mark("properties", qb[0], qb[1], 0.075 * qb[3]);
       });
       ctx.restore();
       // the property head and the structure decoder
       var a3 = T.out(T.seg(t, 0.38, 0.48));
       ctx.save(); ctx.globalAlpha *= dim;
       P.arrow(ctx, 616, 206, 668, 166, T.ease(T.seg(t, 0.38, 0.46)), tint(pc, 0.9), 3);
       card(674, 134, 168, 60, {alpha: a3, fill: th.dark ? tint(pc, 0.13) : P.css(P.mix(P.rgbOf(pc), [255, 255, 255], 0.9)), stroke: pc, sw: 2.2});
       label("property head", 758, 161, {size: 15, weight: 800, color: ink(pc), align: "center", alpha: a3});
       label("→ band gap, enthalpy", 758, 181, {size: 12, weight: 500, family: P.MONO, color: th.muted, align: "center", alpha: a3});
       ctx.restore();
       var hot = T.seg(t, 0.78, 0.84) * (1 - T.seg(t, 0.94, 1));
       P.arrow(ctx, 616, 292, 668, 330, T.ease(T.seg(t, 0.38, 0.46)), tint(sc, 0.9), 3);
       card(674, 300, 168, 60, {alpha: a3, fill: th.dark ? tint(sc, 0.13 + 0.1 * hot) : P.css(P.mix(P.rgbOf(sc), [255, 255, 255], 0.9 - 0.08 * hot)), stroke: sc, sw: 2.2 + hot});
       label("structure decoder", 758, 327, {size: 15, weight: 800, color: ink(sc), align: "center", alpha: a3});
       label("→ a crystal", 758, 347, {size: 12, weight: 500, family: P.MONO, color: th.muted, align: "center", alpha: a3});
       // inverse design: the target enters through the property encoder and the search moves through the space
       var tg = [0.05, -0.25, 0.3], tq = c.proj(tg), go = T.ease(T.seg(t, 0.56, 0.62)), u = T.seg(t, 0.6, 0.8), WIN = [0, 2, 3];
       var off = function (v) { return [tg[0] + v[0], tg[1] + v[1], tg[2] + v[2]]; };
       if (u > 0) for (var k = 0; k < 5; k++) {        // a population of points moves from the target until the decoded properties match
         var win = WIN.indexOf(k) >= 0, fade = win ? 0 : T.seg(t, 0.82, 0.88);
         if (fade >= 1) continue;
         ctx.save(); ctx.globalAlpha *= 1 - fade; ctx.strokeStyle = tint(INDIGO, 0.5); ctx.lineWidth = 2.2; ctx.lineCap = "round"; ctx.beginPath();
         for (var q = 10; q >= 0; q--) { var pp = c.proj(off(walk(k, Math.max(0, u - q * 0.035), 0.7))); q === 10 ? ctx.moveTo(pp[0], pp[1]) : ctx.lineTo(pp[0], pp[1]); }
         ctx.stroke();
         P.sphere(ctx, c, off(walk(k, u, 0.7)), 0.075, win && t > 0.8 ? "#10b981" : INDIGO, {dark: th.dark});
         ctx.restore();
       }
       if (go > 0) {
         star(T.lerp(356, tq[0], go), T.lerp(330, tq[1], go), 13, pc);
         var la = T.seg(t, 0.62, 0.68);
         card(tq[0] - 42, tq[1] + 17, 84, 22, {r: 11, alpha: la, fill: th.dark ? "rgba(27,31,36,.92)" : "rgba(255,255,255,.94)", stroke: tint(pc, 0.6), sw: 1});
         label("the target", tq[0], tq[1] + 33, {size: 13, weight: 800, color: ink(pc), align: "center", alpha: la});
       }
       // the candidates: decoded, checked by the rules
       label("Inverse design", 40, 440, {size: 18, weight: 800, color: ink(INDIGO), alpha: T.seg(t, 0.5, 0.58)});
       label("target → search → decode → rules", 40, 464, {size: 14, color: th.muted, alpha: T.seg(t, 0.52, 0.6)});
       WIN.forEach(function (k, j) {
         var f = T.ease(T.seg(t, 0.82 + j * 0.03, 0.9 + j * 0.03));
         if (f <= 0) return;
         var X = T.lerp(842, 600 + j * 80, f), Y = T.lerp(330, 446, f) - 40 * Math.sin(Math.PI * f);
         P.crystal(ctx, cam(X, Y, 17, -0.6 + 1.6 * t + j, -0.35), ABX, {dark: th.dark, glass: 0.8, alpha: T.seg(f, 0, 0.3)});
         P.check(ctx, X + 20, Y - 20, true, T.seg(t, 0.92 + j * 0.02, 0.96 + j * 0.02), th);
       });
       label("candidates", 836, 444, {size: 17, weight: 800, color: ink(INDIGO), alpha: T.seg(t, 0.9, 0.97)});
       label("pass the rules", 836, 464, {size: 13.5, color: th.muted, alpha: T.seg(t, 0.9, 0.97)});
       label("MEIDNet places compositions on a chosen prototype, such as cubic ABX₃.", 480, 516, {size: 13, color: th.faint, align: "center", alpha: T.seg(t, 0.92, 1)});
     }},

    {block: "explore", ms: 6000,
     cap: "Keep going in Prism with <a href=\"/docs/learn/index.html\">Learn</a> and <a href=\"/docs/develop.html\">Develop</a>, or open <a href=\"" + MATTER + "\" target=\"_blank\" rel=\"noopener\">MEIDNet Matter</a> to explore your own data, train models and generate candidate structures.",
     draw: function (t) {
       P.crystal(ctx, cam(480, 236, 96, -0.6 + 0.9 * t, -0.35), STO, {dark: th.dark, alpha: th.dark ? 0.045 : 0.06, glass: 0.6});
       var a = T.out(T.seg(t, 0, 0.22));
       label("Keep exploring", 480, 116, {size: 50, weight: 800, align: "center", alpha: a});
       label("Learn the ideas and build models in Prism, or bring your own data to Matter.", 480, 156, {size: 19, color: th.muted, align: "center", alpha: T.seg(t, 0.1, 0.3)});
       [["PRISM", "Learn", "modalities, alignment,", "architectures, benchmarks", COL.modalities],
        ["PRISM", "Develop", "the package, the Studio,", "the API and your data", COL.encoders],
        ["MEIDNET MATTER", "Matter ↗", "explore data, train models,", "generate structures", COL.explore]].forEach(function (d, k) {
         var x = 72 + k * 284, b = T.out(T.seg(t, 0.18 + k * 0.08, 0.36 + k * 0.08));
         ctx.save(); ctx.translate(0, 24 * (1 - b));
         card(x, 196, 248, 132, {alpha: b, stroke: d[4], sw: 2.2});
         label(d[0], x + 22, 224, {size: 11.5, weight: 500, family: P.MONO, color: th.faint, alpha: b});
         label(d[1], x + 22, 256, {size: 26, weight: 800, color: ink(d[4]), alpha: b});
         label(d[2], x + 22, 284, {size: 14.5, color: th.muted, alpha: b});
         label(d[3], x + 22, 304, {size: 14.5, color: th.muted, alpha: b});
         ctx.restore();
       });
       var sweep = T.seg(t, 0.55, 0.95) * 8.4 - 1;      // one pass along the chapters, then rest
       BLOCKS.forEach(function (b, k) {
         var x = 165 + k * 105, on = Math.abs(sweep - k) < 0.6, al = T.seg(t, 0.4 + k * 0.03, 0.5 + k * 0.03);
         if (k < 6) { ctx.save(); ctx.globalAlpha *= T.seg(t, 0.42, 0.52); ctx.strokeStyle = th.faint; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(x + 20, 404); ctx.lineTo(x + 85, 404); ctx.stroke(); ctx.restore(); }
         ctx.save(); ctx.globalAlpha *= al; ctx.beginPath(); ctx.arc(x, 404, on ? 17 : 12, 0, 2 * Math.PI); ctx.fillStyle = b.c; ctx.shadowColor = b.c; ctx.shadowBlur = on ? 14 : 0; ctx.fill(); ctx.restore();
         label(b.name, x, 446, {size: 14, weight: 700, color: ink(b.c), align: "center", alpha: al});
       });
     }}
  ];

  /* ── one frame of one chapter, on any canvas: the 960 × 540 stage scaled to its width and centred ── */
  function render(c2d, i, t, W, H, dpr) {
    ctx = c2d; th = P.theme();
    var k = W / VW;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    ctx.setTransform(dpr * k, 0, 0, dpr * k, 0, (H - VH * k) / 2 * dpr);
    try { SCENES[i].draw(T.clamp(t)); } catch (e) { if (window.console) console.error(e); }
  }
  var plain = function (s) { return String(s).replace(/<[^>]*>/g, ""); };
  window.PrismIntroScenes = {
    blocks: BLOCKS, render: render, ratio: VW / VH,
    list: SCENES.map(function (s) { var b = BLOCKS.filter(function (x) { return x.id === s.block; })[0]; return {block: s.block, title: b.name, ms: s.ms, cap: plain(s.cap)}; }),
    index: function (block) { return SCENES.map(function (s) { return s.block; }).indexOf(block); }
  };

  /* ── the player of the landing page (after prism-tour.js) ── */
  var root = document.getElementById("tour3d");
  if (!root) return;
  var canvas = root.querySelector("canvas"), tctx = canvas.getContext("2d");
  var TOTAL = SCENES.reduce(function (a, s) { return a + s.ms; }, 0);
  var S = {ms: 0, playing: false, last: 0, raf: 0, i: -1, visible: false, started: false, W: 0, H: 0, dpr: 1};
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (sel) { return root.querySelector(sel); };
  var strip = $(".t3-strip"), cap = $(".t3-cap"), prog = $(".t3-prog"), playBtn = $("[data-t3=play]"), open = $(".t3-open"), time = $(".t3-time");
  prog.setAttribute("aria-valuemax", String(Math.round(TOTAL / 1000)));
  strip.innerHTML = BLOCKS.map(function (b) {
    return '<li><button type="button" data-block="' + b.id + '" style="--bc:' + b.c + '"><span>' + b.name + "</span><i></i></button></li>";
  }).join("");
  function at(ms) { var a = 0; for (var i = 0; i < SCENES.length; i++) { if (ms < a + SCENES[i].ms || i === SCENES.length - 1) return {i: i, t: T.clamp((ms - a) / SCENES[i].ms), start: a}; a += SCENES[i].ms; } }
  function startOf(i) { var a = 0; for (var k = 0; k < i; k++) a += SCENES[k].ms; return a; }
  function clock(ms) { var s = Math.round(ms / 1000); return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2); }
  function resize() {
    var r = canvas.getBoundingClientRect();
    S.dpr = Math.min(2, window.devicePixelRatio || 1); S.W = Math.max(1, r.width); S.H = Math.max(1, r.height);
    canvas.width = Math.round(S.W * S.dpr); canvas.height = Math.round(S.H * S.dpr);
    draw();
  }
  function draw() {
    if (!S.W) return;
    var w = at(S.ms), sc = SCENES[w.i];
    render(tctx, w.i, w.t, S.W, S.H, S.dpr);
    prog.firstElementChild.style.width = (100 * S.ms / TOTAL).toFixed(2) + "%";
    prog.setAttribute("aria-valuenow", String(Math.round(S.ms / 1000)));
    time.textContent = clock(S.ms) + " / " + clock(TOTAL);
    var bi = BLOCKS.map(function (b) { return b.id; }).indexOf(sc.block);
    strip.querySelectorAll("button").forEach(function (b, j) {
      b.classList.toggle("on", j === bi); b.classList.toggle("done", j < bi);
      b.querySelector("i").style.width = j === bi ? (100 * w.t).toFixed(1) + "%" : "0";
    });
    if (w.i !== S.i) {
      S.i = w.i;
      var blk = BLOCKS[bi];
      cap.innerHTML = '<b style="color:' + ink(blk.c) + '">' + blk.name + ".</b> " + sc.cap;
      root.style.setProperty("--t3c", blk.c);
      var ext = /^https?:/.test(blk.href);
      open.href = blk.href; open.textContent = blk.link;
      if (ext) { open.target = "_blank"; open.rel = "noopener"; } else { open.removeAttribute("target"); open.removeAttribute("rel"); }
    }
  }
  function loop(now) {
    S.raf = 0; if (!S.playing) return;
    var dt = S.last ? Math.min(120, now - S.last) : 0; S.last = now;
    if (S.visible && !document.hidden) {
      S.ms = Math.min(TOTAL, S.ms + dt); draw();
      if (S.ms >= TOTAL) { pause(); playBtn.textContent = "↺ Replay"; playBtn.setAttribute("aria-label", "Play the tour again"); return; }
    }
    S.raf = requestAnimationFrame(loop);
  }
  function play() {
    if (S.ms >= TOTAL - 1) S.ms = 0;
    S.playing = true; S.last = 0; S.started = true;
    playBtn.textContent = "❚❚ Pause"; playBtn.setAttribute("aria-label", "Pause the tour");
    if (!S.raf) S.raf = requestAnimationFrame(loop);
  }
  function pause() { S.playing = false; playBtn.textContent = "▶ Play"; playBtn.setAttribute("aria-label", "Play the tour"); }
  function go(i) {          // a chapter: from its start while playing, its finished picture while paused
    i = Math.max(0, Math.min(SCENES.length - 1, i));
    S.ms = startOf(i) + (S.playing ? 0 : SCENES[i].ms - 1); S.i = -1; draw();
  }
  playBtn.addEventListener("click", function () { S.playing ? pause() : play(); });
  $("[data-t3=prev]").addEventListener("click", function () { go(at(S.ms).i - 1); });
  $("[data-t3=next]").addEventListener("click", function () { go(at(S.ms).i + 1); });
  strip.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-block]"); if (!b) return;
    var i = SCENES.map(function (s) { return s.block; }).indexOf(b.getAttribute("data-block")); if (i >= 0) go(i);
  });
  function seek(e) { var r = prog.getBoundingClientRect(); S.ms = T.clamp((e.clientX - r.left) / r.width) * TOTAL; S.i = -1; draw(); }
  prog.addEventListener("click", seek);
  prog.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight") { S.ms = Math.min(TOTAL, S.ms + 5000); draw(); e.preventDefault(); }
    else if (e.key === "ArrowLeft") { S.ms = Math.max(0, S.ms - 5000); draw(); e.preventDefault(); }
  });
  root.addEventListener("keydown", function (e) {
    if (e.target.closest && e.target.closest(".t3-prog")) return;
    if (e.key === "k" || (e.key === " " && e.target === canvas)) { e.preventDefault(); S.playing ? pause() : play(); }
  });
  var th0 = document.getElementById("theme");
  if (th0) th0.addEventListener("click", function () { setTimeout(function () { S.i = -1; draw(); }, 0); });
  if (window.ResizeObserver) new ResizeObserver(resize).observe(canvas); else window.addEventListener("resize", resize);
  if (window.IntersectionObserver) new IntersectionObserver(function (es) {
    S.visible = es[0].isIntersecting;
    if (S.visible && !S.started && !reduce) { S.ms = 0; S.i = -1; play(); }   // starts the first time it is seen
  }, {threshold: 0.35}).observe(canvas);
  else { S.visible = true; if (!reduce) { S.ms = 0; play(); } }
  S.ms = SCENES[0].ms - 1;            // before it plays (or with reduced motion): the finished opening picture
  resize();
  window.prismTour = {play: play, pause: pause, go: go, seek: function (ms) { S.ms = T.clamp(ms, 0, TOTAL); S.i = -1; draw(); },
                      scenes: SCENES.map(function (s) { return {block: s.block, title: BLOCKS.filter(function (b) { return b.id === s.block; })[0].name, ms: s.ms}; })};
})();
