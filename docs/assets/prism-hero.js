/* MEIDNet Prism landing page: the lettering of the headline (a neural network, a crystal) and the 3D crystal scene of the hero.
   No libraries: the lettering is SVG built from stroke glyphs, the scene a small canvas renderer (painter's algorithm).
   The headline stays real text for search engines and screen readers; without JavaScript it shows as plain text. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";

  var P3 = window.Prism3D, isDark = P3.isDark;

  /* ═══════════ the lettering: one glyph skeleton, two renderings ═══════════
     "neural":  nodes at regular spacing along the strokes, thin connections, faint synapses inside each letter
     "crystal": faceted strokes (arcs become polygons), two alternating atom species, glass in closed rings, a lattice behind */
  var ASC = 1.42, DESC = 0.48, PAD = 0.24, GAP = 0.36, U = 0.76;   // x-height = 1 unit; U = unit in em

  function arc(cx, cy, rx, ry, a0, a1, every) {   // fine points for the curve; vertices every `every` degrees for the facets
    var n = Math.max(8, Math.ceil(Math.abs(a1 - a0) / 6)), pts = [], beads = [];
    for (var i = 0; i <= n; i++) {
      var a = (a0 + (a1 - a0) * i / n) * Math.PI / 180;
      pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
    }
    var k = Math.max(1, Math.round(n * every / Math.abs(a1 - a0)));
    for (var j = 0; j <= n; j += k) beads.push(pts[j]);
    if (beads[beads.length - 1] !== pts[n]) beads.push(pts[n]);
    return {pts: pts, beads: beads};
  }
  function line() { var p = Array.prototype.slice.call(arguments); return {pts: p, beads: p}; }
  function dot(x, y) { return {pts: [], beads: [[x, y]]}; }
  var ring = function () { return arc(0.5, 0.5, 0.5, 0.5, 0, 360, 60); };

  var G = {
    a: {w: 1.0, s: function () { return [ring(), line([1, 1], [1, 0])]; }},
    c: {w: 0.92, s: function () { return [arc(0.5, 0.5, 0.5, 0.5, 40, 320, 70)]; }},
    d: {w: 1.0, s: function () { return [ring(), line([1, ASC], [1, 0])]; }},
    e: {w: 1.0, s: function () { return [line([0.02, 0.5], [1, 0.5]), arc(0.5, 0.5, 0.5, 0.5, 0, 318, 80)]; }},
    i: {w: 0.2, s: function () { return [line([0.1, 0], [0.1, 1]), dot(0.1, 1.34)]; }},
    l: {w: 0.2, s: function () { return [line([0.1, 0], [0.1, 0.71], [0.1, ASC])]; }},
    m: {w: 1.3, s: function () {
      return [line([0, 0], [0, 1]), arc(0.325, 0.62, 0.325, 0.38, 180, 0, 60), line([0.65, 0.62], [0.65, 0]),
              arc(0.975, 0.62, 0.325, 0.38, 180, 0, 60), line([1.3, 0.62], [1.3, 0])]; }},
    o: {w: 1.0, s: function () { return [arc(0.5, 0.5, 0.5, 0.5, 90, 450, 60)]; }},
    r: {w: 0.68, s: function () { return [line([0, 0], [0, 1]), arc(0.42, 0.55, 0.42, 0.42, 180, 60, 60)]; }},
    s: {w: 0.82, s: function () { return [arc(0.41, 0.75, 0.36, 0.25, 20, 270, 85), arc(0.41, 0.25, 0.39, 0.25, 90, -160, 85)]; }},
    t: {w: 0.72, s: function () { return [line([0.28, 1.32], [0.28, 1], [0.28, 0]), line([0, 1], [0.66, 1])]; }},
    u: {w: 0.92, s: function () { return [line([0, 1], [0, 0.46]), arc(0.46, 0.46, 0.46, 0.46, 180, 360, 60), line([0.92, 1], [0.92, 0])]; }},
    v: {w: 0.92, s: function () { return [line([0, 1], [0.46, 0], [0.92, 1])]; }},
    y: {w: 0.92, s: function () { return [line([0, 1], [0.46, 0]), line([0.92, 1], [0.46, 0], [0.24, -0.48])]; }},
    A: {w: 1.16, s: function () { return [line([0, 0], [0.58, ASC], [1.16, 0]), line([0.25, 0.55], [0.91, 0.55])]; }},
    I: {w: 0.2, s: function () { return [line([0.1, 0], [0.1, 0.71], [0.1, ASC])]; }},
    " ": {w: 0.38, s: function () { return []; }}
  };

  function layout(text) {          // the word's strokes in word coordinates, with the glyph each belongs to
    var x = PAD, strokes = [];
    for (var c = 0; c < text.length; c++) {
      var g = G[text[c]];
      if (!g) return null;          // a glyph we do not draw: keep the plain text
      var sh = function (p) { return [p[0] + x, p[1]]; };
      g.s().forEach(function (st) { strokes.push({pts: st.pts.map(sh), beads: st.beads.map(sh), glyph: c}); });
      x += g.w + GAP;
    }
    return {strokes: strokes, W: x - GAP + PAD, H: ASC + DESC + 2 * PAD};
  }
  var near = function (p, q, e) { return Math.hypot(p[0] - q[0], p[1] - q[1]) < e; };
  var f3 = function (v) { return v.toFixed(3); };
  var Y = function (y) { return f3(ASC + PAD - y); };
  var XY = function (p) { return f3(p[0]) + " " + Y(p[1]); };

  function neural(L, id) {
    var nodes = [], edges = [], syn = [], SP = 0.32;
    function node(p, glyph) {
      for (var i = 0; i < nodes.length; i++) if (near(nodes[i].p, p, 0.12)) return i;
      nodes.push({p: p, glyph: glyph}); return nodes.length - 1;
    }
    L.strokes.forEach(function (st) {
      if (!st.pts.length) { node(st.beads[0], st.glyph); return; }
      var prev = node(st.pts[0], st.glyph), acc = 0;
      for (var i = 1; i < st.pts.length; i++) {
        var a = st.pts[i - 1], b = st.pts[i], seg = Math.hypot(b[0] - a[0], b[1] - a[1]), t = SP - acc;
        while (t <= seg - 1e-9) {
          var n = node([a[0] + (b[0] - a[0]) * t / seg, a[1] + (b[1] - a[1]) * t / seg], st.glyph);
          if (n !== prev) edges.push([prev, n]);
          prev = n; t += SP;
        }
        acc = (acc + seg) % SP;
      }
      var last = node(st.pts[st.pts.length - 1], st.glyph);
      if (last !== prev) edges.push([prev, last]);
    });
    var linked = function (i, j) { return edges.some(function (e) { return (e[0] === i && e[1] === j) || (e[0] === j && e[1] === i); }); };
    nodes.forEach(function (n, i) {             // synapses: each node to its nearest unlinked neighbour in the same letter
      nodes.map(function (m, j) { return {j: j, d: Math.hypot(m.p[0] - n.p[0], m.p[1] - n.p[1])}; })
        .filter(function (o) { return o.j > i && nodes[o.j].glyph === n.glyph && o.d > 0.36 && o.d < 0.8 && !linked(i, o.j); })
        .sort(function (u, v) { return u.d - v.d; }).slice(0, 1)
        .forEach(function (o) { syn.push([i, o.j]); });
    });
    var far = [];                              // between neighbouring letters: the closest pair, like links between layers
    nodes.forEach(function (n, i) { nodes.forEach(function (m, j) {
      if (m.glyph === n.glyph + 1) {
        var d = Math.hypot(m.p[0] - n.p[0], m.p[1] - n.p[1]);
        if (d < 0.9 && (!far[n.glyph] || d < far[n.glyph].d)) far[n.glyph] = {i: i, j: j, d: d};
      }
    }); });
    far.forEach(function (f) { if (f) syn.push([f.i, f.j]); });
    var seg = function (e) { return "M" + XY(nodes[e[0]].p) + "L" + XY(nodes[e[1]].p); };
    return '<path d="' + syn.map(seg).join("") + '" fill="none" stroke="url(#' + id + 'g)" stroke-opacity=".55" stroke-width=".026"/>' +
      '<path d="' + edges.map(seg).join("") + '" fill="none" stroke="url(#' + id + 'g)" stroke-width=".05" stroke-linecap="round"/>' +
      nodes.map(function (n, i) {
        var c = 'cx="' + f3(n.p[0]) + '" cy="' + Y(n.p[1]) + '"', r = 0.088 + 0.03 * ((i * 7919) % 5) / 4;   // varied, like neurons
        return '<circle ' + c + ' r="' + f3(r * 1.9) + '" fill="url(#' + id + 'g)" opacity=".13"/>' +
               '<circle ' + c + ' r="' + f3(r) + '" fill="url(#' + id + 'g)"/>' +
               '<circle ' + c + ' r="' + f3(r * 0.42) + '" fill="#fff" opacity=".92"/>';
      }).join("");
  }

  function crystal(L, id) {
    var atoms = [], bonds = [], glass = [], lat = [];
    function atom(p, big) {        // an atom keeps the species it got first: alternating along its stroke
      for (var i = 0; i < atoms.length; i++) if (near(atoms[i].p, p, 0.07)) return atoms[i];
      var a = {p: p, big: big}; atoms.push(a); return a;
    }
    L.strokes.forEach(function (st) {
      var v = st.beads.filter(function (p, i, all) { return i === 0 || !near(p, all[i - 1], 0.02); });
      v.forEach(function (p, i) { atom(p, i % 2 === 0); });
      if (v.length > 1) bonds.push(v);
      if (v.length > 3 && near(v[0], v[v.length - 1], 0.03)) glass.push(v);    // a closed ring: a facet
    });
    for (var gx = 0.25; gx < L.W; gx += 0.5) for (var gy = -DESC + 0.1; gy < ASC + 0.1; gy += 0.5) lat.push([gx, gy]);
    var path = function (v) { return "M" + v.map(XY).join("L"); };
    var d = bonds.map(path).join("");
    return '<g class="mol-lat">' + lat.map(function (p) { return '<circle cx="' + f3(p[0]) + '" cy="' + Y(p[1]) + '" r=".022"/>'; }).join("") + "</g>" +
      glass.map(function (v) { return '<path d="' + path(v) + 'Z" fill="url(#' + id + 'g)" fill-opacity=".16" stroke="#fff" stroke-opacity=".55" stroke-width=".02"/>'; }).join("") +
      '<path class="mol-shadow" d="' + d + '" transform="translate(.05 .07)"/>' +
      '<path d="' + d + '" fill="none" stroke="url(#' + id + 'g)" stroke-width=".13" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="' + d + '" fill="none" stroke="#fff" stroke-opacity=".4" stroke-width=".035" stroke-linecap="round" stroke-linejoin="round" transform="translate(-.02 -.03)"/>' +
      atoms.map(function (a) {
        var c = 'cx="' + f3(a.p[0]) + '" cy="' + Y(a.p[1]) + '"', r = a.big ? 0.17 : 0.11;
        return '<circle ' + c + ' r="' + r + '" fill="url(#' + id + 'g)"/>' +
               (a.big ? "" : '<circle ' + c + ' r="' + r + '" fill="#fff" opacity=".5"/>') +
               '<circle ' + c + ' r="' + r + '" fill="url(#' + id + 's)"/>';
      }).join("");
  }

  var lettering = 0;
  function letteringSvg(text, stops, style) {
    var L = layout(text);
    if (!L) return null;
    var id = "mol" + (++lettering);
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 " + f3(L.W) + " " + f3(L.H));
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    svg.style.width = f3(L.W * U) + "em";
    svg.style.verticalAlign = f3(-(DESC + PAD) * U) + "em";
    svg.innerHTML =
      '<defs><linearGradient id="' + id + 'g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="' + f3(L.W) + '" y2="0">' +
      stops.map(function (s) { return '<stop offset="' + s[0] + '" stop-color="' + s[1] + '"/>'; }).join("") + "</linearGradient>" +
      '<radialGradient id="' + id + 's" cx=".36" cy=".32" r=".68"><stop offset="0" stop-color="#fff" stop-opacity=".95"/>' +
      '<stop offset=".38" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>' +
      (style === "crystal" ? crystal(L, id) : neural(L, id));
    return svg;
  }

  var STYLES = {
    a: {style: "neural", stops: [[0, "#2f6fe4"], [0.45, "#6366f1"], [0.8, "#8b5cf6"], [1, "#a855f7"]]},
    b: {style: "crystal", stops: [[0, "#2563eb"], [0.3, "#0e7490"], [0.55, "#0d9488"], [1, "#10b981"]]}
  };
  document.querySelectorAll("[data-mol]").forEach(function (span) {
    var st = STYLES[span.getAttribute("data-mol")] || STYLES.a;
    var svg = letteringSvg(span.textContent.trim(), st.stops, st.style);
    if (!svg) return;
    span.classList.add("mol-on");
    span.insertBefore(svg, span.firstChild);
  });

  /* ═══════════ the 3D scene: one material, many views ═══════════
     A crystal turns slowly and changes, every few seconds, between three families (a cubic perovskite, rock salt and a
     layered crystal). Around it, one description of the material at a time appears: its crystal graph and its numerical
     properties (what MEIDNet learns from today, solid panels), a diffraction pattern, a microscope image and a text
     (concepts beyond MEIDNet today, dashed panels). Each lights up its point in the shared representation, where the
     views of one material meet. A panel turning edge-on fades out, and the floor grid fades from the middle, so that no
     sliver or stray line shows at any angle. */
  var canvas = document.getElementById("hero3d");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var caption = canvas.parentNode && canvas.parentNode.querySelector && canvas.parentNode.querySelector("figcaption");

  // ---- three crystal families, in crystal()'s format (half edge 1; edges and faces join atom positions)
  function octaFaces() {               // the octahedron of the six face centres around the cell's centre
    var xs = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
    return [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 4, 2], [1, 3, 4], [1, 5, 3], [1, 2, 5]].map(function (f) { return [xs[f[0]], xs[f[1]], xs[f[2]]]; });
  }
  function cubeEdges() {
    var c = [], e = [];
    [-1, 1].forEach(function (x) { [-1, 1].forEach(function (y) { [-1, 1].forEach(function (z) { c.push([x, y, z]); }); }); });
    c.forEach(function (a, i) { c.forEach(function (b, j) { if (j > i && Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]) === 2) e.push([a, b]); }); });
    return e;
  }
  function rocksalt() {                // NaCl type: anions on the corners and face centres, cations on the edge centres and the centre
    var atoms = [];
    for (var x = -1; x <= 1; x++) for (var y = -1; y <= 1; y++) for (var z = -1; z <= 1; z++) {
      var anion = (Math.abs(x) + Math.abs(y) + Math.abs(z)) % 2 === 1;
      atoms.push({p: [x, y, z], site: anion ? "A" : "X", el: anion ? "X" : "A"});
    }
    return {atoms: atoms, edges: cubeEdges(), faces: octaFaces()};
  }
  function layered() {                 // two slabs (a square net of cations, anions above and below in alternate hollows), a gap between
    var atoms = [], edges = [], faces = [];
    [-0.62, 0.62].forEach(function (y0) {
      for (var x = -1; x <= 1; x++) for (var z = -1; z <= 1; z++) atoms.push({p: [x, y0, z], site: "X", el: "M"});
      [[-0.5, -0.5, 1], [0.5, 0.5, 1], [-0.5, 0.5, -1], [0.5, -0.5, -1]].forEach(function (q) {
        var p = [q[0], +(y0 + 0.32 * q[2]).toFixed(3), q[1]];
        atoms.push({p: p, site: "A", el: "X"});
        [[-0.5, -0.5], [0.5, -0.5], [-0.5, 0.5], [0.5, 0.5]].forEach(function (d) { edges.push([p, [q[0] + d[0], y0, q[1] + d[1]]]); });
      });
      faces.push([[-1, y0, -1], [1, y0, -1], [1, y0, 1]], [[-1, y0, -1], [1, y0, 1], [-1, y0, 1]]);
    });
    return {atoms: atoms, edges: edges, faces: faces};
  }
  var FAMILIES = [
    {cell: P3.perovskite({A: "A", B: "B", X: "X"}), name: "cubic perovskite ABX₃"},
    {cell: rocksalt(), name: "rock salt AB", colors: {A: "#10b981", X: "#3b82f6"}, atomScale: 0.48, size: 1.12},
    {cell: layered(), name: "layered crystal", colors: {A: "#f59e0b", X: "#8b5cf6"}, atomScale: 0.5, size: 1.15},
  ];

  // ---- the views of a material, shown one at a time; the first two are what MEIDNet learns from today
  var MODALITIES = [
    {key: "graph", label: "crystal graph", concept: false, mark: "circle", color: "#3b82f6"},
    {key: "props", label: "numerical properties", concept: false, mark: "ring", color: "#e87ba4"},
    {key: "xrd", label: "diffraction · concept", concept: true, mark: "diamond", color: "#f59e0b"},
    {key: "img", label: "microscopy · concept", concept: true, mark: "square", color: "#14b8a6"},
    {key: "text", label: "text · concept", concept: true, mark: "triangle", color: "#8b5cf6"},
  ];
  var SLOTS = [{c: [-2.65, 1.5, -2.3], h: [0.95, 0.68], ry: 0.5}, {c: [2.25, -1.2, -1.6], h: [0.9, 0.62], ry: -0.62}];
  var REPR = {c: [1.45, 2.0, -2.9], h: [1.15, 0.75], ry: -0.32, label: "shared representation"};
  var FAMILY_S = 8, MOD_S = 3.4;          // seconds per crystal family, per view

  var r = P3.T.rng(7), CLOUD = [];        // the shared representation: other materials (faint) and this one's five views
  for (var i = 0; i < 60; i++) { var tt = r() * 2 - 1; CLOUD.push({u: 0.85 * tt, v: 0.5 * Math.sin(2.1 * tt) * 0.8 + 0.3 * (r() * 2 - 1)}); }
  var HOME = [0.18, 0.12], VIEWS = [[-0.12, 0.36], [0.46, 0.34], [0.5, -0.12], [0.06, -0.24], [-0.22, 0.04]];
  var GRAPH = {n: [[-0.62, -0.35], [-0.22, 0.42], [0.18, -0.12], [0.6, 0.38], [0.52, -0.5], [-0.05, -0.62], [-0.68, 0.38]],
               e: [[0, 1], [1, 2], [2, 3], [2, 4], [0, 5], [5, 2], [1, 6], [6, 0], [3, 4]]};
  var PEAKS = [[[0.12, 0.35], [0.3, 1], [0.42, 0.3], [0.52, 0.55], [0.66, 0.4], [0.8, 0.25]],    // a diffraction pattern per family
               [[0.22, 0.45], [0.33, 1], [0.6, 0.62], [0.74, 0.2], [0.86, 0.3]],
               [[0.08, 1], [0.24, 0.25], [0.36, 0.5], [0.55, 0.3], [0.7, 0.45], [0.88, 0.2]]];

  var W = 0, H = 0, DPR = 1, yaw = 0, pitch = 0, dragYaw = 0, dragPitch = 0, t0 = performance.now(), cam = null, tnow = 0, frozen = null;
  function resize() {
    var b = canvas.getBoundingClientRect();
    DPR = Math.min(2, window.devicePixelRatio || 1);
    W = Math.max(1, b.width); H = Math.max(1, b.height);
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    draw();
  }
  function proj(p) { return cam.proj(p); }
  function panelPoint(P, u, v, w) {        // panel-local (u, v in [-1, 1]) to world
    var c = Math.cos(P.ry), sn = Math.sin(P.ry), x = u * P.h[0], y = v * P.h[1];
    return [P.c[0] + x * c + (w || 0) * sn, P.c[1] + y, P.c[2] - x * sn + (w || 0) * c];
  }
  function poly(pts) { ctx.beginPath(); pts.forEach(function (p, j) { j ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); }); ctx.closePath(); }
  function font(px, w) { ctx.font = (w || 500) + " " + Math.round(px) + "px 'IBM Plex Mono', ui-monospace, monospace"; }
  function marker(kind, x, y, s, color) {
    ctx.beginPath();
    if (kind === "circle") ctx.arc(x, y, s, 0, 2 * Math.PI);
    else if (kind === "ring") { ctx.arc(x, y, s, 0, 2 * Math.PI); ctx.lineWidth = Math.max(1.2, s * 0.45); ctx.strokeStyle = color; ctx.stroke(); return; }
    else if (kind === "diamond") { ctx.moveTo(x, y - s * 1.2); ctx.lineTo(x + s * 1.2, y); ctx.lineTo(x, y + s * 1.2); ctx.lineTo(x - s * 1.2, y); ctx.closePath(); }
    else if (kind === "square") ctx.rect(x - s, y - s, 2 * s, 2 * s);
    else { ctx.moveTo(x, y - s * 1.2); ctx.lineTo(x + s * 1.1, y + s * 0.8); ctx.lineTo(x - s * 1.1, y + s * 0.8); ctx.closePath(); }
    ctx.fillStyle = color; ctx.fill();
  }

  // one panel: a glass card in the scene; o.concept draws it dashed; fades as it turns edge-on
  function drawPanel(P, dark, alpha, o, paint) {
    var corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(function (c) { return proj(panelPoint(P, c[0], c[1])); });
    var area = 0;
    for (var k = 0; k < 4; k++) { var p0 = corners[k], p1 = corners[(k + 1) % 4]; area += p0[0] * p1[1] - p1[0] * p0[1]; }
    var sc = proj(P.c)[3], face = Math.abs(area) / 2 / (4 * P.h[0] * P.h[1] * sc * sc), fade = P3.T.clamp((face - 0.2) / 0.3);
    alpha *= fade * fade * (3 - 2 * fade);
    if (alpha < 0.02) return;
    ctx.save(); ctx.globalAlpha *= alpha;
    poly(corners);
    var g = ctx.createLinearGradient(corners[3][0], corners[3][1], corners[1][0], corners[1][1]);
    g.addColorStop(0, dark ? "rgba(51,65,85,.55)" : "rgba(255,255,255,.82)");
    g.addColorStop(1, dark ? "rgba(30,41,59,.3)" : "rgba(226,232,255,.46)");
    ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = o.concept ? 1.3 : 1; if (o.concept) ctx.setLineDash([5, 4]);
    ctx.strokeStyle = o.stroke || (dark ? "rgba(148,163,184,.5)" : "rgba(148,163,184,.6)"); ctx.stroke(); ctx.setLineDash([]);
    paint(function (u, v) { return proj(panelPoint(P, u, v)); }, corners);
    var tl = corners[3];
    font(Math.max(10, Math.min(12.5, W / 46)));
    ctx.fillStyle = dark ? "rgba(203,213,225,.88)" : "rgba(71,85,105,.92)";
    ctx.fillText(o.label, Math.max(4, Math.min(tl[0] + 2, W - ctx.measureText(o.label).width - 4)), tl[1] - 7);   // inside the canvas
    ctx.restore();
  }

  function paintModality(m, L, dark, fam) {
    var line = dark ? "rgba(148,163,184,.75)" : "rgba(100,116,139,.6)", soft = dark ? "rgba(203,213,225,.32)" : "rgba(100,116,139,.3)";
    if (m.key === "graph") {
      ctx.lineWidth = 1.4; ctx.strokeStyle = line;
      GRAPH.e.forEach(function (e) { var a = L(GRAPH.n[e[0]][0] * 0.8, GRAPH.n[e[0]][1] * 0.8), b = L(GRAPH.n[e[1]][0] * 0.8, GRAPH.n[e[1]][1] * 0.8);
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); });
      GRAPH.n.forEach(function (n, j) { var q = L(n[0] * 0.8, n[1] * 0.8);
        ctx.beginPath(); ctx.arc(q[0], q[1], Math.max(2.5, 0.07 * q[3]), 0, 2 * Math.PI); ctx.fillStyle = ["#3b82f6", "#14b8a6", "#8b5cf6"][j % 3]; ctx.fill(); });
    } else if (m.key === "props") {              // several numerical properties as bars, no particular values
      [["#e87ba4", 0.72], ["#8b5cf6", 0.45], ["#3b82f6", 0.86], ["#14b8a6", 0.32]].forEach(function (b, j) {
        var v = 0.55 - j * 0.36, a = L(-0.78, v + 0.1), c = L(-0.78 + 1.56 * b[1], v + 0.1), d = L(-0.78 + 1.56 * b[1], v - 0.1), e = L(-0.78, v - 0.1);
        poly([a, c, d, e]); ctx.fillStyle = b[0]; ctx.globalAlpha *= 0.85; ctx.fill(); ctx.globalAlpha /= 0.85;
        var f = L(-0.78, v - 0.1), g2 = L(0.78, v - 0.1); ctx.strokeStyle = soft; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(f[0], f[1]); ctx.lineTo(g2[0], g2[1]); ctx.stroke();
      });
    } else if (m.key === "xrd") {                // peaks against 2θ
      var o0 = L(-0.85, -0.72), x1 = L(0.85, -0.72);
      ctx.strokeStyle = line; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(o0[0], o0[1]); ctx.lineTo(x1[0], x1[1]); ctx.stroke();
      ctx.strokeStyle = "#f59e0b"; ctx.lineWidth = 1.6;
      PEAKS[fam].forEach(function (p) { var u = -0.85 + 1.7 * p[0], a = L(u, -0.72), b = L(u, -0.72 + 1.4 * p[1]); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); });
      var lab = L(0.62, -0.95); font(Math.max(9, Math.min(11, W / 56))); ctx.fillStyle = soft.replace(/,\.3\d?\)/, ",.9)"); ctx.fillText("2θ", lab[0], lab[1]);
    } else if (m.key === "img") {                // a lattice image: bright columns on a dark field
      var q0 = L(-0.82, 0.78), q1 = L(0.82, 0.78), q2 = L(0.82, -0.78), q3 = L(-0.82, -0.78);
      poly([q0, q1, q2, q3]); ctx.fillStyle = dark ? "rgba(2,6,23,.85)" : "rgba(15,23,42,.88)"; ctx.fill();
      for (var a = -0.62; a <= 0.63; a += 0.31) for (var b = -0.6; b <= 0.61; b += 0.3) {
        var p = L(a, b), rad = Math.max(1.2, 0.035 * p[3]);
        var gr = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], rad * 2.2);
        gr.addColorStop(0, "rgba(255,255,255,.95)"); gr.addColorStop(0.45, "rgba(203,213,225,.55)"); gr.addColorStop(1, "rgba(203,213,225,0)");
        ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(p[0], p[1], rad * 2.2, 0, 2 * Math.PI); ctx.fill();
      }
    } else {                                     // a text: a few lines of words
      ctx.strokeStyle = dark ? "rgba(203,213,225,.55)" : "rgba(71,85,105,.5)"; ctx.lineCap = "round";
      [[0.55, 0.9], [0.22, 0.75], [-0.11, 0.86], [-0.44, 0.52]].forEach(function (l, j) {
        var x = -0.82, words = j === 1 ? [0.3, 0.5, 0.25] : [0.4, 0.22, 0.48];
        words.forEach(function (w) { if (x + w > -0.82 + 1.64 * l[1]) return; var a = L(x, l[0]), b = L(x + w, l[0]); ctx.lineWidth = Math.max(2, 0.05 * a[3]); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); x += w + 0.1; });
      });
      ctx.lineCap = "butt";
    }
  }

  function paintRepr(L, dark, lit) {
    CLOUD.forEach(function (p) { var q = L(p.u, p.v); ctx.beginPath(); ctx.arc(q[0], q[1], Math.max(1.2, 0.022 * q[3]), 0, 2 * Math.PI); ctx.fillStyle = dark ? "rgba(148,163,184,.35)" : "rgba(100,116,139,.3)"; ctx.fill(); });
    var home = L(HOME[0], HOME[1]);
    MODALITIES.forEach(function (m, j) {
      var a = lit[j]; if (a <= 0.01) return;
      var p = L(HOME[0] + VIEWS[j][0] * 0.55, HOME[1] + VIEWS[j][1] * 0.55), s = Math.max(2.2, 0.045 * p[3]);
      ctx.save(); ctx.globalAlpha *= a;
      ctx.strokeStyle = m.color; ctx.lineWidth = 1; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(home[0], home[1]); ctx.lineTo(p[0], p[1]); ctx.stroke(); ctx.setLineDash([]);
      if (m.concept) ctx.globalAlpha *= 0.85;
      marker(m.mark, p[0], p[1], s, m.color);
      ctx.restore();
    });
    var on = lit.reduce(function (a, b) { return a + b; }, 0) / lit.length;
    if (on > 0.01) { var g = ctx.createRadialGradient(home[0], home[1], 0, home[0], home[1], 14); g.addColorStop(0, "rgba(255,255,255," + (0.85 * on) + ")"); g.addColorStop(1, "rgba(255,255,255,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(home[0], home[1], 14, 0, 2 * Math.PI); ctx.fill(); }
  }

  // what is on screen at time t (seconds): the family and its transition, the view in each slot, the lit views
  function state(t) {
    if (reduce) return {fam: 0, famA: 1, explode: 0, shown: [{m: 0, slot: 0, a: 1}, {m: 2, slot: 1, a: 1}], lit: [1, 1, 1, 1, 1]};
    t = Math.max(0, t);
    var cycle = Math.floor(t / FAMILY_S), ft = t - cycle * FAMILY_S, fam = cycle % FAMILIES.length;
    var out = P3.T.seg(ft, FAMILY_S - 0.6, FAMILY_S), inn = P3.T.seg(ft, 0, 0.8);
    var famA = Math.min(1 - out, cycle === 0 ? 1 : inn), explode = Math.max(0.5 * out, cycle === 0 ? 0 : 0.5 * (1 - P3.T.ease(inn)));
    var k = Math.floor(t / MOD_S), mt = t - k * MOD_S, shown = [];
    [k - 1, k].forEach(function (kk) {
      if (kk < 0) return;
      var local = t - kk * MOD_S, a = P3.T.seg(local, 0, 0.55) * (1 - P3.T.seg(local, MOD_S + 0.05, MOD_S + 0.6));
      if (a > 0.01) shown.push({m: kk % MODALITIES.length, slot: kk % 2, a: a});
    });
    var lit = MODALITIES.map(function (m, j) {         // a view lights up when it appears and stays lit through the round
      var round = Math.floor(k / MODALITIES.length), first = round * MODALITIES.length + j;
      if (first > k) return 0;
      var since = t - first * MOD_S;
      return P3.T.seg(since, 0.2, 0.8) * (1 - P3.T.seg(t - (round + 1) * MODALITIES.length * MOD_S, -0.7, 0));
    });
    return {fam: fam, famA: famA, explode: explode, shown: shown, lit: lit, mt: mt};
  }

  var lastFam = -1;
  function draw() {
    if (!W) return;
    var dark = isDark(), S = state(tnow);
    cam = P3.camera({cx: W * 0.52, cy: H * 0.5, scale: Math.min(W, H * 1.1) / 8.3, yaw: yaw, pitch: pitch});
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    // floor grid, fading with the distance from the middle
    ctx.lineWidth = 1;
    var gcol = dark ? "148,163,184" : "100,116,139", g0 = dark ? 0.18 : 0.2;
    for (var g = -3; g <= 3; g += 0.75) for (var n = 0; n < 12; n++) {
      var s0 = -3 + n * 0.5, s1 = s0 + 0.5, sm = s0 + 0.25;
      [[g, s0, g, s1, Math.hypot(g, sm)], [s0, g, s1, g, Math.hypot(sm, g)]].forEach(function (e) {
        var al = g0 * (1 - P3.T.clamp((e[4] - 1.6) / 1.4)); if (al < 0.004) return;
        var a = proj([e[0], -2.05, e[1]]), b = proj([e[2], -2.05, e[3]]);
        ctx.strokeStyle = "rgba(" + gcol + "," + al.toFixed(3) + ")"; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      });
    }
    // the shadow of the crystal on the floor
    var f = proj([0, -2.05, 0]), sh = ctx.createRadialGradient(f[0], f[1], 0, f[0], f[1], 2.0 * f[3]);
    sh.addColorStop(0, dark ? "rgba(0,0,0,.35)" : "rgba(30,41,90,.07)"); sh.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = sh; ctx.beginPath(); ctx.ellipse(f[0], f[1], 2.0 * f[3], 0.62 * f[3], 0, 0, 2 * Math.PI); ctx.fill();
    // panels, far first: the shared representation, and the views on screen
    var items = [{P: REPR, z: proj(REPR.c)[2], repr: true}];
    S.shown.forEach(function (sv) { var P = SLOTS[sv.slot]; items.push({P: P, z: proj(P.c)[2], sv: sv}); });
    items.sort(function (p, q) { return p.z - q.z; }).forEach(function (it) {
      if (it.repr) drawPanel(it.P, dark, 1, {label: REPR.label}, function (L) { paintRepr(L, dark, S.lit); });
      else { var m = MODALITIES[it.sv.m]; drawPanel(it.P, dark, it.sv.a, {label: m.label, concept: m.concept, stroke: m.concept ? m.color : null}, function (L) { paintModality(m, L, dark, S.fam); }); }
    });
    var F = FAMILIES[S.fam];
    P3.crystal(ctx, cam, F.cell, {s: F.size || 1.25, atomScale: F.atomScale || 0.6, dark: dark, colors: F.colors, alpha: S.famA, explode: S.explode, seed: 5});
    if (caption && S.fam !== lastFam) { caption.textContent = F.name + " · dashed panels are concepts · drag to rotate"; lastFam = S.fam; }
  }

  var running = false, visible = true;
  function frame(now) {
    tnow = frozen === null ? Math.max(0, (now - t0) / 1000) : frozen;   // a frame can be stamped just before t0
    yaw = -0.5 + 0.38 * Math.sin(tnow * 0.21) + dragYaw;
    pitch = -0.33 + 0.05 * Math.sin(tnow * 0.16) + dragPitch;
    draw();
    if (running) requestAnimationFrame(frame);
  }
  function start() { if (reduce || running || !visible || document.hidden) return; running = true; requestAnimationFrame(frame); }
  function stop() { running = false; }
  if (reduce) { yaw = -0.5; pitch = -0.33; }

  var drag = null;
  canvas.addEventListener("pointerdown", function (e) { drag = {x: e.clientX, y: e.clientY, yaw: dragYaw, pitch: dragPitch}; canvas.setPointerCapture(e.pointerId); canvas.classList.add("grabbing"); });
  canvas.addEventListener("pointermove", function (e) {
    if (!drag) return;
    dragYaw = drag.yaw + (e.clientX - drag.x) * 0.008;
    dragPitch = Math.max(-0.5, Math.min(0.45, drag.pitch + (e.clientY - drag.y) * 0.005));
    if (reduce) { yaw = -0.5 + dragYaw; pitch = -0.33 + dragPitch; draw(); }
  });
  function endDrag() { drag = null; canvas.classList.remove("grabbing"); }
  canvas.addEventListener("pointerup", endDrag); canvas.addEventListener("pointercancel", endDrag);

  if (window.ResizeObserver) new ResizeObserver(resize).observe(canvas); else window.addEventListener("resize", resize);
  if (window.IntersectionObserver) new IntersectionObserver(function (es) { visible = es[0].isIntersecting; visible ? start() : stop(); }).observe(canvas);
  document.addEventListener("visibilitychange", function () { document.hidden ? stop() : start(); });
  var th = document.getElementById("theme");
  if (th) th.addEventListener("click", function () { setTimeout(draw, 0); });
  window.prismHero = {seek: function (s) { frozen = s; tnow = s; draw(); }, play: function () { frozen = null; }};   // seek: hold the scene at a time (screenshots)
  resize();
  start();
})();
