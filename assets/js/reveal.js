/* Reveals (mask-line rise, fade-rise, rule draw) and the scroll-driven step list.
   DESIGN.md section 8: once per element, nothing animates on page load, and
   prefers-reduced-motion shows everything immediately. */
(() => {
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const targets = [...document.querySelectorAll(".mask, .rise, .draw")];

  if (!reduce && "IntersectionObserver" in window) {
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
    }, { rootMargin: "0px 0px -20% 0px" });
    targets.filter((el) => !el.classList.contains("is-in")).forEach((el) => io.observe(el));
  }

  // Step lists: the active row is a pure function of scroll position (row nearest
  // the viewport's middle). Hover takes over until the next scroll.
  const lists = [...document.querySelectorAll(".steps")];
  if (!lists.length) return;
  lists.forEach((l) => l.classList.add("is-driven"));

  const setActive = (list, row) => list.querySelectorAll(".step").forEach((s) => s.classList.toggle("is-active", s === row));

  let queued = false;
  const update = () => {
    queued = false;
    const mid = innerHeight * 0.55;
    lists.forEach((list) => {
      const rows = [...list.querySelectorAll(".step")];
      let best = rows[0], bestD = Infinity;
      rows.forEach((r) => {
        const b = r.getBoundingClientRect();
        const d = Math.abs(b.top + b.height / 2 - mid);
        if (d < bestD) { bestD = d; best = r; }
      });
      setActive(list, best);
    });
  };
  addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener("resize", update);
  lists.forEach((list) => list.querySelectorAll(".step").forEach((row) => {
    row.addEventListener("pointerenter", () => setActive(list, row));
  }));
  update();
})();
