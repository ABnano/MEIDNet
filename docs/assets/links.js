/* On the Hugging Face page the docs run inside a frame, where GitHub, doi.org or arXiv refuse to load:
   open every link that leaves this site in a new tab. */
(function () {
  function external() {
    document.querySelectorAll('a[href^="http"]').forEach(function (a) {
      try {
        if (new URL(a.href).origin !== location.origin) { a.target = "_blank"; a.rel = "noopener"; }
      } catch (e) { /* not a URL */ }
    });
  }
  function directApp() {          // inside the Hugging Face page: the same page at its own address
    var framed = false;
    try { framed = window.self !== window.top; } catch (e) { framed = true; }
    var host = document.querySelector(".md-copyright");
    if (!framed || !host || document.getElementById("direct-app")) return;
    var a = document.createElement("a");
    a.id = "direct-app"; a.href = location.href; a.target = "_blank"; a.rel = "noopener";
    a.textContent = "Open the direct app ↗"; a.title = "The same page, outside the Hugging Face frame";
    var d = document.createElement("div"); d.appendChild(a); host.appendChild(d);
  }
  if (window.document$ && typeof window.document$.subscribe === "function") { window.document$.subscribe(external); window.document$.subscribe(directApp); }
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { external(); directApp(); });
  else { external(); directApp(); }
})();
