/* Reveals (mask-line rise, fade-rise, rule draw). DESIGN.md section 8: once per element,
   nothing animates on page load, and prefers-reduced-motion shows everything immediately. */
(() => {
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const targets = [...document.querySelectorAll(".mask, .rise, .draw")];
  if (reduce || !("IntersectionObserver" in window)) return;

  // Whatever is on screen at load is simply there: mark it before enabling transitions.
  const vh = innerHeight;
  targets.forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.top < vh && r.bottom > 0) el.classList.add("is-in");
  });
  root.classList.add("rv");
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: "0px 0px -12% 0px" });
  targets.filter((el) => !el.classList.contains("is-in")).forEach((el) => io.observe(el));

  // Content inside a panel or step that opens later must not stay hidden.
  document.addEventListener("toggle", (e) => {
    e.target.querySelectorAll?.(".rise, .mask").forEach((el) => el.classList.add("is-in"));
  }, true);
})();
