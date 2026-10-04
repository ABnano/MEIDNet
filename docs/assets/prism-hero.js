/* MEIDNet Prism landing page: the molecular lettering of the headline and the 3D crystal scene of the hero.
   No libraries: the lettering is SVG built from stroke glyphs, the scene a small canvas renderer (painter's algorithm).
   The headline stays real text for search engines and screen readers; without JavaScript it shows as plain text. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";

  function isDark() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) return t === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  /* ═══════════ molecular lettering: bonds along the strokes, atoms at the joints ═══════════ */
  var ASC = 1.42, DESC = 0.48, PAD = 0.24, GAP = 0.36, U = 0.76;   // x-height = 1 unit; U = unit in em

  function arc(cx, cy, rx, ry, a0, a1, every) {
    var n = Math.max(8, Math.ceil(Math.abs(a1 - a0) / 6)), pts = [], beads = [];
    for (var i = 0; i <= n; i++) {
      var a = (a0 + (a1 - a0) * i / n) * Math.PI / 180;
      pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
    }
    var k = Math.max(1, Math.round(n * every / Math.abs(a1 - a0)));
    for (var j = 0; j <= n; j += k) beads.push(pts[j]);
    beads.push(pts[n]);
    return {pts: pts, beads: beads};
  }
  function line() { var p = Array.prototype.slice.call(arguments); return {pts: p, beads: p}; }
  function dot(x, y) { return {pts: [], beads: [[x, y]]}; }
  var ring = function () { return arc(0.5, 0.5, 0.5, 0.5, 0, 360, 72); };

  var G = {
    a: {w: 1.0, s: function () { return [ring(), line([1, 1], [1, 0])]; }},
    c: {w: 0.92, s: function () { return [arc(0.5, 0.5, 0.5, 0.5, 40, 320, 70)]; }},
    d: {w: 1.0, s: function () { return [ring(), line([1, ASC], [1, 0])]; }},
    e: {w: 1.0, s: function () { return [line([0.02, 0.5], [1, 0.5]), arc(0.5, 0.5, 0.5, 0.5, 0, 318, 80)]; }},
    i: {w: 0.2, s: function () { return [line([0.1, 0], [0.1, 1]), dot(0.1, 1.34)]; }},
    l: {w: 0.2, s: function () { return [line([0.1, 0], [0.1, 0.71], [0.1, ASC])]; }},
    m: {w: 1.3, s: function () {
      return [line([0, 0], [0, 1]), arc(0.325, 0.62, 0.325, 0.38, 180, 0, 90), line([0.65, 0.62], [0.65, 0]),
              arc(0.975, 0.62, 0.325, 0.38, 180, 0, 90), line([1.3, 0.62], [1.3, 0])]; }},
    o: {w: 1.0, s: function () { return [arc(0.5, 0.5, 0.5, 0.5, 90, 450, 60)]; }},
    r: {w: 0.68, s: function () { return [line([0, 0], [0, 1]), arc(0.42, 0.55, 0.42, 0.42, 180, 60, 60)]; }},
    s: {w: 0.82, s: function () { return [arc(0.41, 0.75, 0.36, 0.25, 20, 270, 85), arc(0.41, 0.25, 0.39, 0.25, 90, -160, 85)]; }},
    t: {w: 0.72, s: function () { return [line([0.28, 1.32], [0.28, 1], [0.28, 0]), line([0, 1], [0.66, 1])]; }},
    u: {w: 0.92, s: function () { return [line([0, 1], [0, 0.46]), arc(0.46, 0.46, 0.46, 0.46, 180, 360, 90), line([0.92, 1], [0.92, 0])]; }},
    v: {w: 0.92, s: function () { return [line([0, 1], [0.46, 0], [0.92, 1])]; }},
    y: {w: 0.92, s: function () { return [line([0, 1], [0.46, 0]), line([0.92, 1], [0.46, 0], [0.24, -0.48])]; }},
    A: {w: 1.16, s: function () { return [line([0, 0], [0.58, ASC], [1.16, 0]), line([0.25, 0.55], [0.91, 0.55])]; }},
    I: {w: 0.2, s: function () { return [line([0.1, 0], [0.1, 0.71], [0.1, ASC])]; }},
    " ": {w: 0.38, s: function () { return []; }}
  };

  var lettering = 0;
  function moleculeSvg(text, stops) {
    var id = "mol" + (++lettering), x = PAD, paths = [], beads = [];
    for (var c = 0; c < text.length; c++) {
      var g = G[text[c]];
      if (!g) return null;                       // a glyph we do not draw: keep the plain text
      g.s().forEach(function (st) {
        if (st.pts.length) paths.push(st.pts.map(function (p) { return [p[0] + x, p[1]]; }));
        st.beads.forEach(function (b) {
          var q = [b[0] + x, b[1]];
          if (!beads.some(function (o) { return Math.hypot(o[0] - q[0], o[1] - q[1]) < 0.06; })) beads.push(q);
        });
      });
      x += g.w + GAP;
    }
    var W = x - GAP + PAD, H = ASC + DESC + 2 * PAD;
    var Y = function (y) { return (ASC + PAD - y).toFixed(3); };
    var d = paths.map(function (p) { return "M" + p.map(function (q) { return q[0].toFixed(3) + " " + Y(q[1]); }).join("L"); }).join("");
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 " + W.toFixed(3) + " " + H.toFixed(3));
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    svg.style.width = (W * U).toFixed(3) + "em";
    svg.style.verticalAlign = (-(DESC + PAD) * U).toFixed(3) + "em";
    svg.innerHTML =
      '<defs><linearGradient id="' + id + 'g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="' + W.toFixed(2) + '" y2="0">' +
      stops.map(function (s) { return '<stop offset="' + s[0] + '" stop-color="' + s[1] + '"/>'; }).join("") + "</linearGradient>" +
      '<radialGradient id="' + id + 's" cx=".36" cy=".32" r=".68"><stop offset="0" stop-color="#fff" stop-opacity=".95"/>' +
      '<stop offset=".38" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>' +
      '<path class="mol-shadow" d="' + d + '" transform="translate(.05 .07)"/>' +
      '<path d="' + d + '" fill="none" stroke="url(#' + id + 'g)" stroke-width=".2" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="' + d + '" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width=".05" stroke-linecap="round" stroke-linejoin="round" transform="translate(-.03 -.04)"/>' +
      beads.map(function (b) {
        var cx = b[0].toFixed(3), cy = Y(b[1]);
        return '<circle cx="' + cx + '" cy="' + cy + '" r=".158" fill="url(#' + id + 'g)"/>' +
               '<circle cx="' + cx + '" cy="' + cy + '" r=".158" fill="url(#' + id + 's)"/>';
      }).join("");
    return svg;
  }

  var PALETTES = {
    a: [[0, "#2f6fe4"], [0.45, "#6366f1"], [0.8, "#8b5cf6"], [1, "#a855f7"]],
    b: [[0, "#2563eb"], [0.3, "#0e7490"], [0.55, "#0d9488"], [1, "#10b981"]]
  };
  document.querySelectorAll("[data-mol]").forEach(function (span) {
    var svg = moleculeSvg(span.textContent.trim(), PALETTES[span.getAttribute("data-mol")] || PALETTES.a);
    if (!svg) return;
    span.classList.add("mol-on");
    span.insertBefore(svg, span.firstChild);
  });

  /* ═══════════ the 3D scene: an ABX3 perovskite and what MEIDNet makes of it ═══════════ */
  var canvas = document.getElementById("hero3d");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // crystal: the cubic ABX3 cell, A cations on the corners, the BX6 octahedron in the centre (X on the face centres)
  var a = 1.25, B = [[0, 0, 0]], A = [], EDGES = [], FACES = [];
  var X = [[a, 0, 0], [-a, 0, 0], [0, a, 0], [0, -a, 0], [0, 0, a], [0, 0, -a]];
  [-a, a].forEach(function (x) { [-a, a].forEach(function (y) { [-a, a].forEach(function (z) { A.push([x, y, z]); }); }); });
  A.forEach(function (p) { A.forEach(function (q) {     // the cube: corners one lattice step apart
    var d = Math.abs(p[0] - q[0]) + Math.abs(p[1] - q[1]) + Math.abs(p[2] - q[2]);
    if (Math.abs(d - 2 * a) < 1e-6 && p < q) EDGES.push([p, q]);
  }); });
  [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 4, 2], [1, 3, 4], [1, 5, 3], [1, 2, 5]].forEach(function (f) {
    FACES.push([X[f[0]], X[f[1]], X[f[2]]]);
  });

  // panels behind the crystal: centre, half sizes, rotation about y, what they show
  function rng(seed) { return function () { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }; }
  var r = rng(7), LATENT = [];
  for (var i = 0; i < 90; i++) {                 // paired points: a structure (teal) and its properties (violet), close together
    var t = r() * 2 - 1, u = r() * 2 - 1, cx = 0.75 * t, cy = 0.55 * Math.sin(2.2 * t) * 0.8 + 0.25 * u;
    LATENT.push({u: cx, v: cy, du: (r() - 0.5) * 0.09, dv: (r() - 0.5) * 0.09, c: t});
  }
  var GRAPH = {n: [[-0.62, -0.35], [-0.22, 0.42], [0.18, -0.12], [0.6, 0.38], [0.52, -0.5], [-0.05, -0.62], [-0.68, 0.38]],
               e: [[0, 1], [1, 2], [2, 3], [2, 4], [0, 5], [5, 2], [1, 6], [6, 0], [3, 4]]};
  var PANELS = [
    {c: [-2.2, 1.5, -2.4], h: [0.95, 0.68], ry: 0.5, kind: "graph", label: "crystal graph"},
    {c: [1.45, 2.0, -2.9], h: [1.15, 0.75], ry: -0.32, kind: "latent", label: "latent space z ∈ ℝ¹²⁸"},
    {c: [2.25, -1.25, -1.6], h: [0.8, 0.56], ry: -0.62, kind: "property", label: "property: band gap"}
  ];

  var W = 0, H = 0, DPR = 1, yaw = 0, pitch = 0, dragYaw = 0, dragPitch = 0, t0 = performance.now();
  function resize() {
    var b = canvas.getBoundingClientRect();
    DPR = Math.min(2, window.devicePixelRatio || 1);
    W = Math.max(1, b.width); H = Math.max(1, b.height);
    canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
    draw();
  }
  function proj(p) {
    var cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    var x1 = p[0] * cy + p[2] * sy, z1 = -p[0] * sy + p[2] * cy, y1 = p[1];
    var y2 = y1 * cp - z1 * sp, z2 = y1 * sp + z1 * cp;
    var D = 9, F = Math.min(W, H * 1.1) * D / 8.3, k = F / (D - z2);
    return [W * 0.52 + x1 * k, H * 0.5 - y2 * k, z2, k];
  }
  function panelPoint(P, u, v, w) {        // panel-local (u, v in [-1, 1]) to world
    var c = Math.cos(P.ry), sn = Math.sin(P.ry), x = u * P.h[0], y = v * P.h[1];
    return [P.c[0] + x * c + (w || 0) * sn, P.c[1] + y, P.c[2] - x * sn + (w || 0) * c];
  }
  function poly(pts) { ctx.beginPath(); pts.forEach(function (p, j) { j ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); }); ctx.closePath(); }

  function sphere(p, rad, col, dark) {
    var q = proj(p), R = rad * q[3];
    var g = ctx.createRadialGradient(q[0] - R * 0.38, q[1] - R * 0.42, R * 0.08, q[0], q[1], R);
    g.addColorStop(0, "#ffffff"); g.addColorStop(0.22, col[0]); g.addColorStop(0.72, col[1]); g.addColorStop(1, col[2]);
    ctx.beginPath(); ctx.arc(q[0], q[1], R, 0, 2 * Math.PI);
    ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = 0.8; ctx.strokeStyle = dark ? "rgba(0,0,0,.35)" : "rgba(15,23,42,.12)"; ctx.stroke();
  }

  function drawPanel(P, dark) {
    var corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(function (c) { return proj(panelPoint(P, c[0], c[1])); });
    poly(corners);
    var g = ctx.createLinearGradient(corners[3][0], corners[3][1], corners[1][0], corners[1][1]);
    g.addColorStop(0, dark ? "rgba(51,65,85,.55)" : "rgba(255,255,255,.78)");
    g.addColorStop(1, dark ? "rgba(30,41,59,.28)" : "rgba(226,232,255,.42)");
    ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = 1; ctx.strokeStyle = dark ? "rgba(148,163,184,.45)" : "rgba(148,163,184,.55)"; ctx.stroke();
    var L = function (u, v) { return proj(panelPoint(P, u, v)); };
    if (P.kind === "graph") {
      ctx.lineWidth = 1.4; ctx.strokeStyle = dark ? "rgba(148,163,184,.75)" : "rgba(100,116,139,.6)";
      GRAPH.e.forEach(function (e) { var a = L(GRAPH.n[e[0]][0] * 0.8, GRAPH.n[e[0]][1] * 0.8), b = L(GRAPH.n[e[1]][0] * 0.8, GRAPH.n[e[1]][1] * 0.8);
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); });
      GRAPH.n.forEach(function (n, j) { var q = L(n[0] * 0.8, n[1] * 0.8);
        ctx.beginPath(); ctx.arc(q[0], q[1], Math.max(2.5, 0.07 * q[3]), 0, 2 * Math.PI);
        ctx.fillStyle = ["#3b82f6", "#14b8a6", "#8b5cf6"][j % 3]; ctx.fill(); });
    } else if (P.kind === "latent") {
      LATENT.forEach(function (p) {
        var a = L(p.u, p.v), b = L(p.u + p.du, p.v + p.dv), rad = Math.max(1.4, 0.028 * a[3]);
        ctx.strokeStyle = dark ? "rgba(203,213,225,.3)" : "rgba(100,116,139,.28)"; ctx.lineWidth = 0.8;
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
        var h = 175 + (p.c + 1) * 50;
        ctx.fillStyle = "hsla(" + h + ",70%," + (dark ? 62 : 48) + "%,.9)";
        ctx.beginPath(); ctx.arc(a[0], a[1], rad, 0, 2 * Math.PI); ctx.fill();
        ctx.fillStyle = "hsla(" + (h + 80) + ",70%," + (dark ? 70 : 58) + "%,.85)";
        ctx.beginPath(); ctx.arc(b[0], b[1], rad * 0.85, 0, 2 * Math.PI); ctx.fill();
      });
    } else {
      ctx.strokeStyle = dark ? "rgba(148,163,184,.6)" : "rgba(100,116,139,.55)"; ctx.lineWidth = 1;
      var o = L(-0.85, -0.7), xe = L(0.85, -0.7), ye = L(-0.85, 0.75);
      ctx.beginPath(); ctx.moveTo(ye[0], ye[1]); ctx.lineTo(o[0], o[1]); ctx.lineTo(xe[0], xe[1]); ctx.stroke();
      ctx.beginPath();
      for (var j = 0; j <= 60; j++) {
        var u = -0.85 + 1.7 * j / 60, xg = (u + 0.85) * 3,      // band gap axis, 0 to ~5 eV
            yv = Math.exp(-Math.pow((xg - 1.6) / 0.6, 2)) + 0.55 * Math.exp(-Math.pow((xg - 3.4) / 0.8, 2)),
            q = L(u, -0.7 + 1.3 * yv);
        j ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]);
      }
      ctx.strokeStyle = "#8b5cf6"; ctx.lineWidth = 2; ctx.stroke();
      var tu = -0.85 + 2.0 / 3, a = L(tu, -0.7), b = L(tu, 0.7);   // the target, 2 eV
      ctx.setLineDash([4, 3]); ctx.strokeStyle = "#e87ba4"; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); ctx.setLineDash([]);
    }
    var tl = corners[3];
    ctx.font = "500 " + Math.round(Math.max(10, Math.min(12.5, W / 46))) + "px 'IBM Plex Mono', ui-monospace, monospace";
    ctx.fillStyle = dark ? "rgba(203,213,225,.85)" : "rgba(71,85,105,.9)";
    ctx.fillText(P.label, Math.max(4, Math.min(tl[0] + 2, W - ctx.measureText(P.label).width - 4)), tl[1] - 7);   // inside the canvas
  }

  function draw() {
    if (!W) return;
    var dark = isDark();
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    // floor grid
    ctx.lineWidth = 1; ctx.strokeStyle = dark ? "rgba(148,163,184,.12)" : "rgba(100,116,139,.14)";
    for (var g = -3; g <= 3; g += 0.75) {
      var a = proj([g, -2.05, -3]), b = proj([g, -2.05, 3]), c = proj([-3, -2.05, g]), d = proj([3, -2.05, g]);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.moveTo(c[0], c[1]); ctx.lineTo(d[0], d[1]); ctx.stroke();
    }
    // the cation's shadow on the floor
    var f = proj([0, -2.05, 0]), sh = ctx.createRadialGradient(f[0], f[1], 0, f[0], f[1], 2.0 * f[3]);
    sh.addColorStop(0, dark ? "rgba(0,0,0,.35)" : "rgba(30,41,90,.07)"); sh.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = sh; ctx.beginPath(); ctx.ellipse(f[0], f[1], 2.0 * f[3], 0.62 * f[3], 0, 0, 2 * Math.PI); ctx.fill();
    // panels, far first
    PANELS.slice().sort(function (p, q) { return proj(p.c)[2] - proj(q.c)[2]; }).forEach(function (P) { drawPanel(P, dark); });
    // crystal: faces and atoms sorted by depth
    var items = [];
    FACES.forEach(function (fc) {
      var q = fc.map(proj), z = (q[0][2] + q[1][2] + q[2][2]) / 3;
      items.push({z: z, f: fc, q: q});
    });
    B.forEach(function (p) { items.push({z: proj(p)[2], p: p, rad: 0.27, col: ["#93c5fd", "#3b82f6", "#1e3a8a"]}); });
    X.forEach(function (p) { items.push({z: proj(p)[2], p: p, rad: 0.2, col: ["#99f6e4", "#14b8a6", "#115e59"]}); });
    A.forEach(function (p) { items.push({z: proj(p)[2], p: p, rad: 0.25, col: ["#c4b5fd", "#8b5cf6", "#3b0764"]}); });
    EDGES.forEach(function (e) { var q = [proj(e[0]), proj(e[1])]; items.push({z: (q[0][2] + q[1][2]) / 2 - 0.4, line: q}); });
    items.sort(function (m, n) { return m.z - n.z; });
    var Ldir = [-0.45, 0.7, 0.55];
    items.forEach(function (it) {
      if (it.p) return sphere(it.p, it.rad, it.col, dark);
      if (it.line) {
        ctx.lineWidth = 1.2; ctx.strokeStyle = dark ? "rgba(148,163,184,.45)" : "rgba(100,116,139,.45)";
        ctx.beginPath(); ctx.moveTo(it.line[0][0], it.line[0][1]); ctx.lineTo(it.line[1][0], it.line[1][1]); ctx.stroke(); return;
      }
      var v = it.f, e1 = [v[1][0] - v[0][0], v[1][1] - v[0][1], v[1][2] - v[0][2]], e2 = [v[2][0] - v[0][0], v[2][1] - v[0][1], v[2][2] - v[0][2]];
      var n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]], nl = Math.hypot(n[0], n[1], n[2]);
      var cy = Math.cos(yaw), sy = Math.sin(yaw), nx = (n[0] * cy + n[2] * sy) / nl, nz = (-n[0] * sy + n[2] * cy) / nl, ny = n[1] / nl;
      var lit = Math.abs(nx * Ldir[0] + ny * Ldir[1] + nz * Ldir[2]);
      poly(it.q);
      var gr = ctx.createLinearGradient(it.q[0][0], it.q[0][1], it.q[2][0], it.q[2][1]);
      gr.addColorStop(0, dark ? "rgba(147,197,253," + (0.1 + 0.22 * lit).toFixed(3) + ")" : "rgba(255,255,255," + (0.25 + 0.45 * lit).toFixed(3) + ")");
      gr.addColorStop(1, dark ? "rgba(59,130,246," + (0.08 + 0.14 * lit).toFixed(3) + ")" : "rgba(129,161,250," + (0.12 + 0.22 * lit).toFixed(3) + ")");
      ctx.fillStyle = gr; ctx.fill();
      ctx.lineWidth = 1; ctx.strokeStyle = dark ? "rgba(191,219,254,.5)" : "rgba(255,255,255,.95)"; ctx.stroke();
      ctx.lineWidth = 0.6; ctx.strokeStyle = dark ? "rgba(96,165,250,.35)" : "rgba(99,102,241,.25)"; ctx.stroke();
    });
  }

  var running = false, visible = true;
  function frame(now) {
    var t = (now - t0) / 1000;
    yaw = -0.5 + 0.38 * Math.sin(t * 0.21) + dragYaw;
    pitch = -0.33 + 0.05 * Math.sin(t * 0.16) + dragPitch;
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
  resize();
  start();
})();
