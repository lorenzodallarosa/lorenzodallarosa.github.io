/* Renders the $...$ equations marked by the generator as <span class="math">. KaTeX is
   fetched only when an equation is about to scroll into view. */
(() => {
  const all = [...document.querySelectorAll(".math")];
  if (!all.length) return;
  const BASE = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/";
  let ready;
  const katexReady = () => (ready ??= new Promise((ok, fail) => {
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = BASE + "katex.min.css";
    const js = document.createElement("script");
    js.src = BASE + "katex.min.js";
    js.onload = ok;
    js.onerror = fail;
    document.head.append(css, js);
  }));
  const render = (els) => katexReady().then(() => els.forEach((el) => {
    if (el.dataset.done) return;
    el.dataset.done = "1";
    katex.render(el.textContent, el, { throwOnError: false, output: "html" });
  })).catch(() => {});

  // Equations inside closed steps or hidden panels have no box, so they only intersect
  // once their step or panel is opened.
  const io = new IntersectionObserver((es) => {
    const vis = es.filter((e) => e.isIntersecting).map((e) => e.target);
    vis.forEach((el) => io.unobserve(el));
    if (vis.length) render(vis);
  }, { rootMargin: "200px 0px" });
  all.forEach((el) => io.observe(el));
})();
