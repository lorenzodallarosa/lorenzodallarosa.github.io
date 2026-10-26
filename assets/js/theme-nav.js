/* Top bar inversion over dark sections, the running section counter, the active
   nav link and the mobile menu. Everything is derived from the current scroll
   position, so scrolling back reverses it exactly. */
(() => {
  const bar = document.querySelector(".bar");
  const counter = document.querySelector(".counter");
  const num = counter && counter.querySelector(".c-num");
  const name = counter && counter.querySelector(".c-name");
  const sections = [...document.querySelectorAll("main > section[data-theme]")];
  const links = [...document.querySelectorAll(".bar-nav a")];
  if (!bar || !sections.length) return;

  const at = (y) => sections.find((s) => {
    const r = s.getBoundingClientRect();
    return r.top <= y && r.bottom > y;
  });
  const tone = (s) => (s && s.dataset.theme === "dark" ? "dark" : "light");

  let shown = "";
  let queued = false;
  const update = () => {
    queued = false;
    bar.dataset.on = tone(at(bar.offsetHeight / 2));
    if (counter) {
      counter.dataset.on = tone(at(innerHeight - 28));
      const cur = at(innerHeight / 2) || sections[0];
      const i = sections.indexOf(cur);
      if (cur.id !== shown) {
        shown = cur.id;
        num.textContent = String(i + 1).padStart(2, "0");
        name.textContent = cur.dataset.name || "";
        num.classList.remove("swap");
        void num.offsetWidth;
        num.classList.add("swap");
      }
      links.forEach((a) => {
        const id = a.getAttribute("href").slice(1);
        const on = id === cur.id || (id === "work" && cur.id === "top" && scrollY > 200);
        a.toggleAttribute("aria-current", on);
        if (on) a.setAttribute("aria-current", "true");
      });
    }
  };
  addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener("resize", update);
  update();

  // Mobile menu: plain text "Menu" opening a full-screen cream overlay.
  const btn = document.querySelector(".bar-menu");
  const menu = document.getElementById("menu");
  if (!btn || !menu) return;
  const set = (open) => {
    menu.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
    btn.textContent = open ? "Close" : "Menu";
    document.body.style.overflow = open ? "hidden" : "";
    if (open) bar.dataset.on = "light";
    else update();
  };
  btn.addEventListener("click", () => set(menu.hidden));
  menu.addEventListener("click", (e) => { if (e.target.closest("a")) set(false); });
  addEventListener("keydown", (e) => { if (e.key === "Escape" && !menu.hidden) { set(false); btn.focus(); } });
})();
