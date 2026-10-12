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

  /* ═══════════ the 3D scene: many views of one material, one shared representation ═══════════
     A sphere stands for the shared representation (MEIDNet maps every view of a material onto a unit sphere). Six views
     of a material circle it on an orbit: its crystal structure (turning, and changing every few seconds between a cubic
     perovskite, rock salt and a layered crystal), its crystal graph and its numerical properties (what MEIDNet learns from
     today, solid) and, as concepts beyond MEIDNet today (dashed), a diffraction pattern, a microscope image and a text.
     Each view is encoded along a beam into the sphere and lands where the beam enters; contrastive alignment then draws
     the views of one material to a single point, and the next material begins. The views always face the viewer, so
     none turns edge-on. */
  var canvas = document.getElementById("hero3d");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var caption = canvas.parentNode && canvas.parentNode.querySelector && canvas.parentNode.querySelector("figcaption");
  var CAPTION = "views of one material meet in one shared representation · dashed: concepts · drag to rotate";

  // ---- three crystal families for the structure view, in crystal()'s format (half edge 1)
  function octaFaces() {
    var xs = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
    return [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 4, 2], [1, 3, 4], [1, 5, 3], [1, 2, 5]].map(function (f) { return [xs[f[0]], xs[f[1]], xs[f[2]]]; });
  }
  function cubeEdges() {
    var c = [], e = [];
    [-1, 1].forEach(function (x) { [-1, 1].forEach(function (y) { [-1, 1].forEach(function (z) { c.push([x, y, z]); }); }); });
    c.forEach(function (a, i) { c.forEach(function (b, j) { if (j > i && Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]) === 2) e.push([a, b]); }); });
    return e;
  }
  function rocksalt() {
    var atoms = [];
    for (var x = -1; x <= 1; x++) for (var y = -1; y <= 1; y++) for (var z = -1; z <= 1; z++) {
      var anion = (Math.abs(x) + Math.abs(y) + Math.abs(z)) % 2 === 1;
      atoms.push({p: [x, y, z], site: anion ? "A" : "X", el: anion ? "X" : "A"});
    }
    return {atoms: atoms, edges: cubeEdges(), faces: octaFaces()};
  }
  function layered() {
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
    {cell: P3.perovskite({A: "A", B: "B", X: "X"}), atomScale: 0.62, size: 1},
    {cell: rocksalt(), colors: {A: "#10b981", X: "#3b82f6"}, atomScale: 0.5, size: 0.9},
    {cell: layered(), colors: {A: "#f59e0b", X: "#8b5cf6"}, atomScale: 0.52, size: 0.92},
  ];

  // ---- the six views around the sphere, ordered by hue like light leaving a prism; solid: what MEIDNet learns from today
  var VIEWS = [
    {key: "crystal", label: "crystal structure", concept: false, color: "#6366f1", mark: "hex"},
    {key: "graph", label: "crystal graph", concept: false, color: "#3b82f6", mark: "circle"},
    {key: "img", label: "microscopy · concept", concept: true, color: "#14b8a6", mark: "square"},
    {key: "text", label: "text · concept", concept: true, color: "#22c55e", mark: "triangle"},
    {key: "xrd", label: "diffraction · concept", concept: true, color: "#f59e0b", mark: "diamond"},
    {key: "props", label: "properties", concept: false, color: "#e87ba4", mark: "ring"},
  ];
  var RS = 1.0, RO = 2.62, TILT = 0.5, CARD = [0.62, 0.42];   // sphere radius; radius and tilt of the orbit (a wheel facing the viewer); half-size of a view
  var FAMILY_S = 8, ALIGN_S = 5.6, ORBIT_W = 0.06;            // seconds per crystal family and per material; orbit (rad/s)
  function onOrbit(a) { return [RO * Math.cos(a), RO * Math.sin(a) * Math.cos(TILT), RO * Math.sin(a) * Math.sin(TILT)]; }

  function norm(v) { var l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }
  function mul(v, s) { return [v[0] * s, v[1] * s, v[2] * s]; }
  function slerp(a, b, t) {                  // along the sphere between two unit vectors
    var d = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2])), th = Math.acos(d);
    if (th < 1e-4) return b.slice();
    var s = Math.sin(th), wa = Math.sin((1 - t) * th) / s, wb = Math.sin(t * th) / s;
    return [a[0] * wa + b[0] * wb, a[1] * wa + b[1] * wb, a[2] * wa + b[2] * wb];
  }
  var rr = P3.T.rng(11), CLOUD = [];         // other materials in the shared representation
  for (var i = 0; i < 130; i++) { var cz = rr() * 2 - 1, ph = rr() * 2 * Math.PI, rxy = Math.sqrt(1 - cz * cz); CLOUD.push([rxy * Math.cos(ph), cz, rxy * Math.sin(ph)]); }
  var CIRCLES = [function (a) { return [Math.cos(a), 0, Math.sin(a)]; },                       // an equator and two meridians
                 function (a) { return [0, Math.cos(a), Math.sin(a)]; },
                 function (a) { return [Math.cos(a) * 0.7071, Math.sin(a), Math.cos(a) * 0.7071]; }];
  function homeOf(n) { var r = P3.T.rng(101 + 7 * n); return norm([0.55 * (r() - 0.5), 0.1 + 0.45 * (r() - 0.5), 0.9]); }
  var GRAPH = {n: [[-0.62, -0.35], [-0.22, 0.42], [0.18, -0.12], [0.6, 0.38], [0.52, -0.5], [-0.05, -0.62], [-0.68, 0.38]],
               e: [[0, 1], [1, 2], [2, 3], [2, 4], [0, 5], [5, 2], [1, 6], [6, 0], [3, 4]]};
  var PEAKS = [[0.12, 0.35], [0.3, 1], [0.42, 0.3], [0.52, 0.55], [0.66, 0.4], [0.8, 0.25]];

  var W = 0, H = 0, DPR = 1, yaw = 0, pitch = 0, dragYaw = 0, dragPitch = 0, t0 = performance.now(), cam = null, tnow = 0, frozen = null;
  function resize() {
    var b = canvas.getBoundingClientRect();
    DPR = Math.min(2, window.devicePixelRatio || 1);
    W = Math.max(1, b.width); H = Math.max(1, b.height);
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    draw();
  }
  function proj(p) { return cam.proj(p); }
  function poly(pts) { ctx.beginPath(); pts.forEach(function (p, j) { j ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); }); ctx.closePath(); }
  function font(px, w) { ctx.font = (w || 500) + " " + Math.round(px) + "px 'IBM Plex Mono', ui-monospace, monospace"; }
  function marker(kind, x, y, s, color) {
    ctx.beginPath();
    if (kind === "circle") ctx.arc(x, y, s, 0, 2 * Math.PI);
    else if (kind === "ring") { ctx.arc(x, y, s, 0, 2 * Math.PI); ctx.lineWidth = Math.max(1.4, s * 0.5); ctx.strokeStyle = color; ctx.stroke(); return; }
    else if (kind === "diamond") { ctx.moveTo(x, y - s * 1.25); ctx.lineTo(x + s * 1.25, y); ctx.lineTo(x, y + s * 1.25); ctx.lineTo(x - s * 1.25, y); ctx.closePath(); }
    else if (kind === "square") ctx.rect(x - s, y - s, 2 * s, 2 * s);
    else if (kind === "hex") { for (var j = 0; j < 6; j++) { var a = Math.PI / 6 + j * Math.PI / 3; j ? ctx.lineTo(x + s * 1.15 * Math.cos(a), y + s * 1.15 * Math.sin(a)) : ctx.moveTo(x + s * 1.15 * Math.cos(a), y + s * 1.15 * Math.sin(a)); } ctx.closePath(); }
    else { ctx.moveTo(x, y - s * 1.25); ctx.lineTo(x + s * 1.15, y + s * 0.85); ctx.lineTo(x - s * 1.15, y + s * 0.85); ctx.closePath(); }
    ctx.fillStyle = color; ctx.fill();
  }

  // the content of a view, drawn in its card: L(u, v) maps card coordinates (-1..1) to the screen, k = pixels per unit
  function paintView(v, L, k, dark) {
    var line = dark ? "rgba(148,163,184,.75)" : "rgba(100,116,139,.6)";
    if (v.key === "graph") {
      ctx.lineWidth = 1.3; ctx.strokeStyle = line;
      GRAPH.e.forEach(function (e) { var a = L(GRAPH.n[e[0]][0] * 0.8, GRAPH.n[e[0]][1] * 0.8), b = L(GRAPH.n[e[1]][0] * 0.8, GRAPH.n[e[1]][1] * 0.8);
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); });
      GRAPH.n.forEach(function (n, j) { var q = L(n[0] * 0.8, n[1] * 0.8);
        ctx.beginPath(); ctx.arc(q[0], q[1], Math.max(2.2, 0.065 * k), 0, 2 * Math.PI); ctx.fillStyle = ["#3b82f6", "#14b8a6", "#8b5cf6"][j % 3]; ctx.fill(); });
    } else if (v.key === "props") {           // several numerical properties as bars, no particular values
      [["#e87ba4", 0.72], ["#8b5cf6", 0.45], ["#3b82f6", 0.86], ["#14b8a6", 0.32]].forEach(function (b, j) {
        var y = 0.55 - j * 0.36, a = L(-0.78, y + 0.1), c = L(-0.78 + 1.56 * b[1], y - 0.1);
        ctx.fillStyle = b[0]; ctx.globalAlpha *= 0.85; ctx.fillRect(a[0], a[1], c[0] - a[0], c[1] - a[1]); ctx.globalAlpha /= 0.85;
      });
    } else if (v.key === "xrd") {             // peaks against 2θ
      var o0 = L(-0.85, -0.7), x1 = L(0.85, -0.7);
      ctx.strokeStyle = line; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(o0[0], o0[1]); ctx.lineTo(x1[0], x1[1]); ctx.stroke();
      ctx.strokeStyle = v.color; ctx.lineWidth = 1.6;
      PEAKS.forEach(function (p) { var u = -0.85 + 1.7 * p[0], a = L(u, -0.7), b = L(u, -0.7 + 1.35 * p[1]); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); });
    } else if (v.key === "img") {             // a lattice image: bright columns on a dark field
      var q0 = L(-0.84, 0.8), q2 = L(0.84, -0.8);
      ctx.fillStyle = dark ? "rgba(2,6,23,.85)" : "rgba(15,23,42,.88)"; ctx.fillRect(q0[0], q0[1], q2[0] - q0[0], q2[1] - q0[1]);
      for (var a = -0.62; a <= 0.63; a += 0.31) for (var b = -0.6; b <= 0.61; b += 0.3) {
        var p = L(a, b), rad = Math.max(1.1, 0.034 * k), gr = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], rad * 2.2);
        gr.addColorStop(0, "rgba(255,255,255,.95)"); gr.addColorStop(0.45, "rgba(203,213,225,.55)"); gr.addColorStop(1, "rgba(203,213,225,0)");
        ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(p[0], p[1], rad * 2.2, 0, 2 * Math.PI); ctx.fill();
      }
    } else if (v.key === "text") {            // a few lines of words
      ctx.strokeStyle = dark ? "rgba(203,213,225,.55)" : "rgba(71,85,105,.5)"; ctx.lineCap = "round";
      [[0.55, 0.9], [0.2, 0.75], [-0.15, 0.86], [-0.5, 0.52]].forEach(function (l, j) {
        var x = -0.82, words = j === 1 ? [0.3, 0.5, 0.25] : [0.4, 0.22, 0.48];
        words.forEach(function (w) { if (x + w > -0.82 + 1.64 * l[1]) return; var a = L(x, l[0]), b = L(x + w, l[0]); ctx.lineWidth = Math.max(2, 0.05 * k); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); x += w + 0.1; });
      });
      ctx.lineCap = "butt";
    }
  }

  // what is on screen at time t: the orbit, the crystal family and its change, and where the current material is in its
  // alignment (appear, converge on one point, pulse, fade before the next material)
  function state(t) {
    t = Math.max(0, t);
    var cycle = Math.floor(t / FAMILY_S), ft = t - cycle * FAMILY_S, fam = cycle % FAMILIES.length;
    var out = P3.T.seg(ft, FAMILY_S - 0.6, FAMILY_S), inn = P3.T.seg(ft, 0, 0.8);
    var famA = Math.min(1 - out, cycle === 0 ? 1 : inn), explode = Math.max(0.5 * out, cycle === 0 ? 0 : 0.5 * (1 - P3.T.ease(inn)));
    var n = Math.floor(t / ALIGN_S), at = t - n * ALIGN_S;
    var S = {orbit: 0.35 + ORBIT_W * t, fam: fam, famA: famA, explode: explode, n: n,
             appear: P3.T.seg(at, 0, 0.6), conv: P3.T.ease(P3.T.seg(at, 0.9, 3.3)), pulse: P3.T.seg(at, 3.2, 4.6), gone: P3.T.seg(at, ALIGN_S - 0.6, ALIGN_S)};
    if (reduce) { S.orbit = 0.35; S.fam = 0; S.famA = 1; S.explode = 0; S.n = 0; S.appear = 1; S.conv = 1; S.pulse = 0.5; S.gone = 0; }
    return S;
  }

  function draw() {
    if (!W) return;
    var dark = isDark(), S = state(tnow);
    var stacked = window.matchMedia && window.matchMedia("(max-width: 900px)").matches;   // on phones the scene sits below the headline
    cam = P3.camera({cx: W * (stacked ? 0.5 : 0.6), cy: H * 0.5, scale: Math.min(W, H * 1.1) / (stacked ? 8.4 : 9.2), yaw: yaw, pitch: pitch});
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    var C = proj([0, 0, 0]), zc = C[2], Rpx = RS * C[3], HD = homeOf(S.n), vis = S.appear * (1 - S.gone);

    // the light the views pour into the sphere
    var halo = ctx.createRadialGradient(C[0], C[1], Rpx * 0.3, C[0], C[1], Rpx * 3.2);
    halo.addColorStop(0, dark ? "rgba(129,140,248,.24)" : "rgba(129,140,248,.2)"); halo.addColorStop(1, "rgba(129,140,248,0)");
    ctx.fillStyle = halo; ctx.fillRect(0, 0, W, H);

    var sats = VIEWS.map(function (v, k) {
      var p = onOrbit(S.orbit + k * Math.PI / 3), e = norm(p);
      return {v: v, k: k, p: p, q: proj(p), entry: proj(mul(e, RS)), d: slerp(e, HD, S.conv)};
    });
    sats.forEach(function (s) { s.m = proj(mul(s.d, RS)); s.mFront = s.m[2] >= zc; });
    var zs = sats.map(function (s) { return s.q[2]; }), zmin = Math.min.apply(null, zs), zmax = Math.max.apply(null, zs);
    var depth = function (s) { return 0.5 + 0.5 * P3.T.clamp((s.q[2] - zmin) / Math.max(1e-6, zmax - zmin)); };

    function orbitRing(front) {
      var n = 96;
      for (var j = 0; j < n; j++) {
        var p0 = proj(onOrbit(j * 2 * Math.PI / n)), p1 = proj(onOrbit((j + 1) * 2 * Math.PI / n));
        if ((p0[2] + p1[2]) / 2 >= zc !== front) continue;
        ctx.strokeStyle = dark ? "rgba(148,163,184," + (front ? 0.32 : 0.12) + ")" : "rgba(100,116,139," + (front ? 0.3 : 0.12) + ")";
        ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(p0[0], p0[1]); ctx.lineTo(p1[0], p1[1]); ctx.stroke();
      }
    }
    function sphereLayer(front) {
      var c = dark ? "203,213,225" : "71,85,105";
      CIRCLES.forEach(function (f) {
        var n = 72;
        for (var j = 0; j < n; j++) {
          var p0 = proj(mul(f(j * 2 * Math.PI / n), RS)), p1 = proj(mul(f((j + 1) * 2 * Math.PI / n), RS));
          if ((p0[2] + p1[2]) / 2 >= zc !== front) continue;
          ctx.strokeStyle = "rgba(" + c + "," + (front ? 0.2 : 0.07) + ")"; ctx.lineWidth = 0.9;
          ctx.beginPath(); ctx.moveTo(p0[0], p0[1]); ctx.lineTo(p1[0], p1[1]); ctx.stroke();
        }
      });
      CLOUD.forEach(function (u) {
        var q = proj(mul(u, RS)); if (q[2] >= zc !== front) return;
        ctx.fillStyle = "rgba(" + c + "," + (front ? 0.42 : 0.13) + ")"; ctx.beginPath(); ctx.arc(q[0], q[1], front ? 1.6 : 1.2, 0, 2 * Math.PI); ctx.fill();
      });
      if (vis < 0.01) return;
      var hq = proj(mul(HD, RS));
      sats.forEach(function (s) {                      // the landed views, drawn towards the point where they meet
        if (s.mFront !== front) return;
        ctx.save(); ctx.globalAlpha *= vis * (front ? 1 : 0.35);
        if (S.conv < 0.98) { ctx.strokeStyle = s.v.color; ctx.globalAlpha *= 0.55; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
          ctx.beginPath(); ctx.moveTo(s.m[0], s.m[1]); ctx.lineTo(hq[0], hq[1]); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha /= 0.55; }
        marker(s.v.mark, s.m[0], s.m[1], Math.max(2.6, 0.06 * s.m[3]), s.v.color);
        ctx.restore();
      });
      if (front && hq[2] >= zc && S.pulse > 0) {       // the views of one material meet: a pulse of white light
        var pr = (6 + 26 * S.pulse) * (Rpx / 60), g = ctx.createRadialGradient(hq[0], hq[1], 0, hq[0], hq[1], pr);
        g.addColorStop(0, "rgba(255,255,255," + (0.9 * (1 - S.pulse) * vis) + ")"); g.addColorStop(1, "rgba(255,255,255,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(hq[0], hq[1], pr, 0, 2 * Math.PI); ctx.fill();
      }
    }
    function body() {
      var g = ctx.createRadialGradient(C[0] - Rpx * 0.35, C[1] - Rpx * 0.4, Rpx * 0.08, C[0], C[1], Rpx);
      if (dark) { g.addColorStop(0, "rgba(199,210,254,.26)"); g.addColorStop(0.6, "rgba(99,102,241,.1)"); g.addColorStop(1, "rgba(79,70,229,.24)"); }
      else { g.addColorStop(0, "rgba(255,255,255,.8)"); g.addColorStop(0.6, "rgba(224,231,255,.38)"); g.addColorStop(1, "rgba(165,180,252,.34)"); }
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(C[0], C[1], Rpx, 0, 2 * Math.PI); ctx.fill();
      ctx.lineWidth = 1.2; ctx.strokeStyle = dark ? "rgba(165,180,252,.45)" : "rgba(129,140,248,.55)"; ctx.stroke();
      var sp = ctx.createRadialGradient(C[0] - Rpx * 0.42, C[1] - Rpx * 0.48, 0, C[0] - Rpx * 0.42, C[1] - Rpx * 0.48, Rpx * 0.34);
      sp.addColorStop(0, "rgba(255,255,255," + (dark ? 0.32 : 0.7) + ")"); sp.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = sp; ctx.beginPath(); ctx.arc(C[0] - Rpx * 0.42, C[1] - Rpx * 0.48, Rpx * 0.34, 0, 2 * Math.PI); ctx.fill();
    }
    function beam(s, alpha) {                          // the encoder: the view's light flowing into the sphere
      var a = s.q, b = s.entry, mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      var cx = mx - dy / L * L * 0.12, cy = my + dx / L * L * 0.12;
      var at = function (u) { var w = 1 - u; return [w * w * a[0] + 2 * w * u * cx + u * u * b[0], w * w * a[1] + 2 * w * u * cy + u * u * b[1]]; };
      ctx.save(); ctx.globalAlpha *= alpha;
      var gr = ctx.createLinearGradient(a[0], a[1], b[0], b[1]);
      var rgb = P3.rgbOf(s.v.color);
      gr.addColorStop(0, P3.css(rgb, 0.15)); gr.addColorStop(1, P3.css(rgb, 0.75));
      ctx.strokeStyle = gr; ctx.lineWidth = s.v.concept ? 1.3 : 1.8; if (s.v.concept) ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.quadraticCurveTo(cx, cy, b[0], b[1]); ctx.stroke(); ctx.setLineDash([]);
      for (var j = 0; j < 3; j++) {                    // three pulses travel towards the sphere
        var u = ((tnow * 0.42 + j / 3 + s.k * 0.137) % 1 + 1) % 1, p = at(u);
        ctx.globalAlpha = alpha * Math.sin(Math.PI * u) * (s.v.concept ? 0.7 : 1);
        ctx.fillStyle = s.v.color; ctx.beginPath(); ctx.arc(p[0], p[1], 1.6 + 1.4 * u, 0, 2 * Math.PI); ctx.fill();
      }
      ctx.restore();
    }
    function view(s, alpha) {                          // a view: the turning crystal, or a card that faces the viewer
      var k = s.q[3], dk = depth(s); alpha *= dk;
      beam(s, alpha);
      ctx.save(); ctx.globalAlpha *= alpha;
      var lx = s.q[0], ly;
      if (s.v.key === "crystal") {
        var F = FAMILIES[S.fam];
        P3.crystal(ctx, cam, F.cell, {at: s.p, s: 0.48 * F.size, spin: tnow * 0.45, atomScale: F.atomScale, dark: dark, colors: F.colors,
                                      alpha: S.famA, explode: S.explode, seed: 5});
        ly = s.q[1] - 0.82 * k;
      } else {
        var w = CARD[0] * k, h = CARD[1] * k;
        P3.rrect(ctx, s.q[0] - w, s.q[1] - h, 2 * w, 2 * h, Math.max(4, 0.08 * k));
        var g = ctx.createLinearGradient(s.q[0] - w, s.q[1] - h, s.q[0] + w, s.q[1] + h);
        g.addColorStop(0, dark ? "rgba(51,65,85,.78)" : "rgba(255,255,255,.9)"); g.addColorStop(1, dark ? "rgba(30,41,59,.62)" : "rgba(238,242,255,.72)");
        ctx.fillStyle = g; ctx.fill();
        ctx.lineWidth = s.v.concept ? 1.3 : 1.2; if (s.v.concept) ctx.setLineDash([5, 4]);
        ctx.strokeStyle = P3.css(P3.rgbOf(s.v.color), s.v.concept ? 0.9 : 0.6); ctx.stroke(); ctx.setLineDash([]);
        paintView(s.v, function (u, v) { return [s.q[0] + u * w * 0.86, s.q[1] - v * h * 0.84]; }, k * 0.62, dark);
        ly = s.q[1] - h - 6;
      }
      font(Math.max(9.5, Math.min(12, W / 52)));
      var tw = ctx.measureText(s.v.label).width;
      ctx.fillStyle = dark ? "rgba(203,213,225,.9)" : "rgba(51,65,85,.9)";
      ctx.fillText(s.v.label, Math.max(4, Math.min(lx - tw / 2, W - tw - 4)), Math.max(12, ly));
      ctx.restore();
    }

    orbitRing(false);
    sats.filter(function (s) { return s.q[2] < zc; }).sort(function (p, q) { return p.q[2] - q.q[2]; }).forEach(function (s) { view(s, 1); });
    sphereLayer(false);
    body();
    sphereLayer(true);
    orbitRing(true);
    font(Math.max(9.5, Math.min(12, W / 50)), 600);                                   // the name, inside the sphere
    var txt = "shared representation", ltw = ctx.measureText(txt).width;
    ctx.lineWidth = 3; ctx.lineJoin = "round"; ctx.strokeStyle = dark ? "rgba(17,20,23,.7)" : "rgba(255,255,255,.75)";   // legible over the markers
    ctx.strokeText(txt, C[0] - ltw / 2, C[1] + Rpx * 0.62);
    ctx.fillStyle = dark ? "rgba(199,210,254,.95)" : "rgba(67,56,202,.9)"; ctx.fillText(txt, C[0] - ltw / 2, C[1] + Rpx * 0.62);
    sats.filter(function (s) { return s.q[2] >= zc; }).sort(function (p, q) { return p.q[2] - q.q[2]; }).forEach(function (s) { view(s, 1); });
    if (caption && caption.textContent !== CAPTION) caption.textContent = CAPTION;
  }

  var running = false, visible = true;
  function frame(now) {
    tnow = frozen === null ? Math.max(0, (now - t0) / 1000) : frozen;   // a frame can be stamped just before t0
    yaw = 0.2 * Math.sin(tnow * 0.17) + dragYaw;
    pitch = -0.14 + 0.05 * Math.sin(tnow * 0.13) + dragPitch;
    draw();
    if (running) requestAnimationFrame(frame);
  }
  function start() { if (reduce || running || !visible || document.hidden) return; running = true; requestAnimationFrame(frame); }
  function stop() { running = false; }
  if (reduce) { yaw = 0.12; pitch = -0.14; }

  var drag = null;
  canvas.addEventListener("pointerdown", function (e) { drag = {x: e.clientX, y: e.clientY, yaw: dragYaw, pitch: dragPitch}; canvas.setPointerCapture(e.pointerId); canvas.classList.add("grabbing"); });
  canvas.addEventListener("pointermove", function (e) {
    if (!drag) return;
    dragYaw = drag.yaw + (e.clientX - drag.x) * 0.008;
    dragPitch = Math.max(-0.5, Math.min(0.45, drag.pitch + (e.clientY - drag.y) * 0.005));
    if (reduce) { yaw = 0.12 + dragYaw; pitch = -0.14 + dragPitch; draw(); }
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
