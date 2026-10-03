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
  if (window.document$ && typeof window.document$.subscribe === "function") window.document$.subscribe(external);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", external);
  else external();
})();
