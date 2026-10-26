/* Renders the $...$ equations marked by the generator as <span class="math">. */
(() => {
  if (!window.katex) return;
  document.querySelectorAll(".math").forEach((el) => {
    katex.render(el.textContent, el, { throwOnError: false, output: "html" });
  });
})();
