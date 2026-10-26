/* Small page behaviours: the obfuscated email link and the smaller-project panels. */
(() => {
  // Email: stored reversed and base64-encoded in data attributes, assembled on load.
  const dec = (s) => atob(s).split("").reverse().join("");
  document.querySelectorAll(".js-mail").forEach((a) => {
    try {
      const addr = `${dec(a.dataset.u)}@${dec(a.dataset.d)}`;
      a.href = `mailto:${addr}`;
      a.querySelector(".js-mail-t").textContent = addr;
    } catch {
      /* keep the "name [at] domain [dot] com" fallback */
    }
  });

  // Smaller projects: one card opens its full-width panel; the others close.
  const buttons = [...document.querySelectorAll(".card-btn")];
  const panels = [...document.querySelectorAll(".panel")];
  if (!buttons.length) return;
  document.documentElement.classList.add("has-panels");

  const open = (slug, scroll) => {
    panels.forEach((p) => { p.hidden = p.dataset.slug !== slug; });
    buttons.forEach((b) => b.setAttribute("aria-expanded", String(b.dataset.panel === slug)));
    const panel = panels.find((p) => p.dataset.slug === slug);
    if (panel && scroll) panel.scrollIntoView({ block: "start" });
  };
  const closeAll = () => open(null, false);

  panels.forEach((p) => { p.hidden = true; });
  buttons.forEach((b) => b.addEventListener("click", () => {
    if (b.getAttribute("aria-expanded") === "true") closeAll();
    else open(b.dataset.panel, true);
  }));
  panels.forEach((p) => p.querySelector("[data-close]").addEventListener("click", () => {
    const btn = buttons.find((b) => b.dataset.panel === p.dataset.slug);
    closeAll();
    if (btn) { btn.focus(); btn.scrollIntoView({ block: "center" }); }
  }));

  // Links to a small project (e.g. from the Software panel) open its panel.
  const fromHash = () => {
    const slug = decodeURIComponent(location.hash.slice(1));
    if (panels.some((p) => p.dataset.slug === slug)) open(slug, true);
  };
  addEventListener("hashchange", fromHash);
  fromHash();
})();
